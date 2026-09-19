"""Genera PNG listos para enviar por WhatsApp (sin URL, solo imagen)."""
from __future__ import annotations

import io
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_M

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = Path.home() / "OneDrive" / "Escritorio" / "publisidad de seguridad" / "imagenes"
FALLBACK_DESKTOP = Path.home() / "Desktop" / "publisidad de seguridad" / "imagenes"
LOGO = ROOT / "web" / "static" / "excalibu-mark.png"
DEMO_URL = "https://excalibu-sentinel.onrender.com/demo"

BG = "#050c14"
PANEL = "#121a28"
GOLD = "#ffb020"
TEAL = "#12c4a0"
TEXT = "#f7fbff"
MUTED = "#8fa3bf"
BORDER = "#243044"


def _fonts() -> dict:
    win = Path("C:/Windows/Fonts")
    def load(name: str, size: int):
        p = win / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
        return ImageFont.load_default()

    return {
        "h1": load("segoeuib.ttf", 56),
        "h2": load("segoeuib.ttf", 44),
        "h3": load("segoeuib.ttf", 28),
        "body": load("segoeui.ttf", 24),
        "small": load("segoeui.ttf", 20),
        "tiny": load("segoeui.ttf", 17),
        "wa": load("segoeuib.ttf", 40),
    }


def _qr(size: int = 200) -> Image.Image:
    qr = qrcode.QRCode(version=1, error_correction=ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(DEMO_URL)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((size, size), Image.Resampling.LANCZOS)


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _gradient_bg(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(5 + t * 8)
        g = int(12 + t * 14)
        b = int(20 + t * 18)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse((w - 420, -120, w + 80, 380), fill=(18, 196, 160, 35))
    od.ellipse((-180, h - 380, 280, h + 80), fill=(255, 176, 32, 28))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _paste_logo(base: Image.Image, x: int, y: int, size: int = 110) -> None:
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        base.paste(logo, (x, y), logo)
        return
    draw = ImageDraw.Draw(base)
    _rounded_rect(draw, (x, y, x + size, y + size), 22, fill=PANEL, outline=TEAL, width=3)
    f = _fonts()["h3"]
    draw.text((x + size // 2, y + size // 2), "E", fill=TEAL, font=f, anchor="mm")


def _draw_panfleto() -> Image.Image:
    w, h = 1080, 1350
    img = _gradient_bg(w, h)
    draw = ImageDraw.Draw(img)
    f = _fonts()

    _paste_logo(img, 48, 42, 100)
    draw.text((170, 52), "Excalibu Sentinel", fill=TEXT, font=f["h1"])
    draw.text((170, 112), "EXCALIBU TELECOM CR · COSTA RICA", fill=GOLD, font=f["small"])
    draw.line([(48, 165), (w - 48, 165)], fill=TEAL, width=3)

    title = "Cámaras + WiFi +\nprueba de rondas"
    draw.multiline_text((w // 2, 210), title, fill=TEXT, font=f["h2"], anchor="ma", spacing=8)
    # gold emphasis on last line - redraw partial
    draw.text((w // 2, 258), "prueba de rondas", fill=GOLD, font=f["h2"], anchor="ma")

    offers = [
        ("📹  CÁMARAS", "WiFi, IP, NVR y DVR instalados"),
        ("📶  WiFi / INTERNET", "Red estable en su sitio"),
        ("📱  RONDAS QR", "Hora, lugar y GPS registrados"),
        ("⏰  ALERTAS", "Si no cumplen horario de ronda"),
        ("📊  PORTAL CLIENTE", "Su cliente ve el servicio"),
        ("📄  REPORTES PDF", "Evidencia para administración"),
    ]
    ox, oy = 48, 320
    cw, ch, gap = 480, 118, 16
    for i, (title_o, desc) in enumerate(offers):
        col, row = i % 2, i // 2
        x1 = ox + col * (cw + gap)
        y1 = oy + row * (ch + gap)
        _rounded_rect(draw, (x1, y1, x1 + cw, y1 + ch), 16, fill=PANEL, outline=BORDER, width=2)
        draw.text((x1 + 18, y1 + 16), title_o, fill=TEAL, font=f["h3"])
        draw.text((x1 + 18, y1 + 56), desc, fill=TEXT, font=f["body"])

    sy = 680
    _rounded_rect(draw, (48, sy, w - 48, sy + 88), 16, fill="#0f1e28", outline=TEAL, width=2)
    draw.text((w // 2, sy + 22), "Excalibu Sentinel — audita su operación", fill=GOLD, font=f["h3"], anchor="ma")
    draw.text((w // 2, sy + 58), "Su guardia cuida el sitio. Excalibu cuida al guardia.", fill=MUTED, font=f["small"], anchor="ma")

    py = sy + 108
    pkgs = [("Paquete A", "Cámaras + WiFi"), ("Paquete B", "Software rondas"), ("Paquete C ★", "Todo integrado")]
    pw = 310
    for i, (name, sub) in enumerate(pkgs):
        x1 = 48 + i * (pw + 22)
        fill = "#1a1508" if i == 2 else PANEL
        outline = GOLD if i == 2 else BORDER
        _rounded_rect(draw, (x1, py, x1 + pw, py + 72), 12, fill=fill, outline=outline, width=2)
        draw.text((x1 + pw // 2, py + 16), name, fill=GOLD, font=f["h3"], anchor="ma")
        draw.text((x1 + pw // 2, py + 46), sub, fill=TEXT, font=f["tiny"], anchor="ma")

    draw.line([(48, 920), (w - 48, 920)], fill=TEAL, width=2)
    draw.text((48, 948), "WhatsApp 6370-6546", fill=TEXT, font=f["wa"])
    draw.text((48, 1008), "Distribuidor · Instalador · Seguridad · Condominios · Bodegas", fill=MUTED, font=f["small"])
    draw.text((48, 1042), "Cotización sin compromiso", fill=MUTED, font=f["tiny"])

    qr = _qr(180)
    img.paste(qr, (w - 48 - 180, 940))

    return img


def _draw_post() -> Image.Image:
    w, h = 1080, 1080
    img = _gradient_bg(w, h)
    draw = ImageDraw.Draw(img)
    f = _fonts()
    _paste_logo(img, 48, 40, 120)
    draw.text((190, 48), "Excalibu Sentinel", fill=TEXT, font=f["h1"])
    draw.text((190, 112), "EXCALIBU TELECOM CR", fill=GOLD, font=f["small"])
    draw.multiline_text((w // 2, 200), "Cámaras + WiFi +\nprueba de rondas", fill=TEXT, font=f["h2"], anchor="ma", spacing=6)
    draw.text((w // 2, 248), "prueba de rondas", fill=GOLD, font=f["h2"], anchor="ma")

    lines = [
        "📹 Instalo cámaras WiFi, NVR, DVR",
        "📶 Conecto WiFi e internet",
        "📱 Activo rondas QR + GPS + alertas",
        "📊 Portal para su cliente final",
    ]
    y = 320
    for line in lines:
        _rounded_rect(draw, (60, y, w - 60, y + 72), 14, fill=PANEL, outline=BORDER, width=2)
        draw.text((80, y + 22), line, fill=TEXT, font=f["body"])
        y += 88

    draw.line([(48, 720), (w - 48, 720)], fill=TEAL, width=2)
    draw.text((48, 750), "WhatsApp 6370-6546", fill=TEXT, font=f["wa"])
    draw.text((48, 810), "Su guardia cuida el sitio. Excalibu cuida al guardia.", fill=MUTED, font=f["small"])
    img.paste(_qr(150), (w - 210, 740))
    return img


def _draw_story() -> Image.Image:
    w, h = 1080, 1920
    img = _gradient_bg(w, h)
    draw = ImageDraw.Draw(img)
    f = _fonts()
    _paste_logo(img, w // 2 - 80, 80, 160)
    draw.text((w // 2, 270), "Excalibu Sentinel", fill=TEXT, font=f["h1"], anchor="ma")
    draw.text((w // 2, 340), "EXCALIBU TELECOM CR", fill=GOLD, font=f["small"], anchor="ma")
    draw.text((w // 2, 420), "¿Paga seguridad", fill=TEXT, font=f["h2"], anchor="ma")
    draw.text((w // 2, 480), "sin prueba?", fill=GOLD, font=f["h2"], anchor="ma")

    lines = [
        ("Instalo cámaras WiFi, NVR, DVR", "📹"),
        ("WiFi e internet en el sitio", "📶"),
        ("Rondas QR, GPS y alertas", "📱"),
        ("Portal para su cliente", "📊"),
    ]
    y = 560
    for text, icon in lines:
        _rounded_rect(draw, (64, y, w - 64, y + 100), 18, fill=PANEL, outline=BORDER, width=2)
        draw.text((100, y + 34), icon, fill=TEXT, font=f["h2"])
        draw.text((160, y + 36), text, fill=TEXT, font=f["body"])
        y += 120

    draw.text((w // 2, y + 40), "Su guardia cuida el sitio.", fill=MUTED, font=f["body"], anchor="ma")
    draw.text((w // 2, y + 78), "Excalibu cuida al guardia.", fill=GOLD, font=f["h3"], anchor="ma")

    draw.line([(64, 1580), (w - 64, 1580)], fill=TEAL, width=3)
    draw.text((w // 2, 1620), "WhatsApp 6370-6546", fill=TEXT, font=f["wa"], anchor="ma")
    qr = _qr(220)
    img.paste(qr, (w // 2 - 110, 1700))
    draw.text((w // 2, 1940 - 60), "Excalibu Telecom CR · Costa Rica", fill=MUTED, font=f["tiny"], anchor="ma")
    return img


def main() -> None:
    out = DESKTOP if DESKTOP.parent.exists() else FALLBACK_DESKTOP
    out.mkdir(parents=True, exist_ok=True)

    files = {
        "panfleto-whatsapp.png": _draw_panfleto(),
        "post-instagram.png": _draw_post(),
        "story-whatsapp.png": _draw_story(),
    }
    for name, im in files.items():
        path = out / name
        im.save(path, "PNG", optimize=True)
        print(f"OK {path} ({im.size[0]}x{im.size[1]})")

    readme = out / "LEEME-IMAGENES.txt"
    readme.write_text(
        """IMÁGENES LISTAS PARA WHATSAPP
=============================

Envíe directo desde el celular o PC — son archivos .PNG, no links.

  panfleto-whatsapp.png  → Foto principal (1080×1350)
  post-instagram.png     → Cuadrado feed (1080×1080)
  story-whatsapp.png     → Vertical status (1080×1920)

Cómo enviar:
  1. Abra WhatsApp → adjuntar → Galería / Documento
  2. Elija la imagen de esta carpeta
  3. Listo — sin URL

Excalibu Telecom CR · WhatsApp 6370-6546
""",
        encoding="utf-8",
    )
    print(f"README {readme}")


if __name__ == "__main__":
    main()
