"""Marca pública por empresa (login, API)."""

from __future__ import annotations

import re

from app.company_logo import company_logo_path
from app.helpers import company_dict
from app.models import Company


def format_phone_cr(phone: str, whatsapp: str) -> tuple[str, str]:
    raw = (phone or whatsapp or "").strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 8:
        digits = "506" + digits
    elif len(digits) == 11 and digits.startswith("506"):
        pass
    elif len(digits) > 8:
        digits = "506" + digits[-8:]
    if len(digits) < 11:
        return raw, ""
    display = f"+506 {digits[3:7]} {digits[7:11]}"
    tel = f"+{digits}"
    return display, tel


def public_branding_payload(company: Company) -> dict:
    tagline = (getattr(company, "brand_tagline", None) or "").strip() or "Seguridad privada"
    phone_display, phone_tel = format_phone_cr(company.phone, company.alert_whatsapp)
    wa_digits = re.sub(r"\D", "", company.alert_whatsapp or company.phone or "")
    if len(wa_digits) == 8:
        wa_digits = "506" + wa_digits
    elif len(wa_digits) > 8 and not wa_digits.startswith("506"):
        wa_digits = "506" + wa_digits[-8:]
    return {
        "code": company.code,
        "name": company.name,
        "tagline": tagline,
        "phone_display": phone_display,
        "phone_tel": phone_tel,
        "whatsapp_url": f"https://wa.me/{wa_digits}" if len(wa_digits) >= 11 else "",
        "logo_url": company_dict(company, include_subscription=False).get("logo_url") or "",
        "has_logo": bool(company.logo_filename or company_logo_path(company.id, "")),
    }
