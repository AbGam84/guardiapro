"""Supervisor + puestos Lima + guardias en nube (Grupo Gómez). Idempotente."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from bootstrap_grupo_gomez_cloud import _json, _load_env  # noqa: E402

COMPANY_CODE = "grupo-gomez"

SITES = [
    {"name": "Lima 1", "address": "Puesto Lima 1"},
    {"name": "Lima 2", "address": "Puesto Lima 2"},
    {"name": "Lima 3", "address": "Puesto Lima 3"},
    {"name": "Lima 4", "address": "Puesto Lima 4"},
    {"name": "Lima 5", "address": "Puesto Lima 5"},
]

GUARDS = [
    {"name": "Oficial Lima 1", "username": "lima1.gomez", "badge": "LIM-01", "site": "Lima 1"},
    {"name": "Oficial Lima 2", "username": "lima2.gomez", "badge": "LIM-02", "site": "Lima 2"},
    {"name": "Oficial Lima 3", "username": "lima3.gomez", "badge": "LIM-03", "site": "Lima 3"},
    {"name": "Oficial Lima 4", "username": "lima4.gomez", "badge": "LIM-04", "site": "Lima 4"},
    {"name": "Oficial Lima 5", "username": "lima5.gomez", "badge": "LIM-05", "site": "Lima 5"},
]

SUPERVISOR = {
    "name": "Supervisor operaciones",
    "username": "supervisor.gomez",
}


def _ensure_user(
    base: str,
    token: str,
    cid: int,
    *,
    name: str,
    username: str,
    role: str,
    password: str,
    client_site_id: int | None = None,
) -> dict | None:
    detail = _json("GET", base, f"/api/vendor/companies/{cid}", token=token)
    pool = (detail.get("admins") or []) + (detail.get("supervisors") or []) + (detail.get("guards") or [])
    for u in pool:
        if (u.get("username") or "").lower() == username.lower():
            return None
    body: dict = {
        "name": name,
        "username": username,
        "password": password,
        "auto_password": False,
        "role": role,
    }
    if client_site_id:
        body["client_site_id"] = client_site_id
    return _json("POST", base, f"/api/vendor/companies/{cid}/users", body, token)


def main() -> None:
    _load_env()
    base = (os.getenv("GUARDIA_CLOUD_URL") or "https://excalibu-sentinel.onrender.com").rstrip("/")
    vu = os.getenv("GUARDIA_VENDOR_USER") or "vendor"
    vp = os.getenv("GUARDIA_VENDOR_PASSWORD") or ""
    sup_pass = os.getenv("GUARDIA_SYNC_SUPERVISOR_PASSWORD") or os.getenv("GUARDIA_SYNC_ADMIN_PASSWORD") or ""
    guard_pass = os.getenv("GUARDIA_SYNC_GUARD_PASSWORD") or sup_pass
    if not vp or not sup_pass:
        print("Faltan GUARDIA_VENDOR_PASSWORD y clave supervisor/admin en push-cloud.env", file=sys.stderr)
        sys.exit(1)

    vt = _json("POST", base, "/api/vendor/login", {"username": vu, "password": vp})["access_token"]
    ov = _json("GET", base, "/api/vendor/overview", token=vt)
    row = next((c for c in ov.get("companies", []) if c.get("code") == COMPANY_CODE), None)
    if not row:
        print(f"Empresa {COMPANY_CODE} no existe — ejecute bootstrap_grupo_gomez_cloud.py primero", file=sys.stderr)
        sys.exit(1)
    cid = row["id"]

    site_ids: dict[str, int] = {}
    for s in SITES:
        r = _json(
            "POST",
            base,
            f"/api/vendor/companies/{cid}/sites",
            {"name": s["name"], "address": s["address"]},
            vt,
        )
        site_ids[s["name"]] = r["site"]["id"]

    created_sup = _ensure_user(
        base,
        vt,
        cid,
        name=SUPERVISOR["name"],
        username=SUPERVISOR["username"],
        role="supervisor",
        password=sup_pass,
    )
    guard_links: list[dict] = []
    for g in GUARDS:
        sid = site_ids.get(g["site"])
        r = _ensure_user(
            base,
            vt,
            cid,
            name=g["name"],
            username=g["username"],
            role="guard",
            password=guard_pass,
            client_site_id=sid,
        )
        if r:
            u = r.get("user") or {}
            guard_links.append(
                {
                    "name": g["name"],
                    "username": g["username"],
                    "field_code": u.get("field_code"),
                    "link": u.get("field_login_path_branded") or u.get("field_login_path"),
                }
            )

    delivery = {
        "admin": f"{base}/login?empresa={COMPANY_CODE}",
        "supervisor": f"{base}/acceso/{COMPANY_CODE}/supervisor",
        "oficial_base": f"{base}/oficial?empresa={COMPANY_CODE}",
        "supervisor_user": SUPERVISOR["username"],
        "supervisor_created": created_sup is not None,
        "guards": guard_links,
    }
    print(json.dumps(delivery, ensure_ascii=False, indent=2))
    print("\nClaves: supervisor = GUARDIA_SYNC_SUPERVISOR_PASSWORD o GUARDIA_SYNC_ADMIN_PASSWORD")
    print("Claves guardias: GUARDIA_SYNC_GUARD_PASSWORD (o misma que supervisor si no esta definida)")


if __name__ == "__main__":
    main()
