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


class ShiftEndIn(BaseModel):
    note: str = ""


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


class CompanySettingsIn(BaseModel):
    name: str = ""
    phone: str = ""
    alert_whatsapp: str = ""
