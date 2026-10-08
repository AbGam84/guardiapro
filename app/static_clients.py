"""Marca de clientes empaquetada en repo (funciona aunque la DB esté vacía)."""

from __future__ import annotations

from app.company_logo import static_client_logo_web_url
from app.public_brand import format_phone_cr

# Metadatos mínimos por código URL — logo en web/static/clients/{code}-logo.*
STATIC_CLIENTS: dict[str, dict[str, str]] = {
    "grupo-gomez": {
        "name": "Grupo Gómez y Asociados",
        "brand_tagline": "Seguridad privada",
        "phone": "+506 6070 9197",
        "alert_whatsapp": "50660709197",
    },
}


def static_branding_payload(company_code: str) -> dict | None:
    code = (company_code or "").strip().lower()
    if not code:
        return None
    logo = static_client_logo_web_url(code)
    meta = STATIC_CLIENTS.get(code)
    if not logo and not meta:
        return None
    meta = meta or {}
    phone_display, phone_tel = format_phone_cr(meta.get("phone", ""), meta.get("alert_whatsapp", ""))
    wa_digits = "".join(ch for ch in (meta.get("alert_whatsapp") or meta.get("phone") or "") if ch.isdigit())
    if len(wa_digits) == 8:
        wa_digits = "506" + wa_digits
    return {
        "code": code,
        "name": meta.get("name") or code.replace("-", " ").title(),
        "tagline": meta.get("brand_tagline") or "Seguridad privada",
        "phone_display": phone_display,
        "phone_tel": phone_tel,
        "whatsapp_url": f"https://wa.me/{wa_digits}" if len(wa_digits) >= 11 else "",
        "logo_url": logo or "",
        "has_logo": bool(logo),
    }
