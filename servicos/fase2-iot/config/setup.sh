#!/bin/bash
# Script de Setup para macOS e Linux
# Sistema de Irrigação Inteligente para Tomate

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 1
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)" || exit 1

echo ""
echo "============================================================"
echo "  SETUP - Sistema de Irrigação Inteligente para Tomate"
echo "============================================================"
echo ""

# Verificar se Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "Erro: Python 3 não encontrado!"
    echo "Instale Python de https://www.python.org/downloads/"
    exit 1
fi

echo "[OK] Python encontrado"
python3 --version

echo ""
echo "Criando diretórios necessários..."
mkdir -p "$PROJECT_ROOT/dados/plots" || exit 1

echo ""
echo "Instalando dependências Python..."
python3 -m pip install -r "$SCRIPT_DIR/requirements.txt"
if [ $? -ne 0 ]; then
    echo "Erro ao instalar dependências!"
    exit 1
fi

echo ""
echo "[OK] Dependências instaladas com sucesso!"
echo ""
echo "Próximos passos:"
echo ""
echo "  Na raiz do projeto:"
echo "  1. Execute a aplicação:"
echo "     python3 app.py"
echo ""
echo "  2. Escolha uma opção no menu:"
echo "     - 1: Simulação Wokwi + captura serial Python"
echo "     - 2: Análises em R"
echo "     - 3: Consulta de previsão do tempo"
echo ""
echo "Para instruções detalhadas, veja config/SETUP_INSTRUCTIONS.md"
echo ""
