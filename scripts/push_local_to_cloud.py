"""
Replica empresas creadas en local hacia Excalibu Sentinel en la nube (Render).

Lee la SQLite local (GUARDIA_DATA_DIR) y usa el panel comercial (API vendor) +
login admin para sitios y logo.

Uso (desde guardiapro):
  set GUARDIA_CLOUD_URL=https://excalibu-sentinel.onrender.com
  set GUARDIA_VENDOR_USER=vendor
  set GUARDIA_VENDOR_PASSWORD=...
  set GUARDIA_SYNC_ADMIN_PASSWORD=...   (clave actual de admin.gomez en local, si ya existe)
  set PYTHONPATH=.
  python scripts/push_local_to_cloud.py

Opcional: copie push-cloud.env.example → push-cloud.env (no se sube a git).
"""
from __future__ import annotations

import json
import mimetypes
import os
import random
import sys
import uuid
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ENV_FILE = ROOT / "push-cloud.env"


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(ENV_FILE)

CLOUD = (os.getenv("GUARDIA_CLOUD_URL") or "https://excalibu-sentinel.onrender.com").rstrip("/")
VENDOR_USER = (os.getenv("GUARDIA_VENDOR_USER") or "vendor").strip()
VENDOR_PASS = os.getenv("GUARDIA_VENDOR_PASSWORD") or ""
SYNC_ADMIN_PASS = os.getenv("GUARDIA_SYNC_ADMIN_PASSWORD") or ""


def _http(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    url = CLOUD + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            detail = parsed.get("detail", detail)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(f"{method} {path} → {e.code}: {detail}") from e


def _upload_logo_vendor(token: str, company_id: int, logo_path: Path) -> None:
    boundary = f"----Excalibu{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(str(logo_path))[0] or "application/octet-stream"
    content = logo_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{logo_path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    url = CLOUD + f"/api/vendor/companies/{company_id}/logo"
    req = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=120) as resp:
            resp.read()
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Logo upload → {e.code}: {detail}") from e


def _gen_password(length: int = 12) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(alphabet) for _ in range(length))


def _months_until(paid_until: datetime | None) -> int:
    if not paid_until:
        return 1
    now = datetime.utcnow()
    if paid_until <= now:
        return 1
    days = (paid_until - now).days
    return max(1, (days + 29) // 30)


def main() -> None:
    if not VENDOR_PASS:
        print("Falta GUARDIA_VENDOR_PASSWORD (o archivo push-cloud.env).", file=sys.stderr)
        sys.exit(1)

    from app.company_logo import company_logo_path
    from app.database import SessionLocal
    from app.models import ClientSite, Company, User

    db = SessionLocal()
    companies = db.query(Company).filter(Company.active.is_(True)).order_by(Company.id).all()
    if not companies:
        print("No hay empresas activas en local.")
        sys.exit(0)

    vtok = _http("POST", "/api/vendor/login", {"username": VENDOR_USER, "password": VENDOR_PASS})[
        "access_token"
    ]
    overview = _http("GET", "/api/vendor/overview", token=vtok)
    cloud_by_code = {c["code"]: c for c in overview.get("companies") or []}

    created_admin_password: str | None = None

    for co in companies:
        print(f"\n=== {co.name} ({co.code}) ===")
        cloud = cloud_by_code.get(co.code)
        admin_plain = SYNC_ADMIN_PASS.strip()

        if not cloud:
            primary = (
                db.query(User)
                .filter(User.company_id == co.id, User.role == "admin", User.active.is_(True))
                .order_by(User.id.asc())
                .first()
            )
            if not primary:
                print("  Sin admin local — omitida.")
                continue
            prepaid = _months_until(co.paid_until)
            auto = not bool(admin_plain)
            admin_for_create = admin_plain if admin_plain else _gen_password()
            payload = {
                "name": co.name,
                "code": co.code,
                "phone": co.phone or "",
                "alert_whatsapp": co.alert_whatsapp or "",
                "monthly_fee_crc": int(co.monthly_fee_crc or 58000),
                "max_officers": int(co.max_officers or 10),
                "prepaid_months": prepaid,
                "admin_name": primary.name or "Administrador",
                "admin_username": primary.username,
                "admin_password": admin_for_create,
                "auto_password": auto,
            }
            out = _http("POST", "/api/vendor/companies", payload, token=vtok)
            cloud = out["company"]
            creds = out.get("credentials") or {}
            created_admin_password = admin_plain or creds.get("password") or admin_for_create
            cloud_by_code[co.code] = cloud
            print(f"  Creada en nube (id {cloud['id']}). Admin: {primary.username}")
            if auto and created_admin_password:
                print(f"  Clave admin NUBE (guárdela): {created_admin_password}")
        else:
            print(f"  Ya existe en nube (id {cloud['id']}).")

        cid = int(cloud["id"])
        _http(
            "PATCH",
            f"/api/vendor/companies/{cid}/subscription",
            {
                "monthly_fee_crc": int(co.monthly_fee_crc or 58000),
                "max_officers": int(co.max_officers or 10),
                "subscription_status": co.subscription_status or "active",
                "add_months": 0,
            },
            token=vtok,
        )

        detail = _http("GET", f"/api/vendor/companies/{cid}", token=vtok)
        existing_users = {u["username"]: u for u in (detail.get("admins") or []) + (detail.get("guards") or [])}

        local_users = (
            db.query(User)
            .filter(User.company_id == co.id, User.active.is_(True))
            .order_by(User.id.asc())
            .all()
        )
        primary_admin = next((u for u in local_users if u.role == "admin"), None)

        pending_guards: list[tuple] = []
        for u in local_users:
            if u.username in existing_users:
                continue
            if u.role == "admin" and primary_admin and u.id != primary_admin.id:
                pwd = SYNC_ADMIN_PASS or _gen_password()
                body = {
                    "name": u.name,
                    "username": u.username,
                    "password": pwd,
                    "auto_password": False,
                    "role": "admin",
                }
                _http("POST", f"/api/vendor/companies/{cid}/users", body, token=vtok)
                print(f"  Admin creado: {u.username} · clave nube: {pwd}")
            elif u.role == "guard":
                ls = (
                    db.query(ClientSite).filter(ClientSite.id == u.client_site_id).first()
                    if u.client_site_id
                    else None
                )
                pending_guards.append(
                    (
                        u,
                        {
                            "name": u.name,
                            "username": u.username,
                            "password": _gen_password(),
                            "auto_password": False,
                            "role": "guard",
                            "badge": u.badge or "",
                            "phone": u.phone or "",
                            "field_code": u.field_code or "",
                        },
                        ls.name if ls else None,
                    )
                )

        try:
            cloud_sites = _http("GET", f"/api/vendor/companies/{cid}/sites", token=vtok).get("sites") or []
        except RuntimeError as ex:
            if "404" in str(ex):
                print("  Sitios: API comercial en nube aún sin actualizar — Manual Deploy en Render y corra de nuevo.")
                cloud_sites = []
            else:
                raise
        site_by_name = {s["name"]: s["id"] for s in cloud_sites}
        local_sites = db.query(ClientSite).filter(ClientSite.company_id == co.id, ClientSite.active.is_(True)).all()
        for s in local_sites:
            if s.name in site_by_name:
                continue
            try:
                row = _http(
                    "POST",
                    f"/api/vendor/companies/{cid}/sites",
                    {
                        "name": s.name,
                        "address": s.address or "Guanacaste, CR",
                        "client_name": s.client_name or "",
                        "client_phone": s.client_phone or "",
                        "notes": s.notes or "",
                    },
                    token=vtok,
                )
                site_by_name[s.name] = row["site"]["id"]
                print(f"  Sitio: {s.name}")
            except RuntimeError as ex:
                if "404" in str(ex):
                    break
                raise

        detail = _http("GET", f"/api/vendor/companies/{cid}", token=vtok)
        existing_users = {u["username"]: u for u in (detail.get("admins") or []) + (detail.get("guards") or [])}

        for u, body, site_name in pending_guards:
            if u.username in existing_users:
                continue
            if site_name and site_name in site_by_name:
                body["client_site_id"] = site_by_name[site_name]
            _http("POST", f"/api/vendor/companies/{cid}/users", body, token=vtok)
            fc = body.get("field_code") or "?"
            print(f"  Puesto: {u.name} ({u.username}) · código celular {fc}")

        logo = company_logo_path(co.id, co.logo_filename or "")
        if logo and logo.is_file():
            try:
                _upload_logo_vendor(vtok, cid, logo)
                print(f"  Logo subido ({logo.name}).")
            except RuntimeError as ex:
                if "404" in str(ex):
                    print("  Logo: espere deploy Render con commit d6c3ca7+ y corra de nuevo.")
                else:
                    raise

        login_user = primary_admin.username if primary_admin else "admin"
        print(f"  Login cliente: {CLOUD}/login?empresa={co.code}")
        print(f"  Admin: {CLOUD}/admin · usuario {login_user}")

    db.close()
    print("\nListo — revise /comercial en la nube y pruebe login admin.")


if __name__ == "__main__":
    main()
