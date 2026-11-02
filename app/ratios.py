from fractions import Fraction

RATIOS = {
    "9:16": Fraction(9, 16),
    "16:9": Fraction(16, 9),
    "19:6": Fraction(19, 6),
    "1:1": Fraction(1, 1),
    "4:5": Fraction(4, 5),
    "3:4": Fraction(3, 4),
}

def target_size(width: int, height: int, ratio_name: str, max_side: int = 2560):
    ratio = RATIOS[ratio_name]
    # GPT Image 2.5 currently accepts aspect ratios only up to 3:1.
    # For 19:6, create a 3:1 AI canvas then add a narrow natural edge extension.
    ai_ratio = min(float(ratio), 3.0)
    if width / height > ai_ratio:
        out_w, out_h = width, round(width / ai_ratio)
    else:
        out_h, out_w = height, round(height * ai_ratio)
    scale = min(1.0, max_side / max(out_w, out_h))
    out_w, out_h = int(out_w * scale), int(out_h * scale)
    out_w = max(16, (out_w // 16) * 16)
    out_h = max(16, (out_h // 16) * 16)
    return out_w, out_h
