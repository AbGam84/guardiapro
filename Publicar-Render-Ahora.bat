@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Publicar excalibu-sentinel en Render (API)
echo.
echo Si no tiene RENDER_API_KEY:
echo   Render ^→ Account Settings ^→ API Keys ^→ Create
echo   Agregue en push-cloud.env: RENDER_API_KEY=rnd_...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\render_publish.ps1
pause
