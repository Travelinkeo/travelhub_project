@echo off
REM Iniciar Celery Worker + Beat en ventanas separadas
cd /d "%~dp0.."
echo ========================================
echo Iniciando Sistema Celery Completo
echo ========================================
echo Worker: Procesa tareas
echo Beat: Programa tareas cada 5 min
echo ========================================

start "Celery Worker" cmd /k "celery -A travelhub worker --loglevel=info --pool=solo"
timeout /t 3 /nobreak >nul
start "Celery Beat" cmd /k "celery -A travelhub beat --loglevel=info"

echo.
echo ========================================
echo Sistema Celery iniciado
echo ========================================
echo Worker: Ventana "Celery Worker"
echo Beat: Ventana "Celery Beat"
echo ========================================
pause
