"""Páginas HTML — app operativa y marketing."""

import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company
from app.paths import WEB, WEB_MARKETING

router = APIRouter(tags=["pages"])


def _html(relative: str) -> HTMLResponse:
    path = WEB / relative
    if not path.exists():
        raise HTTPException(status_code=404, detail="Página no encontrada")
    return HTMLResponse(path.read_text(encoding="utf-8"))


def _safe_company_code(raw: str | None) -> str:
    code = (raw or "").strip().lower()
    if not code or not re.fullmatch(r"[a-z0-9-]+", code):
        return ""
    return code


def _login_html(request: Request, db: Session) -> HTMLResponse:
    path = WEB / "login.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Página no encontrada")
    content = path.read_text(encoding="utf-8")
    code = _safe_company_code(request.query_params.get("empresa") or request.query_params.get("code"))
    if code and db.query(Company).filter(Company.code == code, Company.active.is_(True)).first():
        inject = f"""
<script id="excalibu-brand-prefill">
(function(){{
  function run(){{
    var c = {json.dumps(code)};
    var ci = document.querySelector('input[name="company_code"]');
    if (ci) {{ ci.value = c; var det = ci.closest('details'); if (det) det.open = true; }}
    if (typeof refreshClientBrand === "function") {{ refreshClientBrand(c); return; }}
    if (typeof applyBranding === "function") {{
      fetch("/api/branding/" + encodeURIComponent(c))
        .then(function(r) {{ return r.ok ? r.json() : null; }})
        .then(function(b) {{ if (b) applyBranding(b); }});
    }}
  }}
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else setTimeout(run, 0);
}})();
</script>
"""
        content = content.replace("</body>", inject + "\n</body>")
    return HTMLResponse(content, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


def _marketing(name: str) -> HTMLResponse:
    path = WEB_MARKETING / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Material no encontrado")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@router.get("/web/{page:path}")
def web_alias(page: str):
    allowed = {"login", "guardia", "admin", "vendor", "cliente", "demo", "login.html", "guardia.html", "admin.html"}
    target = page.replace(".html", "")
    if target in allowed or page in allowed:
        return RedirectResponse(f"/{target.replace('.html', '')}", status_code=307)
    return RedirectResponse("/login", status_code=307)


@router.get("/")
def root(request: Request, db: Session = Depends(get_db)):
    return _login_html(request, db)


@router.get("/login")
def page_login(request: Request, db: Session = Depends(get_db)):
    return _login_html(request, db)


@router.get("/guardia")
def page_guard():
    return _html("guardia.html")


@router.get("/oficial")
def page_oficial():
    return _html("oficial.html")


@router.get("/admin")
def page_admin():
    return _html("admin.html")


@router.get("/cliente")
def page_client():
    return _html("cliente.html")


@router.get("/comercial")
def page_comercial():
    return _html("comercial.html")


@router.get("/vendor")
def page_vendor_legacy():
    return RedirectResponse("/comercial", status_code=307)


@router.get("/demo")
def page_demo_legacy():
    return RedirectResponse("/login", status_code=307)


@router.get("/cameras/{camera_id}")
def page_camera_view(camera_id: int):
    return _html("cameras.html")


@router.get("/manifest.json")
def manifest():
    return FileResponse(WEB / "manifest.json")


@router.get("/sw.js")
def service_worker():
    return FileResponse(WEB / "static" / "sw.js", media_type="application/javascript")


# Marketing (también en /marketing/…)
@router.get("/marketing/{page:path}")
def marketing_page(page: str):
    mapping = {
        "": "index.html",
        "index.html": "index.html",
        "volante": "volante.html",
        "volante.html": "volante.html",
        "post": "post.html",
        "post.html": "post.html",
        "story": "story.html",
        "story.html": "story.html",
        "panfleto": "panfleto.html",
        "panfleto.html": "panfleto.html",
        "informe": "informe.html",
        "informe.html": "informe.html",
    }
    name = mapping.get(page, page if page.endswith(".html") else f"{page}.html")
    return _marketing(name)


@router.get("/publicidad-volante")
def page_flyer_legacy():
    return _marketing("volante.html")


@router.get("/publicidad-post")
def page_post_legacy():
    return _marketing("post.html")


@router.get("/publicidad-story")
def page_story_legacy():
    return _marketing("story.html")


@router.get("/informe")
@router.get("/informe-seguridad")
def page_informe_seguridad():
    return _marketing("informe.html")


@router.get("/publicidad-panfleto")
def page_pamphlet_legacy():
    return _marketing("panfleto.html")
