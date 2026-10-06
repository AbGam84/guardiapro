"""Licencia mensual por empresa."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException

from app.models import Company, User, utcnow

DEFAULT_MONTHLY_FEE_CRC = 58_000
DEFAULT_MAX_OFFICERS = 10


def extend_paid_until(company: Company, months: int = 1) -> None:
    months = max(1, min(months, 36))
    base = company.paid_until if company.paid_until and company.paid_until > utcnow() else utcnow()
    company.paid_until = base + timedelta(days=30 * months)
    company.subscription_status = "active"


def subscription_public(company: Company) -> dict:
    guards_used = getattr(company, "_guards_count", None)
    return {
        "plan": company.subscription_plan or "monthly",
        "monthly_fee_crc": int(company.monthly_fee_crc or DEFAULT_MONTHLY_FEE_CRC),
        "max_officers": int(company.max_officers or DEFAULT_MAX_OFFICERS),
        "subscription_status": company.subscription_status or "active",
        "paid_until": company.paid_until.isoformat() if company.paid_until else None,
        "guards_used": guards_used,
        "is_operational": subscription_allows_access(company),
    }


def subscription_allows_access(company: Company) -> bool:
    if not company.active:
        return False
    status = (company.subscription_status or "active").lower()
    if status == "suspended":
        return False
    if company.paid_until and company.paid_until < utcnow():
        return False
    return status in {"active", "trial", "past_due"}


def assert_subscription_active(company: Company) -> None:
    if subscription_allows_access(company):
        return
    status = (company.subscription_status or "").lower()
    if company.paid_until and company.paid_until < utcnow():
        raise HTTPException(
            status_code=402,
            detail=(
                "Licencia mensual vencida. Renueve con AbSol@r Costa Rica "
                "(WhatsApp +506 6370-6546 · soporte@absolar.latam)."
            ),
        )
    if status == "suspended":
        raise HTTPException(
            status_code=402,
            detail="Licencia suspendida. Contacte a AbSol@r para reactivar el servicio.",
        )
    raise HTTPException(status_code=402, detail="Licencia no activa. Contacte a AbSol@r Costa Rica.")


def assert_can_add_guard(db, company: Company) -> None:
    limit = int(company.max_officers or DEFAULT_MAX_OFFICERS)
    count = (
        db.query(User)
        .filter(User.company_id == company.id, User.role == "guard", User.active.is_(True))
        .count()
    )
    if count >= limit:
        raise HTTPException(
            status_code=400,
            detail=f"Límite de oficiales ({limit}) alcanzado. Suba de plan en el panel comercial.",
        )
