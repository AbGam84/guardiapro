"""Códigos de campo por oficial — login independiente en celular."""
import secrets

from sqlalchemy.orm import Session

from app.models import User


def generate_field_code(db: Session, company_id: int) -> str:
    for _ in range(40):
        code = f"{secrets.randbelow(900000) + 100000}"
        taken = (
            db.query(User.id)
            .filter(User.company_id == company_id, User.field_code == code)
            .first()
        )
        if not taken:
            return code
    raise RuntimeError("No se pudo generar código único")


def ensure_guard_field_code(db: Session, user: User) -> str:
    if user.role != "guard":
        return user.field_code or ""
    if user.field_code:
        return user.field_code
    user.field_code = generate_field_code(db, user.company_id)
    db.commit()
    db.refresh(user)
    return user.field_code
