@echo off
echo Configurando Beat en Railway...
echo.
echo INSTRUCCIONES:
echo 1. Ve a railway.app/dashboard
echo 2. Selecciona tu proyecto TravelHub
echo 3. Click "New Service" -^> "Empty Service"
echo 4. Nombre: beat
echo 5. En Settings -^> Start Command: celery -A travelhub beat --loglevel=info
echo 6. En Variables: Copiar todas las variables del servicio web
echo.
echo Presiona cualquier tecla para abrir Railway dashboard...
pause >nul
start https://railway.app/dashboard
pause
