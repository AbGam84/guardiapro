"""Genera app/routes/api.py desde app/main.py (ejecutar una vez)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "app/main.py").read_text(encoding="utf-8")
lines = src.splitlines()
body = "\n".join(lines[155:1266])
body = body.replace("@app.", "@router.")
body = body.replace("_public_base", "public_base")
body = body.replace("_company(", "get_company(")
body = body.replace("_whatsapp_link", "whatsapp_link")
body = body.replace("_client_site_id", "client_site_id")
body = body.replace("_ensure_site_access", "ensure_site_access")
body = body.replace(
    "        from app.geo import haversine_m\n\n        seg",
    "        seg",
)

header = (ROOT / "app/routes/_api_header.py").read_text(encoding="utf-8")
(ROOT / "app/routes/api.py").write_text(header + body, encoding="utf-8")
print("OK", ROOT / "app/routes/api.py", "lines", len((header + body).splitlines()))
