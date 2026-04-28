@echo off
REM ============================================
REM Backup Completo de TravelHub
REM Ejecutar ANTES de cualquier despliegue
REM ============================================

cd /d "%~dp0.."

echo ============================================
echo BACKUP COMPLETO - TravelHub
echo ============================================
echo.

REM Crear carpeta de backups si no existe
if not exist "backups" mkdir backups

REM Fecha y hora para nombre de archivo
set FECHA=%date:~-4%%date:~3,2%%date:~0,2%
set HORA=%time:~0,2%%time:~3,2%%time:~6,2%
set HORA=%HORA: =0%
set TIMESTAMP=%FECHA%_%HORA%

echo [1/4] Backup de Base de Datos...
echo Verificando Django...
python manage.py check --quiet
if %errorlevel% neq 0 (
    echo ERROR: Django tiene problemas. Ejecuta: python manage.py check
    pause
    exit /b 1
)

echo Creando backup...
python manage.py dumpdata > backups\backup_db_%TIMESTAMP%.json 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo crear backup de base de datos
    echo.
    echo ALTERNATIVA: Copia manual de db.sqlite3
    if exist "db.sqlite3" (
        copy db.sqlite3 backups\db_%TIMESTAMP%.sqlite3 > nul
        echo ✓ Backup manual creado: backups\db_%TIMESTAMP%.sqlite3
    ) else (
        echo ADVERTENCIA: No se encontro db.sqlite3
        echo Si usas PostgreSQL, el backup se hara en el servidor
    )
) else (
    echo ✓ Base de datos respaldada: backups\backup_db_%TIMESTAMP%.json
)
echo.

echo [2/4] Backup de Archivos Media...
if exist "media" (
    tar -czf backups\backup_media_%TIMESTAMP%.tar.gz media
    if %errorlevel% neq 0 (
        echo ADVERTENCIA: Fallo el backup de media (tar no disponible)
        echo Puedes copiar manualmente la carpeta 'media'
    ) else (
        echo ✓ Media respaldada: backups\backup_media_%TIMESTAMP%.tar.gz
    )
) else (
    echo - No hay carpeta media para respaldar
)
echo.

echo [3/4] Backup de Configuracion...
if exist ".env" (
    copy .env backups\.env_%TIMESTAMP%.backup > nul
    echo ✓ Configuracion respaldada: backups\.env_%TIMESTAMP%.backup
) else (
    echo ADVERTENCIA: No se encontro archivo .env
)
echo.

echo [4/4] Verificando backups...
dir backups\*%TIMESTAMP%* /b
echo.

echo ============================================
echo BACKUP COMPLETADO EXITOSAMENTE
echo ============================================
echo.
echo Archivos creados:
echo - backups\backup_db_%TIMESTAMP%.json
echo - backups\backup_media_%TIMESTAMP%.tar.gz (si tar disponible)
echo - backups\.env_%TIMESTAMP%.backup
echo.
echo IMPORTANTE: Guarda estos archivos en un lugar seguro
echo (Google Drive, Dropbox, disco externo, etc.)
echo.
pause
