@echo off
cd /d "%~dp0"
set PY=
if exist .venv\Scripts\python.exe set PY=.venv\Scripts\python.exe
if not defined PY if exist "C:\Users\PC\Documents\TallerPro\.venv\Scripts\python.exe" set PY=C:\Users\PC\Documents\TallerPro\.venv\Scripts\python.exe
if not defined PY (
  echo No se encontro Python. Instale Python 3 o use el venv de TallerPro.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Instalando dependencias en venv compartido...
  "%PY%" -m pip install -r requirements.txt
)
set PYTHONPATH=%CD%

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4" ^| findstr /v "192.168.56"') do (
  set LAN_IP=%%a
  goto :gotip
)
:gotip
for /f "tokens=* delims= " %%b in ("%LAN_IP%") do set LAN_IP=%%b

echo.
echo ========================================
echo   GuardiaPro - servidor local
echo ========================================
echo   PC:      http://127.0.0.1:8097/login
if defined LAN_IP echo   Celular: http://%LAN_IP%:8097/guardia
echo   Admin:   admin / Admin2026!
echo   Guardia: juan / Guardia2026!
echo ========================================
echo   NO use guardiapro.onrender.com aun
echo   (hay que publicarlo en Render primero)
echo ========================================
echo.

start http://127.0.0.1:8097/login
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8097
