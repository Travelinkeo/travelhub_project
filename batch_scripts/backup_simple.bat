@echo off
REM ============================================
REM Backup Simple - Copia directa de archivos
REM ============================================

cd /d "%~dp0.."

echo ============================================
echo BACKUP SIMPLE - TravelHub
echo ============================================
echo.

REM Crear carpeta de backups
if not exist "backups" mkdir backups

REM Fecha para nombre
set FECHA=%date:~-4%%date:~3,2%%date:~0,2%
set HORA=%time:~0,2%%time:~3,2%%time:~6,2%
set HORA=%HORA: =0%
set TIMESTAMP=%FECHA%_%HORA%

echo [1/3] Backup de Base de Datos SQLite...
if exist "db.sqlite3" (
    copy db.sqlite3 backups\db_%TIMESTAMP%.sqlite3 > nul
    echo ✓ Copiado: backups\db_%TIMESTAMP%.sqlite3
) else (
    echo - No hay db.sqlite3 (probablemente usas PostgreSQL)
)
echo.

echo [2/3] Backup de Archivos .env...
if exist ".env" (
    copy .env backups\.env_%TIMESTAMP%.backup > nul
    echo ✓ Copiado: backups\.env_%TIMESTAMP%.backup
) else (
    echo ADVERTENCIA: No se encontro .env
)
echo.

echo [3/3] Backup de Media (si existe)...
if exist "media" (
    echo Copiando carpeta media... (puede tardar)
    xcopy media backups\media_%TIMESTAMP%\ /E /I /Q > nul
    echo ✓ Copiado: backups\media_%TIMESTAMP%\
) else (
    echo - No hay carpeta media
)
echo.

echo ============================================
echo BACKUP COMPLETADO
echo ============================================
echo.
echo Archivos en backups\:
dir backups\*%TIMESTAMP%* /b
echo.
echo IMPORTANTE: Guarda estos archivos en lugar seguro
echo.
pause
