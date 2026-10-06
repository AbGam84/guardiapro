"""Etiquetas de producto — puestos fijos vs personas."""

from app.config import _env

# Empresas con rotación alta: el login es por puesto (Lima1), no por nombre de persona.
POST_MODE = _env("GUARDIA_POST_MODE", "1") in {"1", "true", "yes", "on"}


def labels() -> dict:
    if POST_MODE:
        return {
            "guard_unit": "Puesto",
            "guard_unit_plural": "Puestos",
            "guard_unit_lower": "puesto",
            "guard_field_hint": "Código del puesto (ej. Lima1) — no nombre de persona",
            "guard_badge_hint": "Ref. interna (ej. LIMA-1)",
            "person_on_shift": "Persona en turno (opcional, bitácora)",
        }
    return {
        "guard_unit": "Oficial",
        "guard_unit_plural": "Oficiales",
        "guard_unit_lower": "oficial",
        "guard_field_hint": "Nombre completo del oficial",
        "guard_badge_hint": "Placa / badge",
        "person_on_shift": "",
    }
