from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.geo import format_distance, haversine_m, route_distance_m
from app.helpers import log_dict, user_dict
from app.models import ClientSite, LogEntry, PatrolCheckpoint, Shift, User


def _gps_points(logs: list[LogEntry]) -> list[tuple[float, float]]:
    return [(e.lat, e.lng) for e in logs if e.lat is not None and e.lng is not None]


def shift_patrol_stats(db: Session, shift: Shift) -> dict:
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.shift_id == shift.id)
        .order_by(LogEntry.created_at.asc())
        .all()
    )
    cp_logs = [e for e in logs if e.entry_type == "checkpoint" and e.checkpoint_id]
    points = _gps_points(logs)
    total_m = route_distance_m(points)

    marks = []
    prev = None
    for e in cp_logs:
        cp = db.query(PatrolCheckpoint).filter(PatrolCheckpoint.id == e.checkpoint_id).first()
        seg_m = 0.0
        if prev and e.lat is not None and e.lng is not None:
            seg_m = haversine_m(prev[0], prev[1], e.lat, e.lng)
        if e.lat is not None and e.lng is not None:
            prev = (e.lat, e.lng)
        marks.append(
            {
                "time": e.created_at.isoformat() if e.created_at else None,
                "checkpoint": cp.name if cp else "",
                "lat": e.lat,
                "lng": e.lng,
                "distance_from_prev_m": round(seg_m, 1),
                "note": e.note,
            }
        )

    site = db.query(ClientSite).filter(ClientSite.id == shift.site_id).first()
    guard = db.query(User).filter(User.id == shift.guard_id).first()
    return {
        "shift_id": shift.id,
        "guard": user_dict(guard),
        "site": {"id": site.id, "name": site.name, "address": site.address} if site else {},
        "started_at": shift.started_at.isoformat() if shift.started_at else None,
        "ended_at": shift.ended_at.isoformat() if shift.ended_at else None,
        "total_distance_m": round(total_m, 1),
        "total_distance_label": format_distance(total_m),
        "checkpoint_marks": len(cp_logs),
        "marks": marks,
        "logs": [log_dict(x) for x in logs],
    }


def patrol_period_stats(
    db: Session,
    company_id: int,
    *,
    days: int,
    guard_id: int = 0,
    site_id: int = 0,
) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    q = db.query(Shift).filter(Shift.company_id == company_id, Shift.started_at >= since)
    if guard_id:
        q = q.filter(Shift.guard_id == guard_id)
    if site_id:
        q = q.filter(Shift.site_id == site_id)
    shifts = q.order_by(Shift.started_at.desc()).all()

    by_guard: dict[int, dict] = {}
    shift_rows = []
    for sh in shifts:
        st = shift_patrol_stats(db, sh)
        shift_rows.append(st)
        gid = sh.guard_id
        if gid not in by_guard:
            by_guard[gid] = {
                "guard": st["guard"],
                "shifts": 0,
                "total_distance_m": 0.0,
                "checkpoint_marks": 0,
                "sites": set(),
            }
        by_guard[gid]["shifts"] += 1
        by_guard[gid]["total_distance_m"] += st["total_distance_m"]
        by_guard[gid]["checkpoint_marks"] += st["checkpoint_marks"]
        if st["site"].get("name"):
            by_guard[gid]["sites"].add(st["site"]["name"])

    guards_summary = []
    for g in by_guard.values():
        guards_summary.append(
            {
                "guard": g["guard"],
                "shifts": g["shifts"],
                "total_distance_m": round(g["total_distance_m"], 1),
                "total_distance_label": format_distance(g["total_distance_m"]),
                "checkpoint_marks": g["checkpoint_marks"],
                "sites": sorted(g["sites"]),
            }
        )
    guards_summary.sort(key=lambda x: x["guard"].get("name") or "")

    total_dist = sum(s["total_distance_m"] for s in shift_rows)
    return {
        "period_days": days,
        "since": since.isoformat(),
        "until": datetime.utcnow().isoformat(),
        "shift_count": len(shift_rows),
        "total_distance_m": round(total_dist, 1),
        "total_distance_label": format_distance(total_dist),
        "guards": guards_summary,
        "shifts": shift_rows,
    }
