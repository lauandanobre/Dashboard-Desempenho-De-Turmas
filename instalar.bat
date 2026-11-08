@echo off
cd /d "%~dp0"
echo ============================================
echo   Instalacao do Metricas das Turmas
echo ============================================
echo.
if not exist "src\services\ingest_service.py" (
    echo ERRO: a pasta "src" esta faltando ou incompleta. Extraia o zip de novo com "Extrair tudo".
    pause
    exit /b 1
)
set PY=python
python --version >nul 2>&1 || set PY=py -3
%PY% -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python 3.10 ou mais novo nao encontrado.
    echo Instale o Python 3.12 em https://www.python.org/downloads/ e marque "Add Python to PATH".
    echo Depois feche esta janela e de dois cliques em instalar.bat de novo.
    pause
    exit /b 1
)
echo Criando ambiente (1/2)...
%PY% -m venv .venv || goto :erro
call .venv\Scripts\activate
echo Instalando bibliotecas (2/2). Pode levar alguns minutos...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || goto :erro
echo.
echo PRONTO! Agora de dois cliques em abrir.bat para usar o programa.
pause
exit /b 0

:erro
echo.
echo ERRO na instalacao. Tire um print desta janela e envie para o grupo.
pause
exit /b 1
