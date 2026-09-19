@echo off
cd /d "%~dp0"
set PY=
if exist .venv\Scripts\python.exe set PY=.venv\Scripts\python.exe
if not defined PY if exist "C:\Users\PC\Documents\TallerPro\.venv\Scripts\python.exe" set PY=C:\Users\PC\Documents\TallerPro\.venv\Scripts\python.exe
if not defined PY (
  echo No se encontro Python.
  pause
  exit /b 1
)
set PYTHONPATH=%CD%
echo.
echo ========================================
echo   Excalibu Sentinel - servidor local
echo ========================================
echo   PC:      http://127.0.0.1:8097/login
echo   Guardia: http://127.0.0.1:8097/guardia
echo   Admin:   admin / Admin2026!
echo ========================================
start http://127.0.0.1:8097/login
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8097
