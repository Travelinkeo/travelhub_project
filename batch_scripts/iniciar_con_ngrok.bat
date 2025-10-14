@echo off
cd /d "%~dp0.."
echo ========================================
echo   TravelHub - Inicio con Ngrok
echo ========================================
echo.

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Iniciar Django en segundo plano
echo Iniciando servidor Django...
start /B python manage.py runserver 0.0.0.0:8000

REM Esperar 3 segundos para que Django inicie
timeout /t 3 /nobreak > nul

REM Iniciar ngrok (desde tools_bin)
echo Iniciando tunel ngrok...
echo.
echo ============================================================
echo   IMPORTANTE: Copia la URL https://xxxxx.ngrok-free.app
echo   que aparecera abajo y compartela con tu esposa
echo ============================================================
echo.
tools_bin\ngrok.exe http 8000

REM Al cerrar ngrok, detener Django
taskkill /F /IM python.exe
