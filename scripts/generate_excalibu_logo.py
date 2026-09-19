"""Regenera assets de marca Excalibu Sentinel (SVG → PNG)."""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "static"
MARK_SVG = OUT / "excalibu-mark.svg"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _teal(t: float = 0.5) -> tuple[int, int, int, int]:
    return (
        int(_lerp(94, 18, t)),
        int(_lerp(234, 196, t)),
        int(_lerp(212, 160, t)),
        255,
    )


def _gold(t: float = 0.5) -> tuple[int, int, int, int]:
    return (
        int(_lerp(255, 255, t)),
        int(_lerp(209, 140, t)),
        int(_lerp(102, 26, t)),
        255,
    )


def _draw_mark(size: int = 512):
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (10, 15, 24, 255))
    draw = ImageDraw.Draw(img)
    s = size / 512.0

    def sc(x: float, y: float) -> tuple[float, float]:
        return x * s, y * s

    # Fondo redondeado
    pad = int(4 * s)
    draw.rounded_rectangle((pad, pad, size - pad, size - pad), radius=int(108 * s), fill=(10, 15, 24, 255))

    cx, cy = sc(256, 268)

    # Arco GPS
    bbox = (cx - 168 * s, cy - 168 * s, cx + 168 * s, cy + 168 * s)
    draw.arc(bbox, start=200, end=340, fill=(18, 196, 160, 70), width=max(2, int(3 * s)))
    for px, py, col in [(108, 320, _teal()), (256, 198, _gold()), (404, 320, _teal())]:
        x, y = sc(px, py)
        r = int(10 * s)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=col)

    # Escudo
    shield = [
        sc(256, 56),
        sc(404, 148),
        sc(384, 332),
        sc(256, 468),
        sc(128, 332),
        sc(108, 148),
    ]
    draw.polygon(shield, fill=(18, 26, 40, 255), outline=_gold(0.3), width=max(4, int(14 * s)))

    gx, gy = sc(256, 248)
    # Torso guardia
    torso = [
        (gx - 78 * s, gy + 52 * s),
        (gx - 78 * s, gy + 8 * s),
        (gx - 44 * s, gy - 6 * s),
        (gx + 44 * s, gy - 6 * s),
        (gx + 78 * s, gy + 8 * s),
        (gx + 78 * s, gy + 52 * s),
        (gx + 62 * s, gy + 118 * s),
        (gx - 62 * s, gy + 118 * s),
    ]
    draw.polygon(torso, fill=_teal(0.4))
    # Cabeza
    hx, hy = sc(256, 196)
    draw.ellipse((hx - 30 * s, hy - 32 * s, hx + 30 * s, hy + 32 * s), fill=(212, 184, 150, 255))
    # Gorra
    cap = [
        (hx - 38 * s, hy - 10 * s),
        (hx + 38 * s, hy - 10 * s),
        (hx + 34 * s, hy - 36 * s),
        (hx - 34 * s, hy - 36 * s),
    ]
    draw.polygon(cap, fill=(30, 41, 59, 255))
    draw.ellipse((hx - 42 * s, hy - 14 * s, hx + 42 * s, hy + 6 * s), fill=(51, 65, 85, 255))
    draw.rounded_rectangle(
        (hx - 36 * s, hy - 18 * s, hx + 36 * s, hy - 8 * s),
        radius=int(3 * s),
        fill=_gold(0.2),
    )
    # Placa EX
    draw.rounded_rectangle(
        (gx - 22 * s, gy + 18 * s, gx + 22 * s, gy + 52 * s),
        radius=int(6 * s),
        fill=_gold(0.5),
    )
    # Linterna
    draw.rounded_rectangle(
        (gx + 44 * s, gy + 28 * s, gx + 68 * s, gy + 80 * s),
        radius=int(4 * s),
        fill=(100, 116, 139, 255),
    )
    draw.polygon(
        [
            (gx + 68 * s, gy + 38 * s),
            (gx + 92 * s, gy + 28 * s),
            (gx + 92 * s, gy + 52 * s),
            (gx + 68 * s, gy + 52 * s),
        ],
        fill=(254, 240, 138, 190),
    )

    # Check verificado
    ckx, cky = sc(392, 392)
    cr = int(44 * s)
    draw.ellipse((ckx - cr, cky - cr, ckx + cr, cky + cr), fill=(10, 15, 24, 255), outline=_teal(0.2), width=max(3, int(5 * s)))
    draw.line(
        [(ckx - 20 * s, cky), (ckx - 6 * s, cky + 14 * s), (ckx + 24 * s, cky - 16 * s)],
        fill=(61, 214, 140, 255),
        width=max(4, int(9 * s)),
        joint="curve",
    )

    # Mini QR
    qx, qy = sc(88, 392)
    qs = int(56 * s)
    draw.rounded_rectangle((qx, qy, qx + qs, qy + qs), radius=int(8 * s), outline=(62, 181, 224, 255), width=max(2, int(3 * s)))
    cell = int(14 * s)
    for ox, oy in [(8, 8), (34, 8), (8, 34)]:
        draw.rounded_rectangle(
            (qx + ox * s, qy + oy * s, qx + (ox + 14) * s, qy + (oy + 14) * s),
            radius=int(2 * s),
            fill=_teal(0.3),
        )
    draw.rectangle((qx + 28 * s, qy + 28 * s, qx + 36 * s, qy + 36 * s), fill=_gold(0.6))
    draw.rectangle((qx + 40 * s, qy + 40 * s, qx + 48 * s, qy + 48 * s), fill=_gold(0.6))

    return img


def main() -> None:
    try:
        from PIL import Image
    except ImportError:
        print("Instale Pillow: pip install Pillow")
        return

    if not MARK_SVG.exists():
        print("Falta", MARK_SVG)

    img = _draw_mark(512)
    img.save(OUT / "excalibu-mark.png")
    img.save(OUT / "excalibu-logo.png")

    for size in (192, 512):
        img.resize((size, size), Image.Resampling.LANCZOS).save(OUT / f"excalibu-icon-{size}.png")
    img.resize((64, 64), Image.Resampling.LANCZOS).save(OUT / "favicon.png")
    print("Assets OK:", OUT)


if __name__ == "__main__":
    main()
