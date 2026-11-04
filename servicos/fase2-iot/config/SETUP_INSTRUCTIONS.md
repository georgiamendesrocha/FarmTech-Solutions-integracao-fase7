# 🚀 Instruções de Setup - Sistema de Irrigação Inteligente

Use o terminal do VS Code na **raiz do módulo**, onde estão `app.py`, `app.r`, `dados/` e `config/`. Na estrutura `servicos/fase2-iot/`, execute os comandos a partir dessa pasta. Abrir o menu não instala ferramentas.

## 📋 Pré-requisitos

- Python 3 e pip no mesmo ambiente que executará `app.py`.
- PySerial para captura COM ou RFC2217.
- R com Rscript para a opção 2; RStudio é opcional.
- VS Code, PlatformIO e Wokwi para compilar/simular; placa física ESP32 opcional.
- Internet para instalar dependências ausentes e consultar previsão.

Instaladores oficiais: [Python](https://www.python.org/downloads/), [R](https://cloud.r-project.org/), [VS Code](https://code.visualstudio.com/). A auditoria de 01/11/2026 não instalou dependências.

## ⚡ Preparar e iniciar

Verifique o ambiente existente:

```powershell
python --version
python -m pip --version
python -c "import serial; print(serial.__version__)"
Rscript --version
```

Se faltar PySerial:

```powershell
python -m pip install -r scripts/requirements-serial.txt
```

Se também precisar do CLI PlatformIO nesse Python:

```powershell
python -m pip install -r config/requirements.txt
```

Alternativa opcional: `python config/setup.py` verifica Python, cria diretórios, instala os requisitos e procura pio/Rscript. Os atalhos `.\config\setup.bat` e `bash config/setup.sh` também instalam dependências. Não instalam R nem extensões do VS Code.

```powershell
python app.py
```

## 🪟 PATH no Windows: Python e PySerial

PATH lista as pastas onde o terminal procura programas. Instalar uma ferramenta e adicioná-la ao PATH são etapas diferentes.

1. Se `python` não for reconhecido, teste `py --version`. Se funcionar, use `py -m pip ...` e `py app.py` consistentemente.
2. Com vários Pythons, confira `python -c "import sys; print(sys.executable)"` e instale PySerial nesse interpretador.
3. Na instalação de Python, marque a opção de adicioná-lo ao PATH ou configure a pasta do executável nas variáveis de ambiente do usuário. Reabra o terminal/VS Code.
4. `python -m pip` dispensa o comando pip no PATH. O pacote é **pyserial**, embora o código importe **serial**.

Não é necessário reinstalar Python para corrigir um terminal antigo ou outro ambiente.

## 🪟 PATH no Windows: Rscript

Se `Rscript --version` falhar, procure `Rscript.exe` na instalação R, normalmente em `C:\Program Files\R\R-<versão>\bin`. Algumas instalações usam subpasta `x64`; escolha a pasta que contém o executável.

Substitua `<versão>` pela versão instalada:

```powershell
& "C:\Program Files\R\R-<versão>\bin\Rscript.exe" --version
& "C:\Program Files\R\R-<versão>\bin\Rscript.exe" app.r
```

O `&` executa um caminho entre aspas no PowerShell. Isso roda R diretamente; **a opção 2 do Python precisa de Rscript no PATH**.

Adicione a pasta ao PATH da sessão, preservando o valor existente:

```powershell
$env:Path = "C:\Program Files\R\R-<versão>\bin;" + $env:Path
Get-Command Rscript
Rscript --version
python app.py
```

Para tornar permanente, abra **Editar as variáveis de ambiente da sua conta → Path → Editar → Novo**, adicione a pasta e reabra o terminal/VS Code. Não substitua toda a variável Path. A auditoria de 01/11/2026 não alterou o PATH permanente.

## 📲 Menus e captura

| Menu Python | Ação |
|---|---|
| 1 | Aguarda Wokwi e inicia captura PySerial RFC2217 local em 4000, 115200 baud |
| 2 | Abre as quatro opções de análise R |
| 3 | Pede cidade, consulta Open-Meteo, grava JSON/CSV |
| 4 | Sai |

No R: **1** analisa IoT; **2** analisa previsão; **3** integra os dois; **4** retorna ao Python, ou ao terminal se iniciado diretamente. Caminhos de entrada/saída no [guia de scripts](../scripts/readme.md#análises-e-associação-temporal-em-r).

Antes da opção 1, siga o [procedimento Wokwi no README](../README.md#iniciar-o-wokwi-no-vs-code), que inclui a compilação pelo PlatformIO e a inicialização pela paleta do VS Code. **Enter ou Ctrl+C** encerram a captura do menu e retornam ao Python.

Captura independente: `python scripts/serial_grava_csv.py --port rfc2217://127.0.0.1:4000 --baud 115200`. Para hardware, use sua COM. Nesse modo, encerre com **Ctrl+C**. O Monitor PlatformIO é uma alternativa independente, descrita no [guia de scripts](../scripts/readme.md).

## 🐛 Problemas comuns

- **pio ausente:** abra o terminal da extensão PlatformIO; seu ambiente pode ser diferente do Python do menu.
- **Porta 4000 indisponível:** confira Wokwi iniciado, firmware compilado e `rfc2217ServerPort = 4000`.
- **CSV ausente:** o painel serial Wokwi sozinho não grava. Use um coletor e aguarde `CSV_ROW` válida por alteração ou log de 30 s.
- **Erro de arquivo no R:** gere histórico/previsão primeiro. O módulo não distribui um CSV de exemplo.
- **Cidade incorreta:** o primeiro resultado da geocodificação é escolhido; confira nome/coordenadas no JSON.
- **Falha de API:** o erro retorna ao menu. Não use arquivo antigo como prova de consulta nova.

## 🔗 Referências locais

[Dependências](readme.md) · [Scripts](../scripts/readme.md) · [Firmware](../src/readme.md) · [Testes e limites](../document/RASTREABILIDADE_F2.md).
