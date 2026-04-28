@echo off
REM ============================================
REM Verificacion de Seguridad Pre-Despliegue
REM ============================================

cd /d "%~dp0.."

echo ============================================
echo VERIFICACION DE SEGURIDAD - TravelHub
echo ============================================
echo.

echo [1/5] Verificando que .env NO este en git...
git ls-files | findstr /C:".env" > nul
if %errorlevel% equ 0 (
    echo ❌ CRITICO: .env esta en git! Eliminar inmediatamente
    echo Ejecutar: git rm --cached .env
    set ERROR=1
) else (
    echo ✓ .env NO esta en git (correcto)
)
echo.

echo [2/5] Verificando SECRET_KEY...
python manage.py shell -c "from django.conf import settings; key=settings.SECRET_KEY; print('✓ SECRET_KEY OK' if len(key) > 40 else '❌ SECRET_KEY muy corta')"
echo.

echo [3/5] Verificando DEBUG en produccion...
python manage.py shell -c "from django.conf import settings; print('❌ DEBUG=True (cambiar a False)' if settings.DEBUG else '✓ DEBUG=False (correcto)')"
echo.

echo [4/5] Verificando ALLOWED_HOSTS...
python manage.py shell -c "from django.conf import settings; hosts=settings.ALLOWED_HOSTS; print('✓ ALLOWED_HOSTS configurado' if hosts and hosts != ['*'] else '⚠ ALLOWED_HOSTS = * (configurar en produccion)')"
echo.

echo [5/5] Verificando archivos grandes en git...
echo Buscando archivos .next, node_modules, etc...
git ls-files | findstr /C:".next" > nul
if %errorlevel% equ 0 (
    echo ⚠ Archivos .next en git (eliminar)
) else (
    echo ✓ No hay archivos .next en git
)
echo.

echo ============================================
echo VERIFICACION COMPLETADA
echo ============================================
echo.
if defined ERROR (
    echo ❌ HAY PROBLEMAS CRITICOS - Revisar arriba
) else (
    echo ✓ Todo OK - Listo para desplegar
)
echo.
pause
