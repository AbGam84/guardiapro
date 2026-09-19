"""Repara esquema DB, limpia demo y restablece clave admin."""

import sys

from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))



from app.auth import hash_password, verify_password

from app.config import ADMIN_NAME, ADMIN_PASSWORD, ADMIN_USERNAME

from app.database import Base, SessionLocal, engine

from app.migrate import ensure_schema

from app.models import Company, User

from app.seed import ensure_admin_access, migrate_demo_to_clean, purge_demo_cameras, seed_if_empty





def main() -> None:

    Base.metadata.create_all(bind=engine)

    ensure_schema(engine)

    db = SessionLocal()

    try:

        seed_if_empty(db)

        if migrate_demo_to_clean(db):

            print("Demo eliminado — base lista para datos reales.")

        removed = purge_demo_cameras(db)

        if removed:

            print(f"Cámaras demo eliminadas: {removed}")

        ensure_admin_access(db)

        company = db.query(Company).first()

        uname = ADMIN_USERNAME.strip().lower()

        admin = db.query(User).filter(User.username == uname).first()

        expected = hash_password(ADMIN_PASSWORD)

        if not company:

            print("Sin empresa en DB — seed inicial ejecutado.")

        elif not admin:

            db.add(

                User(

                    company_id=company.id,

                    name=ADMIN_NAME,

                    username=uname,

                    password_hash=expected,

                    role="admin",

                    badge="ADM-001",

                )

            )

            db.commit()

            print(f"Admin creado: {uname} / {ADMIN_PASSWORD}")

        elif not verify_password(ADMIN_PASSWORD, admin.password_hash):

            admin.password_hash = expected

            admin.active = True

            db.commit()

            print(f"Clave admin restablecida: {uname} / {ADMIN_PASSWORD}")

        else:

            print(f"OK — admin {uname} operativo. Empresa: {company.name} ({company.code})")

    finally:

        db.close()





if __name__ == "__main__":

    main()

