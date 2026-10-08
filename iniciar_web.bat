@echo off
REM ================================================================
REM  Levanta la app web del simulador en http://localhost:8501
REM
REM  Usa SIEMPRE el entorno virtual de este proyecto (.venv), aunque en
REM  la terminal haya otro entorno activo. Doble clic o, en una terminal:
REM      iniciar_web.bat
REM  Para detener el servidor: Ctrl+C en esta ventana.
REM ================================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No se encontro el entorno virtual .venv de este proyecto.
    echo Crealo una sola vez con Python 3.13:
    echo     py -3.13 -m venv .venv
    echo     .venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Instalando las dependencias de la app en .venv ...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

".venv\Scripts\python.exe" -m streamlit run streamlit_app.py %*
