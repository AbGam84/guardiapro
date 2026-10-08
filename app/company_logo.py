"""Logo por empresa (marca blanca en login, app y PDF)."""

from __future__ import annotations

from pathlib import Path

from app.config import UPLOADS_DIR
from app.paths import WEB

LOGOS_DIR = UPLOADS_DIR / "logos"
LOGOS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_CLIENTS_DIR = WEB / "static" / "clients"

_ALLOWED = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _logo_path(company_id: int, ext: str) -> Path:
    return LOGOS_DIR / f"company_{company_id}{ext}"


def company_logo_path(company_id: int, filename: str = "") -> Path | None:
    if filename:
        p = LOGOS_DIR / filename
        if p.is_file() and p.parent.resolve() == LOGOS_DIR.resolve():
            return p
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        p = _logo_path(company_id, ext)
        if p.is_file():
            return p
    return None


def static_client_logo_disk_path(company_code: str) -> Path | None:
    code = (company_code or "").strip().lower()
    if not code or not STATIC_CLIENTS_DIR.is_dir():
        return None
    for name in (
        f"{code}-logo.jpeg",
        f"{code}-logo.jpg",
        f"{code}-logo.png",
        f"{code}-logo.webp",
        f"{code}.jpeg",
        f"{code}.jpg",
        f"{code}.png",
    ):
        p = STATIC_CLIENTS_DIR / name
        if p.is_file():
            return p
    return None


def static_client_logo_web_url(company_code: str) -> str:
    code = (company_code or "").strip().lower()
    p = static_client_logo_disk_path(code)
    if not p:
        return ""
    return f"/static/clients/{p.name}"


def company_logo_url(company_id: int, filename: str = "", company_code: str = "") -> str:
    if company_logo_path(company_id, filename):
        return f"/api/company/logo?company_id={company_id}"
    static_url = static_client_logo_web_url(company_code)
    if static_url:
        return static_url
    return ""


def resolve_company_logo_file(company_id: int, filename: str, company_code: str) -> Path | None:
    path = company_logo_path(company_id, filename)
    if path:
        return path
    return static_client_logo_disk_path(company_code)


def save_company_logo(company_id: int, content: bytes, original_name: str = "") -> str:
    ext = Path(original_name or "logo.png").suffix.lower()
    if ext not in _ALLOWED:
        ext = ".png"
    for old in LOGOS_DIR.glob(f"company_{company_id}.*"):
        old.unlink(missing_ok=True)
    dest = _logo_path(company_id, ext)
    dest.write_bytes(content)
    return dest.name


def delete_company_logo(company_id: int) -> None:
    for p in LOGOS_DIR.glob(f"company_{company_id}.*"):
        p.unlink(missing_ok=True)


def logo_media_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "application/octet-stream")
