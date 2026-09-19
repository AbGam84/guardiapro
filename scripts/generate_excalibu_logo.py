"""Regenera assets de marca Excalibu Sentinel."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "static"
MARK_SVG = OUT / "excalibu-mark.svg"


def main() -> None:
    if not MARK_SVG.exists():
        print("Falta excalibu-mark.svg")
        return
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Instale Pillow para PNG")
        return
    # PNG de respaldo desde SVG simplificado si no hay mark png
    mark = OUT / "excalibu-mark.png"
    if mark.exists():
        img = Image.open(mark).convert("RGBA")
        for size in (192, 512):
            img.resize((size, size), Image.Resampling.LANCZOS).save(OUT / f"excalibu-icon-{size}.png")
        img.resize((64, 64), Image.Resampling.LANCZOS).save(OUT / "favicon.png")
        img.save(OUT / "excalibu-logo.png")
    print("Assets OK:", OUT)


if __name__ == "__main__":
    main()
