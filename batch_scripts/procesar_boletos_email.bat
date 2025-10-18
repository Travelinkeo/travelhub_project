@echo off
REM Script para procesar boletos desde correo electrónico
REM Ejecutar este script con Task Scheduler cada 15 minutos

cd /d "%~dp0.."

echo ========================================
echo Procesando boletos desde correo...
echo ========================================
echo.

call venv\Scripts\activate.bat
python manage.py procesar_boletos_email

echo.
echo ========================================
echo Proceso completado
echo ========================================
