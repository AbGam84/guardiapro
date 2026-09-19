"""Repara esquema DB y restablece clave admin según .env / config."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.auth import hash_password, verify_password
from app.config import ADMIN_NAME, ADMIN_PASSWORD, ADMIN_USERNAME
from app.database import Base, SessionLocal, engine
from app.migrate import ensure_schema
from app.models import Company, User
from app.seed import seed_cameras_if_empty, seed_client_and_schedules_if_missing, seed_if_empty


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
        seed_cameras_if_empty(db)
        seed_client_and_schedules_if_missing(db)
        company = db.query(Company).first()
        uname = ADMIN_USERNAME.strip().lower()
        admin = db.query(User).filter(User.username == uname).first()
        expected = hash_password(ADMIN_PASSWORD)
        if not company:
            print("Sin empresa en DB — seed inicial ejecutado si era vacía.")
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
            print(f"OK — admin {uname} operativo con clave configurada.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
