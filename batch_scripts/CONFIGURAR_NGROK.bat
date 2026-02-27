@echo off
echo ========================================
echo   CONFIGURACION DE NGROK
echo ========================================
echo.
echo Este script configurara tu TOKEN de Ngrok para evitar errores de conexion.
echo.
echo 1. Ve a https://dashboard.ngrok.com/get-started/your-authtoken
echo 2. Copia tu "Authtoken" (empieza por 1z...)
echo.
set /p token="Pega tu Authtoken aqui y presiona ENTER: "

ngrok config add-authtoken %token%

echo.
echo ========================================
echo   Configuracion Guardada.
echo   Ahora intenta ejecutar START_TRAVELHUB_REMOTE nuevamente.
echo ========================================
pause
