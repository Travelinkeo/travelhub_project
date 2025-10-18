@echo off
REM ============================================
REM Script para ejecutar tests de Fase 5
REM ============================================

cd /d "%~dp0.."

echo.
echo ========================================
echo   TESTS DE FASE 5: MEJORAS DE CALIDAD
echo ========================================
echo.

REM Activar entorno virtual
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: No se encontro el entorno virtual
    pause
    exit /b 1
)

echo [1/8] Tests de Notificaciones...
pytest tests/test_notifications.py -v

echo.
echo [2/8] Tests de Cache...
pytest tests/test_cache.py -v

echo.
echo [3/8] Tests de Celery...
pytest tests/test_tasks.py -v

echo.
echo [4/8] Tests de ViewSets con Cache...
pytest tests/test_cached_viewsets.py -v

echo.
echo [5/8] Tests de Optimizacion de Queries...
pytest tests/test_query_optimization.py -v

echo.
echo [6/8] Tests de Middleware...
pytest tests/test_middleware_performance.py -v

echo.
echo [7/8] Tests de Comandos...
pytest tests/test_management_commands.py -v

echo.
echo [8/8] Tests Adicionales de Parsers...
pytest tests/test_parsers_coverage.py -v

echo.
echo ========================================
echo   REPORTE DE COBERTURA
echo ========================================
pytest --cov --cov-report=term-missing

echo.
echo ========================================
echo   TESTS DE FASE 5 COMPLETADOS
echo ========================================
pause
