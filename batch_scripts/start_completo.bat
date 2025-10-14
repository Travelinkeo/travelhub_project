@echo off
cd /d "%~dp0.."
echo Iniciando TravelHub completo...
echo.

echo 1. Iniciando Django Backend...
start cmd /k "cd /d %~dp0.. && venv\Scripts\activate && python manage.py runserver"

echo 2. Esperando 5 segundos...
timeout /t 5 /nobreak > nul

echo 3. Iniciando Cloudflare Tunnel...
start cmd /k "cd /d %~dp0.. && tools_bin\cloudflared tunnel --url http://localhost:8000"

echo 4. Esperando 5 segundos...
timeout /t 5 /nobreak > nul

echo 5. Iniciando Frontend Next.js...
start cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo ========================================
echo TravelHub iniciado completamente!
echo.
echo Backend: https://donald-border-lovers-incl.trycloudflare.com
echo Frontend: http://localhost:3000
echo Admin: https://donald-border-lovers-incl.trycloudflare.com/admin/
echo ========================================
echo.
pause