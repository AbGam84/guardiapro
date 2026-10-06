# Excalibu Sentinel × AbSol@r Costa Rica

**Producto software:** Excalibu Sentinel (bitácora, rondas QR, GPS, portal cliente).  
**Distribución e instalación:** AbSol@r Costa Rica · soporte@absolar.latam · +506 6370-6546.

## Repo y carpetas

| Qué | Dónde |
|-----|--------|
| Código Sentinel | `C:\Users\PC\Documents\guardiapro` |
| Web comercial AbSol@r | `GovBidReady/solar/public-web/seguridad.html` |
| Demo nube | https://excalibu-sentinel.onrender.com/login |

## Arranque local

```bat
Iniciar-Excalibu.bat
```

→ http://127.0.0.1:8097/login

## Marca (config)

Variables en `app/config.py`:

- `GUARDIA_COMPANY_NAME` — default **AbSol@r Costa Rica**
- `GUARDIA_SUPPORT` / email — contacto comercial
- `ABSOLAR_SEGURIDAD_URL` — landing paquete cámaras + software

## Próximos cambios sugeridos

1. Unificar precios login comercial con `seguridad.html` (desde ₡58k/mes).
2. PDF bitácora: pie con logo AbSol@r + Excalibu.
3. Código demo empresa: `absolar` además de `excalibu-telecom`.
