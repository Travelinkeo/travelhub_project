@echo off
echo Iniciando ngrok con pooling habilitado...
ngrok http 8000 --pooling-enabled
pause