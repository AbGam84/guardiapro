# Excalibu Sentinel

**Bitácora digital, rondas con QR, GPS y alertas** para empresas de seguridad privada en Costa Rica.

Eslogan: *Su guardia cuida el sitio. Excalibu cuida al guardia.*

## Funciones

| Módulo | Qué hace |
|--------|----------|
| **Bitácora oficial** | Inicio/fin turno con GPS, novedades e incidentes |
| **Rondas QR** | Checkpoints por sitio — escaneo en el muro |
| **Alertas** | Aviso si no cumplen horario de ronda |
| **Portal cliente** | Solo lectura para el contratante |
| **Cámaras** | Vista integrada en el turno del oficial |
| **WhatsApp** | Alerta al supervisor en incidentes graves |
| **PDF / imprimir** | Bitácora por turno para entregar al cliente |
| **Multi-empresa** | Panel Vendor crea empresas aisladas |
| **PWA + offline** | Instalable en celular del oficial |

## Local

Doble clic: **`Iniciar.bat`** → http://127.0.0.1:8097/login

| Rol | Usuario | Clave |
|-----|---------|-------|
| Admin | admin | Admin2026! |
| Oficial | juan | Guardia2026! |
| Cliente | cliente | Cliente2026! |
| Comercial | vendor | GuardiaVendor2026! |

## Estructura

```
app/main.py          → arranque FastAPI
app/routes/pages.py  → pantallas HTML
app/routes/api.py    → API REST
web/marketing/       → volantes y posts
docs/                → guías y textos comerciales
```

Más detalle: [docs/README.md](docs/README.md)

## Nube (Render)

1. `Publicar-En-La-Nube.bat`
2. Aplicar blueprint en Render (repo `AbGam84/guardiapro`, servicio `excalibu-sentinel`)
3. URL: **https://excalibu-sentinel.onrender.com**

Ver `PASO-A-PASO-RENDER.txt`.

## Marketing

- `/marketing/` — volante, post, story, panfleto
- Textos WhatsApp: `docs/marketing/PUBLICIDAD-DISTRIBUIDOR.txt`
- PNG: `Generar-Imagenes-Publicidad.bat`

## Cobro sugerido

- Instalación: ₡90.000 – ₡150.000
- Mensual (hasta 20 oficiales): ₡55.000 – ₡85.000
- Paquete cámaras + WiFi + Sentinel: cotización integrada

**Excalibu Telecom CR** · WhatsApp +506 6370-6546
