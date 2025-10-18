@echo off
REM ============================================================================
REM Iniciar Celery Worker - TravelHub
REM ============================================================================

cd /d "%~dp0.."

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                    INICIANDO CELERY WORKER                               ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

REM Activar entorno virtual si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo [1/2] Verificando Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [!] ADVERTENCIA: Redis no está corriendo
    echo     Celery necesita Redis para funcionar
    echo     Instala Redis o usa: docker run -d -p 6379:6379 redis
    echo.
    pause
    exit /b 1
)
echo [OK] Redis está corriendo
echo.

echo [2/2] Iniciando Celery Worker...
celery -A travelhub worker --loglevel=info --pool=solo

pause
