# Excalibu Sentinel — documentación

## Arranque local

Doble clic en **`Iniciar.bat`** (raíz del proyecto).

| Rol | Usuario | Clave |
|-----|---------|-------|
| Admin | admin | Admin2026! |
| Oficial | *(crear en Admin → Ajustes)* | — |
| Vendor | vendor | GuardiaVendor2026 |

URLs locales: http://127.0.0.1:8097/login · `/guardia` · `/admin` · `/cliente`

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
