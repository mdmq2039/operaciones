@echo off
REM ====================================================================
REM   Aplicativo de Tareo de Operaciones - PECEPE
REM   Doble clic para iniciar el dashboard en el navegador.
REM ====================================================================
cd /d "%~dp0"
echo Iniciando el aplicativo de Tareo de Operaciones...
echo Si es la primera vez, instalando dependencias...
python -m pip install -r requirements.txt --quiet
echo.
echo Abriendo en el navegador (PC o celular en la misma red)...
echo Para detener: cierra esta ventana o presiona Ctrl+C.
echo.
python -m streamlit run app.py
pause
