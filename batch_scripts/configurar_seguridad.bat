@echo off
REM ============================================================================
REM Script de Configuración de Seguridad - TravelHub
REM ============================================================================

cd /d "%~dp0.."

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║         CONFIGURACIÓN DE SEGURIDAD - TRAVELHUB                           ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

REM Verificar si .env ya existe
if exist .env (
    echo [!] ADVERTENCIA: El archivo .env ya existe.
    echo.
    choice /C SN /M "¿Deseas sobrescribirlo? (S=Si, N=No)"
    if errorlevel 2 goto :skip_env
)

REM Copiar .env.example a .env
echo [1/4] Creando archivo .env...
copy .env.example .env >nul
if errorlevel 1 (
    echo [ERROR] No se pudo crear .env
    pause
    exit /b 1
)
echo [OK] Archivo .env creado
echo.

:skip_env

REM Generar SECRET_KEY
echo [2/4] Generando SECRET_KEY segura...
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" > temp_secret.txt
if errorlevel 1 (
    echo [ERROR] No se pudo generar SECRET_KEY
    echo Asegúrate de tener Django instalado: pip install django
    pause
    exit /b 1
)

set /p NEW_SECRET=<temp_secret.txt
del temp_secret.txt

echo [OK] SECRET_KEY generada
echo.

REM Actualizar .env con la nueva SECRET_KEY
echo [3/4] Actualizando .env con SECRET_KEY...
powershell -Command "(Get-Content .env) -replace 'SECRET_KEY=.*', 'SECRET_KEY=%NEW_SECRET%' | Set-Content .env"
echo [OK] SECRET_KEY actualizada en .env
echo.

REM Verificar configuración
echo [4/4] Verificando configuración...
echo.
echo ┌─────────────────────────────────────────────────────────────────────────┐
echo │ CONFIGURACIÓN ACTUAL:                                                   │
echo └─────────────────────────────────────────────────────────────────────────┘
echo.

findstr /C:"SECRET_KEY=" .env | findstr /V "your-secret-key-here"
if errorlevel 1 (
    echo [!] ADVERTENCIA: SECRET_KEY no configurada correctamente
) else (
    echo [OK] SECRET_KEY configurada
)

findstr /C:"DB_PASSWORD=" .env | findstr /V "your_secure_database_password_here"
if errorlevel 1 (
    echo [!] ADVERTENCIA: DB_PASSWORD no configurada
    echo.
    echo Por favor, edita .env y configura DB_PASSWORD=Linkeo1331*
) else (
    echo [OK] DB_PASSWORD configurada
)

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                    CONFIGURACIÓN COMPLETADA                              ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo PRÓXIMOS PASOS:
echo.
echo 1. Edita el archivo .env y verifica DB_PASSWORD
echo 2. Ejecuta: python manage.py runserver
echo 3. Verifica que no haya errores de configuración
echo.
echo Para más información, consulta: SEGURIDAD_ACCION_INMEDIATA.md
echo.

pause
