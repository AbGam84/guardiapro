import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


DATA_DIR = Path(_env("GUARDIA_DATA_DIR", str(ROOT / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = _env("DATABASE_URL", f"sqlite:///{DATA_DIR / 'guardiapro.db'}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

SECRET_KEY = _env("GUARDIA_SECRET_KEY") or "guardiapro-dev-local-change-in-prod"
ACCESS_TOKEN_HOURS = int(_env("GUARDIA_TOKEN_HOURS", "12"))

ENVIRONMENT = _env("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT.lower() in {"production", "prod", "cloud"}

ADMIN_USERNAME = _env("GUARDIA_ADMIN_USER", "admin")
ADMIN_PASSWORD = _env("GUARDIA_ADMIN_PASSWORD", "Admin2026!")
ADMIN_NAME = _env("GUARDIA_ADMIN_NAME", "Administrador")

VENDOR_USERNAME = _env("GUARDIA_VENDOR_USER", "vendor")
VENDOR_PASSWORD = _env("GUARDIA_VENDOR_PASSWORD", "GuardiaVendor2026!")
VENDOR_NAME = _env("GUARDIA_VENDOR_NAME", "Excalibu Telecom Comercial")

HOST = _env("HOST", "0.0.0.0")
PORT = int(_env("PORT", "8097"))
PUBLIC_BASE_URL = (
    _env("PUBLIC_BASE_URL") or _env("RENDER_EXTERNAL_URL") or ""
).rstrip("/")
if PUBLIC_BASE_URL and not PUBLIC_BASE_URL.startswith("http"):
    PUBLIC_BASE_URL = f"https://{PUBLIC_BASE_URL}"

PRODUCT_NAME = "Excalibu Sentinel"
PRODUCT_SHORT = "Excalibu"
COMPANY_NAME = _env("GUARDIA_COMPANY_NAME", "Excalibu Telecom CR")
COMPANY_TAGLINE = "Distribuidor e instalador · Cámaras · WiFi · Internet"
SLOGAN = "Su guardia cuida el sitio. Excalibu cuida al guardia."
TAGLINE = "Bitácora, QR, GPS, cámaras y reportes · Costa Rica"
COPYRIGHT = f"© {COMPANY_NAME} · Excalibu Sentinel · Costa Rica"
SUPPORT_WHATSAPP = _env("GUARDIA_SUPPORT", "+50663706546")
SUPPORT_WHATSAPP_DISPLAY = _env("GUARDIA_SUPPORT_DISPLAY", "+506 6370-6546")
SHOW_DEMO_HINTS = _env("GUARDIA_SHOW_DEMO", "0" if IS_PRODUCTION else "1") in {"1", "true", "yes"}
