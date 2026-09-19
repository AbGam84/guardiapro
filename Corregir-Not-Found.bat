@echo off
cd /d "%~dp0"
title Excalibu Sentinel - corregir Not Found
set PY=
if exist .venv\Scripts\python.exe set PY=.venv\Scripts\python.exe
if not defined PY set PY=C:\Users\PC\Documents\TallerPro\.venv\Scripts\python.exe
set CF=%~dp0tools\cloudflared.exe

echo.
echo ========================================
echo   EXCALIBU SENTINEL - CORREGIR URLs
echo ========================================
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8097" ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1

set PYTHONPATH=%CD%
start "Excalibu-Local" /MIN "%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8097
timeout /t 3 /nobreak >nul

echo [OK] LOCAL (su PC):
echo      http://127.0.0.1:8097/login
echo      http://127.0.0.1:8097/guardia
echo.

if exist "%CF%" (
  echo Iniciando link publico temporal...
  start "Excalibu-Tunel" "%CF%" tunnel --url http://127.0.0.1:8097
  echo      Espere 10 seg y copie el link trycloudflare.com de la ventana Excalibu-Tunel
) else (
  echo Para internet sin Render: ejecute Abrir-Fuera-De-WiFi.bat
)

echo.
echo [!!] RENDER da Not Found porque FALTA APPLY:
echo      1) https://dashboard.render.com/blueprints/new?repo=https://github.com/AbGam84/guardiapro
echo      2) GitHub -^> AbGam84 -^> APPLY
echo      3) URL final: https://excalibu-sentinel.onrender.com/guardia
echo.
echo      guardiapro.onrender.com NO sirve (nombre viejo, nunca creado)
echo ========================================
start http://127.0.0.1:8097/login
pause
