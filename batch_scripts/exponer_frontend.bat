@echo off
echo Exponiendo Frontend via Cloudflare...
echo.
echo IMPORTANTE: Asegurate de que el frontend este corriendo en puerto 3000
echo.
.\cloudflared.exe tunnel --url http://localhost:3000
pause