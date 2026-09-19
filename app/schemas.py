from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str
    company_code: str = ""


class LogEntryIn(BaseModel):
    entry_type: str
    note: str = ""
    severity: str = "normal"
    checkpoint_id: int | None = None
    lat: float | None = None
    lng: float | None = None


class ShiftStartIn(BaseModel):
    site_id: int
    note: str = ""
    assignment_id: int | None = None
    lat: float | None = None
    lng: float | None = None


class ShiftEndIn(BaseModel):
    note: str = ""
    lat: float | None = None
    lng: float | None = None


class PatrolScheduleIn(BaseModel):
    site_id: int
    checkpoint_id: int | None = None
    expected_time: str = "22:00"
    grace_minutes: int = Field(default=30, ge=5, le=180)


class SiteIn(BaseModel):
    name: str
    address: str = ""
    client_name: str = ""
    client_phone: str = ""
    notes: str = ""
    lat: float | None = None
    lng: float | None = None


class CheckpointIn(BaseModel):
    site_id: int
    name: str
    description: str = ""
    sort_order: int = 0
    lat: float | None = None
    lng: float | None = None


class QrScanIn(BaseModel):
    qr_token: str
    lat: float | None = None
    lng: float | None = None


class AssignmentIn(BaseModel):
    site_id: int
    guard_id: int
    shift_date: str
    start_time: str = "06:00"
    end_time: str = "18:00"
    notes: str = ""


class UserIn(BaseModel):
    name: str
    username: str
    password: str
    role: str = "guard"
    badge: str = ""
    phone: str = ""
    client_site_id: int | None = None


class CompanySettingsIn(BaseModel):
    name: str = ""
    phone: str = ""
    alert_whatsapp: str = ""


class CameraIn(BaseModel):
    site_id: int
    camera_type: str = "wifi"
    parent_id: int | None = None
    name: str
    brand: str = "other"
    model_name: str = ""
    location: str = ""
    ip_address: str = ""
    rtsp_port: int = 554
    http_port: int = 80
    channel: int = 1
    username: str = ""
    password: str = ""
    rtsp_url: str = ""
    stream_url: str = ""
    web_url: str = ""
    onvif_port: int = 80
    notes: str = ""


class CameraUpdateIn(BaseModel):
    name: str | None = None
    camera_type: str | None = None
    parent_id: int | None = None
    brand: str | None = None
    model_name: str | None = None
    location: str | None = None
    ip_address: str | None = None
    rtsp_port: int | None = None
    http_port: int | None = None
    channel: int | None = None
    username: str | None = None
    password: str | None = None
    rtsp_url: str | None = None
    stream_url: str | None = None
    web_url: str | None = None
    onvif_port: int | None = None
    notes: str | None = None
    active: bool | None = None
