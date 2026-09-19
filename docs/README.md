# Excalibu Sentinel — documentación

## Arranque local

Doble clic en **`Iniciar.bat`** (raíz del proyecto).

| Rol | Usuario | Clave | Panel |
|-----|---------|-------|-------|
| Comercial (Excalibu) | vendor | GuardiaVendor2026 | `/comercial` |
| Admin cliente | admin | Admin2026! | `/admin` |
| Oficial | código 6 dígitos | — | `/oficial` |

**Panel comercial** (`/comercial`): vender licencias — crear empresas, administradores del cliente y oficiales con código celular. No es el admin operativo.

URLs locales: http://127.0.0.1:8097/login · `/comercial` · `/admin` · `/oficial` · `/cliente`

## Estructura del código

```
app/
  main.py          # FastAPI — arranque y mounts
  routes/
    pages.py       # HTML (login, admin, marketing…)
    api.py         # REST API
  models.py        # SQLAlchemy
  patrol_alerts.py # Alertas ronda incumplida
web/
  admin.html       # Centro de control
  guardia.html     # App del oficial (PWA)
  cliente.html     # Portal solo lectura
  marketing/       # Volantes y posts HTML
docs/
  marketing/       # Textos WA, guía Canva
scripts/
  repair_db.py     # Migración al arrancar
  smoke_test.py    # Prueba rápida API
```

## Nube (Render)

Servicio: **excalibu-sentinel** → https://excalibu-sentinel.onrender.com

Ver `PASO-A-PASO-RENDER.txt` en la raíz.

## Marketing

- HTML: `/marketing/` (volante, post, story, panfleto)
- Textos listos: `docs/marketing/PUBLICIDAD-DISTRIBUIDOR.txt`
- PNG: `Generar-Imagenes-Publicidad.bat`

Empresa: **Excalibu Telecom CR** · WhatsApp +506 6370-6546
