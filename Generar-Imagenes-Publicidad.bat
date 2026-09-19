@echo off
cd /d "%~dp0"
set PY=
if exist .venv\Scripts\python.exe set PY=.venv\Scripts\python.exe
if not defined PY set PY=python
echo Generando PNG para WhatsApp...
"%PY%" scripts\generate_publicidad_png.py
echo.
echo Abriendo carpeta de imagenes...
start "" "%USERPROFILE%\OneDrive\Escritorio\publisidad de seguridad\imagenes"
pause
