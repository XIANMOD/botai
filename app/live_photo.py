from pathlib import Path
import subprocess, uuid, zipfile, shutil
from PIL import Image
from .config import settings

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-1800:])
    return p

def make_live_photo(video_path: Path, out_dir: Path):
    """
    Builds a Live Photo-style asset pair: JPEG key photo + short MOV.
    Apple Photos import compatibility can vary; see README.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    asset_id = str(uuid.uuid4()).upper()
    duration = max(1.0, min(settings.live_photo_seconds, 3.0))
    probe = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)])
    total = float(probe.stdout.strip() or "0")
    if total <= 0.2:
        raise RuntimeError("Durasi video tidak valid.")
    start = max(0.0, (total - duration) / 2.0)
    mov = out_dir / "DIMZ_LivePhoto.mov"
    jpg = out_dir / "DIMZ_KeyPhoto.jpg"
    run(["ffmpeg", "-y", "-ss", str(start), "-i", str(video_path), "-t", str(duration),
         "-an", "-vf", "scale='min(1920,iw)':-2,fps=30", "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mov)])
    frame_time = min(duration / 2, 1.0)
    run(["ffmpeg", "-y", "-ss", str(start + frame_time), "-i", str(video_path),
         "-frames:v", "1", str(jpg)])
    # Shared Apple content identifier is necessary but not sufficient for Photos pairing.
    exiftool = shutil.which("exiftool")
    if exiftool:
        for media in (mov, jpg):
            run([exiftool, "-overwrite_original",
                 f"-Keys:ContentIdentifier={asset_id}", f"-ItemList:ContentIdentifier={asset_id}",
                 str(media)])
    readme = out_dir / "IMPORT.txt"
    readme.write_text(
        "DIMZ AI RESIZER - Live Photo asset pair\\n"
        f"Asset identifier: {asset_id}\\n"
        "Files: DIMZ_KeyPhoto.jpg + DIMZ_LivePhoto.mov\\n\\n"
        "This package contains a paired still/video export. Apple Photos requires a valid "
        "Apple Live Photo metadata structure and may not recognize a generic pair after "
        "saving from Files. If it does not appear as Live Photo, import/convert the pair "
        "with a trusted iOS Live Photo creator app. The bot does not claim guaranteed "
        "native Photos pairing.\\n", encoding="utf-8")
    archive = out_dir / "DIMZ_LivePhoto_Pair.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(jpg, jpg.name)
        z.write(mov, mov.name)
        z.write(readme, readme.name)
    return archive
