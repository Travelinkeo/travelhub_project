@echo off
echo ========================================
echo   TravelHub - ACCESO REMOTO (CLOUDFLARE)
echo ========================================
echo.

REM 0. Ir a la carpeta raíz del proyecto
cd /d "%~dp0.."

REM 1. Activar Entorno Virtual Correcto (.venv)
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] No se encuentra el entorno virtual .venv
    pause
    exit
)

echo [1/2] Iniciando Servidor Django (Puerto 8000)...
start /B "TravelHub Server" python manage.py runserver 0.0.0.0:8000

echo Esperando 5 segundos...
timeout /t 5 /nobreak > nul

echo [2/2] Iniciando Cloudflare Tunnel...
echo.
echo ============================================================
echo   ENLACE REMOTO CLOUDFLARE:
echo   Busca la URL que termina en ".trycloudflare.com"
echo ============================================================
echo.
tools_bin\cloudflared.exe tunnel --url http://localhost:8000

echo.
echo Presiona Ctrl+C para salir
pause
