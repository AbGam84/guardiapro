"""Detección de rondas no cumplidas según horario programado."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import ClientSite, LogEntry, PatrolCheckpoint, PatrolMissedAlert, PatrolRoundSchedule, Shift


def _parse_hm(value: str) -> tuple[int, int]:
    parts = (value or "00:00").strip().split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def _expected_dt(day: datetime, hm: str) -> datetime:
    h, m = _parse_hm(hm)
    return datetime(day.year, day.month, day.day, h, m)


def _mark_in_window(
    db: Session,
    *,
    company_id: int,
    site_id: int,
    checkpoint_id: int | None,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    q = (
        db.query(LogEntry)
        .join(Shift, LogEntry.shift_id == Shift.id)
        .filter(
            LogEntry.company_id == company_id,
            Shift.site_id == site_id,
            LogEntry.entry_type.in_(("checkpoint", "ronda")),
            LogEntry.created_at >= window_start,
            LogEntry.created_at <= window_end,
        )
    )
    if checkpoint_id:
        q = q.filter(LogEntry.checkpoint_id == checkpoint_id)
    return q.first() is not None


def schedule_dict(db: Session, row: PatrolRoundSchedule) -> dict:
    site = db.query(ClientSite).filter(ClientSite.id == row.site_id).first()
    cp = None
    if row.checkpoint_id:
        cp = db.query(PatrolCheckpoint).filter(PatrolCheckpoint.id == row.checkpoint_id).first()
    return {
        "id": row.id,
        "site_id": row.site_id,
        "site_name": site.name if site else "",
        "checkpoint_id": row.checkpoint_id,
        "checkpoint_name": cp.name if cp else "Cualquier punto del sitio",
        "expected_time": row.expected_time,
        "grace_minutes": row.grace_minutes,
        "active": row.active,
    }


def alert_dict(db: Session, row: PatrolMissedAlert) -> dict:
    site = db.query(ClientSite).filter(ClientSite.id == row.site_id).first()
    cp = None
    if row.checkpoint_id:
        cp = db.query(PatrolCheckpoint).filter(PatrolCheckpoint.id == row.checkpoint_id).first()
    return {
        "id": row.id,
        "site_id": row.site_id,
        "site_name": site.name if site else "",
        "checkpoint_id": row.checkpoint_id,
        "checkpoint_name": cp.name if cp else "Ronda general",
        "alert_date": row.alert_date,
        "expected_time": row.expected_time,
        "message": row.message,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
    }


def check_missed_rounds(db: Session, company_id: int, *, now: datetime | None = None) -> list[PatrolMissedAlert]:
    """Evalúa horarios vencidos y crea alertas pending si no hubo marca."""
    now = now or datetime.utcnow()
    today = now.date()
    alert_date = today.isoformat()
    day_start = datetime(today.year, today.month, today.day)
    created: list[PatrolMissedAlert] = []

    schedules = (
        db.query(PatrolRoundSchedule)
        .filter(
            PatrolRoundSchedule.company_id == company_id,
            PatrolRoundSchedule.active.is_(True),
        )
        .all()
    )

    for sch in schedules:
        expected = _expected_dt(day_start, sch.expected_time)
        deadline = expected + timedelta(minutes=max(5, sch.grace_minutes or 30))
        if now < deadline:
            continue

        exists = (
            db.query(PatrolMissedAlert)
            .filter(
                PatrolMissedAlert.company_id == company_id,
                PatrolMissedAlert.schedule_id == sch.id,
                PatrolMissedAlert.alert_date == alert_date,
            )
            .first()
        )
        if exists:
            continue

        window_start = expected - timedelta(minutes=15)
        window_end = deadline
        if _mark_in_window(
            db,
            company_id=company_id,
            site_id=sch.site_id,
            checkpoint_id=sch.checkpoint_id,
            window_start=window_start,
            window_end=window_end,
        ):
            continue

        site = db.query(ClientSite).filter(ClientSite.id == sch.site_id).first()
        cp = None
        if sch.checkpoint_id:
            cp = db.query(PatrolCheckpoint).filter(PatrolCheckpoint.id == sch.checkpoint_id).first()
        site_name = site.name if site else f"Sitio #{sch.site_id}"
        cp_label = cp.name if cp else "ronda programada"
        msg = (
            f"Ronda no cumplida — {site_name}\n"
            f"Debía marcar {cp_label} a las {sch.expected_time} (UTC)\n"
            f"Ventana vencida · {alert_date}"
        )
        alert = PatrolMissedAlert(
            company_id=company_id,
            site_id=sch.site_id,
            checkpoint_id=sch.checkpoint_id,
            schedule_id=sch.id,
            alert_date=alert_date,
            expected_time=sch.expected_time,
            message=msg,
            status="pending",
        )
        db.add(alert)
        created.append(alert)

    if created:
        db.commit()
        for a in created:
            db.refresh(a)
    return created


def list_missed_alerts(
    db: Session,
    company_id: int,
    *,
    status: str = "",
    site_id: int = 0,
    limit: int = 50,
) -> list[PatrolMissedAlert]:
    q = db.query(PatrolMissedAlert).filter(PatrolMissedAlert.company_id == company_id)
    if status:
        q = q.filter(PatrolMissedAlert.status == status.strip().lower())
    if site_id:
        q = q.filter(PatrolMissedAlert.site_id == site_id)
    return q.order_by(PatrolMissedAlert.created_at.desc()).limit(min(limit, 200)).all()
