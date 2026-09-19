"""Páginas HTML — app operativa y marketing."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.paths import WEB, WEB_MARKETING

router = APIRouter(tags=["pages"])


def _html(relative: str) -> HTMLResponse:
    path = WEB / relative
    if not path.exists():
        raise HTTPException(status_code=404, detail="Página no encontrada")
    return HTMLResponse(path.read_text(encoding="utf-8"))


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
def root():
    return FileResponse(WEB / "login.html")


@router.get("/login")
def page_login():
    return _html("login.html")


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


@router.get("/vendor")
def page_vendor():
    return _html("vendor.html")


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


@router.get("/publicidad-panfleto")
def page_pamphlet_legacy():
    return _marketing("panfleto.html")
