"""
Grupo Gómez y Asociados — sitios y puestos Lima (no nombres de personas).

Ejecutar tras crear la empresa en /comercial (código grupo-gomez):
  cd guardiapro && set PYTHONPATH=. && python scripts/setup_grupo_gomez_puestos.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.auth import hash_password
from app.company_logo import company_logo_path, save_company_logo
from app.database import SessionLocal
from app.field_codes import generate_field_code
from app.models import ClientSite, Company, User
from app.passwords import generate_client_password
from app.subscription import extend_paid_until

COMPANY_CODE = "grupo-gomez"
LOGO = ROOT / "web" / "static" / "clients" / "grupo-gomez-logo.jpeg"

SITES = [
    ("loma-verde", "Condominio Loma Verde", "Loma Verde"),
    ("avellana", "Avellana", "Avellana"),
    ("potrero-fiesta", "Potrero — Hotel Fiesta", "Potrero / Hotel Fiesta"),
    ("playa-colibri", "Playa Grande — Casa Colibrí", "Playa Grande Casa Colibrí"),
]

PUESTOS = [
    ("Lima1", "lima1", "LIMA-1", "loma-verde"),
    ("Lima2", "lima2", "LIMA-2", "loma-verde"),
    ("Lima3", "lima3", "LIMA-3", "avellana"),
    ("Lima4", "lima4", "LIMA-4", "potrero-fiesta"),
    ("Lima6", "lima6", "LIMA-6", "playa-colibri"),
]


def main() -> None:
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.code == COMPANY_CODE).first()
        if not company:
            print(f"No existe empresa «{COMPANY_CODE}». Créela primero en /comercial.")
            sys.exit(1)
        company.name = "Grupo Gómez y Asociados"
        if not company.paid_until:
            extend_paid_until(company, 1)
        if LOGO.is_file() and not company_logo_path(company.id, company.logo_filename or ""):
            company.logo_filename = save_company_logo(company.id, LOGO.read_bytes(), LOGO.name)

        site_by_code: dict[str, ClientSite] = {}
        for code, name, client in SITES:
            row = db.query(ClientSite).filter(ClientSite.company_id == company.id, ClientSite.name == name).first()
            if not row:
                row = ClientSite(company_id=company.id, name=name, client_name=client, address="Guanacaste, CR")
                db.add(row)
                db.flush()
            site_by_code[code] = row

        created_pw: list[tuple[str, str, str]] = []
        for post_name, username, badge, site_code in PUESTOS:
            site = site_by_code[site_code]
            user = db.query(User).filter(User.username == username).first()
            plain = generate_client_password()
            if not user:
                user = User(
                    company_id=company.id,
                    name=post_name,
                    username=username,
                    password_hash=hash_password(plain),
                    role="guard",
                    badge=badge,
                    client_site_id=site.id,
                )
                db.add(user)
                db.flush()
                user.field_code = generate_field_code(db, company.id)
                created_pw.append((post_name, username, plain))
            else:
                user.company_id = company.id
                user.name = post_name
                user.badge = badge
                user.client_site_id = site.id
                user.active = True
                if not user.field_code:
                    user.field_code = generate_field_code(db, company.id)

        db.commit()
        print(f"OK — {company.name} ({company.code})")
        print("Sitios:", ", ".join(s.name for s in site_by_code.values()))
        print("Puestos:", ", ".join(p[0] for p in PUESTOS))
        if created_pw:
            print("\nClaves nuevas (celular /oficial usa código; respaldo /login):")
            for post, uname, pwd in created_pw:
                print(f"  {post} · usuario {uname} · clave {pwd}")
        else:
            print("\nPuestos ya existían — no se regeneraron claves (use panel si hace falta).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
