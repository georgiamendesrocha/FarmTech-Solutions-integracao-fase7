# 🛠️ Configuração do Projeto - Sistema de Irrigação Inteligente

Este diretório concentra dependências e instaladores opcionais. Veja o [guia de instalação e PATH](SETUP_INSTRUCTIONS.md) e o [README principal](../README.md). Os comandos usam a raiz do módulo, onde estão `app.py` e `platformio.ini`; na estrutura `servicos/fase2-iot/`, essa é a pasta de execução.

## 📁 Arquivos

| Arquivo | Função |
|---|---|
| [requirements.txt](requirements.txt) | PlatformIO ≥6.1.0 e PySerial ≥3.5, sem fixar versões exatas |
| [setup.py](setup.py) | Verifica Python, cria diretórios, instala requisitos via pip e procura pio/Rscript |
| [setup.bat](setup.bat) | Instala requisitos no Windows pela pasta do próprio atalho |
| [setup.sh](setup.sh) | Cria diretórios e instala requisitos em Bash pela pasta do script |
| [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md) | Instalação, execução e diagnóstico Windows |

Os instaladores podem acessar a rede e modificar o ambiente Python. Não são necessários a cada execução. Não instalam R, VS Code ou Wokwi. O setup Python verifica 3.7+, mas isso não representa uma matriz de compatibilidade validada de todas as versões/dependências. O ambiente efetivamente testado consta na [rastreabilidade](../document/RASTREABILIDADE_F2.md).

## 📦 Dependências por fluxo

| Uso | Dependência |
|---|---|
| Menu Python | Biblioteca padrão |
| Captura COM/RFC2217 | PySerial: [requirements-serial.txt](../scripts/requirements-serial.txt) |
| Meteorologia | urllib, json e csv da biblioteca padrão; HTTPS à Open-Meteo |
| Compilação/upload e monitor alternativo | PlatformIO; DHTesp declarada em [platformio.ini](../platformio.ini) |
| Simulação | VS Code, extensão Wokwi, [diagram.json](../diagram.json), [wokwi.toml](../wokwi.toml) e binário compilado |
| Análises | R com Rscript; somente pacotes base em [app.r](../app.r) |

`requests` não é necessário. A opção 1 do Python chama PySerial; o Monitor PlatformIO é uma alternativa independente.

## 🔧 Instalação e verificação

Na raiz, instale apenas o que faltar:

```powershell
python --version
python -m pip --version
# Somente captura:
python -m pip install -r scripts/requirements-serial.txt
# Ou conjunto completo, incluindo CLI PlatformIO:
python -m pip install -r config/requirements.txt
```

Alternativa opcional: `python config/setup.py`, ou `python setup.py` dentro de `config/`. Atalhos: `.\config\setup.bat` e `bash config/setup.sh`.

```powershell
python -c "import sys; print(sys.executable)"
python -c "import serial; print(serial.__version__)"
python -m pip show platformio pyserial
Get-Command Rscript -ErrorAction SilentlyContinue
Rscript --version
python app.py
```

`>=` permite atualizações; não garante versões idênticas. Não há lock de dependências.

## 🐛 Diagnóstico

- **Python ausente:** configure Python 3 e reabra o terminal. O launcher Windows `py` pode localizar instalações; use o mesmo interpretador para pip e o menu.
- **No module named serial:** instale `pyserial` com o requirements do coletor; não o pacote chamado `serial`.
- **pio ausente:** use o terminal do PlatformIO no VS Code. Se instalado nesse Python, `python -m platformio --version` dispensa o executável pio no PATH.
- **Rscript ausente:** siga a seção PATH do [guia Windows](SETUP_INSTRUCTIONS.md). Um editor R não substitui Rscript.
- **Porta 4000 indisponível:** inicie Wokwi, confira binário/TOML e não execute dois coletores na mesma porta/arquivo.
- **CSV ausente no R:** primeiro capture IoT ou consulte previsão. Comandos independentes usam a raiz como diretório de trabalho.

Não é necessário limpar caches ou forçar reinstalação para diagnosticar PATH. A auditoria de 01/11/2026 não executou instalações.

## 🔗 Documentação relacionada

[README](../README.md) · [Scripts](../scripts/readme.md) · [Segurança](../document/AUDITORIA_SEGURANCA_F2.md).
