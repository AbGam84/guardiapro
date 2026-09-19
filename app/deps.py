"""Dependencias y helpers compartidos entre rutas API."""

from urllib.parse import quote

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.config import PUBLIC_BASE_URL
from app.models import Company, User


def public_base(request: Request) -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    return str(request.base_url).rstrip("/")


def get_company(db: Session, user: User) -> Company:
    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company or not company.active:
        raise HTTPException(status_code=403, detail="Empresa inactiva")
    return company


def whatsapp_link(phone: str, text: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if not digits:
        return ""
    return f"https://wa.me/{digits}?text={quote(text)}"


def client_site_id(user: User) -> int | None:
    if user.role == "client":
        return user.client_site_id
    return None


def ensure_site_access(user: User, site_id: int) -> None:
    cid = client_site_id(user)
    if cid is not None and cid != site_id:
        raise HTTPException(status_code=403, detail="Sin acceso a este sitio")
