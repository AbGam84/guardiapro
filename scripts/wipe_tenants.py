"""Borra todas las empresas clientes (SQLite local). El acceso comercial sigue siendo vendor por .env."""
from app.database import SessionLocal
from app.seed import _COMMERCIAL_BASELINE_MARKER, wipe_all_tenant_data

if __name__ == "__main__":
    db = SessionLocal()
    try:
        n = wipe_all_tenant_data(db)
        _COMMERCIAL_BASELINE_MARKER.write_text("ok\n", encoding="utf-8")
        print(f"Empresas eliminadas: {n}. Panel comercial listo para la primera venta.")
    finally:
        db.close()
