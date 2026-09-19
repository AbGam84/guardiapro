import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def qr_png(payload: str, *, box_size: int = 8, border: int = 2) -> bytes:
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=box_size, border=border)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def checkpoint_scan_url(base_url: str, qr_token: str) -> str:
    base = (base_url or "").rstrip("/")
    if not base:
        return f"/guardia?qr={qr_token}"
    return f"{base}/guardia?qr={qr_token}"
