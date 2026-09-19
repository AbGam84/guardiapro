@echo off
cd /d "%~dp0"
title GuardiaPro - link publico (internet)
set CF=%~dp0tools\cloudflared.exe

if not exist "%CF%" (
  echo Descargando tunel...
  mkdir tools 2>nul
  powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%CF%'"
)

netstat -ano | findstr ":8097" | findstr LISTENING >nul
if errorlevel 1 (
  echo Primero inicie GuardiaPro local:
  echo   Iniciar-GuardiaPro.bat
  echo.
  pause
  exit /b 1
)

echo.
echo ========================================
echo   GuardiaPro - ACCESO DESDE INTERNET
echo ========================================
echo   Deje esta ventana ABIERTA.
echo   En unos segundos aparece un link:
echo   https://....trycloudflare.com/guardia
echo.
echo   Comparta ese link al celular del guardia
echo   (funciona con datos moviles, otra WiFi, etc.)
echo.
echo   Para link fijo 24/7 use Render:
echo   Publicar-En-La-Nube.bat
echo ========================================
echo.

"%CF%" tunnel --url http://127.0.0.1:8097
