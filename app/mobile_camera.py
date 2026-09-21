"""Cámara compartida desde el celular del oficial."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import UPLOADS_DIR
from app.models import LogEntry, SecurityCamera, Shift, User

MOBILE_DIR = UPLOADS_DIR / "mobile"
MOBILE_DIR.mkdir(parents=True, exist_ok=True)


def frame_path(camera_id: int) -> Path:
    return MOBILE_DIR / f"cam_{camera_id}.jpg"


def stream_url(camera_id: int, last_frame_at: datetime | None) -> str:
    ts = int(last_frame_at.timestamp()) if last_frame_at else 0
    return f"/uploads/mobile/cam_{camera_id}.jpg?t={ts}"


def stop_shares_for_shift(db: Session, shift_id: int) -> None:
    rows = (
        db.query(SecurityCamera)
        .filter(
            SecurityCamera.share_shift_id == shift_id,
            SecurityCamera.camera_type == "mobile",
            SecurityCamera.share_active.is_(True),
        )
        .all()
    )
    for cam in rows:
        cam.share_active = False


def active_mobile_camera(db: Session, shift_id: int, guard_id: int) -> SecurityCamera | None:
    return (
        db.query(SecurityCamera)
        .filter(
            SecurityCamera.share_shift_id == shift_id,
            SecurityCamera.share_guard_id == guard_id,
            SecurityCamera.camera_type == "mobile",
            SecurityCamera.share_active.is_(True),
            SecurityCamera.active.is_(True),
        )
        .first()
    )


def start_mobile_share(db: Session, shift: Shift, guard: User) -> SecurityCamera:
    existing = active_mobile_camera(db, shift.id, guard.id)
    if existing:
        return existing

    name = f"Celular — {guard.name}"
    if guard.badge:
        name = f"Celular — {guard.name} ({guard.badge})"

    cam = SecurityCamera(
        company_id=shift.company_id,
        site_id=shift.site_id,
        camera_type="mobile",
        name=name,
        brand="other",
        model_name="Celular oficial",
        location="Transmisión en vivo desde turno",
        notes=f"Compartida por oficial en turno #{shift.id}",
        share_guard_id=guard.id,
        share_shift_id=shift.id,
        share_active=True,
    )
    db.add(cam)
    db.flush()
    cam.stream_url = stream_url(cam.id, None)
    db.add(
        LogEntry(
            company_id=shift.company_id,
            shift_id=shift.id,
            guard_id=guard.id,
            entry_type="novedad",
            note=f"Inició transmisión de cámara celular — visible en panel admin",
            severity="normal",
        )
    )
    db.commit()
    db.refresh(cam)
    return cam
