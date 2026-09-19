"""Rutas del proyecto en disco."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
WEB_APP = WEB  # pantallas operativas (login, admin, guardia…)
WEB_MARKETING = WEB / "marketing"
DOCS = ROOT / "docs"
DATA = ROOT / "data"
