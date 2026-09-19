from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(40), default="")
    alert_whatsapp: Mapped[str] = mapped_column(String(40), default="")
    logo_filename: Mapped[str] = mapped_column(String(255), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    client_site_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("client_sites.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="guard")
    badge: Mapped[str] = mapped_column(String(40), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    field_code: Mapped[str] = mapped_column(String(12), default="", index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ClientSite(Base):
    __tablename__ = "client_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str] = mapped_column(String(255), default="")
    client_name: Mapped[str] = mapped_column(String(160), default="")
    client_phone: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PatrolCheckpoint(Base):
    """Puntos de ronda obligatorios en un sitio."""

    __tablename__ = "patrol_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("client_sites.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(255), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ShiftAssignment(Base):
    """Programación: quién cubre qué sitio hoy."""

    __tablename__ = "shift_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("client_sites.id"), index=True)
    guard_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    shift_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    start_time: Mapped[str] = mapped_column(String(5), default="06:00")
    end_time: Mapped[str] = mapped_column(String(5), default="18:00")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned | active | done | missed


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("client_sites.id"), index=True)
    guard_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    assignment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("shift_assignments.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    start_note: Mapped[str] = mapped_column(Text, default="")
    end_note: Mapped[str] = mapped_column(Text, default="")
    start_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_lng: Mapped[float | None] = mapped_column(Float, nullable=True)


class PatrolRoundSchedule(Base):
    """Horarios obligatorios de ronda por sitio / checkpoint."""

    __tablename__ = "patrol_round_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("client_sites.id"), index=True)
    checkpoint_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("patrol_checkpoints.id"), nullable=True)
    expected_time: Mapped[str] = mapped_column(String(5), default="22:00")  # HH:MM UTC
    grace_minutes: Mapped[int] = mapped_column(Integer, default=30)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PatrolMissedAlert(Base):
    """Alerta cuando no se cumplió una ronda programada."""

    __tablename__ = "patrol_missed_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("client_sites.id"), index=True)
    checkpoint_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("patrol_checkpoints.id"), nullable=True)
    schedule_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("patrol_round_schedules.id"), nullable=True)
    alert_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    expected_time: Mapped[str] = mapped_column(String(5), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | acknowledged
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SecurityCamera(Base):
    """Cámaras del sitio: WiFi, NVR, DVR o canal en grabador."""

    __tablename__ = "security_cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("client_sites.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("security_cameras.id"), nullable=True)
    camera_type: Mapped[str] = mapped_column(String(20), default="wifi", index=True)
    name: Mapped[str] = mapped_column(String(120))
    brand: Mapped[str] = mapped_column(String(40), default="other")
    model_name: Mapped[str] = mapped_column(String(80), default="")
    location: Mapped[str] = mapped_column(String(160), default="")
    ip_address: Mapped[str] = mapped_column(String(45), default="")
    rtsp_port: Mapped[int] = mapped_column(Integer, default=554)
    http_port: Mapped[int] = mapped_column(Integer, default=80)
    channel: Mapped[int] = mapped_column(Integer, default=1)
    username: Mapped[str] = mapped_column(String(80), default="")
    password: Mapped[str] = mapped_column(String(120), default="")
    rtsp_url: Mapped[str] = mapped_column(String(512), default="")
    stream_url: Mapped[str] = mapped_column(String(512), default="")
    web_url: Mapped[str] = mapped_column(String(512), default="")
    onvif_port: Mapped[int] = mapped_column(Integer, default=80)
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), index=True)
    shift_id: Mapped[int] = mapped_column(Integer, ForeignKey("shifts.id"), index=True)
    guard_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    checkpoint_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("patrol_checkpoints.id"), nullable=True)
    entry_type: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="normal")  # normal | alta | critica
    note: Mapped[str] = mapped_column(Text, default="")
    photo_filename: Mapped[str] = mapped_column(String(255), default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
