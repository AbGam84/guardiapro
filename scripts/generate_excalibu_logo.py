"""Regenera assets de marca Excalibu Sentinel."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "static"
MARK_SVG = OUT / "excalibu-mark.svg"


def _fallback_mark() -> "Image.Image":
    from PIL import Image, ImageDraw

    size = 512
    img = Image.new("RGBA", (size, size), (10, 15, 24, 255))
    draw = ImageDraw.Draw(img)
    r = 108
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=(10, 15, 24, 255))
    cx, cy = size // 2, size // 2
    draw.polygon(
        [(cx, 64), (392, 148), (372, 320), (cx, 448), (140, 320), (120, 148)],
        fill=(15, 23, 36, 255),
        outline=(255, 176, 32, 255),
    )
    draw.polygon([(cx, 88), (cx + 22, 196), (cx, 432), (cx - 22, 196)], fill=(18, 196, 160, 255))
    draw.rectangle((cx - 34, 196, cx + 34, 234), fill=(255, 140, 26, 255))
    draw.ellipse((cx - 14, 240, cx + 14, 268), fill=(10, 15, 24, 255), outline=(255, 176, 32, 255), width=4)
    return img


def main() -> None:
    try:
        from PIL import Image
    except ImportError:
        print("Instale Pillow: pip install Pillow")
        return

    mark = OUT / "excalibu-mark.png"
    if mark.exists():
        img = Image.open(mark).convert("RGBA")
    else:
        img = _fallback_mark()
        img.save(mark)
        print("Generado excalibu-mark.png (fallback)")

    for size in (192, 512):
        img.resize((size, size), Image.Resampling.LANCZOS).save(OUT / f"excalibu-icon-{size}.png")
    img.resize((64, 64), Image.Resampling.LANCZOS).save(OUT / "favicon.png")
    img.save(OUT / "excalibu-logo.png")
    print("Assets OK:", OUT)


if __name__ == "__main__":
    main()
