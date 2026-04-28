@echo off
echo Iniciando TravelHub completo con acceso publico...
echo.

echo 1. Iniciando Django Backend...
start cmd /k "cd /d %~dp0 && venv\Scripts\activate && python manage.py runserver"

echo 2. Esperando 5 segundos...
timeout /t 5 /nobreak > nul

echo 3. Iniciando Cloudflare Tunnel para Backend...
start cmd /k "cd /d %~dp0 && .\cloudflared.exe tunnel --url http://localhost:8000"

echo 4. Esperando 5 segundos...
timeout /t 5 /nobreak > nul

echo 5. Iniciando Frontend Next.js...
start cmd /k "cd /d %~dp0\frontend && npm run dev"

echo 6. Esperando 10 segundos para que Next.js inicie...
timeout /t 10 /nobreak > nul

echo 7. Iniciando Cloudflare Tunnel para Frontend...
start cmd /k "cd /d %~dp0 && .\cloudflared.exe tunnel --url http://localhost:3000"

echo.
echo ========================================
echo TravelHub iniciado completamente!
echo.
echo IMPORTANTE: Espera a que aparezcan las URLs de Cloudflare
echo en las ventanas que se abrieron.
echo.
echo Backend estara en: https://XXXX.trycloudflare.com
echo Frontend estara en: https://YYYY.trycloudflare.com
echo ========================================
echo.
pause