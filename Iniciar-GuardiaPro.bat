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
echo GuardiaPro en http://127.0.0.1:8097
start http://127.0.0.1:8097/login
"%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8097
