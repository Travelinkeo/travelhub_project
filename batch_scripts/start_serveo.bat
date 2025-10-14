@echo off
echo Iniciando Django y Serveo...
echo.
echo 1. Iniciando Django en puerto 8000...
start cmd /k "cd /d %~dp0 && venv\Scripts\activate && python manage.py runserver"

echo 2. Esperando 5 segundos para que Django inicie...
timeout /t 5 /nobreak > nul

echo 3. Creando tunel SSH con Serveo...
echo La URL sera: https://travelhub.serveo.net
ssh -R travelhub:80:localhost:8000 serveo.net

pause