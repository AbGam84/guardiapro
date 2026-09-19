import uuid

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema(engine: Engine) -> None:
    """Agrega columnas nuevas sin perder datos existentes (SQLite / Postgres)."""
    insp = inspect(engine)
    tables = insp.get_table_names()
    if "patrol_checkpoints" not in tables:
        return

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

    # Tokens únicos para checkpoints existentes
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id FROM patrol_checkpoints WHERE qr_token IS NULL OR qr_token = ''")).fetchall()
        for (cp_id,) in rows:
            token = uuid.uuid4().hex
            conn.execute(
                text("UPDATE patrol_checkpoints SET qr_token = :t WHERE id = :id"),
                {"t": token, "id": cp_id},
            )
