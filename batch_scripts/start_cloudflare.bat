@echo off
cd /d "%~dp0.."
echo Iniciando Django y Cloudflare Tunnel...
echo.
echo 1. Iniciando Django en puerto 8000...
start cmd /k "venv\Scripts\activate && python manage.py runserver"

echo 2. Esperando 5 segundos para que Django inicie...
timeout /t 5 /nobreak > nul

echo 3. Creando tunel con Cloudflare...
echo.
tools_bin\cloudflared.exe tunnel --url http://localhost:8000

pause