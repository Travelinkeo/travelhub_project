@echo off
REM ============================================
REM Configurar tareas programadas en Windows
REM Ejecutar como Administrador
REM ============================================

echo ============================================
echo   CONFIGURACION DE TAREAS PROGRAMADAS
echo ============================================
echo.

REM Obtener ruta del proyecto
set PROYECTO_DIR=%~dp0..
set SCRIPT_TASAS=%PROYECTO_DIR%\batch_scripts\sincronizar_tasas_auto.bat

echo Proyecto: %PROYECTO_DIR%
echo Script: %SCRIPT_TASAS%
echo.

REM Eliminar tareas existentes (si existen)
echo Eliminando tareas antiguas...
schtasks /Delete /TN "TravelHub_Tasas_08AM" /F 2>nul
schtasks /Delete /TN "TravelHub_Tasas_12PM" /F 2>nul
schtasks /Delete /TN "TravelHub_Tasas_05PM" /F 2>nul
echo.

REM Crear tarea para las 08:00 AM
echo Creando tarea para las 08:00 AM...
schtasks /Create /TN "TravelHub_Tasas_08AM" /TR "\"%SCRIPT_TASAS%\"" /SC DAILY /ST 08:00 /F
if %ERRORLEVEL% EQU 0 (
    echo [OK] Tarea 08:00 AM creada
) else (
    echo [ERROR] No se pudo crear tarea 08:00 AM
)
echo.

REM Crear tarea para las 12:00 PM
echo Creando tarea para las 12:00 PM...
schtasks /Create /TN "TravelHub_Tasas_12PM" /TR "\"%SCRIPT_TASAS%\"" /SC DAILY /ST 12:00 /F
if %ERRORLEVEL% EQU 0 (
    echo [OK] Tarea 12:00 PM creada
) else (
    echo [ERROR] No se pudo crear tarea 12:00 PM
)
echo.

REM Crear tarea para las 05:00 PM
echo Creando tarea para las 05:00 PM...
schtasks /Create /TN "TravelHub_Tasas_05PM" /TR "\"%SCRIPT_TASAS%\"" /SC DAILY /ST 17:00 /F
if %ERRORLEVEL% EQU 0 (
    echo [OK] Tarea 05:00 PM creada
) else (
    echo [ERROR] No se pudo crear tarea 05:00 PM
)
echo.

echo ============================================
echo   CONFIGURACION COMPLETADA
echo ============================================
echo.
echo Tareas programadas creadas:
echo   - TravelHub_Tasas_08AM (08:00 AM diario)
echo   - TravelHub_Tasas_12PM (12:00 PM diario)
echo   - TravelHub_Tasas_05PM (05:00 PM diario)
echo.
echo Para verificar:
echo   schtasks /Query /TN "TravelHub_Tasas_08AM"
echo.
echo Para ejecutar manualmente:
echo   schtasks /Run /TN "TravelHub_Tasas_08AM"
echo.
echo Logs en: %PROYECTO_DIR%\logs\tasas_sync.log
echo.

pause
