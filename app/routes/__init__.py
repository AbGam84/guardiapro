"""Registro central de routers HTTP."""

from fastapi import FastAPI

from app.routes import api, pages
from app.vendor_api import router as vendor_router


def register_routes(app: FastAPI) -> None:
    app.include_router(api.router)
    app.include_router(pages.router)
    app.include_router(vendor_router)
