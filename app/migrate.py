import uuid

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema(engine: Engine) -> None:
    """Agrega columnas nuevas sin perder datos existentes (SQLite / Postgres)."""
    insp = inspect(engine)
    tables = insp.get_table_names()

    if "patrol_checkpoints" in tables:
        cols = {c["name"] for c in insp.get_columns("patrol_checkpoints")}
        dialect = engine.dialect.name

        with engine.begin() as conn:
            if "qr_token" not in cols:
                conn.execute(text("ALTER TABLE patrol_checkpoints ADD COLUMN qr_token VARCHAR(64)"))
            if "lat" not in cols:
                if dialect == "sqlite":
                    conn.execute(text("ALTER TABLE patrol_checkpoints ADD COLUMN lat FLOAT"))
                else:
                    conn.execute(text("ALTER TABLE patrol_checkpoints ADD COLUMN lat DOUBLE PRECISION"))
            if "lng" not in cols:
                if dialect == "sqlite":
                    conn.execute(text("ALTER TABLE patrol_checkpoints ADD COLUMN lng FLOAT"))
                else:
                    conn.execute(text("ALTER TABLE patrol_checkpoints ADD COLUMN lng DOUBLE PRECISION"))

        with engine.begin() as conn:
            rows = conn.execute(
                text("SELECT id FROM patrol_checkpoints WHERE qr_token IS NULL OR qr_token = ''")
            ).fetchall()
            for (cp_id,) in rows:
                token = uuid.uuid4().hex
                conn.execute(
                    text("UPDATE patrol_checkpoints SET qr_token = :t WHERE id = :id"),
                    {"t": token, "id": cp_id},
                )

    if "users" in tables:
        cols = {c["name"] for c in insp.get_columns("users")}
        dialect = engine.dialect.name
        with engine.begin() as conn:
            if "client_site_id" not in cols:
                if dialect == "sqlite":
                    conn.execute(text("ALTER TABLE users ADD COLUMN client_site_id INTEGER"))
                else:
                    conn.execute(text("ALTER TABLE users ADD COLUMN client_site_id INTEGER"))
            if "field_code" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN field_code VARCHAR(12) DEFAULT ''"))

    if "shifts" in tables:
        cols = {c["name"] for c in insp.get_columns("shifts")}
        dialect = engine.dialect.name
        with engine.begin() as conn:
            for col in ("start_lat", "start_lng", "end_lat", "end_lng"):
                if col not in cols:
                    if dialect == "sqlite":
                        conn.execute(text(f"ALTER TABLE shifts ADD COLUMN {col} FLOAT"))
                    else:
                        conn.execute(text(f"ALTER TABLE shifts ADD COLUMN {col} DOUBLE PRECISION"))

    if "log_entries" in tables:
        cols = {c["name"] for c in insp.get_columns("log_entries")}
        with engine.begin() as conn:
            if "sector" not in cols:
                conn.execute(text("ALTER TABLE log_entries ADD COLUMN sector VARCHAR(120) DEFAULT ''"))
            if "involved" not in cols:
                conn.execute(text("ALTER TABLE log_entries ADD COLUMN involved VARCHAR(255) DEFAULT ''"))
            if "action_taken" not in cols:
                conn.execute(text("ALTER TABLE log_entries ADD COLUMN action_taken TEXT DEFAULT ''"))

    if "security_cameras" in tables:
        cols = {c["name"] for c in insp.get_columns("security_cameras")}
        dialect = engine.dialect.name
        with engine.begin() as conn:
            if "share_guard_id" not in cols:
                conn.execute(text("ALTER TABLE security_cameras ADD COLUMN share_guard_id INTEGER"))
            if "share_shift_id" not in cols:
                conn.execute(text("ALTER TABLE security_cameras ADD COLUMN share_shift_id INTEGER"))
            if "share_active" not in cols:
                if dialect == "sqlite":
                    conn.execute(text("ALTER TABLE security_cameras ADD COLUMN share_active BOOLEAN DEFAULT 0"))
                else:
                    conn.execute(text("ALTER TABLE security_cameras ADD COLUMN share_active BOOLEAN DEFAULT FALSE"))
            if "mobile_frame" not in cols:
                conn.execute(text("ALTER TABLE security_cameras ADD COLUMN mobile_frame VARCHAR(255) DEFAULT ''"))
            if "last_frame_at" not in cols:
                conn.execute(text("ALTER TABLE security_cameras ADD COLUMN last_frame_at DATETIME"))

    if "camera_pair_tokens" not in tables:
        from app.database import Base
        from app.models import CameraPairToken  # noqa: F401

        Base.metadata.create_all(bind=engine, tables=[CameraPairToken.__table__])
