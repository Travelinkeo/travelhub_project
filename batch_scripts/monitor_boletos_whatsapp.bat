@echo off
REM ============================================================================
REM Monitor de Boletos - WhatsApp con Google Drive
REM ============================================================================
REM Este script inicia el monitor automatico de boletos que:
REM - Lee correos de boletos (KIU, SABRE, AMADEUS, Copa, Wingo, TK Connect)
REM - Parsea automaticamente los datos
REM - Genera PDF profesional
REM - Sube PDF a Google Drive
REM - Envia WhatsApp con link de descarga
REM - Guarda en base de datos
REM ============================================================================

cd /d "%~dp0.."

echo ============================================================================
echo MONITOR DE BOLETOS - WHATSAPP + GOOGLE DRIVE
echo ============================================================================
echo.
echo Iniciando monitor automatico...
echo WhatsApp destino: +582126317079
echo Intervalo: 60 segundos
echo.
echo IMPORTANTE: Tu numero debe estar activado en Twilio Sandbox
echo Si no has activado tu numero:
echo   1. Envia WhatsApp a: +1 415 523 8886
echo   2. Con el mensaje: join [tu-codigo]
echo.
echo Presiona Ctrl+C para detener el monitor
echo ============================================================================
echo.

REM Activar entorno virtual si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Ejecutar monitor
python manage.py monitor_tickets_whatsapp_drive --phone +582126317079 --interval 60 --mark-read

pause
