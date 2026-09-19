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
    LoginIn,
    PatrolScheduleIn,
    QrScanIn,
    ShiftEndIn,
    ShiftStartIn,
    SiteIn,
    UserIn,
)

router = APIRouter()
