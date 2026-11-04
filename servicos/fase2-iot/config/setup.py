#!/usr/bin/env python3
"""
Setup do Projeto: Sistema de Irrigação Inteligente para Tomate

Este script instala todas as dependências necessárias para executar o projeto.
Executar: python setup.py

Pré-requisitos do Sistema:
- Python 3.7+
- R com Rscript (para análises em R)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_success(text):
    print(f"✓ {text}")

def print_error(text):
    print(f"✗ {text}")

def print_warning(text):
    print(f"⚠ {text}")

def print_info(text):
    print(f"ℹ {text}")

def check_python_version():
    """Verifica se a versão do Python é 3.7+"""
    print_header("Verificando Versão do Python")
    
    version_info = sys.version_info
    version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    
    if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 7):
        print_error(f"Python {version_str} detectado, mas 3.7+ é necessário.")
        sys.exit(1)
    
    print_success(f"Python {version_str} detectado")

def create_directories():
    """Cria os diretórios necessários"""
    print_header("Criando Estrutura de Diretórios")
    
    root = Path(__file__).parent.parent  # Vai para a raiz do projeto
    directories = [
        root / "dados",
        root / "dados" / "plots",
    ]
    
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print_success(f"Diretório criado: {directory.relative_to(root)}")
        else:
            print_info(f"Diretório já existe: {directory.relative_to(root)}")

def install_python_dependencies():
    """Instala as dependências Python"""
    print_header("Instalando Dependências Python")
    
    root = Path(__file__).parent
    requirements_file = root / "requirements.txt"
    
    if not requirements_file.exists():
        print_error(f"Arquivo {requirements_file.name} não encontrado.")
        sys.exit(1)
    
    print_info("Instalando pacotes do requirements.txt...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True
        )
        print_success("Dependências Python instaladas com sucesso")
    except subprocess.CalledProcessError:
        print_error("Erro ao instalar as dependências Python")
        sys.exit(1)

def check_required_tools():
    """Verifica a disponibilidade de ferramentas necessárias"""
    print_header("Verificando Ferramentas do Sistema")
    
    # Verifica PlatformIO
    if shutil.which("pio") is None:
        print_warning("Comando 'pio' (PlatformIO CLI) não encontrado no PATH")
        print_info("Verifique o PATH ou use o terminal da extensão PlatformIO no VS Code.")
    else:
        pio_version = subprocess.run(
            ["pio", "--version"],
            capture_output=True,
            text=True
        ).stdout.strip()
        print_success(f"PlatformIO CLI encontrado: {pio_version}")
    
    # Verifica R
    if shutil.which("Rscript") is None:
        print_error("Comando 'Rscript' não encontrado no PATH")
        print_warning("R deve ser instalado manualmente para usar a análise em R")
        print_info("Download: https://cloud.r-project.org/")
    else:
        r_version = subprocess.run(
            ["Rscript", "--version"],
            capture_output=True,
            text=True
        ).stderr.strip()
        print_success(f"R encontrado: {r_version}")

def display_next_steps():
    """Exibe instruções dos próximos passos"""
    print_header("Próximos Passos")
    
    print_info("Setup concluído! Para começar:")
    print()
    print("  1. Execute a aplicação principal:")
    print("     python app.py")
    print()
    print("  2. Escolha uma opção no menu:")
    print("     - 1: Simulação Wokwi + captura serial")
    print("     - 2: Análises em R")
    print("     - 3: Consulta de previsão do tempo")
    print()
    print("  Notas:")
    print("  - Certifique-se de que o Wokwi está disponível para simulação")
    print("  - Para análises em R, instale R se ainda não fez")
    print()

def main():
    """Função principal"""
    print("\n" + "="*60)
    print("  SETUP - Sistema de Irrigação Inteligente para Tomate")
    print("="*60)
    
    try:
        check_python_version()
        create_directories()
        install_python_dependencies()
        check_required_tools()
        display_next_steps()
        
        print_header("✓ Setup Concluído com Sucesso!")
        
    except KeyboardInterrupt:
        print("\n")
        print_error("Setup interrompido pelo usuário.")
        sys.exit(1)
    except Exception as exc:
        print("\n")
        print_error(f"Erro inesperado durante o setup: {exc}")
        sys.exit(1)

if __name__ == "__main__":
    main()
