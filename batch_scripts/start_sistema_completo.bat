@echo off
REM Iniciar sistema completo: Redis + Celery Worker + Celery Beat
cd /d "%~dp0.."
echo ========================================
echo Iniciando Sistema Completo TravelHub
echo ========================================
echo 1. Redis Server
echo 2. Celery Worker
echo 3. Celery Beat
echo ========================================

REM Verificar Redis
where redis-server >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Redis no instalado
    echo Instalar: winget install Redis.Redis
    echo.
    pause
    exit /b 1
)

REM Iniciar Redis
start "Redis Server" cmd /k "redis-server"
timeout /t 3 /nobreak >nul

REM Iniciar Celery Worker
start "Celery Worker" cmd /k "celery -A travelhub worker --loglevel=info --pool=solo"
timeout /t 3 /nobreak >nul

REM Iniciar Celery Beat
start "Celery Beat" cmd /k "celery -A travelhub beat --loglevel=info"

echo.
echo ========================================
echo Sistema iniciado en 3 ventanas:
echo ========================================
echo 1. Redis Server
echo 2. Celery Worker
echo 3. Celery Beat
echo ========================================
echo Monitor de boletos activo cada 5 minutos
echo ========================================
pause
