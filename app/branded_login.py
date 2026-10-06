"""Login HTML con marca del cliente (servidor) — no depende de login.html en caché."""

from __future__ import annotations

import html

from app.models import Company
from app.public_brand import public_branding_payload


def branded_login_html(company: Company, *, next_path: str = "") -> str:
    b = public_branding_payload(company)
    name = html.escape(b.get("name") or company.name or company.code)
    tagline = html.escape(b.get("tagline") or "Seguridad privada")
    code = html.escape(company.code)
    logo_block = ""
    if b.get("logo_url"):
        logo_src = html.escape(b["logo_url"])
        logo_block = (
            f'<img src="{logo_src}" alt="{name}" class="brand-logo" width="120" height="120" '
            'style="object-fit:contain;background:#0d1420;border-radius:12px;padding:8px;margin:0 auto 10px;display:block" />'
        )
    phone_block = ""
    if b.get("phone_display"):
        href = html.escape(b.get("whatsapp_url") or b.get("phone_tel") or "#")
        phone = html.escape(b["phone_display"])
        phone_block = f'<p class="client-brand-phone"><a href="{href}">{phone}</a></p>'

    next_q = html.escape(next_path) if next_path else ""
    next_js = repr(next_path) if next_path else '""'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{name} — acceso</title>
  <link rel="icon" href="/static/favicon.png" type="image/png" />
  <link rel="stylesheet" href="/static/css/app.css?v=7" />
  <style>
    .client-brand-head {{ text-align: center; margin-bottom: 12px; }}
    .client-brand-tagline {{ margin: 8px 0 0; font-size: .92rem; color: var(--gold); letter-spacing: .04em; text-transform: uppercase; font-weight: 600; }}
    .client-brand-phone {{ margin: 10px 0 0; font-size: 1.05rem; }}
    .client-brand-phone a {{ color: var(--teal); text-decoration: none; font-weight: 600; }}
    .login-powered {{ margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border); font-size: .72rem; color: var(--muted); text-align: center; }}
  </style>
</head>
<body>
  <div class="login-wrap panel">
    <div class="client-brand-head">
      {logo_block}
      <h1 style="font-size:1.15rem;line-height:1.35;margin:0;font-weight:700">{name}</h1>
      <p class="client-brand-tagline">{tagline}</p>
      {phone_block}
      <p class="login-powered">Acceso operativo · Excalibu Sentinel</p>
    </div>
    <form id="loginForm" class="form-grid">
      <label>Usuario<input name="username" required autocomplete="username" autofocus /></label>
      <label>Clave<input name="password" type="password" required autocomplete="current-password" /></label>
      <input type="hidden" name="company_code" value="{code}" />
      <button class="btn btn-primary btn-block" type="submit">Entrar</button>
    </form>
    <p id="err" class="error hidden"></p>
  </div>
  <script src="/static/js/api.js"></script>
  <script>
    document.getElementById("loginForm").addEventListener("submit", async (e) => {{
      e.preventDefault();
      const err = document.getElementById("err");
      err.classList.add("hidden");
      const fd = new FormData(e.target);
      try {{
        const data = await api("/api/auth/login", {{
          method: "POST",
          body: JSON.stringify({{
            username: fd.get("username"),
            password: fd.get("password"),
            company_code: fd.get("company_code") || "",
          }}),
        }});
        setToken(data.access_token);
        const role = data.user.role;
        const next = {next_js} || new URLSearchParams(location.search).get("next");
        if (next) location.href = next;
        else if (role === "guard") location.href = "/guardia";
        else if (role === "client") location.href = "/cliente";
        else location.href = "/admin";
      }} catch (ex) {{
        err.textContent = ex.message;
        err.classList.remove("hidden");
      }}
    }});
  </script>
</body>
</html>"""
