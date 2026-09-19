"""Panel vendor — crear empresas de seguridad (multi-tenant)."""

from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import ALGORITHM, create_access_token, hash_password, security
from app.config import COPYRIGHT, PRODUCT_NAME, SECRET_KEY, VENDOR_NAME, VENDOR_PASSWORD, VENDOR_USERNAME
from app.database import get_db
from app.helpers import company_dict, user_dict
from app.models import ClientSite, Company, PatrolCheckpoint, Shift, User

router = APIRouter(prefix="/api/vendor", tags=["vendor"])


class VendorLoginIn(BaseModel):
    username: str
    password: str


class CompanyCreateIn(BaseModel):
    name: str
    code: str = ""
    phone: str = ""
    alert_whatsapp: str = ""
    admin_name: str = "Administrador"
    admin_username: str = "admin"
    admin_password: str = Field(min_length=6)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return (text or "empresa")[:36]


def get_vendor(creds=Depends(security)):
    if creds is None:
        raise HTTPException(status_code=401, detail="Vendor: inicie sesión")
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc
    if payload.get("role") != "vendor" or payload.get("sub") != VENDOR_USERNAME:
        raise HTTPException(status_code=403, detail="Solo vendor GuardiaPro")
    return {"username": VENDOR_USERNAME, "name": VENDOR_NAME}


@router.post("/login")
def vendor_login(payload: VendorLoginIn):
    if payload.username.strip() != VENDOR_USERNAME or payload.password != VENDOR_PASSWORD:
        raise HTTPException(status_code=401, detail="Usuario o clave vendor incorrectos")
    token = create_access_token({"sub": VENDOR_USERNAME, "role": "vendor"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"username": VENDOR_USERNAME, "name": VENDOR_NAME, "role": "vendor"},
        "product": PRODUCT_NAME,
        "copyright": COPYRIGHT,
    }


@router.get("/overview")
def vendor_overview(db: Session = Depends(get_db), vendor=Depends(get_vendor)):
    companies = db.query(Company).order_by(Company.id.desc()).all()
    users = db.query(User).order_by(User.id.desc()).limit(200).all()
    open_shifts = db.query(Shift).filter(Shift.status == "open").count()
    return {
        "companies_count": len(companies),
        "users_count": len(users),
        "open_shifts": open_shifts,
        "companies": [company_dict(c) for c in companies],
        "users": [user_dict(u) for u in users],
    }


@router.post("/companies")
def vendor_create_company(payload: CompanyCreateIn, db: Session = Depends(get_db), vendor=Depends(get_vendor)):
    code = slugify(payload.code or payload.name)
    base = code
    n = 2
    while db.query(Company).filter(Company.code == code).first():
        code = f"{base}-{n}"
        n += 1
    if db.query(User).filter(User.username == payload.admin_username.strip().lower()).first():
        raise HTTPException(status_code=400, detail="Usuario admin ya existe")
    company = Company(
        code=code,
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        alert_whatsapp=payload.alert_whatsapp.strip(),
    )
    db.add(company)
    db.flush()
    admin = User(
        company_id=company.id,
        name=payload.admin_name.strip(),
        username=payload.admin_username.strip().lower(),
        password_hash=hash_password(payload.admin_password),
        role="admin",
        badge="ADM-001",
    )
    db.add(admin)
    db.commit()
    db.refresh(company)
    return {
        "ok": True,
        "company": company_dict(company),
        "admin": user_dict(admin),
        "login_url": "/login",
        "message": f"Empresa «{company.name}» creada. Código: {company.code}",
    }
