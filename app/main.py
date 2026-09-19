import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import aiofiles
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, require_roles, verify_password
from app.config import (
    COPYRIGHT,
    HOST,
    IS_PRODUCTION,
    PORT,
    PRODUCT_NAME,
    PUBLIC_BASE_URL,
    SHOW_DEMO_HINTS,
    SUPPORT_WHATSAPP,
    TAGLINE,
    UPLOADS_DIR,
)
from app.database import Base, engine, get_db
from app.helpers import (
    ENTRY_LABELS,
    SEVERITY_LABELS,
    assignment_dict,
    checkpoint_dict,
    company_dict,
    log_dict,
    shift_dict,
    site_dict,
    user_dict,
)
from app.models import (
    ClientSite,
    Company,
    LogEntry,
    PatrolCheckpoint,
    Shift,
    ShiftAssignment,
    User,
)
from app.reports import shift_report_html
from app.schemas import (
    AssignmentIn,
    CheckpointIn,
    CompanySettingsIn,
    LogEntryIn,
    LoginIn,
    ShiftEndIn,
    ShiftStartIn,
    SiteIn,
    UserIn,
)
from app.seed import seed_if_empty
from app.vendor_api import router as vendor_router

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        seed_if_empty(db)
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
app.include_router(vendor_router)


def _company(db: Session, user: User) -> Company:
    c = db.query(Company).filter(Company.id == user.company_id).first()
    if not c or not c.active:
        raise HTTPException(status_code=403, detail="Empresa inactiva")
    return c


def _whatsapp_link(phone: str, text: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if not digits:
        return ""
    return f"https://wa.me/{digits}?text={quote(text)}"


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "product": PRODUCT_NAME,
        "tagline": TAGLINE,
        "production": IS_PRODUCTION,
        "build": "20260919",
    }


@app.get("/api/product")
def product():
    return {
        "name": PRODUCT_NAME,
        "tagline": TAGLINE,
        "copyright": COPYRIGHT,
        "support": SUPPORT_WHATSAPP,
        "show_demo_hints": SHOW_DEMO_HINTS,
        "entry_types": [{"code": k, "label": v} for k, v in ENTRY_LABELS.items()],
        "severities": [{"code": k, "label": v} for k, v in SEVERITY_LABELS.items()],
    }


@app.post("/api/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    uname = (payload.username or "").strip().lower()
    user = db.query(User).filter(User.username == uname, User.active.is_(True)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o clave incorrectos")
    company = _company(db, user)
    code = (payload.company_code or "").strip().lower()
    if code and company.code != code:
        raise HTTPException(status_code=401, detail="Código de empresa incorrecto")
    token = create_access_token(
        {"sub": user.username, "role": user.role, "company_id": user.company_id, "company_code": company.code}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_dict(user),
        "company": company_dict(company),
        "copyright": COPYRIGHT,
    }


@app.get("/api/auth/me")
def me(user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    company = _company(db, user)
    open_shift = (
        db.query(Shift)
        .filter(Shift.guard_id == user.id, Shift.status == "open")
        .order_by(Shift.started_at.desc())
        .first()
    )
    today = datetime.utcnow().date().isoformat()
    my_assignments = []
    if user.role == "guard":
        rows = (
            db.query(ShiftAssignment)
            .filter(
                ShiftAssignment.company_id == user.company_id,
                ShiftAssignment.guard_id == user.id,
                ShiftAssignment.shift_date == today,
            )
            .all()
        )
        my_assignments = [assignment_dict(db, a) for a in rows]
    return {
        "user": user_dict(user),
        "company": company_dict(company),
        "open_shift": shift_dict(db, open_shift) if open_shift else None,
        "assignments_today": my_assignments,
    }


@app.get("/api/sites")
def list_sites(user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    rows = (
        db.query(ClientSite)
        .filter(ClientSite.company_id == user.company_id, ClientSite.active.is_(True))
        .order_by(ClientSite.name.asc())
        .all()
    )
    return {"sites": [site_dict(s) for s in rows]}


@app.post("/api/sites")
def create_site(
    payload: SiteIn,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    row = ClientSite(
        company_id=user.company_id,
        name=payload.name.strip(),
        address=payload.address.strip(),
        client_name=payload.client_name.strip(),
        client_phone=payload.client_phone.strip(),
        notes=payload.notes.strip(),
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"site": site_dict(row)}


@app.get("/api/sites/{site_id}/checkpoints")
def list_checkpoints(
    site_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PatrolCheckpoint)
        .filter(
            PatrolCheckpoint.company_id == user.company_id,
            PatrolCheckpoint.site_id == site_id,
            PatrolCheckpoint.active.is_(True),
        )
        .order_by(PatrolCheckpoint.sort_order.asc())
        .all()
    )
    return {"checkpoints": [checkpoint_dict(c) for c in rows]}


@app.post("/api/checkpoints")
def create_checkpoint(
    payload: CheckpointIn,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    site = (
        db.query(ClientSite)
        .filter(ClientSite.id == payload.site_id, ClientSite.company_id == user.company_id)
        .first()
    )
    if not site:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    row = PatrolCheckpoint(
        company_id=user.company_id,
        site_id=payload.site_id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        sort_order=payload.sort_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"checkpoint": checkpoint_dict(row)}


@app.get("/api/assignments")
def list_assignments(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
    shift_date: str = "",
):
    q = db.query(ShiftAssignment).filter(ShiftAssignment.company_id == user.company_id)
    if shift_date:
        q = q.filter(ShiftAssignment.shift_date == shift_date)
    else:
        q = q.filter(ShiftAssignment.shift_date == datetime.utcnow().date().isoformat())
    rows = q.order_by(ShiftAssignment.start_time.asc()).all()
    return {"assignments": [assignment_dict(db, a) for a in rows]}


@app.post("/api/assignments")
def create_assignment(
    payload: AssignmentIn,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    guard = (
        db.query(User)
        .filter(User.id == payload.guard_id, User.company_id == user.company_id, User.role == "guard")
        .first()
    )
    site = (
        db.query(ClientSite)
        .filter(ClientSite.id == payload.site_id, ClientSite.company_id == user.company_id)
        .first()
    )
    if not guard or not site:
        raise HTTPException(status_code=404, detail="Oficial o sitio no encontrado")
    row = ShiftAssignment(
        company_id=user.company_id,
        site_id=payload.site_id,
        guard_id=payload.guard_id,
        shift_date=payload.shift_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        notes=payload.notes.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"assignment": assignment_dict(db, row)}


@app.get("/api/shifts/active")
def my_active_shift(user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    sh = (
        db.query(Shift)
        .filter(Shift.guard_id == user.id, Shift.status == "open")
        .order_by(Shift.started_at.desc())
        .first()
    )
    return {"shift": shift_dict(db, sh) if sh else None}


@app.post("/api/shifts/start")
def start_shift(
    payload: ShiftStartIn,
    user: Annotated[User, Depends(require_roles("guard", "supervisor", "admin"))],
    db: Session = Depends(get_db),
):
    if user.role == "guard" and db.query(Shift).filter(Shift.guard_id == user.id, Shift.status == "open").first():
        raise HTTPException(status_code=400, detail="Ya tiene un turno abierto")
    site = (
        db.query(ClientSite)
        .filter(ClientSite.id == payload.site_id, ClientSite.company_id == user.company_id, ClientSite.active.is_(True))
        .first()
    )
    if not site:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    assignment = None
    if payload.assignment_id:
        assignment = (
            db.query(ShiftAssignment)
            .filter(ShiftAssignment.id == payload.assignment_id, ShiftAssignment.company_id == user.company_id)
            .first()
        )
        if assignment:
            assignment.status = "active"
    sh = Shift(
        company_id=user.company_id,
        site_id=site.id,
        guard_id=user.id,
        assignment_id=assignment.id if assignment else None,
        status="open",
        start_note=(payload.note or "").strip(),
    )
    db.add(sh)
    db.flush()
    db.add(
        LogEntry(
            company_id=user.company_id,
            shift_id=sh.id,
            guard_id=user.id,
            entry_type="inicio",
            note=(payload.note or f"Inicio de turno en {site.name}").strip(),
        )
    )
    db.commit()
    db.refresh(sh)
    return {"shift": shift_dict(db, sh)}


@app.post("/api/shifts/{shift_id}/log")
def add_log(
    shift_id: int,
    payload: LogEntryIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    sh = (
        db.query(Shift)
        .filter(Shift.id == shift_id, Shift.company_id == user.company_id, Shift.status == "open")
        .first()
    )
    if not sh:
        raise HTTPException(status_code=404, detail="Turno no encontrado o cerrado")
    if user.role == "guard" and sh.guard_id != user.id:
        raise HTTPException(status_code=403, detail="Solo el oficial del turno puede reportar")
    et = (payload.entry_type or "novedad").strip().lower()
    if et not in ENTRY_LABELS:
        raise HTTPException(status_code=400, detail="Tipo inválido")
    sev = (payload.severity or "normal").strip().lower()
    if sev not in SEVERITY_LABELS:
        sev = "normal"
    entry = LogEntry(
        company_id=user.company_id,
        shift_id=sh.id,
        guard_id=user.id,
        checkpoint_id=payload.checkpoint_id,
        entry_type=et,
        severity=sev,
        note=(payload.note or "").strip(),
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    company = _company(db, user)
    site = db.query(ClientSite).filter(ClientSite.id == sh.site_id).first()
    alert = None
    if et == "incidente" and sev in ("alta", "critica"):
        msg = (
            f"INCIDENTE {sev.upper()} — {company.name}\n"
            f"Sitio: {site.name if site else ''}\n"
            f"Oficial: {user.name} ({user.badge})\n"
            f"{entry.note}"
        )
        phone = company.alert_whatsapp or SUPPORT_WHATSAPP
        alert = {"whatsapp_url": _whatsapp_link(phone, msg), "message": msg}
    return {"entry": log_dict(entry), "shift_id": sh.id, "alert": alert}


@app.post("/api/shifts/{shift_id}/log/photo")
async def add_log_photo(
    shift_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    entry_type: str = Form("incidente"),
    note: str = Form(""),
    severity: str = Form("alta"),
    checkpoint_id: int | None = Form(None),
    lat: float | None = Form(None),
    lng: float | None = Form(None),
    photo: UploadFile = File(...),
):
    sh = (
        db.query(Shift)
        .filter(Shift.id == shift_id, Shift.company_id == user.company_id, Shift.status == "open")
        .first()
    )
    if not sh:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if user.role == "guard" and sh.guard_id != user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")
    ext = Path(photo.filename or "foto.jpg").suffix.lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Formato no permitido")
    fname = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOADS_DIR / fname
    async with aiofiles.open(dest, "wb") as f:
        await f.write(await photo.read())
    entry = LogEntry(
        company_id=user.company_id,
        shift_id=sh.id,
        guard_id=user.id,
        checkpoint_id=checkpoint_id,
        entry_type=(entry_type or "incidente").lower(),
        severity=(severity or "alta").lower(),
        note=(note or "Foto adjunta").strip(),
        photo_filename=fname,
        lat=lat,
        lng=lng,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"entry": log_dict(entry)}


@app.post("/api/shifts/{shift_id}/close")
def close_shift(
    shift_id: int,
    payload: ShiftEndIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    sh = (
        db.query(Shift)
        .filter(Shift.id == shift_id, Shift.company_id == user.company_id, Shift.status == "open")
        .first()
    )
    if not sh:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if user.role == "guard" and sh.guard_id != user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")
    sh.status = "closed"
    sh.ended_at = datetime.utcnow()
    sh.end_note = (payload.note or "").strip()
    if sh.assignment_id:
        a = db.query(ShiftAssignment).filter(ShiftAssignment.id == sh.assignment_id).first()
        if a:
            a.status = "done"
    db.add(
        LogEntry(
            company_id=user.company_id,
            shift_id=sh.id,
            guard_id=user.id,
            entry_type="fin",
            note=(payload.note or "Fin de turno").strip(),
        )
    )
    db.commit()
    db.refresh(sh)
    return {"shift": shift_dict(db, sh)}


@app.get("/api/shifts")
def list_shifts(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
    status: str = "",
    guard_id: int = 0,
    site_id: int = 0,
    limit: int = 100,
):
    q = db.query(Shift).filter(Shift.company_id == user.company_id)
    if status:
        q = q.filter(Shift.status == status.strip().lower())
    if guard_id:
        q = q.filter(Shift.guard_id == guard_id)
    if site_id:
        q = q.filter(Shift.site_id == site_id)
    rows = q.order_by(Shift.started_at.desc()).limit(min(limit, 500)).all()
    return {"shifts": [shift_dict(db, s) for s in rows]}


@app.get("/api/shifts/{shift_id}")
def get_shift(
    shift_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    sh = db.query(Shift).filter(Shift.id == shift_id, Shift.company_id == user.company_id).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if user.role == "guard" and sh.guard_id != user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")
    return {"shift": shift_dict(db, sh)}


@app.get("/api/shifts/{shift_id}/report")
def shift_report(
    shift_id: int,
    user: Annotated[User, Depends(require_roles("admin", "supervisor", "guard"))],
    db: Session = Depends(get_db),
):
    sh = db.query(Shift).filter(Shift.id == shift_id, Shift.company_id == user.company_id).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if user.role == "guard" and sh.guard_id != user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")
    html = shift_report_html(db, shift_id, user.company_id)
    return HTMLResponse(html)


@app.get("/api/dashboard")
def dashboard(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    guards = db.query(User).filter(User.company_id == user.company_id, User.role == "guard", User.active.is_(True)).count()
    sites = db.query(ClientSite).filter(ClientSite.company_id == user.company_id, ClientSite.active.is_(True)).count()
    open_shifts = db.query(Shift).filter(Shift.company_id == user.company_id, Shift.status == "open").count()
    today = datetime.utcnow().date()
    logs_today = (
        db.query(LogEntry)
        .filter(
            LogEntry.company_id == user.company_id,
            LogEntry.created_at >= datetime(today.year, today.month, today.day),
        )
        .count()
    )
    incidents = (
        db.query(LogEntry)
        .filter(LogEntry.company_id == user.company_id, LogEntry.entry_type == "incidente")
        .order_by(LogEntry.created_at.desc())
        .limit(15)
        .all()
    )
    open_list = (
        db.query(Shift)
        .filter(Shift.company_id == user.company_id, Shift.status == "open")
        .order_by(Shift.started_at.desc())
        .limit(20)
        .all()
    )
    return {
        "guards": guards,
        "sites": sites,
        "open_shifts": open_shifts,
        "logs_today": logs_today,
        "recent_incidents": [log_dict(x) for x in incidents],
        "active_shifts": [shift_dict(db, s, include_logs=False) for s in open_list],
    }


@app.get("/api/guards")
def list_guards(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    rows = (
        db.query(User)
        .filter(User.company_id == user.company_id, User.role == "guard", User.active.is_(True))
        .order_by(User.name.asc())
        .all()
    )
    return {"guards": [user_dict(u) for u in rows]}


@app.post("/api/users")
def create_user(
    payload: UserIn,
    user: Annotated[User, Depends(require_roles("admin"))],
    db: Session = Depends(get_db),
):
    if payload.role not in ("admin", "supervisor", "guard"):
        raise HTTPException(status_code=400, detail="Rol inválido")
    uname = payload.username.strip().lower()
    if db.query(User).filter(User.username == uname).first():
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    row = User(
        company_id=user.company_id,
        name=payload.name.strip(),
        username=uname,
        password_hash=hash_password(payload.password),
        role=payload.role,
        badge=payload.badge.strip(),
        phone=payload.phone.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"user": user_dict(row)}


@app.patch("/api/company/settings")
def update_company_settings(
    payload: CompanySettingsIn,
    user: Annotated[User, Depends(require_roles("admin"))],
    db: Session = Depends(get_db),
):
    company = _company(db, user)
    if payload.name.strip():
        company.name = payload.name.strip()
    company.phone = payload.phone.strip() or company.phone
    company.alert_whatsapp = payload.alert_whatsapp.strip() or company.alert_whatsapp
    db.commit()
    return {"company": company_dict(company)}


def _html(name: str) -> HTMLResponse:
    path = WEB / name
    if not path.exists():
        raise HTTPException(status_code=404)
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/")
def root():
    return FileResponse(WEB / "login.html")


@app.get("/login")
def page_login():
    return _html("login.html")


@app.get("/guardia")
def page_guard():
    return _html("guardia.html")


@app.get("/admin")
def page_admin():
    return _html("admin.html")


@app.get("/vendor")
def page_vendor():
    return _html("vendor.html")


@app.get("/manifest.json")
def manifest():
    return FileResponse(WEB / "manifest.json")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=not IS_PRODUCTION)
