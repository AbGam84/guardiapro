from html import escape

from sqlalchemy.orm import Session

from app.helpers import ENTRY_LABELS, SEVERITY_LABELS, log_dict, shift_dict
from app.models import Company, LogEntry, Shift


def shift_report_html(db: Session, shift_id: int, company_id: int) -> str:
    sh = db.query(Shift).filter(Shift.id == shift_id, Shift.company_id == company_id).first()
    if not sh:
        return "<p>Turno no encontrado</p>"
    company = db.query(Company).filter(Company.id == company_id).first()
    data = shift_dict(db, sh)
    rows = ""
    for log in data.get("logs") or []:
        sev = log.get("severity_label") or "Normal"
        photo = ""
        if log.get("photo_url"):
            photo = f'<br><img src="{escape(log["photo_url"])}" style="max-width:280px;margin-top:8px;border-radius:8px" />'
        rows += f"""
        <tr>
          <td>{escape(log.get("created_at") or "")}</td>
          <td>{escape(log.get("entry_label") or "")}</td>
          <td>{escape(sev)}</td>
          <td>{escape(log.get("note") or "")}{photo}</td>
        </tr>"""
    guard = data.get("guard") or {}
    site = data.get("site") or {}
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"/>
<title>Bitácora turno #{sh.id}</title>
<style>
body{{font-family:Segoe UI,sans-serif;margin:24px;color:#111}}
h1{{margin:0 0 4px;font-size:1.4rem}}
.meta{{color:#555;font-size:.9rem;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
th,td{{border:1px solid #ccc;padding:8px;text-align:left;vertical-align:top}}
th{{background:#f0f4f8}}
@media print{{button{{display:none}}}}
</style></head><body>
<button onclick="window.print()">Imprimir / PDF</button>
<h1>Bitácora de servicio — GuardiaPro</h1>
<p class="meta">
  <strong>{escape(company.name if company else "")}</strong><br>
  Oficial: {escape(guard.get("name") or "")} ({escape(guard.get("badge") or "")})<br>
  Sitio: {escape(site.get("name") or "")} — {escape(site.get("address") or "")}<br>
  Cliente: {escape(site.get("client_name") or "")}<br>
  Inicio: {escape(data.get("started_at") or "")} · Fin: {escape(data.get("ended_at") or "—")}
</p>
<table>
<thead><tr><th>Fecha/hora</th><th>Tipo</th><th>Prioridad</th><th>Detalle</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p class="meta" style="margin-top:20px">Documento generado por GuardiaPro · Costa Rica</p>
</body></html>"""
