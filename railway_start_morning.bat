@echo off
REM Encender servicios de Railway (7 AM)
echo Encendiendo servicios de Railway...

railway service --service travelhub-web up
railway service --service travelhub-worker up
railway service --service travelhub-beat up

echo Servicios encendidos. Sistema operativo.
pause
