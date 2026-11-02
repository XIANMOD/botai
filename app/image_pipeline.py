from pathlib import Path
from PIL import Image, ImageOps, ImageFilter
from openai import OpenAI
import base64
from .config import settings
from .ratios import target_size

def prepare_canvas(source_path: Path, ratio_name: str, canvas_path: Path, mask_path: Path):
    src = ImageOps.exif_transpose(Image.open(source_path)).convert("RGB")
    w, h = src.size
    out_w, out_h = target_size(w, h, ratio_name)
    # Scale down only if required; never upscale the source before AI.
    scale = min(1.0, out_w / w, out_h / h)
    sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
    src = src.resize((sw, sh), Image.Resampling.LANCZOS)
    left, top = (out_w - sw) // 2, (out_h - sh) // 2

    canvas = Image.new("RGB", (out_w, out_h), (24, 24, 24))
    canvas.paste(src, (left, top))
    # Alpha=255 protects original pixels; alpha=0 marks areas for AI edit.
    mask = Image.new("RGBA", (out_w, out_h), (255, 255, 255, 0))
    protected = Image.new("RGBA", (sw, sh), (255, 255, 255, 255))
    mask.paste(protected, (left, top))
    canvas.save(canvas_path, "PNG")
    mask.save(mask_path, "PNG")
    return (w, h), (out_w, out_h)

def ai_outpaint(source_path: Path, ratio_name: str, output_path: Path):
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY belum diisi. Tambahkan API key di Railway Variables.")
    canvas_path = output_path.with_name("canvas.png")
    mask_path = output_path.with_name("mask.png")
    original_size, final_size = prepare_canvas(source_path, ratio_name, canvas_path, mask_path)

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = (
        "Photorealistic image outpainting. Extend only the transparent/masked empty canvas "
        "around the protected original photograph. Preserve the original scene, objects, "
        "people, faces, signs, text, colors, lighting, camera perspective and composition. "
        "Do not redesign, beautify, stylize, or alter the protected original area. "
        "Continue the same real environment naturally into the empty areas with consistent "
        "perspective, texture, noise, focus, exposure and night/day lighting. "
        "No blur panels, no borders, no frames, no artificial gradients, no added text, "
        "no watermarks. Seamless realistic photographic continuation."
    )
    with open(canvas_path, "rb") as img, open(mask_path, "rb") as mask:
        result = client.images.edit(
            model=settings.image_model,
            image=img,
            mask=mask,
            prompt=prompt,
            size=f"{canvas_path_size(canvas_path)[0]}x{canvas_path_size(canvas_path)[1]}",
            quality=settings.image_quality,
            output_format="png",
        )
    data = result.data[0].b64_json
    if not data:
        raise RuntimeError("AI tidak mengembalikan gambar. Coba ulangi.")
    output_path.write_bytes(base64.b64decode(data))
    # Final safety resize to exact requested aspect if API rounds dimensions.
    im = Image.open(output_path).convert("RGB")
    # 19:6 is 3.166:1, slightly wider than the provider's 3:1 limit.
    # Extend only the outermost edge pixels to reach the exact requested ratio.
    if ratio_name == "19:6":
        target_w = round(im.height * 19 / 6)
        extra = max(0, target_w - im.width)
        if extra:
            left = extra // 2
            right = extra - left
            lstrip = im.crop((0, 0, 1, im.height)).resize((left, im.height))
            rstrip = im.crop((im.width - 1, 0, im.width, im.height)).resize((right, im.height))
            final = Image.new("RGB", (target_w, im.height))
            final.paste(lstrip, (0, 0))
            final.paste(im, (left, 0))
            final.paste(rstrip, (left + im.width, 0))
            im = final
    im.save(output_path, "PNG")
    canvas_path.unlink(missing_ok=True)
    mask_path.unlink(missing_ok=True)
    return output_path

def canvas_path_size(path):
    with Image.open(path) as im:
        return im.size
