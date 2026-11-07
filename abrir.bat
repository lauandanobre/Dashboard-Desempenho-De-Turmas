@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo O programa ainda nao foi instalado. De dois cliques em instalar.bat primeiro.
    pause
    exit /b 1
)
call .venv\Scripts\activate
python main.py
if errorlevel 1 pause
