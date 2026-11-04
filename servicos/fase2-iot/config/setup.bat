@echo off
REM Script de Setup para Windows
REM Sistema de Irrigação Inteligente para Tomate

echo.
echo ============================================================
echo   SETUP - Sistema de Irrigacao Inteligente para Tomate
echo ============================================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Erro: Python não encontrado!
    echo Instale Python de https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version

echo.
echo Instalando dependências Python...
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo Erro ao instalar dependências!
    pause
    exit /b 1
)

echo.
echo [OK] Dependências instaladas com sucesso!
echo.
echo Próximos passos:
echo.
echo   Na raiz do projeto:
echo   1. Execute a aplicação:
echo      python app.py
echo.
echo   2. Escolha uma opção no menu:
echo      - 1: Simulação Wokwi + captura serial Python
echo      - 2: Análises em R
echo      - 3: Consulta de previsão do tempo
echo.
echo Para instruções detalhadas, veja config/SETUP_INSTRUCTIONS.md
echo.
pause
