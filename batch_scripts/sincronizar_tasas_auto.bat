@echo off
REM ============================================
REM Sincronizacion automatica de tasas BCV
REM Se ejecuta 3 veces al dia: 08:00, 12:00, 17:00
REM ============================================

cd /d "%~dp0.."

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Ejecutar sincronizacion
echo [%date% %time%] Sincronizando tasas de cambio...
python manage.py sincronizar_tasa_bcv >> logs\tasas_sync.log 2>&1

REM Verificar resultado
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Sincronizacion exitosa >> logs\tasas_sync.log
) else (
    echo [%date% %time%] ERROR en sincronizacion >> logs\tasas_sync.log
)

deactivate
