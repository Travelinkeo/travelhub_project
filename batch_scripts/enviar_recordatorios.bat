@echo off
REM Script para enviar recordatorios de pago automaticamente
REM Se ejecuta diariamente via Task Scheduler

cd /d "%~dp0.."
call venv\Scripts\activate.bat
python manage.py enviar_recordatorios_pago --dias=3

REM Opcional: Guardar log
echo Recordatorios enviados el %date% %time% >> logs\recordatorios.log
