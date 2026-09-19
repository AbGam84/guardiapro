from html import escape

from sqlalchemy.orm import Session

from app.config import COPYRIGHT, PRODUCT_NAME
from app.geo import format_distance
from app.helpers import ENTRY_LABELS, SEVERITY_LABELS, log_dict, shift_dict
from app.models import Company, LogEntry, Shift
from app.patrol_stats import patrol_period_stats, shift_patrol_stats

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
        detail_parts = []
        if log.get("sector"):
            detail_parts.append(f"<strong>Sector:</strong> {escape(log['sector'])}")
        if log.get("note"):
            detail_parts.append(f"<strong>Descripción:</strong> {escape(log['note'])}")
        if log.get("involved"):
            detail_parts.append(f"<strong>Involucrado:</strong> {escape(log['involved'])}")
        if log.get("action_taken"):
            detail_parts.append(f"<strong>Acción:</strong> {escape(log['action_taken'])}")
        detail = "<br>".join(detail_parts) or escape(log.get("note") or "")
        rows += f"""
        <tr>
          <td>{escape(log.get("created_at") or "")}</td>
          <td>{escape(log.get("entry_label") or "")}</td>
          <td>{escape(sev)}</td>
          <td>{detail}{photo}</td>
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
<h1>Bitácora de servicio — {escape(PRODUCT_NAME)}</h1>
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
<p class="meta" style="margin-top:20px">{escape(COPYRIGHT)}</p>
</body></html>"""


def patrol_report_html(db: Session, company_id: int, *, days: int, guard_id: int = 0) -> str:
    company = db.query(Company).filter(Company.id == company_id).first()
    data = patrol_period_stats(db, company_id, days=days, guard_id=guard_id)
    period_label = "Semanal (7 días)" if days <= 7 else "Quincenal (15 días)"

    guard_rows = ""
    for g in data["guards"]:
        sites = ", ".join(g.get("sites") or []) or "—"
        guard_rows += f"""
        <tr>
          <td>{escape(g["guard"].get("name") or "")}<br><span class="muted">{escape(g["guard"].get("badge") or "")}</span></td>
          <td>{g["shifts"]}</td>
          <td>{g["checkpoint_marks"]}</td>
          <td>{escape(g["total_distance_label"])}</td>
          <td>{escape(sites)}</td>
        </tr>"""

    detail = ""
    for sh in data["shifts"]:
        marks = ""
        for m in sh.get("marks") or []:
            loc = f"{m['lat']:.5f}, {m['lng']:.5f}" if m.get("lat") is not None else "—"
            dist = format_distance(m.get("distance_from_prev_m") or 0) if m.get("distance_from_prev_m") else "—"
            marks += f"<li>{escape(m.get('time') or '')} · <strong>{escape(m.get('checkpoint') or '')}</strong> · {escape(loc)} · +{escape(dist)}</li>"
        detail += f"""
        <div class="shift-block">
          <h3>{escape(sh["guard"].get("name") or "")} — {escape(sh["site"].get("name") or "")}</h3>
          <p class="meta">Turno #{sh["shift_id"]} · {escape(sh.get("started_at") or "")} → {escape(sh.get("ended_at") or "abierto")}<br>
          Recorrido: <strong>{escape(sh.get("total_distance_label") or "")}</strong> · Marcas QR: {sh.get("checkpoint_marks") or 0}</p>
          <ul>{marks or "<li>Sin marcas QR en este turno</li>"}</ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"/>
<title>Reporte recorrido — {escape(PRODUCT_NAME)}</title>
<style>
body{{font-family:Segoe UI,sans-serif;margin:24px;color:#111}}
h1{{margin:0 0 4px;font-size:1.4rem}}
.meta{{color:#555;font-size:.9rem;margin-bottom:16px}}
.muted{{color:#666;font-size:.85rem}}
table{{width:100%;border-collapse:collapse;font-size:.85rem;margin-bottom:24px}}
th,td{{border:1px solid #ccc;padding:8px;text-align:left;vertical-align:top}}
th{{background:#f0f4f8}}
.shift-block{{border:1px solid #ddd;border-radius:8px;padding:12px 16px;margin-bottom:16px;page-break-inside:avoid}}
.shift-block h3{{margin:0 0 6px;font-size:1rem}}
.shift-block ul{{margin:8px 0 0;padding-left:18px;font-size:.85rem}}
.summary{{display:flex;gap:24px;flex-wrap:wrap;margin:16px 0}}
.summary div{{background:#f7fbff;border:1px solid #cde;padding:12px 16px;border-radius:8px}}
@media print{{button{{display:none}}}}
</style></head><body>
<button onclick="window.print()">Imprimir / PDF</button>
<h1>Reporte de recorrido — {escape(period_label)}</h1>
<p class="meta"><strong>{escape(company.name if company else "")}</strong><br>
Período: {escape(data.get("since") or "")} → {escape(data.get("until") or "")}</p>
<div class="summary">
  <div><span class="muted">Turnos</span><br><strong>{data.get("shift_count") or 0}</strong></div>
  <div><span class="muted">Distancia total</span><br><strong>{escape(data.get("total_distance_label") or "")}</strong></div>
  <div><span class="muted">Oficiales</span><br><strong>{len(data.get("guards") or [])}</strong></div>
</div>
<h2>Resumen por oficial</h2>
<table>
<thead><tr><th>Oficial</th><th>Turnos</th><th>Marcas QR</th><th>Recorrido</th><th>Sitios</th></tr></thead>
<tbody>{guard_rows or "<tr><td colspan='5'>Sin datos en el período</td></tr>"}</tbody>
</table>
<h2>Detalle de marcas y recorrido</h2>
{detail or "<p class='muted'>Sin turnos registrados en el período.</p>"}
<p class="meta" style="margin-top:20px">{escape(COPYRIGHT)}</p>
</body></html>"""
