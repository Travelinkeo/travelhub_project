@echo off
REM Iniciar Celery Worker para procesar tareas
cd /d "%~dp0.."
echo ========================================
echo Iniciando Celery Worker
echo ========================================
celery -A travelhub worker --loglevel=info --pool=solo
pause
