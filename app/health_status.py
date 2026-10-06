"""Payload de /api/health — operación y disco (sin secretos)."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import text

from app.config import (
    DATA_DIR,
    DATABASE_URL,
    IS_PRODUCTION,
    PRODUCT_NAME,
    PUBLIC_BASE_URL,
    SECRET_KEY,
    SHOW_DEMO_HINTS,
    SLOGAN,
    SUPPORT_WHATSAPP_DISPLAY,
    TAGLINE,
    UPLOADS_DIR,
)
from app.database import engine

_COMMERCIAL_BASELINE_MARKER = DATA_DIR / ".commercial_baseline_v2"
_DEV_SECRET = "guardiapro-dev-local-change-in-prod"
_BUILD = (os.getenv("GUARDIA_BUILD") or os.getenv("RENDER_GIT_COMMIT") or "dev").strip()[:12]


def _data_dir_persistent(path: Path) -> bool:
    normalized = str(path.resolve()).replace("\\", "/").lower()
    if normalized.startswith("/tmp") or normalized.startswith("/var/tmp"):
        return False
    if "/tmp/" in normalized:
        return False
    return True


def _data_dir_writable(path: Path) -> bool:
    probe = path / ".health_write_probe"
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _database_kind() -> str:
    url = (DATABASE_URL or "").lower()
    if url.startswith("sqlite"):
        return "sqlite"
    if "postgresql" in url or "postgres" in url:
        return "postgresql"
    return "other"


def _database_ok() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _active_companies_count() -> int:
    try:
        from app.database import SessionLocal
        from app.models import Company

        db = SessionLocal()
        try:
            return db.query(Company).filter(Company.active.is_(True)).count()
        finally:
            db.close()
    except Exception:
        return -1


def build_health_payload() -> dict:
    db_ok = _database_ok()
    data_writable = _data_dir_writable(DATA_DIR)
    persistent = _data_dir_persistent(DATA_DIR)
    uploads_ok = _data_dir_writable(UPLOADS_DIR)
    secret_ok = not IS_PRODUCTION or SECRET_KEY != _DEV_SECRET

    checks: dict[str, str] = {
        "database": "ok" if db_ok else "fail",
        "data_writable": "ok" if data_writable else "fail",
        "uploads_writable": "ok" if uploads_ok else "fail",
    }
    if IS_PRODUCTION:
        checks["persistent_storage"] = "ok" if persistent else "fail"
        checks["secret_key"] = "ok" if secret_ok else "warn"

    ok = db_ok and data_writable and uploads_ok and (not IS_PRODUCTION or persistent)

    payload: dict = {
        "ok": ok,
        "product": PRODUCT_NAME,
        "slogan": SLOGAN,
        "tagline": TAGLINE,
        "production": IS_PRODUCTION,
        "build": _BUILD,
        "checks": checks,
        "database": _database_kind(),
        "support_whatsapp": SUPPORT_WHATSAPP_DISPLAY,
    }

    if PUBLIC_BASE_URL:
        payload["public_url"] = PUBLIC_BASE_URL

    service = (os.getenv("RENDER_SERVICE_NAME") or "").strip()
    if service:
        payload["service"] = service

    if IS_PRODUCTION:
        db_path = DATA_DIR / "guardiapro.db"
        payload["storage"] = {
            "data_dir": str(DATA_DIR.resolve()).replace("\\", "/"),
            "persistent": persistent,
            "commercial_baseline": _COMMERCIAL_BASELINE_MARKER.is_file(),
            "db_exists": db_path.is_file(),
            "uploads_dir": str(UPLOADS_DIR.resolve()).replace("\\", "/"),
        }
        count = _active_companies_count()
        if count >= 0:
            payload["tenants"] = {"companies_active": count}

    else:
        payload["environment"] = os.getenv("ENVIRONMENT", "development")
        payload["show_demo_hints"] = SHOW_DEMO_HINTS

    if not secret_ok and IS_PRODUCTION:
        payload["warnings"] = ["Configure GUARDIA_SECRET_KEY en producción"]

    return payload
