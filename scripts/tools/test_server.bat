@echo off
cd /d "%~dp0"
echo Iniciando servidor Django por 10 segundos...
start /b python manage.py runserver --noreload
timeout /t 10 /nobreak
taskkill /f /im python.exe 2>nul
echo Servidor detenido
