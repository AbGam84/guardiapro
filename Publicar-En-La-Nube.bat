@echo off
cd /d "%~dp0"
title Excalibu Sentinel - publicar en Render
echo.
echo  Excalibu Sentinel en la nube 24/7
echo  =================================
echo.
pause

where git >nul 2>&1
if errorlevel 1 (
  echo Instale Git primero.
  pause
  exit /b 1
)

git add -A
git commit -m "Excalibu Sentinel listo para nube" 2>nul
git push origin main

echo.
echo Abriendo Render Blueprint...
start https://dashboard.render.com/blueprints/new?repo=https://github.com/AbGam84/guardiapro
echo.
echo URL final: https://excalibu-sentinel.onrender.com
echo Guardia:   /guardia
echo Admin:     /admin
echo.
pause
