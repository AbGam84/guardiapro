@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

cd /d "%~dp0"

title Excalibu Sentinel - publicar en Render

echo.
echo  Excalibu Sentinel en la nube 24/7
echo  =================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo Instale Git primero.
  pause
  exit /b 1
)

where gh >nul 2>&1
if errorlevel 1 (
  echo Instale GitHub CLI: gh auth login
  pause
  exit /b 1
)

set /p MSG=Mensaje del commit (Enter = Actualizacion Excalibu Sentinel): 
if "%MSG%"=="" set "MSG=Actualizacion Excalibu Sentinel"

set "GIT_AUTHOR_NAME=AbGam84"
set "GIT_AUTHOR_EMAIL=soporte@absolar.latam"
set "GIT_COMMITTER_NAME=AbGam84"
set "GIT_COMMITTER_EMAIL=soporte@absolar.latam"

git add -A
git diff --cached --quiet
if not errorlevel 1 (
  echo No hay cambios para subir.
  goto pushonly
)
git commit -m "%MSG%"
if errorlevel 1 (
  pause
  exit /b 1
)

:pushonly
for /f "delims=" %%T in ('gh auth token 2^>nul') do set "GHTOKEN=%%T"
if not defined GHTOKEN (
  echo gh auth login
  pause
  exit /b 1
)

git push "https://x-access-token:!GHTOKEN!@github.com/AbGam84/guardiapro.git" main
if errorlevel 1 (
  echo Push fallo — pruebe: gh auth setup-git
  pause
  exit /b 1
)

echo.
echo URL: https://excalibu-sentinel.onrender.com
echo Comercial: /comercial  Admin: /admin  Oficial: /oficial
echo.
start https://dashboard.render.com
start https://excalibu-sentinel.onrender.com/login
pause
endlocal
