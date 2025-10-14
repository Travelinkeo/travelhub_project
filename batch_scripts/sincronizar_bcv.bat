@echo off
REM Script para sincronizar tasa BCV automáticamente
REM Ejecutar con Task Scheduler diariamente

cd /d "%~dp0.."
call venv\Scripts\activate.bat
python manage.py sincronizar_tasa_bcv >> logs\bcv_sync.log 2>&1
