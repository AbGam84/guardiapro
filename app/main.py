"""Excalibu Sentinel — aplicación FastAPI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import HOST, IS_PRODUCTION, PORT, PRODUCT_NAME, UPLOADS_DIR
from app.database import Base, engine, get_db
from app.migrate import ensure_schema
from app.paths import WEB
from app.routes import register_routes
from app.seed import ensure_admin_access, migrate_demo_to_clean, purge_demo_cameras, seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    db = next(get_db())
    try:
        seed_if_empty(db)
        migrate_demo_to_clean(db)
        purge_demo_cameras(db)
        ensure_admin_access(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=PRODUCT_NAME,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
register_routes(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=not IS_PRODUCTION)
