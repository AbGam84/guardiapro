@echo off
cd /d "%~dp0"
echo Abriendo material de marketing...
start http://127.0.0.1:8097/marketing/
timeout /t 1 /nobreak >nul
start http://127.0.0.1:8097/marketing/volante
timeout /t 1 /nobreak >nul
start http://127.0.0.1:8097/marketing/post
echo.
echo Si no abre: inicie primero Iniciar.bat
echo.
echo Textos WA: docs\marketing\PUBLICIDAD-DISTRIBUIDOR.txt
echo Guia Canva: docs\marketing\CANVA-GUIA.txt
pause
