"""API REST — Excalibu Sentinel."""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, require_roles, verify_password
from app.camera_util import BRANDS, CAMERA_TYPES
from app.config import (
    COPYRIGHT,
    COMPANY_NAME,
    COMPANY_TAGLINE,
    IS_PRODUCTION,
    PRODUCT_NAME,
    SHOW_DEMO_HINTS,
    SUPPORT_WHATSAPP,
    SUPPORT_WHATSAPP_DISPLAY,
    SLOGAN,
    TAGLINE,
    UPLOADS_DIR,
)
from app.database import get_db
from app.deps import client_site_id, ensure_site_access, get_company, public_base, whatsapp_link
from app.field_codes import generate_field_code
from app.geo import format_distance, haversine_m
from app.helpers import (
    ENTRY_LABELS,
    SEVERITY_LABELS,
    assignment_dict,
    camera_dict,
    checkpoint_dict,
    company_dict,
    log_dict,
    shift_dict,
    site_dict,
    user_dict,
)
from app.models import (
    ClientSite,
    LogEntry,
    PatrolCheckpoint,
    PatrolMissedAlert,
    PatrolRoundSchedule,
    SecurityCamera,
    Shift,
    ShiftAssignment,
    User,
)
from app.patrol_alerts import alert_dict, check_missed_rounds, list_missed_alerts, schedule_dict
from app.patrol_stats import patrol_period_stats, shift_patrol_stats
from app.qr_util import checkpoint_scan_url, qr_png
from app.reports import patrol_report_html, shift_report_html
from app.schemas import (
    AssignmentIn,
    CameraIn,
    CameraUpdateIn,
    CheckpointIn,
    CompanySettingsIn,
    LogEntryIn,
    FieldCodeLoginIn,
    LoginIn,
    PatrolScheduleIn,
    QrScanIn,
    ShiftEndIn,
    ShiftStartIn,
    SiteIn,
    UserIn,
)

router = APIRouter()
@router.get("/health")
def health_short():
    return RedirectResponse("/api/health", status_code=307)


@router.get("/api/health")
def health():
    return {
        "ok": True,
        "product": PRODUCT_NAME,
        "slogan": SLOGAN,
        "tagline": TAGLINE,
        "production": IS_PRODUCTION,
        "build": "20260925",
    }


@router.get("/api/product")
def product():
    wa_digits = "".join(ch for ch in SUPPORT_WHATSAPP if ch.isdigit())
    return {
        "name": PRODUCT_NAME,
        "company_name": COMPANY_NAME,
        "company_tagline": COMPANY_TAGLINE,
        "slogan": SLOGAN,
        "tagline": TAGLINE,
        "copyright": COPYRIGHT,
        "support_display": SUPPORT_WHATSAPP_DISPLAY,
        "whatsapp_url": f"https://wa.me/{wa_digits}",
        "differentiators": [
            "Meta-capa: audita la operación de su propia empresa de seguridad",
            "QR imprimible + distancia de recorrido GPS por guardia",
            "Cámaras WiFi, NVR y DVR del sitio en la misma app del oficial",
            "Reportes semanal y quincenal listos para el cliente final",
            "Sin lectores NFC ni hardware extra — celular + QR en muro",
            "Demo en vivo en 2 minutos, despliegue Costa Rica / LATAM",
        ],
        "support": SUPPORT_WHATSAPP,
        "show_demo_hints": SHOW_DEMO_HINTS,
        "entry_types": [{"code": k, "label": v} for k, v in ENTRY_LABELS.items()],
        "severities": [{"code": k, "label": v} for k, v in SEVERITY_LABELS.items()],
    }


@router.post("/api/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    uname = (payload.username or "").strip().lower()
    user = db.query(User).filter(User.username == uname, User.active.is_(True)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o clave incorrectos")
    company = get_company(db, user)
    code = (payload.company_code or "").strip().lower()
    legacy_codes = {"demo-seguridad", "demo", "guardiapro", "excalibu", "excalibu-telecom"}
    if code and company.code != code and code not in legacy_codes:
        raise HTTPException(
            status_code=401,
            detail=f"Código de empresa incorrecto. Use «{company.code}» o deje el campo vacío.",
        )
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


@router.post("/api/auth/login-code")
def login_field_code(payload: FieldCodeLoginIn, db: Session = Depends(get_db)):
    code = (payload.field_code or "").strip()
    user = (
        db.query(User)
        .filter(
            User.field_code == code,
            User.role == "guard",
            User.active.is_(True),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="Código de oficial incorrecto")
    company = get_company(db, user)
    token = create_access_token(
        {"sub": user.username, "role": user.role, "company_id": user.company_id, "company_code": company.code}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_dict(user),
        "company": company_dict(company),
    }


@router.get("/api/auth/me")
def me(user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    company = get_company(db, user)
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


@router.get("/api/sites")
def list_sites(user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    q = db.query(ClientSite).filter(ClientSite.company_id == user.company_id, ClientSite.active.is_(True))
    cid = client_site_id(user)
    if cid:
        q = q.filter(ClientSite.id == cid)
    rows = q.order_by(ClientSite.name.asc()).all()
    return {"sites": [site_dict(s) for s in rows]}


@router.post("/api/sites")
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


def _valid_camera_type(t: str) -> str:
    t = (t or "wifi").strip().lower()
    if t not in CAMERA_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {', '.join(CAMERA_TYPES)}")
    return t


@router.get("/api/camera-meta")
def camera_meta():
    return {"types": CAMERA_TYPES, "brands": BRANDS}


@router.get("/api/sites/{site_id}/cameras")
def list_site_cameras(
    site_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    site = (
        db.query(ClientSite)
        .filter(ClientSite.id == site_id, ClientSite.company_id == user.company_id)
        .first()
    )
    if not site:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    show_secrets = user.role in ("admin", "supervisor")
    rows = (
        db.query(SecurityCamera)
        .filter(
            SecurityCamera.company_id == user.company_id,
            SecurityCamera.site_id == site_id,
            SecurityCamera.active.is_(True),
        )
        .order_by(SecurityCamera.camera_type.asc(), SecurityCamera.name.asc())
        .all()
    )
    return {"cameras": [camera_dict(c, show_secrets=show_secrets) for c in rows]}


@router.post("/api/cameras")
def create_camera(
    payload: CameraIn,
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
    cam_type = _valid_camera_type(payload.camera_type)
    if payload.parent_id:
        parent = (
            db.query(SecurityCamera)
            .filter(
                SecurityCamera.id == payload.parent_id,
                SecurityCamera.company_id == user.company_id,
                SecurityCamera.site_id == payload.site_id,
            )
            .first()
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Grabador NVR/DVR no encontrado")
    row = SecurityCamera(
        company_id=user.company_id,
        site_id=payload.site_id,
        parent_id=payload.parent_id,
        camera_type=cam_type,
        name=payload.name.strip(),
        brand=(payload.brand or "other").strip().lower(),
        model_name=payload.model_name.strip(),
        location=payload.location.strip(),
        ip_address=payload.ip_address.strip(),
        rtsp_port=payload.rtsp_port or 554,
        http_port=payload.http_port or 80,
        channel=max(1, payload.channel or 1),
        username=payload.username.strip(),
        password=payload.password,
        rtsp_url=payload.rtsp_url.strip(),
        stream_url=payload.stream_url.strip(),
        web_url=payload.web_url.strip(),
        onvif_port=payload.onvif_port or 80,
        notes=payload.notes.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"camera": camera_dict(row, show_secrets=True)}


@router.get("/api/cameras/{camera_id}")
def get_camera(
    camera_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    row = (
        db.query(SecurityCamera)
        .filter(SecurityCamera.id == camera_id, SecurityCamera.company_id == user.company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    show_secrets = user.role in ("admin", "supervisor")
    return {"camera": camera_dict(row, show_secrets=show_secrets)}


@router.patch("/api/cameras/{camera_id}")
def update_camera(
    camera_id: int,
    payload: CameraUpdateIn,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    row = (
        db.query(SecurityCamera)
        .filter(SecurityCamera.id == camera_id, SecurityCamera.company_id == user.company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    data = payload.model_dump(exclude_unset=True)
    if "camera_type" in data and data["camera_type"]:
        data["camera_type"] = _valid_camera_type(data["camera_type"])
    if "brand" in data and data["brand"]:
        data["brand"] = data["brand"].strip().lower()
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return {"camera": camera_dict(row, show_secrets=True)}


@router.delete("/api/cameras/{camera_id}")
def delete_camera(
    camera_id: int,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    row = (
        db.query(SecurityCamera)
        .filter(SecurityCamera.id == camera_id, SecurityCamera.company_id == user.company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    row.active = False
    db.commit()
    return {"ok": True}


@router.get("/api/sites/{site_id}/checkpoints")
def list_checkpoints(
    site_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    base = public_base(request)
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
    return {
        "checkpoints": [
            checkpoint_dict(c, qr_url=checkpoint_scan_url(base, c.qr_token) if c.qr_token else "")
            for c in rows
        ]
    }


@router.post("/api/checkpoints")
def create_checkpoint(
    payload: CheckpointIn,
    request: Request,
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
        qr_token=uuid.uuid4().hex,
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    base = public_base(request)
    return {"checkpoint": checkpoint_dict(row, qr_url=checkpoint_scan_url(base, row.qr_token))}


@router.post("/api/checkpoints/scan")
def scan_checkpoint_qr(
    payload: QrScanIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    token = (payload.qr_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="QR inválido")
    cp = (
        db.query(PatrolCheckpoint)
        .filter(
            PatrolCheckpoint.qr_token == token,
            PatrolCheckpoint.company_id == user.company_id,
            PatrolCheckpoint.active.is_(True),
        )
        .first()
    )
    if not cp:
        raise HTTPException(status_code=404, detail="Punto de control no encontrado")
    sh = (
        db.query(Shift)
        .filter(Shift.guard_id == user.id, Shift.status == "open", Shift.company_id == user.company_id)
        .order_by(Shift.started_at.desc())
        .first()
    )
    if not sh:
        raise HTTPException(status_code=400, detail="Debe tener un turno abierto para marcar QR")
    if sh.site_id != cp.site_id:
        raise HTTPException(status_code=400, detail=f"Este QR es de otro sitio. Turno actual: sitio #{sh.site_id}")
    site = db.query(ClientSite).filter(ClientSite.id == sh.site_id).first()
    dist_note = ""
    last_cp = (
        db.query(LogEntry)
        .filter(
            LogEntry.shift_id == sh.id,
            LogEntry.entry_type == "checkpoint",
            LogEntry.lat.isnot(None),
            LogEntry.lng.isnot(None),
        )
        .order_by(LogEntry.created_at.desc())
        .first()
    )
    if last_cp and payload.lat is not None and payload.lng is not None:
        seg = haversine_m(last_cp.lat, last_cp.lng, payload.lat, payload.lng)
        dist_note = f" · +{format_distance(seg)} desde marca anterior"
    entry = LogEntry(
        company_id=user.company_id,
        shift_id=sh.id,
        guard_id=user.id,
        checkpoint_id=cp.id,
        entry_type="checkpoint",
        note=f"QR: {cp.name} @ {site.name if site else ''}{dist_note}",
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    stats = shift_patrol_stats(db, sh)
    return {
        "ok": True,
        "message": f"Marca registrada: {cp.name}",
        "checkpoint": checkpoint_dict(cp),
        "entry": log_dict(entry),
        "patrol": {
            "total_distance_label": stats["total_distance_label"],
            "checkpoint_marks": stats["checkpoint_marks"],
        },
    }


@router.get("/api/checkpoints/{checkpoint_id}/qr.png")
def checkpoint_qr_png(
    checkpoint_id: int,
    request: Request,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    cp = (
        db.query(PatrolCheckpoint)
        .filter(PatrolCheckpoint.id == checkpoint_id, PatrolCheckpoint.company_id == user.company_id)
        .first()
    )
    if not cp or not cp.qr_token:
        raise HTTPException(status_code=404, detail="Checkpoint no encontrado")
    url = checkpoint_scan_url(public_base(request), cp.qr_token)
    return Response(content=qr_png(url), media_type="image/png")


@router.get("/api/sites/{site_id}/qr-print")
def site_qr_print_sheet(
    site_id: int,
    request: Request,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    site = (
        db.query(ClientSite)
        .filter(ClientSite.id == site_id, ClientSite.company_id == user.company_id)
        .first()
    )
    if not site:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    company = get_company(db, user)
    base = public_base(request)
    rows = (
        db.query(PatrolCheckpoint)
        .filter(
            PatrolCheckpoint.site_id == site_id,
            PatrolCheckpoint.company_id == user.company_id,
            PatrolCheckpoint.active.is_(True),
        )
        .order_by(PatrolCheckpoint.sort_order.asc())
        .all()
    )
    cards = ""
    for cp in rows:
        if not cp.qr_token:
            continue
        url = checkpoint_scan_url(base, cp.qr_token)
        img_b64 = __import__("base64").b64encode(qr_png(url, box_size=6)).decode()
        cards += f"""
        <div class="card">
          <img src="data:image/png;base64,{img_b64}" alt="QR {cp.name}"/>
          <h3>{cp.name}</h3>
          <p>{cp.description or site.name}</p>
          <p class="muted">Pegue en muro · escaneo con celular del oficial</p>
        </div>"""
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"/>
<title>QR rondas — {site.name}</title>
<style>
body{{font-family:Segoe UI,sans-serif;margin:20px;color:#111}}
h1{{margin:0 0 4px}} .meta{{color:#555;margin-bottom:20px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}}
.card{{border:2px dashed #333;border-radius:12px;padding:16px;text-align:center;page-break-inside:avoid}}
.card img{{width:180px;height:180px}}
.card h3{{margin:10px 0 4px;font-size:1rem}}
.card p{{margin:0;font-size:.85rem}}
.muted{{color:#666;font-size:.75rem;margin-top:8px}}
@media print{{button{{display:none}} .card{{break-inside:avoid}}}}
</style></head><body>
<button onclick="window.print()">Imprimir hoja QR</button>
<h1>Puntos de ronda — QR</h1>
<p class="meta"><strong>{company.name}</strong> · {site.name} · {site.address or ""}<br>
Oficial escanea con Excalibu Sentinel → registra lugar, hora y distancia de recorrido.</p>
<div class="grid">{cards or "<p>Sin checkpoints. Créelos en Admin → Sitios.</p>"}</div>
</body></html>"""
    return HTMLResponse(html)


@router.get("/api/assignments")
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


@router.post("/api/assignments")
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


@router.get("/api/shifts/active")
def my_active_shift(user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    sh = (
        db.query(Shift)
        .filter(Shift.guard_id == user.id, Shift.status == "open")
        .order_by(Shift.started_at.desc())
        .first()
    )
    return {"shift": shift_dict(db, sh) if sh else None}


@router.post("/api/shifts/start")
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
        start_lat=payload.lat,
        start_lng=payload.lng,
    )
    db.add(sh)
    db.flush()
    start_note = (payload.note or f"Inicio de turno en {site.name}").strip()
    if payload.lat is not None and payload.lng is not None:
        start_note = f"{start_note} · GPS {payload.lat:.5f}, {payload.lng:.5f}"
    db.add(
        LogEntry(
            company_id=user.company_id,
            shift_id=sh.id,
            guard_id=user.id,
            entry_type="inicio",
            note=start_note,
            lat=payload.lat,
            lng=payload.lng,
        )
    )
    db.commit()
    db.refresh(sh)
    return {"shift": shift_dict(db, sh)}


@router.post("/api/shifts/{shift_id}/log")
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
    company = get_company(db, user)
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
        alert = {"whatsapp_url": whatsapp_link(phone, msg), "message": msg}
    return {"entry": log_dict(entry), "shift_id": sh.id, "alert": alert}


@router.post("/api/shifts/{shift_id}/log/photo")
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


@router.post("/api/shifts/{shift_id}/close")
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
    sh.end_lat = payload.lat
    sh.end_lng = payload.lng
    if sh.assignment_id:
        a = db.query(ShiftAssignment).filter(ShiftAssignment.id == sh.assignment_id).first()
        if a:
            a.status = "done"
    end_note = (payload.note or "Fin de turno").strip()
    if payload.lat is not None and payload.lng is not None:
        end_note = f"{end_note} · GPS {payload.lat:.5f}, {payload.lng:.5f}"
    db.add(
        LogEntry(
            company_id=user.company_id,
            shift_id=sh.id,
            guard_id=user.id,
            entry_type="fin",
            note=end_note,
            lat=payload.lat,
            lng=payload.lng,
        )
    )
    db.commit()
    db.refresh(sh)
    return {"shift": shift_dict(db, sh)}


@router.get("/api/shifts")
def list_shifts(
    user: Annotated[User, Depends(require_roles("admin", "supervisor", "client"))],
    db: Session = Depends(get_db),
    status: str = "",
    guard_id: int = 0,
    site_id: int = 0,
    limit: int = 100,
):
    q = db.query(Shift).filter(Shift.company_id == user.company_id)
    cid = client_site_id(user)
    if cid:
        q = q.filter(Shift.site_id == cid)
    elif site_id:
        q = q.filter(Shift.site_id == site_id)
    if status:
        q = q.filter(Shift.status == status.strip().lower())
    if guard_id:
        q = q.filter(Shift.guard_id == guard_id)
    rows = q.order_by(Shift.started_at.desc()).limit(min(limit, 500)).all()
    return {"shifts": [shift_dict(db, s, include_logs=False) for s in rows]}


@router.get("/api/shifts/{shift_id}")
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
    ensure_site_access(user, sh.site_id)
    return {"shift": shift_dict(db, sh)}


@router.get("/api/shifts/{shift_id}/report")
def shift_report(
    shift_id: int,
    user: Annotated[User, Depends(require_roles("admin", "supervisor", "guard", "client"))],
    db: Session = Depends(get_db),
):
    sh = db.query(Shift).filter(Shift.id == shift_id, Shift.company_id == user.company_id).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if user.role == "guard" and sh.guard_id != user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")
    ensure_site_access(user, sh.site_id)
    html = shift_report_html(db, shift_id, user.company_id)
    return HTMLResponse(html)


@router.get("/api/shifts/{shift_id}/patrol")
def shift_patrol(
    shift_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    sh = db.query(Shift).filter(Shift.id == shift_id, Shift.company_id == user.company_id).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if user.role == "guard" and sh.guard_id != user.id:
        raise HTTPException(status_code=403, detail="Sin permiso")
    return shift_patrol_stats(db, sh)


@router.get("/api/reports/patrol")
def patrol_report_json(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
    period: str = "weekly",
    guard_id: int = 0,
):
    days = 15 if period.strip().lower() in {"biweekly", "quincenal", "15", "quince"} else 7
    return patrol_period_stats(db, user.company_id, days=days, guard_id=guard_id)


@router.get("/api/reports/patrol/print")
def patrol_report_print(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
    period: str = "weekly",
    guard_id: int = 0,
):
    days = 15 if period.strip().lower() in {"biweekly", "quincenal", "15", "quince"} else 7
    html = patrol_report_html(db, user.company_id, days=days, guard_id=guard_id)
    return HTMLResponse(html)


@router.get("/api/patrol-schedules")
def list_patrol_schedules(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
    site_id: int = 0,
):
    q = db.query(PatrolRoundSchedule).filter(PatrolRoundSchedule.company_id == user.company_id)
    if site_id:
        q = q.filter(PatrolRoundSchedule.site_id == site_id)
    rows = q.order_by(PatrolRoundSchedule.site_id.asc(), PatrolRoundSchedule.expected_time.asc()).all()
    return {"schedules": [schedule_dict(db, s) for s in rows]}


@router.post("/api/patrol-schedules")
def create_patrol_schedule(
    payload: PatrolScheduleIn,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    site = (
        db.query(ClientSite)
        .filter(ClientSite.id == payload.site_id, ClientSite.company_id == user.company_id, ClientSite.active.is_(True))
        .first()
    )
    if not site:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    if payload.checkpoint_id:
        cp = (
            db.query(PatrolCheckpoint)
            .filter(
                PatrolCheckpoint.id == payload.checkpoint_id,
                PatrolCheckpoint.company_id == user.company_id,
                PatrolCheckpoint.site_id == payload.site_id,
            )
            .first()
        )
        if not cp:
            raise HTTPException(status_code=404, detail="Checkpoint no encontrado")
    hm = (payload.expected_time or "22:00").strip()
    if len(hm) < 4 or ":" not in hm:
        raise HTTPException(status_code=400, detail="Hora inválida (use HH:MM)")
    row = PatrolRoundSchedule(
        company_id=user.company_id,
        site_id=payload.site_id,
        checkpoint_id=payload.checkpoint_id,
        expected_time=hm[:5],
        grace_minutes=payload.grace_minutes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"schedule": schedule_dict(db, row)}


@router.delete("/api/patrol-schedules/{schedule_id}")
def delete_patrol_schedule(
    schedule_id: int,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    row = (
        db.query(PatrolRoundSchedule)
        .filter(PatrolRoundSchedule.id == schedule_id, PatrolRoundSchedule.company_id == user.company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Horario no encontrado")
    row.active = False
    db.commit()
    return {"ok": True}


@router.get("/api/alerts/missed")
def missed_alerts(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
    status: str = "pending",
    site_id: int = 0,
    check: bool = True,
):
    company = get_company(db, user)
    if check:
        check_missed_rounds(db, user.company_id)
    rows = list_missed_alerts(db, user.company_id, status=status, site_id=site_id)
    alerts = []
    for a in rows:
        d = alert_dict(db, a)
        d["whatsapp_url"] = whatsapp_link(company.alert_whatsapp or SUPPORT_WHATSAPP, a.message)
        alerts.append(d)
    return {"alerts": alerts, "count": len(alerts)}


@router.post("/api/alerts/missed/{alert_id}/acknowledge")
def acknowledge_missed_alert(
    alert_id: int,
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    row = (
        db.query(PatrolMissedAlert)
        .filter(PatrolMissedAlert.id == alert_id, PatrolMissedAlert.company_id == user.company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    row.status = "acknowledged"
    row.acknowledged_at = datetime.utcnow()
    db.commit()
    return {"alert": alert_dict(db, row)}


@router.get("/api/client/dashboard")
def client_dashboard(
    user: Annotated[User, Depends(require_roles("client"))],
    db: Session = Depends(get_db),
):
    cid = client_site_id(user)
    if not cid:
        raise HTTPException(status_code=400, detail="Usuario cliente sin sitio asignado")
    site = db.query(ClientSite).filter(ClientSite.id == cid, ClientSite.company_id == user.company_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    shifts = (
        db.query(Shift)
        .filter(Shift.company_id == user.company_id, Shift.site_id == cid)
        .order_by(Shift.started_at.desc())
        .limit(30)
        .all()
    )
    incidents = (
        db.query(LogEntry)
        .join(Shift, LogEntry.shift_id == Shift.id)
        .filter(
            LogEntry.company_id == user.company_id,
            Shift.site_id == cid,
            LogEntry.entry_type == "incidente",
        )
        .order_by(LogEntry.created_at.desc())
        .limit(10)
        .all()
    )
    patrol = patrol_period_stats(db, user.company_id, days=7, site_id=cid)
    missed = list_missed_alerts(db, user.company_id, site_id=cid, limit=10)
    return {
        "site": site_dict(site),
        "company": company_dict(get_company(db, user)),
        "shifts": [shift_dict(db, s, include_logs=False) for s in shifts],
        "recent_incidents": [log_dict(x) for x in incidents],
        "patrol_summary": patrol,
        "missed_alerts": [alert_dict(db, a) for a in missed],
    }


@router.get("/api/dashboard")
def dashboard(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    check_missed_rounds(db, user.company_id)
    guards = db.query(User).filter(User.company_id == user.company_id, User.role == "guard", User.active.is_(True)).count()
    sites = db.query(ClientSite).filter(ClientSite.company_id == user.company_id, ClientSite.active.is_(True)).count()
    cameras = db.query(SecurityCamera).filter(SecurityCamera.company_id == user.company_id, SecurityCamera.active.is_(True)).count()
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
    company = get_company(db, user)
    missed = list_missed_alerts(db, user.company_id, status="pending", limit=10)
    missed_out = []
    for a in missed:
        d = alert_dict(db, a)
        d["whatsapp_url"] = whatsapp_link(company.alert_whatsapp or SUPPORT_WHATSAPP, a.message)
        missed_out.append(d)
    return {
        "guards": guards,
        "sites": sites,
        "cameras": cameras,
        "open_shifts": open_shifts,
        "logs_today": logs_today,
        "recent_incidents": [log_dict(x) for x in incidents],
        "active_shifts": [shift_dict(db, s, include_logs=False) for s in open_list],
        "missed_alerts": missed_out,
        "missed_alerts_count": len(missed_out),
    }


@router.get("/api/guards")
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
    changed = False
    for g in rows:
        if not g.field_code:
            g.field_code = generate_field_code(db, user.company_id)
            changed = True
    if changed:
        db.commit()
        for g in rows:
            db.refresh(g)
    guards = []
    for u in rows:
        d = user_dict(u)
        d["field_login_path"] = f"/oficial?code={u.field_code}"
        guards.append(d)
    return {"guards": guards}


@router.post("/api/guards/{guard_id}/field-code")
def regenerate_guard_field_code(
    guard_id: int,
    user: Annotated[User, Depends(require_roles("admin"))],
    db: Session = Depends(get_db),
):
    guard = (
        db.query(User)
        .filter(
            User.id == guard_id,
            User.company_id == user.company_id,
            User.role == "guard",
            User.active.is_(True),
        )
        .first()
    )
    if not guard:
        raise HTTPException(status_code=404, detail="Oficial no encontrado")
    guard.field_code = generate_field_code(db, user.company_id)
    db.commit()
    db.refresh(guard)
    return {"guard": user_dict(guard), "field_login_path": f"/oficial?code={guard.field_code}"}


@router.get("/api/patrol/live")
def patrol_live(
    user: Annotated[User, Depends(require_roles("admin", "supervisor"))],
    db: Session = Depends(get_db),
):
    """Turnos abiertos con recorrido GPS y marcas QR en tiempo real."""
    shifts = (
        db.query(Shift)
        .filter(Shift.company_id == user.company_id, Shift.status == "open")
        .order_by(Shift.started_at.desc())
        .all()
    )
    rows = []
    for sh in shifts:
        st = shift_patrol_stats(db, sh)
        rows.append(
            {
                "shift_id": sh.id,
                "guard": st.get("guard"),
                "site": st.get("site"),
                "started_at": st.get("started_at"),
                "total_distance_label": st.get("total_distance_label"),
                "checkpoint_marks": st.get("checkpoint_marks"),
                "marks": st.get("marks"),
            }
        )
    return {"live_shifts": rows, "count": len(rows)}


@router.get("/api/users")
def list_users(
    user: Annotated[User, Depends(require_roles("admin"))],
    db: Session = Depends(get_db),
):
    rows = (
        db.query(User)
        .filter(User.company_id == user.company_id, User.active.is_(True))
        .order_by(User.role.asc(), User.name.asc())
        .all()
    )
    return {"users": [user_dict(u) for u in rows]}


@router.post("/api/users")
def create_user(
    payload: UserIn,
    user: Annotated[User, Depends(require_roles("admin"))],
    db: Session = Depends(get_db),
):
    if payload.role not in ("admin", "supervisor", "guard", "client"):
        raise HTTPException(status_code=400, detail="Rol inválido")
    uname = payload.username.strip().lower()
    if db.query(User).filter(User.username == uname).first():
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    client_site_id = payload.client_site_id
    if payload.role == "client":
        if not client_site_id:
            raise HTTPException(status_code=400, detail="Cliente requiere sitio asignado")
        site = (
            db.query(ClientSite)
            .filter(ClientSite.id == client_site_id, ClientSite.company_id == user.company_id)
            .first()
        )
        if not site:
            raise HTTPException(status_code=404, detail="Sitio no encontrado")
    row = User(
        company_id=user.company_id,
        name=payload.name.strip(),
        username=uname,
        password_hash=hash_password(payload.password),
        role=payload.role,
        badge=payload.badge.strip(),
        phone=payload.phone.strip(),
        client_site_id=client_site_id if payload.role == "client" else None,
    )
    db.add(row)
    db.flush()
    if row.role == "guard":
        row.field_code = generate_field_code(db, user.company_id)
    db.commit()
    db.refresh(row)
    out = user_dict(row)
    if row.role == "guard":
        out["field_login_path"] = f"/oficial?code={row.field_code}"
    return {"user": out}


@router.patch("/api/company/settings")
def update_company_settings(
    payload: CompanySettingsIn,
    user: Annotated[User, Depends(require_roles("admin"))],
    db: Session = Depends(get_db),
):
    company = get_company(db, user)
    if payload.name.strip():
        company.name = payload.name.strip()
    company.phone = payload.phone.strip() or company.phone
    company.alert_whatsapp = payload.alert_whatsapp.strip() or company.alert_whatsapp
    db.commit()
    return {"company": company_dict(company)}