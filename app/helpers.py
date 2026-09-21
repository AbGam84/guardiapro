from sqlalchemy.orm import Session

from app.camera_util import BRANDS, CAMERA_TYPES, build_rtsp_url, build_web_url
from app.models import ClientSite, Company, LogEntry, PatrolCheckpoint, SecurityCamera, Shift, ShiftAssignment, User

ENTRY_LABELS = {
    "inicio": "Inicio de turno",
    "ronda": "Ronda / patrullaje",
    "checkpoint": "Punto de control",
    "incidente": "Incidente",
    "novedad": "Novedad",
    "visita": "Visita / ingreso",
    "vehiculo": "Vehículo",
    "llaves": "Llaves / acceso",
    "entrega": "Entrega de turno",
    "fin": "Fin de turno",
}

SEVERITY_LABELS = {
    "normal": "Normal",
    "alta": "Alta",
    "critica": "Crítica",
}


def user_dict(u: User | None) -> dict:
    if not u:
        return {}
    return {
        "id": u.id,
        "name": u.name,
        "username": u.username,
        "role": u.role,
        "badge": u.badge,
        "phone": u.phone,
        "field_code": u.field_code or "",
        "company_id": u.company_id,
        "client_site_id": u.client_site_id,
    }


def company_dict(c: Company | None) -> dict:
    if not c:
        return {}
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "phone": c.phone,
        "alert_whatsapp": c.alert_whatsapp,
        "active": c.active,
    }


def site_dict(s: ClientSite | None) -> dict:
    if not s:
        return {}
    return {
        "id": s.id,
        "name": s.name,
        "address": s.address,
        "client_name": s.client_name,
        "client_phone": s.client_phone,
        "notes": s.notes,
        "lat": s.lat,
        "lng": s.lng,
        "active": s.active,
    }


def checkpoint_dict(cp: PatrolCheckpoint | None, *, qr_url: str = "") -> dict:
    if not cp:
        return {}
    return {
        "id": cp.id,
        "site_id": cp.site_id,
        "name": cp.name,
        "description": cp.description,
        "sort_order": cp.sort_order,
        "qr_token": cp.qr_token or "",
        "qr_url": qr_url,
        "lat": cp.lat,
        "lng": cp.lng,
        "active": cp.active,
    }


def log_dict(e: LogEntry) -> dict:
    return {
        "id": e.id,
        "entry_type": e.entry_type,
        "entry_label": ENTRY_LABELS.get(e.entry_type, e.entry_type),
        "severity": e.severity,
        "severity_label": SEVERITY_LABELS.get(e.severity, e.severity),
        "sector": e.sector or "",
        "involved": e.involved or "",
        "action_taken": e.action_taken or "",
        "note": e.note,
        "lat": e.lat,
        "lng": e.lng,
        "checkpoint_id": e.checkpoint_id,
        "photo_url": f"/uploads/{e.photo_filename}" if e.photo_filename else "",
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "guard_id": e.guard_id,
    }


def shift_dict(db: Session, sh: Shift, *, include_logs: bool = True) -> dict:
    guard = db.query(User).filter(User.id == sh.guard_id).first()
    site = db.query(ClientSite).filter(ClientSite.id == sh.site_id).first()
    logs = []
    if include_logs:
        logs = (
            db.query(LogEntry)
            .filter(LogEntry.shift_id == sh.id)
            .order_by(LogEntry.created_at.asc())
            .all()
        )
    return {
        "id": sh.id,
        "status": sh.status,
        "started_at": sh.started_at.isoformat() if sh.started_at else None,
        "ended_at": sh.ended_at.isoformat() if sh.ended_at else None,
        "start_note": sh.start_note,
        "end_note": sh.end_note,
        "start_lat": sh.start_lat,
        "start_lng": sh.start_lng,
        "end_lat": sh.end_lat,
        "end_lng": sh.end_lng,
        "guard": user_dict(guard),
        "site": site_dict(site),
        "log_count": len(logs),
        "logs": [log_dict(x) for x in logs],
    }


def camera_dict(cam: SecurityCamera | None, *, show_secrets: bool = False) -> dict:
    if not cam:
        return {}
    rtsp = build_rtsp_url(
        brand=cam.brand,
        camera_type=cam.camera_type,
        ip=cam.ip_address,
        port=cam.rtsp_port,
        channel=cam.channel,
        username=cam.username,
        password=cam.password,
        rtsp_override=cam.rtsp_url,
    )
    web = build_web_url(
        brand=cam.brand,
        ip=cam.ip_address,
        http_port=cam.http_port,
        username=cam.username,
        web_override=cam.web_url,
    )
    live_url = cam.stream_url
    if cam.camera_type == "mobile" and cam.share_active:
        from app.mobile_camera import stream_url as mobile_stream

        live_url = mobile_stream(cam.id, cam.last_frame_at)
    return {
        "id": cam.id,
        "site_id": cam.site_id,
        "parent_id": cam.parent_id,
        "camera_type": cam.camera_type,
        "camera_type_label": CAMERA_TYPES.get(cam.camera_type, cam.camera_type),
        "share_active": bool(cam.share_active),
        "is_live": cam.camera_type == "mobile" and cam.share_active,
        "last_frame_at": cam.last_frame_at.isoformat() if cam.last_frame_at else None,
        "name": cam.name,
        "brand": cam.brand,
        "brand_label": BRANDS.get(cam.brand, cam.brand),
        "model_name": cam.model_name,
        "location": cam.location,
        "ip_address": cam.ip_address,
        "rtsp_port": cam.rtsp_port,
        "http_port": cam.http_port,
        "channel": cam.channel,
        "username": cam.username if show_secrets else (cam.username[:2] + "***" if cam.username else ""),
        "has_password": bool(cam.password),
        "password": cam.password if show_secrets else "",
        "rtsp_url": rtsp if show_secrets else ("••••••••" if rtsp else ""),
        "rtsp_url_hint": "Configurado" if rtsp else "",
        "stream_url": live_url or cam.stream_url,
        "web_url": web or cam.web_url,
        "onvif_port": cam.onvif_port,
        "notes": cam.notes,
        "active": cam.active,
        "view_path": f"/cameras/{cam.id}",
    }


def assignment_dict(db: Session, a: ShiftAssignment) -> dict:
    guard = db.query(User).filter(User.id == a.guard_id).first()
    site = db.query(ClientSite).filter(ClientSite.id == a.site_id).first()
    return {
        "id": a.id,
        "shift_date": a.shift_date,
        "start_time": a.start_time,
        "end_time": a.end_time,
        "notes": a.notes,
        "status": a.status,
        "guard": user_dict(guard),
        "site": site_dict(site),
    }
