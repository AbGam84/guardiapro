"""Sube logo de una empresa local a Render vía login admin (API ya desplegada)."""
from __future__ import annotations

import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "push-cloud.env"


def _load_env() -> None:
    if not ENV_FILE.is_file():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _json(method: str, base: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(base + path, data=data, headers=headers, method=method)
    with urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _upload(base: str, token: str, logo: Path) -> None:
    boundary = f"----Excalibu{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(str(logo))[0] or "image/jpeg"
    content = logo.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{logo.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = Request(
        base + "/api/company/logo",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urlopen(req, timeout=120) as resp:
        resp.read()


def main() -> None:
    _load_env()
    base = (os.getenv("GUARDIA_CLOUD_URL") or "https://excalibu-sentinel.onrender.com").rstrip("/")
    user = os.getenv("GUARDIA_CLOUD_ADMIN_USER") or "admin.gomez"
    pwd = os.getenv("GUARDIA_SYNC_ADMIN_PASSWORD") or os.getenv("GUARDIA_CLOUD_ADMIN_PASSWORD") or ""
    code = (sys.argv[1] if len(sys.argv) > 1 else "grupo-gomez").strip().lower()
    logo = ROOT / "web" / "static" / "clients" / f"{code.replace('_', '-')}-logo.jpeg"
    if not logo.is_file():
        logo = ROOT / "web" / "static" / "clients" / "grupo-gomez-logo.jpeg"
    if not pwd:
        print("Falta GUARDIA_SYNC_ADMIN_PASSWORD en push-cloud.env", file=sys.stderr)
        sys.exit(1)
    if not logo.is_file():
        print(f"Sin archivo logo: {logo}", file=sys.stderr)
        sys.exit(1)
    tok = _json("POST", base, "/api/auth/login", {"username": user, "password": pwd, "company_code": code})[
        "access_token"
    ]
    _upload(base, tok, logo)
    b = _json("GET", base, f"/api/branding/{code}")
    print(f"OK · {b.get('name')} · has_logo={b.get('has_logo')} · {base}/login?empresa={code}")


if __name__ == "__main__":
    main()
