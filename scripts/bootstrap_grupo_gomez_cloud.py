"""Crea Grupo Gómez en nube vacía + logo (post-deploy Render)."""
from __future__ import annotations

import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "push-cloud.env"


def _load_env() -> None:
    if not ENV.is_file():
        return
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def _json(method: str, base: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(base + path, data=data, headers=headers, method=method)
    with urlopen(req, timeout=120) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def main() -> None:
    _load_env()
    base = (os.getenv("GUARDIA_CLOUD_URL") or "https://excalibu-sentinel.onrender.com").rstrip("/")
    vu = os.getenv("GUARDIA_VENDOR_USER") or "vendor"
    vp = os.getenv("GUARDIA_VENDOR_PASSWORD") or ""
    admin_pass = os.getenv("GUARDIA_SYNC_ADMIN_PASSWORD") or ""
    if not vp or not admin_pass:
        print("Faltan GUARDIA_VENDOR_PASSWORD o GUARDIA_SYNC_ADMIN_PASSWORD", file=sys.stderr)
        sys.exit(1)

    try:
        _json("GET", base, "/api/branding/grupo-gomez")
        print("grupo-gomez ya existe — subiendo logo…")
        vt = _json("POST", base, "/api/vendor/login", {"username": vu, "password": vp})["access_token"]
        ov = _json("GET", base, "/api/vendor/overview", token=vt)
        cid = next(c["id"] for c in ov.get("companies", []) if c.get("code") == "grupo-gomez")
    except Exception:
        vt = _json("POST", base, "/api/vendor/login", {"username": vu, "password": vp})["access_token"]
        co = _json(
            "POST",
            base,
            "/api/vendor/companies",
            {
                "name": "Grupo Gómez y Asociados",
                "code": "grupo-gomez",
                "phone": "+506 6070 9197",
                "alert_whatsapp": "50660709197",
                "brand_tagline": "Seguridad privada",
                "admin_name": "Administrador",
                "admin_username": "admin.gomez",
                "admin_password": admin_pass,
                "auto_password": False,
                "prepaid_months": 12,
            },
            vt,
        )
        cid = co["company"]["id"]
        print("Empresa creada:", co["company"]["name"])

    logo = Path.home() / "OneDrive" / "Escritorio" / "logo de empresa seguridad.jpeg"
    if not logo.is_file():
        logo = ROOT / "web" / "static" / "clients" / "grupo-gomez-logo.jpeg"
    if not logo.is_file():
        print("Sin archivo logo", file=sys.stderr)
        sys.exit(1)

    boundary = f"----Excalibu{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(str(logo))[0] or "image/jpeg"
    content = logo.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{logo.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    req = Request(
        base + f"/api/vendor/companies/{cid}/logo",
        data=body,
        headers={
            "Authorization": f"Bearer {vt}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urlopen(req, timeout=120) as resp:
        resp.read()

    brand = _json("GET", base, "/api/branding/grupo-gomez")
    print(json.dumps(brand, ensure_ascii=False))
    print(f"URL cliente: {base}/login?empresa=grupo-gomez")
    print("Admin: admin.gomez (clave en push-cloud.env GUARDIA_SYNC_ADMIN_PASSWORD)")


if __name__ == "__main__":
    main()
