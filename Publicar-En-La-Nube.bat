@echo off
cd /d "%~dp0"
title GuardiaPro - publicar en Render
echo.
echo  GuardiaPro en la nube 24/7
echo  ==========================
echo.
pause

where git >nul 2>&1
if errorlevel 1 (
  echo Instale Git primero.
  pause
  exit /b 1
)

if not exist ".git" git init
git add -A
git commit -m "GuardiaPro listo para nube" 2>nul

git remote remove origin 2>nul
git remote add origin https://github.com/AbGam84/guardiapro.git
git branch -M main
echo.
echo Subiendo a GitHub...
git push -u origin main

echo.
echo Abriendo Render Blueprint...
start "" "https://dashboard.render.com/blueprints/new?repo=https://github.com/AbGam84/guardiapro"
echo.
echo URL final: https://guardiapro.onrender.com
echo Vendor: /vendor  usuario vendor  clave GuardiaVendor2026
echo.
pause
