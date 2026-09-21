"""Vincular cámaras escaneando QR (celular compartido, DVR, WiFi)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.camera_qr_parse import parse_device_qr, pair_qr_text
from app.models import CameraPairToken, ClientSite, SecurityCamera, User

PAIR_TTL_MINUTES = 45


def create_pair_token(
    db: Session,
    user: User,
    *,
    pair_kind: str = "mobile",
    raw_payload: str = "",
    parsed: dict | None = None,
    camera_id: int | None = None,
    shift_id: int | None = None,
) -> CameraPairToken:
    token = uuid.uuid4().hex[:16]
    row = CameraPairToken(
        token=token,
        company_id=user.company_id,
        creator_id=user.id,
        pair_kind=pair_kind,
        raw_payload=(raw_payload or "")[:2000],
        parsed_json=json.dumps(parsed or {}, ensure_ascii=False),
        camera_id=camera_id,
        share_shift_id=shift_id,
        expires_at=datetime.utcnow() + timedelta(minutes=PAIR_TTL_MINUTES),
    )
    db.add(row)
    db.flush()
    return row


def get_valid_token(db: Session, token: str, company_id: int) -> CameraPairToken | None:
    row = (
        db.query(CameraPairToken)
        .filter(
            CameraPairToken.token == token,
            CameraPairToken.company_id == company_id,
            CameraPairToken.used_at.is_(None),
            CameraPairToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    return row


def token_dict(row: CameraPairToken) -> dict:
    parsed = {}
    try:
        parsed = json.loads(row.parsed_json or "{}")
    except json.JSONDecodeError:
        pass
    return {
        "token": row.token,
        "pair_kind": row.pair_kind,
        "qr_text": pair_qr_text(row.token),
        "camera_id": row.camera_id,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "parsed": parsed,
    }


def _camera_from_parsed(parsed: dict, site_id: int, company_id: int) -> SecurityCamera:
    cam_type = parsed.get("camera_type") or parsed.get("pair_kind") or "wifi"
    if cam_type not in ("wifi", "nvr", "dvr", "nvr_channel", "dvr_channel", "mobile"):
        cam_type = "wifi"
    return SecurityCamera(
        company_id=company_id,
        site_id=site_id,
        camera_type=cam_type,
        name=(parsed.get("name") or "Cámara QR")[:120],
        brand=(parsed.get("brand") or "other")[:40],
        model_name=(parsed.get("model_name") or "")[:80],
        location=(parsed.get("location") or "Registrada por QR")[:160],
        ip_address=(parsed.get("ip_address") or "")[:45],
        rtsp_port=int(parsed.get("rtsp_port") or 554),
        http_port=int(parsed.get("http_port") or 80),
        channel=max(1, int(parsed.get("channel") or 1)),
        username=(parsed.get("username") or "")[:80],
        password=(parsed.get("password") or "")[:120],
        rtsp_url=(parsed.get("rtsp_url") or "")[:512],
        stream_url=(parsed.get("stream_url") or "")[:512],
        web_url=(parsed.get("web_url") or "")[:512],
        notes=(parsed.get("notes") or "Alta por escaneo QR")[:2000],
    )


def claim_token(
    db: Session,
    user: User,
    token: str,
    site_id: int,
    *,
    name: str = "",
) -> tuple[SecurityCamera, str]:
    site = (
        db.query(ClientSite)
        .filter(ClientSite.id == site_id, ClientSite.company_id == user.company_id, ClientSite.active.is_(True))
        .first()
    )
    if not site:
        raise ValueError("Sitio no encontrado")

    row = get_valid_token(db, token, user.company_id)
    if not row:
        raise ValueError("QR expirado o inválido — pida al oficial que genere uno nuevo")

    if row.camera_id:
        cam = (
            db.query(SecurityCamera)
            .filter(SecurityCamera.id == row.camera_id, SecurityCamera.company_id == user.company_id)
            .first()
        )
        if cam:
            cam.site_id = site.id
            if name.strip():
                cam.name = name.strip()[:120]
            cam.active = True
            if cam.camera_type == "mobile":
                cam.location = f"Vinculada a {site.name} por QR"
            row.used_at = datetime.utcnow()
            db.flush()
            db.refresh(cam)
            return cam, f"Cámara vinculada al puesto «{site.name}»"

    parsed = {}
    try:
        parsed = json.loads(row.parsed_json or "{}")
    except json.JSONDecodeError:
        pass
    if name.strip():
        parsed["name"] = name.strip()
    cam = _camera_from_parsed(parsed, site.id, user.company_id)
    db.add(cam)
    db.flush()
    row.camera_id = cam.id
    row.used_at = datetime.utcnow()
    db.flush()
    db.refresh(cam)
    return cam, f"Cámara «{cam.name}» añadida a «{site.name}»"


def scan_and_register(
    db: Session,
    user: User,
    qr_text: str,
    site_id: int,
    *,
    name: str = "",
    auto_create: bool = True,
) -> dict:
    parsed = parse_device_qr(qr_text)
    if parsed.get("pair_token"):
        cam, msg = claim_token(db, user, parsed["pair_token"], site_id, name=name)
        from app.helpers import camera_dict

        return {
            "action": "linked",
            "recognized": True,
            "message": msg,
            "camera": camera_dict(cam, show_secrets=True),
            "parse": parsed,
        }

    if not parsed.get("recognized"):
        return {"action": "unknown", "recognized": False, "parse": parsed}

    if not auto_create:
        return {"action": "prefill", "recognized": True, "parse": parsed, "suggest": parsed}

    cam = _camera_from_parsed(parsed, site_id, user.company_id)
    if name.strip():
        cam.name = name.strip()[:120]
    db.add(cam)
    db.flush()
    db.refresh(cam)
    from app.helpers import camera_dict

    return {
        "action": "created",
        "recognized": True,
        "message": f"Cámara «{cam.name}» añadida al puesto por QR {parsed.get('source', '')}",
        "camera": camera_dict(cam, show_secrets=True),
        "parse": parsed,
    }
