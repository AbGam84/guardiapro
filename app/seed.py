import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.config import ADMIN_NAME, ADMIN_PASSWORD, ADMIN_USERNAME
from app.models import (
    ClientSite,
    Company,
    PatrolCheckpoint,
    PatrolRoundSchedule,
    SecurityCamera,
    ShiftAssignment,
    User,
)


def seed_if_empty(db: Session) -> None:
    if db.query(Company).first():
        return

    company = Company(
        code="demo-seguridad",
        name="Seguridad Pacífico Demo",
        phone="+506 6000-0000",
        alert_whatsapp="+50663706546",
    )
    db.add(company)
    db.flush()

    users = [
        User(
            company_id=company.id,
            name="Administrador",
            username=ADMIN_USERNAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
            badge="ADM-001",
        ),
        User(
            company_id=company.id,
            name="Supervisor Turno",
            username="supervisor",
            password_hash=hash_password("Super2026!"),
            role="supervisor",
            badge="SUP-001",
            phone="+506 6000-0001",
        ),
        User(
            company_id=company.id,
            name="Juan Pérez",
            username="juan",
            password_hash=hash_password("Guardia2026!"),
            role="guard",
            badge="OF-1042",
            phone="+506 6000-0002",
        ),
        User(
            company_id=company.id,
            name="María Solano",
            username="maria",
            password_hash=hash_password("Guardia2026!"),
            role="guard",
            badge="OF-1043",
        ),
    ]
    db.add_all(users)
    db.flush()

    sites = [
        ClientSite(
            company_id=company.id,
            name="Condominio Jaco Beach",
            address="Jaco, Puntarenas",
            client_name="Administración condominio",
            client_phone="+506 2643-0000",
            lat=9.6147,
            lng=-84.6298,
        ),
        ClientSite(
            company_id=company.id,
            name="Bodega Central",
            address="San José",
            client_name="Distribuidora CR",
        ),
        ClientSite(
            company_id=company.id,
            name="Plaza Comercial Heredia",
            address="Heredia centro",
            client_name="Inversiones Plaza",
        ),
    ]
    db.add_all(sites)
    db.flush()

    users.append(
        User(
            company_id=company.id,
            client_site_id=sites[0].id,
            name="Administración Jaco Beach",
            username="cliente",
            password_hash=hash_password("Cliente2026!"),
            role="client",
            badge="CLI-JACO",
            phone="+506 2643-0000",
        )
    )
    db.add(users[-1])

    checkpoints = [
        PatrolCheckpoint(company_id=company.id, site_id=sites[0].id, name="Entrada principal", sort_order=1, qr_token=uuid.uuid4().hex),
        PatrolCheckpoint(company_id=company.id, site_id=sites[0].id, name="Estacionamiento", sort_order=2, qr_token=uuid.uuid4().hex),
        PatrolCheckpoint(company_id=company.id, site_id=sites[0].id, name="Piscina / área común", sort_order=3, qr_token=uuid.uuid4().hex),
        PatrolCheckpoint(company_id=company.id, site_id=sites[0].id, name="Perimeter norte", sort_order=4, qr_token=uuid.uuid4().hex),
        PatrolCheckpoint(company_id=company.id, site_id=sites[1].id, name="Portón carga", sort_order=1, qr_token=uuid.uuid4().hex),
        PatrolCheckpoint(company_id=company.id, site_id=sites[1].id, name="Bodega interior", sort_order=2, qr_token=uuid.uuid4().hex),
    ]
    db.add_all(checkpoints)
    db.flush()

    db.add_all(
        [
            PatrolRoundSchedule(
                company_id=company.id,
                site_id=sites[0].id,
                checkpoint_id=checkpoints[0].id,
                expected_time="06:00",
                grace_minutes=30,
            ),
            PatrolRoundSchedule(
                company_id=company.id,
                site_id=sites[0].id,
                checkpoint_id=checkpoints[0].id,
                expected_time="14:00",
                grace_minutes=30,
            ),
            PatrolRoundSchedule(
                company_id=company.id,
                site_id=sites[0].id,
                checkpoint_id=checkpoints[0].id,
                expected_time="22:00",
                grace_minutes=30,
            ),
            PatrolRoundSchedule(
                company_id=company.id,
                site_id=sites[1].id,
                checkpoint_id=None,
                expected_time="00:00",
                grace_minutes=45,
            ),
        ]
    )

    nvr = SecurityCamera(
        company_id=company.id,
        site_id=sites[0].id,
        camera_type="nvr",
        name="NVR Condominio Jaco",
        brand="hikvision",
        ip_address="192.168.1.64",
        rtsp_port=554,
        http_port=80,
        username="admin",
        password="demo1234",
        location="Cuarto eléctrico",
        notes="Grabador principal 8 canales",
    )
    db.add(nvr)
    db.flush()
    db.add_all(
        [
            SecurityCamera(
                company_id=company.id,
                site_id=sites[0].id,
                parent_id=nvr.id,
                camera_type="nvr_channel",
                name="Cam entrada vehicular",
                brand="hikvision",
                ip_address="192.168.1.64",
                channel=1,
                username="admin",
                password="demo1234",
                location="Portón principal",
            ),
            SecurityCamera(
                company_id=company.id,
                site_id=sites[0].id,
                parent_id=nvr.id,
                camera_type="nvr_channel",
                name="Cam piscina",
                brand="hikvision",
                ip_address="192.168.1.64",
                channel=3,
                username="admin",
                password="demo1234",
                location="Área común",
            ),
            SecurityCamera(
                company_id=company.id,
                site_id=sites[1].id,
                camera_type="wifi",
                name="Cam bodega WiFi",
                brand="tplink",
                ip_address="192.168.1.50",
                username="admin",
                password="demo1234",
                location="Interior bodega",
                stream_url="",
                notes="Tapo C200 — usar app Tapo si no hay stream web",
            ),
            SecurityCamera(
                company_id=company.id,
                site_id=sites[1].id,
                camera_type="dvr",
                name="DVR bodega 4 canales",
                brand="xmeye",
                ip_address="192.168.1.70",
                rtsp_port=554,
                http_port=34567,
                username="admin",
                password="demo1234",
                location="Oficina bodega",
            ),
        ]
    )

    today = date.today().isoformat()
    db.add_all(
        [
            ShiftAssignment(
                company_id=company.id,
                site_id=sites[0].id,
                guard_id=users[2].id,
                shift_date=today,
                start_time="06:00",
                end_time="18:00",
                notes="Turno día Jaco",
            ),
            ShiftAssignment(
                company_id=company.id,
                site_id=sites[1].id,
                guard_id=users[3].id,
                shift_date=today,
                start_time="18:00",
                end_time="06:00",
                notes="Turno noche bodega",
            ),
        ]
    )
    db.commit()


def ensure_admin_access(db: Session) -> None:
    """Garantiza que el admin exista y que la clave coincida con config/env."""
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


def seed_client_and_schedules_if_missing(db: Session) -> None:
    company = db.query(Company).first()
    if not company:
        return
    site = db.query(ClientSite).filter(ClientSite.company_id == company.id).order_by(ClientSite.id.asc()).first()
    if not site:
        return
    if not db.query(User).filter(User.username == "cliente").first():
        db.add(
            User(
                company_id=company.id,
                client_site_id=site.id,
                name="Portal cliente demo",
                username="cliente",
                password_hash=hash_password("Cliente2026!"),
                role="client",
                badge="CLI-DEMO",
            )
        )
    if not db.query(PatrolRoundSchedule).filter(PatrolRoundSchedule.company_id == company.id).first():
        cp = (
            db.query(PatrolCheckpoint)
            .filter(PatrolCheckpoint.company_id == company.id, PatrolCheckpoint.site_id == site.id)
            .order_by(PatrolCheckpoint.sort_order.asc())
            .first()
        )
        if cp:
            for hm in ("06:00", "14:00", "22:00"):
                db.add(
                    PatrolRoundSchedule(
                        company_id=company.id,
                        site_id=site.id,
                        checkpoint_id=cp.id,
                        expected_time=hm,
                        grace_minutes=30,
                    )
                )
    db.commit()


def seed_cameras_if_empty(db: Session) -> None:
    if db.query(SecurityCamera).first():
        return
    company = db.query(Company).first()
    if not company:
        return
    sites = db.query(ClientSite).filter(ClientSite.company_id == company.id).limit(2).all()
    if not sites:
        return
    nvr = SecurityCamera(
        company_id=company.id,
        site_id=sites[0].id,
        camera_type="nvr",
        name="NVR demo sitio",
        brand="hikvision",
        ip_address="192.168.1.64",
        username="admin",
        password="demo1234",
        location="Cuarto eléctrico",
    )
    db.add(nvr)
    db.flush()
    db.add(
        SecurityCamera(
            company_id=company.id,
            site_id=sites[0].id,
            parent_id=nvr.id,
            camera_type="nvr_channel",
            name="Cam entrada",
            brand="hikvision",
            ip_address="192.168.1.64",
            channel=1,
            username="admin",
            password="demo1234",
            location="Portón",
        )
    )
    if len(sites) > 1:
        db.add(
            SecurityCamera(
                company_id=company.id,
                site_id=sites[1].id,
                camera_type="wifi",
                name="Cam WiFi demo",
                brand="tplink",
                ip_address="192.168.1.50",
                username="admin",
                password="demo1234",
                location="Interior",
            )
        )
    db.commit()
