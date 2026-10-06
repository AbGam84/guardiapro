"""Panel comercial — vender licencias y crear admins / oficiales con código."""

from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import ALGORITHM, create_access_token, hash_password, security
from app.config import (
    COMPANY_NAME,
    COPYRIGHT,
    PRODUCT_NAME,
    SECRET_KEY,
    SUPPORT_WHATSAPP_DISPLAY,
    VENDOR_NAME,
    VENDOR_PASSWORD,
    VENDOR_USERNAME,
)
from app.database import get_db
from app.field_codes import generate_field_code
from app.helpers import company_dict, user_dict
from app.models import ClientSite, Company, Shift, User
from app.passwords import generate_client_password
from app.subscription import (
    assert_can_add_guard,
    extend_paid_until,
    refresh_subscription_status,
    subscription_allows_access,
)

router = APIRouter(prefix="/api/vendor", tags=["vendor"])


class VendorLoginIn(BaseModel):
    username: str
    password: str


class CompanyCreateIn(BaseModel):
    name: str
    code: str = ""
    phone: str = ""
    alert_whatsapp: str = ""
    monthly_fee_crc: int = Field(default=58000, ge=0)
    max_officers: int = Field(default=10, ge=1, le=500)
    prepaid_months: int = Field(default=1, ge=1, le=36)
    admin_name: str = "Administrador"
    admin_username: str = "admin"
    admin_password: str | None = None
    auto_password: bool = True


class VendorSubscriptionIn(BaseModel):
    monthly_fee_crc: int | None = Field(default=None, ge=0)
    max_officers: int | None = Field(default=None, ge=1, le=500)
    subscription_status: str = ""
    add_months: int = Field(default=0, ge=0, le=36)


class VendorUserIn(BaseModel):
    name: str
    username: str
    password: str | None = None
    auto_password: bool = True
    role: str = "guard"
    badge: str = ""
    phone: str = ""
    client_site_id: int | None = None


class VendorResetPasswordIn(BaseModel):
    password: str = Field(min_length=6)


def _plain_password_for_client(raw: str, auto: bool) -> tuple[str, bool]:
    """Devuelve (clave en claro, fue_generada)."""
    plain = (raw or "").strip()
    if auto:
        if not plain:
            return generate_client_password(), True
        if len(plain) < 6:
            raise HTTPException(status_code=400, detail="La clave manual debe tener al menos 6 caracteres")
        return plain, False
    if not plain:
        raise HTTPException(status_code=400, detail="Indique clave o active «Generar clave automática»")
    if len(plain) < 6:
        raise HTTPException(status_code=400, detail="La clave manual debe tener al menos 6 caracteres")
    return plain, False


def _client_credentials_block(company: Company, username: str, password: str, portal: str) -> dict:
    refresh_subscription_status(company)
    until = company.paid_until.isoformat() if company.paid_until else None
    return {
        "portal": portal,
        "login_url": "/login",
        "username": username,
        "password": password,
        "company_code": company.code,
        "paid_until": until,
        "note": (
            "Entregue usuario y clave al cliente. Si la licencia vence, el login se bloquea; "
            "al sumar meses pagados en este panel se reactiva sin cambiar usuario ni clave."
        ),
    }


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return (text or "empresa")[:36]


def get_vendor(creds=Depends(security)):
    if creds is None:
        raise HTTPException(status_code=401, detail="Panel comercial: inicie sesión")
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc
    if payload.get("role") != "vendor" or payload.get("sub") != VENDOR_USERNAME:
        raise HTTPException(status_code=403, detail="Solo panel comercial Excalibu")
    return {"username": VENDOR_USERNAME, "name": VENDOR_NAME}


def _guard_payload(u: User) -> dict:
    d = user_dict(u)
    d["field_login_path"] = f"/oficial?code={u.field_code}" if u.field_code else ""
    return d


@router.post("/login")
def vendor_login(payload: VendorLoginIn):
    if payload.username.strip() != VENDOR_USERNAME or payload.password != VENDOR_PASSWORD:
        raise HTTPException(status_code=401, detail="Usuario o clave comercial incorrectos")
    token = create_access_token({"sub": VENDOR_USERNAME, "role": "vendor"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"username": VENDOR_USERNAME, "name": VENDOR_NAME, "role": "vendor"},
        "product": PRODUCT_NAME,
        "copyright": COPYRIGHT,
        "distributor": COMPANY_NAME,
    }


@router.get("/overview")
def vendor_overview(db: Session = Depends(get_db), vendor=Depends(get_vendor)):
    companies = db.query(Company).filter(Company.active.is_(True)).order_by(Company.id.desc()).all()
    for c in companies:
        refresh_subscription_status(c)
    db.commit()
    guards = db.query(User).filter(User.role == "guard", User.active.is_(True)).count()
    admins = db.query(User).filter(User.role == "admin", User.active.is_(True)).count()
    open_shifts = db.query(Shift).filter(Shift.status == "open").count()
    return {
        "companies_count": len(companies),
        "guards_count": guards,
        "admins_count": admins,
        "open_shifts": open_shifts,
        "companies": [company_dict(c) for c in companies],
        "support_whatsapp": SUPPORT_WHATSAPP_DISPLAY,
    }


@router.post("/companies")
def vendor_create_company(payload: CompanyCreateIn, db: Session = Depends(get_db), vendor=Depends(get_vendor)):
    code = slugify(payload.code or payload.name)
    base = code
    n = 2
    while db.query(Company).filter(Company.code == code).first():
        code = f"{base}-{n}"
        n += 1
    uname = payload.admin_username.strip().lower()
    if db.query(User).filter(User.username == uname).first():
        raise HTTPException(status_code=400, detail="Usuario admin ya existe — elija otro")
    admin_plain, generated = _plain_password_for_client(payload.admin_password or "", payload.auto_password)
    company = Company(
        code=code,
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        alert_whatsapp=payload.alert_whatsapp.strip(),
        subscription_plan="monthly",
        monthly_fee_crc=int(payload.monthly_fee_crc),
        max_officers=int(payload.max_officers),
        subscription_status="active",
    )
    extend_paid_until(company, payload.prepaid_months)
    db.add(company)
    db.flush()
    admin = User(
        company_id=company.id,
        name=payload.admin_name.strip(),
        username=uname,
        password_hash=hash_password(admin_plain),
        role="admin",
        badge="ADM-001",
    )
    db.add(admin)
    db.commit()
    db.refresh(company)
    db.refresh(admin)
    creds = _client_credentials_block(company, admin.username, admin_plain, "/admin")
    creds["admin_url"] = "/admin"
    creds["password_generated"] = generated
    return {
        "ok": True,
        "company": company_dict(company),
        "admin": user_dict(admin),
        "credentials": creds,
        "message": f"Empresa «{company.name}» lista. Copie la clave y entréguela al cliente.",
    }


@router.patch("/companies/{company_id}/subscription")
def vendor_update_subscription(
    company_id: int,
    payload: VendorSubscriptionIn,
    db: Session = Depends(get_db),
    vendor=Depends(get_vendor),
):
    company = db.query(Company).filter(Company.id == company_id, Company.active.is_(True)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if payload.monthly_fee_crc is not None:
        company.monthly_fee_crc = int(payload.monthly_fee_crc)
    if payload.max_officers is not None:
        company.max_officers = int(payload.max_officers)
    status = (payload.subscription_status or "").strip().lower()
    if status in ("active", "trial", "past_due", "suspended"):
        company.subscription_status = status
    reactivated = False
    if payload.add_months:
        extend_paid_until(company, payload.add_months)
        reactivated = True
    db.commit()
    db.refresh(company)
    msg = "Licencia actualizada."
    if reactivated:
        msg = (
            f"Licencia extendida {payload.add_months} mes(es). "
            "El cliente entra con el mismo usuario y clave — no hace falta restablecer."
        )
    return {
        "ok": True,
        "company": company_dict(company),
        "message": msg,
        "operational": subscription_allows_access(company),
    }


@router.get("/companies/{company_id}")
def vendor_company_detail(company_id: int, db: Session = Depends(get_db), vendor=Depends(get_vendor)):
    company = db.query(Company).filter(Company.id == company_id, Company.active.is_(True)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    users = (
        db.query(User)
        .filter(User.company_id == company_id, User.active.is_(True))
        .order_by(User.role.asc(), User.name.asc())
        .all()
    )
    changed = False
    for u in users:
        if u.role == "guard" and not u.field_code:
            u.field_code = generate_field_code(db, company_id)
            changed = True
    if changed:
        db.commit()
        for u in users:
            db.refresh(u)
    sites = db.query(ClientSite).filter(ClientSite.company_id == company_id, ClientSite.active.is_(True)).count()
    guards = [_guard_payload(u) for u in users if u.role == "guard"]
    admins = [user_dict(u) for u in users if u.role == "admin"]
    supervisors = [user_dict(u) for u in users if u.role == "supervisor"]
    return {
        "company": company_dict(company),
        "sites_count": sites,
        "admins": admins,
        "supervisors": supervisors,
        "guards": guards,
        "open_shifts": db.query(Shift).filter(Shift.company_id == company_id, Shift.status == "open").count(),
    }


@router.post("/companies/{company_id}/users")
def vendor_create_user(
    company_id: int,
    payload: VendorUserIn,
    db: Session = Depends(get_db),
    vendor=Depends(get_vendor),
):
    company = db.query(Company).filter(Company.id == company_id, Company.active.is_(True)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    role = (payload.role or "guard").strip().lower()
    if role not in ("admin", "supervisor", "guard"):
        raise HTTPException(status_code=400, detail="Rol inválido")
    if role == "guard":
        assert_can_add_guard(db, company)
    uname = payload.username.strip().lower()
    if db.query(User).filter(User.username == uname).first():
        raise HTTPException(status_code=400, detail="Usuario ya existe globalmente")
    plain, generated = _plain_password_for_client(payload.password or "", payload.auto_password)
    home_site = payload.client_site_id
    if home_site:
        site = (
            db.query(ClientSite)
            .filter(ClientSite.id == home_site, ClientSite.company_id == company.id)
            .first()
        )
        if not site:
            raise HTTPException(status_code=404, detail="Sitio no encontrado")
    row = User(
        company_id=company.id,
        name=payload.name.strip(),
        username=uname,
        password_hash=hash_password(plain),
        role=role,
        badge=payload.badge.strip(),
        phone=payload.phone.strip(),
        client_site_id=home_site if role in ("guard", "client") else None,
    )
    db.add(row)
    db.flush()
    if role == "guard":
        row.field_code = generate_field_code(db, company.id)
    db.commit()
    db.refresh(row)
    out = user_dict(row)
    if role == "guard":
        out = _guard_payload(row)
    portal = "/admin" if role in ("admin", "supervisor") else "/oficial"
    creds = _client_credentials_block(company, row.username, plain, portal)
    creds["field_code"] = row.field_code or None
    creds["password_generated"] = generated
    return {
        "user": out,
        "credentials": creds,
        "message": f"Usuario {role} creado para {company.name}. Copie la clave para el cliente.",
    }


@router.post("/companies/{company_id}/reactivate")
def vendor_reactivate_month(
    company_id: int,
    months: int = 1,
    db: Session = Depends(get_db),
    vendor=Depends(get_vendor),
):
    """Cliente pagó mensualidad: extiende licencia sin tocar usuario/clave."""
    company = db.query(Company).filter(Company.id == company_id, Company.active.is_(True)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    months = max(1, min(months, 36))
    extend_paid_until(company, months)
    db.commit()
    db.refresh(company)
    return {
        "ok": True,
        "company": company_dict(company),
        "operational": subscription_allows_access(company),
        "message": (
            f"Servicio reactivado {months} mes(es). Mismo usuario y contraseña en /login — "
            "no restablezca la clave salvo que el cliente lo pida."
        ),
    }


@router.post("/companies/{company_id}/users/{user_id}/reset-password")
def vendor_reset_user_password(
    company_id: int,
    user_id: int,
    payload: VendorResetPasswordIn,
    db: Session = Depends(get_db),
    vendor=Depends(get_vendor),
):
    row = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.company_id == company_id,
            User.active.is_(True),
            User.role.in_(("admin", "supervisor")),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")
    row.password_hash = hash_password(payload.password)
    db.commit()
    return {
        "ok": True,
        "user": user_dict(row),
        "message": f"Clave restablecida para «{row.username}». Entrada: /login",
        "login": {"url": "/login", "username": row.username, "company_code_hint": "Dejar vacío"},
    }


@router.post("/guards/{guard_id}/field-code")
def vendor_regenerate_field_code(
    guard_id: int,
    db: Session = Depends(get_db),
    vendor=Depends(get_vendor),
):
    guard = (
        db.query(User)
        .filter(User.id == guard_id, User.role == "guard", User.active.is_(True))
        .first()
    )
    if not guard:
        raise HTTPException(status_code=404, detail="Oficial no encontrado")
    guard.field_code = generate_field_code(db, guard.company_id)
    db.commit()
    db.refresh(guard)
    return {"guard": _guard_payload(guard)}
