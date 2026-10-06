"""Actualiza nombre, lema y teléfono de marca en Render (login personalizado)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "push-cloud.env"


def _env() -> None:
    if not ENV.is_file():
        return
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _post(base: str, path: str, body: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(base + path, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _patch(base: str, path: str, body: dict, token: str) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Bearer {token}"}
    req = Request(base + path, data=json.dumps(body).encode(), headers=headers, method="PATCH")
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> None:
    _env()
    base = (os.getenv("GUARDIA_CLOUD_URL") or "https://excalibu-sentinel.onrender.com").rstrip("/")
    user = os.getenv("GUARDIA_CLOUD_ADMIN_USER") or "admin.gomez"
    pwd = os.getenv("GUARDIA_SYNC_ADMIN_PASSWORD") or ""
    if not pwd:
        print("Falta GUARDIA_SYNC_ADMIN_PASSWORD", file=sys.stderr)
        sys.exit(1)
    tok = _post(base, "/api/auth/login", {"username": user, "password": pwd})["access_token"]
    _patch(
        base,
        "/api/company/settings",
        {
            "name": "Grupo Gómez y Asociados",
            "phone": "+506 6070 9197",
            "alert_whatsapp": "50660709197",
            "brand_tagline": "Seguridad privada",
        },
        tok,
    )
    code = "grupo-gomez"
    with urlopen(base + f"/api/branding/{code}", timeout=60) as r:
        print(r.read().decode())


if __name__ == "__main__":
    main()
