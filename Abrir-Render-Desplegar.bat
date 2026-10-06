@echo off
chcp 65001 >nul
echo Render: excalibu-sentinel
echo 1) Deploys - si hay "In progress" antiguo, Cancel deploy
echo 2) Manual Deploy - latest commit main
echo 3) Environment - quitar GUARDIA_BUILD=20260929 si existe
start https://dashboard.render.com/web/srv-dand4drtqb8s73bgpe30/deploys
start https://excalibu-sentinel.onrender.com/login?empresa=grupo-gomez
pause
