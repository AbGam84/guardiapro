"""Cámara compartida desde el celular del oficial."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.camera_pair import create_pair_token, pair_qr_text, token_dict
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


def start_mobile_share(db: Session, shift: Shift, guard: User) -> tuple[SecurityCamera, dict]:
    existing = active_mobile_camera(db, shift.id, guard.id)
    if existing:
        from app.models import CameraPairToken

        pair = (
            db.query(CameraPairToken)
            .filter(
                CameraPairToken.camera_id == existing.id,
                CameraPairToken.used_at.is_(None),
                CameraPairToken.expires_at > datetime.utcnow(),
            )
            .order_by(CameraPairToken.id.desc())
            .first()
        )
        if pair:
            pair.raw_payload = pair_qr_text(pair.token)
            return existing, token_dict(pair)
        pair = create_pair_token(
            db,
            guard,
            pair_kind="mobile",
            raw_payload="",
            parsed={"name": existing.name, "camera_type": "mobile"},
            camera_id=existing.id,
            shift_id=shift.id,
        )
        pair.raw_payload = pair_qr_text(pair.token)
        db.commit()
        db.refresh(existing)
        return existing, token_dict(pair)

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
        location="Transmisión en vivo — escanee QR en admin para vincular puesto",
        notes=f"Compartida por oficial en turno #{shift.id}",
        share_guard_id=guard.id,
        share_shift_id=shift.id,
        share_active=True,
    )
    db.add(cam)
    db.flush()
    cam.stream_url = stream_url(cam.id, None)

    pair = create_pair_token(
        db,
        guard,
        pair_kind="mobile",
        raw_payload="",
        parsed={"name": name, "camera_type": "mobile", "guard_id": guard.id},
        camera_id=cam.id,
        shift_id=shift.id,
    )
    pair.raw_payload = pair_qr_text(pair.token)

    db.add(
        LogEntry(
            company_id=shift.company_id,
            shift_id=shift.id,
            guard_id=guard.id,
            entry_type="novedad",
            note="Inició transmisión de cámara celular — admin puede escanear QR para vincular al puesto",
            severity="normal",
        )
    )
    db.commit()
    db.refresh(cam)
    db.refresh(pair)
    return cam, token_dict(pair)
