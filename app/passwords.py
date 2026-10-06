"""Contraseñas entregables al cliente (generación segura)."""

from __future__ import annotations

import secrets
import string

# Sin caracteres ambiguos en entrega por WhatsApp
_ALPHABET = "".join(
    ch for ch in (string.ascii_letters + string.digits) if ch not in "0O1lI"
)


def generate_client_password(length: int = 12) -> str:
    length = max(10, min(length, 24))
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
