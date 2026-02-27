@echo off
echo ========================================
echo   TravelHub - ACCESO REMOTO (NGROK)
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

echo [2/2] Iniciando Tunel NGROK...
echo.
echo ============================================================
echo   TU ENLACE REMOTO APARECERA EN LA OTRA VENTANA
echo   Busca la linea que dice "Forwarding https://xxxx.ngrok..."
echo ============================================================
echo.
ngrok http 8000 --log=stdout

echo.
echo Presiona Ctrl+C para salir
pause
