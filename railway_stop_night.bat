@echo off
REM Apagar servicios de Railway (11 PM)
echo Apagando servicios de Railway...

railway service --service travelhub-web down
railway service --service travelhub-worker down
railway service --service travelhub-beat down

echo Servicios apagados. Ahorrando costos hasta las 7 AM.
pause
