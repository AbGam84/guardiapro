"""Genera logo SVG + PNG Excalibu Sentinel."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "static"

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="Excalibu Sentinel">
  <defs>
    <linearGradient id="blade" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#12c4a0"/>
      <stop offset="100%" stop-color="#3eb5e0"/>
    </linearGradient>
    <linearGradient id="gold" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffb020"/>
      <stop offset="100%" stop-color="#ff8c1a"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="96" fill="#0a0f18"/>
  <path d="M256 72 L296 200 L256 440 L216 200 Z" fill="url(#blade)" opacity=".95"/>
  <rect x="232" y="200" width="48" height="28" rx="6" fill="url(#gold)"/>
  <rect x="220" y="228" width="72" height="16" rx="4" fill="url(#gold)"/>
  <circle cx="256" cy="248" r="10" fill="#0a0f18" stroke="#ffb020" stroke-width="4"/>
  <path d="M150 320 Q256 260 362 320 L340 360 Q256 310 172 360 Z" fill="#121a28" stroke="#243044" stroke-width="6"/>
  <path d="M190 338 L256 300 L322 338" fill="none" stroke="#12c4a0" stroke-width="5" stroke-linecap="round"/>
  <text x="256" y="410" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="52" font-weight="700" fill="#eef4ff">Excalibu</text>
  <text x="256" y="452" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="22" letter-spacing="6" fill="#12c4a0">SENTINEL</text>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    svg_path = OUT / "excalibu-logo.svg"
    svg_path.write_text(SVG, encoding="utf-8")
    try:
        import cairosvg  # optional
        cairosvg.svg2png(bytestring=SVG.encode(), write_to=str(OUT / "excalibu-logo.png"), output_width=512, output_height=512)
    except Exception:
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGBA", (512, 512), (10, 15, 24, 255))
            d = ImageDraw.Draw(img)
            d.polygon([(256, 72), (296, 200), (256, 440), (216, 200)], fill=(18, 196, 160, 230))
            d.rectangle((232, 200, 280, 228), fill=(255, 176, 32, 255))
            d.rectangle((220, 228, 292, 244), fill=(255, 140, 26, 255))
            d.ellipse((246, 238, 266, 258), outline=(255, 176, 32, 255), width=3)
            d.text((256, 400), "Excalibu", fill=(238, 244, 255, 255), anchor="mm")
            d.text((256, 440), "SENTINEL", fill=(18, 196, 160, 255), anchor="mm")
            img.save(OUT / "excalibu-logo.png")
            img.resize((64, 64), Image.Resampling.LANCZOS).save(OUT / "favicon.png")
        except Exception as exc:
            print("PNG skip:", exc)
    print("Logo:", svg_path)


if __name__ == "__main__":
    main()
