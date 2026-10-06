@echo off
cd /d "%~dp0"
if not exist push-cloud.env (
  echo Cree push-cloud.env desde push-cloud.env.example con claves de Render.
  pause
  exit /b 1
)
set PYTHONPATH=.
python scripts\push_local_to_cloud.py
pause
