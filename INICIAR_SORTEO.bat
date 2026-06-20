@echo off
REM ====================================================================
REM   Sorteo al Azar - Aplicacion de Sorteo desde Excel
REM   Doble clic para iniciar. Accede desde tu celular en la misma WiFi.
REM ====================================================================
cd /d "%~dp0"
echo ============================================
echo   SORTEO AL AZAR - Iniciando...
echo ============================================
echo.
echo Instalando dependencias si es necesario...
python -m pip install -r requirements.txt --quiet
echo.
echo ============================================
echo   La app se abrira en tu navegador.
echo   Para acceder desde tu CELULAR:
echo   Abre Chrome y ve a la URL "Network URL"
echo   que aparece abajo (misma red WiFi).
echo ============================================
echo.
python -m streamlit run sorteo_app.py --server.port 8502
pause
