@echo off
echo ========================================
echo   TravelHub - Backend + Frontend + Ngrok
echo ========================================
echo.

REM Activar entorno virtual de Django
call venv\Scripts\activate.bat

REM Iniciar Django en segundo plano
echo [1/4] Iniciando servidor Django (puerto 8000)...
start /B python manage.py runserver 0.0.0.0:8000

REM Esperar 3 segundos
timeout /t 3 /nobreak > nul

REM Iniciar Next.js en segundo plano
echo [2/4] Iniciando frontend Next.js (puerto 3000)...
cd frontend
start /B cmd /c "npm run dev"
cd ..

REM Esperar 5 segundos para que Next.js inicie
timeout /t 5 /nobreak > nul

REM Iniciar ngrok para Django (backend)
echo [3/4] Iniciando tunel ngrok para BACKEND...
start cmd /k "ngrok.exe http 8000 --log=stdout"

REM Esperar 2 segundos
timeout /t 2 /nobreak > nul

REM Iniciar ngrok para Next.js (frontend)
echo [4/4] Iniciando tunel ngrok para FRONTEND...
echo.
echo ============================================================
echo   IMPORTANTE: Se abriran 2 ventanas de ngrok
echo   
echo   Ventana 1 (Backend):  https://xxxxx.ngrok-free.app
echo   Ventana 2 (Frontend): https://yyyyy.ngrok-free.app
echo   
echo   Comparte AMBAS URLs con tu esposa:
echo   - Backend:  Para el admin de Django
echo   - Frontend: Para la interfaz de usuario
echo ============================================================
echo.
start cmd /k "ngrok.exe http 3000 --log=stdout"

echo.
echo Presiona cualquier tecla para detener todos los servicios...
pause > nul

REM Detener todos los procesos
taskkill /F /IM python.exe
taskkill /F /IM node.exe
taskkill /F /IM ngrok.exe
