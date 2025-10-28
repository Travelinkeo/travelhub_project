@echo off
REM ============================================
REM Eliminar .env del tracking de git
REM ============================================

cd /d "%~dp0.."

echo ============================================
echo FIX: Eliminar .env de git
echo ============================================
echo.

echo [1/3] Eliminando .env del tracking de git...
git rm --cached .env
if %errorlevel% neq 0 (
    echo ADVERTENCIA: .env no estaba en git o ya fue eliminado
) else (
    echo ✓ .env eliminado del tracking
)
echo.

echo [2/3] Verificando .gitignore...
findstr /C:".env" .gitignore > nul
if %errorlevel% equ 0 (
    echo ✓ .env esta en .gitignore
) else (
    echo ❌ .env NO esta en .gitignore (agregando...)
    echo .env >> .gitignore
)
echo.

echo [3/3] Creando commit...
git add .gitignore .env.example
git commit -m "security: Remove .env from git tracking and add .env.example"
if %errorlevel% neq 0 (
    echo ADVERTENCIA: No hay cambios para commitear o error en git
) else (
    echo ✓ Commit creado
)
echo.

echo ============================================
echo COMPLETADO
echo ============================================
echo.
echo Siguiente paso: git push
echo.
pause
