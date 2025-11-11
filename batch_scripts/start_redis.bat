@echo off
REM Iniciar Redis Server
echo ========================================
echo Iniciando Redis Server
echo ========================================
echo Redis es necesario para Celery
echo ========================================

REM Verificar si Redis está instalado
where redis-server >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Redis no está instalado
    echo.
    echo Instalar Redis:
    echo 1. Descargar: https://github.com/microsoftarchive/redis/releases
    echo 2. O usar: choco install redis-64
    echo 3. O usar: winget install Redis.Redis
    echo.
    pause
    exit /b 1
)

redis-server
pause
