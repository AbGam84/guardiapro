"""Datos iniciales — producción limpia (sin demo)."""
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.config import (
    ADMIN_NAME,
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    COMPANY_NAME,
    SUPPORT_WHATSAPP,
)
from app.models import (
    ClientSite,
    Company,
    LogEntry,
    PatrolCheckpoint,
    PatrolMissedAlert,
    PatrolRoundSchedule,
    SecurityCamera,
    Shift,
    ShiftAssignment,
    User,
)

COMPANY_CODE = "excalibu-telecom"
_DEMO_CODES = {"demo-seguridad", "demo"}
_DEMO_USERNAMES = {"juan", "maria", "cliente", "supervisor"}


def _is_demo_company(company: Company) -> bool:
    return company.code in _DEMO_CODES or "demo" in company.name.lower()


def purge_operational_data(db: Session, company_id: int) -> None:
    """Elimina sitios, turnos, cámaras y usuarios no-admin."""
    db.query(LogEntry).filter(LogEntry.company_id == company_id).delete(synchronize_session=False)
    db.query(PatrolMissedAlert).filter(PatrolMissedAlert.company_id == company_id).delete(synchronize_session=False)
    db.query(Shift).filter(Shift.company_id == company_id).delete(synchronize_session=False)
    db.query(ShiftAssignment).filter(ShiftAssignment.company_id == company_id).delete(synchronize_session=False)
    db.query(PatrolRoundSchedule).filter(PatrolRoundSchedule.company_id == company_id).delete(synchronize_session=False)
    db.query(SecurityCamera).filter(SecurityCamera.company_id == company_id).delete(synchronize_session=False)
    db.query(PatrolCheckpoint).filter(PatrolCheckpoint.company_id == company_id).delete(synchronize_session=False)
    db.query(ClientSite).filter(ClientSite.company_id == company_id).delete(synchronize_session=False)
    uname = ADMIN_USERNAME.strip().lower()
    db.query(User).filter(
        User.company_id == company_id,
        User.username != uname,
    ).delete(synchronize_session=False)


def purge_demo_cameras(db: Session) -> int:
    """Quita cámaras de prueba (demo1234, nombres demo, IPs de ejemplo)."""
    company = db.query(Company).first()
    if not company:
        return 0
    demo_ips = {"192.168.1.64", "192.168.1.50", "192.168.1.70"}
    rows = (
        db.query(SecurityCamera)
        .filter(SecurityCamera.company_id == company.id, SecurityCamera.active.is_(True))
        .all()
    )
    removed = 0
    for cam in rows:
        name_l = (cam.name or "").lower()
        if (
            cam.password == "demo1234"
            or "demo" in name_l
            or (cam.ip_address or "") in demo_ips
        ):
            db.delete(cam)
            removed += 1
    if removed:
        db.commit()
    return removed


def migrate_demo_to_clean(db: Session) -> bool:
    """Una vez: borra contenido demo si la DB venía del seed anterior."""
    company = db.query(Company).first()
    if not company:
        return False
    has_demo_users = (
        db.query(User.id)
        .filter(User.company_id == company.id, User.username.in_(_DEMO_USERNAMES))
        .first()
        is not None
    )
    if not _is_demo_company(company) and not has_demo_users:
        return False
    purge_operational_data(db, company.id)
    company.code = COMPANY_CODE
    company.name = COMPANY_NAME
    if not company.alert_whatsapp:
        company.alert_whatsapp = SUPPORT_WHATSAPP
    db.commit()
    return True


def seed_if_empty(db: Session) -> None:
    if db.query(Company).first():
        return
    company = Company(
        code=COMPANY_CODE,
        name=COMPANY_NAME,
        phone="",
        alert_whatsapp=SUPPORT_WHATSAPP,
    )
    db.add(company)
    db.flush()
    db.add(
        User(
            company_id=company.id,
            name=ADMIN_NAME,
            username=ADMIN_USERNAME.strip().lower(),
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
            badge="ADM-001",
        )
    )
    db.commit()


def ensure_admin_access(db: Session) -> None:
    company = db.query(Company).first()
    if not company:
        return
    uname = ADMIN_USERNAME.strip().lower()
    admin = db.query(User).filter(User.username == uname).first()
    expected = hash_password(ADMIN_PASSWORD)
    if not admin:
        db.add(
            User(
                company_id=company.id,
                name=ADMIN_NAME,
                username=uname,
                password_hash=expected,
                role="admin",
                badge="ADM-001",
            )
        )
        db.commit()
        return
    if not verify_password(ADMIN_PASSWORD, admin.password_hash) or not admin.active:
        admin.password_hash = expected
        admin.active = True
        db.commit()
