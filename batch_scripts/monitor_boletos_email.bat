@echo off
REM ============================================================================
REM Monitor de Boletos - Envio por Email
REM ============================================================================
REM Este script inicia el monitor automatico de boletos que:
REM - Lee correos de boletos (KIU, SABRE, AMADEUS, Copa, Wingo, TK Connect)
REM - Parsea automaticamente los datos
REM - Genera PDF profesional
REM - Envia email con PDF adjunto
REM - Guarda en base de datos
REM ============================================================================

cd /d "%~dp0.."

echo ============================================================================
echo MONITOR DE BOLETOS - TRAVELHUB
echo ============================================================================
echo.
echo Iniciando monitor automatico...
echo Email destino: travelinkeo@gmail.com
echo Intervalo: 60 segundos
echo.
echo Presiona Ctrl+C para detener el monitor
echo ============================================================================
echo.

REM Activar entorno virtual si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Ejecutar monitor
python manage.py monitor_tickets_email --email travelinkeo@gmail.com --interval 60 --mark-read

pause
