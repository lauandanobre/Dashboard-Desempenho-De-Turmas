@echo off
REM Gera o executavel do Metricas das Turmas (Windows).
REM Resultado: dist\MetricasDasTurmas\MetricasDasTurmas.exe
cd /d "%~dp0"

if not exist .venv (
    echo Criando ambiente virtual...
    python -m venv .venv || goto :erro
)
call .venv\Scripts\activate || goto :erro

echo Instalando dependencias...
python -m pip install --upgrade pip >nul
pip install -r requirements-dev.txt || goto :erro

echo Rodando testes...
python -m pytest -q || goto :erro

echo Gerando executavel (pode levar alguns minutos)...
pyinstaller --noconfirm MetricasTurmas.spec || goto :erro

echo.
echo PRONTO! Abra: dist\MetricasDasTurmas\MetricasDasTurmas.exe
echo Para distribuir, compacte a pasta dist\MetricasDasTurmas inteira em .zip
pause
exit /b 0

:erro
echo.
echo ERRO: veja a mensagem acima.
pause
exit /b 1
