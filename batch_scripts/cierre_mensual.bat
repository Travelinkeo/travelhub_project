@echo off
REM Script para ejecutar cierre contable mensual
REM Ejecutar con Task Scheduler el día 1 de cada mes

cd /d "%~dp0"
call venv\Scripts\activate.bat
python manage.py cierre_mensual >> logs\cierre_mensual.log 2>&1
