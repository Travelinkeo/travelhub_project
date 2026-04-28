@echo off
REM Iniciar Celery Beat para tareas programadas
cd /d "%~dp0.."
echo ========================================
echo Iniciando Celery Beat (Tareas Programadas)
echo ========================================
echo Tarea: Monitor Boletos cada 5 minutos
echo ========================================
celery -A travelhub beat --loglevel=info
pause
