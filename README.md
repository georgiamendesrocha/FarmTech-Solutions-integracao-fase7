# FIAP — Faculdade de Informática e Administração Paulista

<p align="center">
  <a href="https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="Logotipo da FIAP" width="300"></a>
</p>

# FarmTech Solutions — Fase 7: A Consolidação de um Sistema

**Tecnólogo em Inteligência Artificial**

| Integrantes | Registro acadêmico |
|---|---|
| Carlos Magnus Costa Amaral | RM573978 |
| Edemir Sufiatti | RM571375 |
| Georgia Mendes Rocha | RM573281 |
| Marina Leme Soares | RM570461 |

**Tutora:** Nicolly Cândida Rodrigues de Souza

**Coordenador:** André Godoi Chiovato

> [Vídeo demonstrativo — Entrega principal](https://youtu.be/vq5WaDTVN0E)
>
> **Vídeo demonstrativo — Ir Além:** `[Inserir link do YouTube]`

## Sumário

- [Apresentação](#apresentação-e-resumo-executivo) e [objetivos](#problema-abordado-e-objetivos).
- [Evolução das Fases 1 a 6](#evolução-nas-fases-1-a-6).
- [Arquitetura](#arquitetura-geral) e [estrutura de diretórios](#estrutura-de-diretórios).
- [Instalação e configuração](#pré-requisitos-instalação-e-configuração) e [execução](#como-iniciar-e-utilizar-a-aplicação).
- [Solução de problemas e execução para o avaliador](#solução-de-problemas-e-execução-para-o-avaliador).
- [Dashboard integrada](#fase-7--parte-1-dashboard-final-e-serviços-integrados).
- [Indicadores, métricas e resultados](#indicadores-métricas-e-resultados-do-sistema-integrado).
- [Evidências visuais](#demonstrações-visuais-da-dashboard).
- [Parte 2 — Alertas AWS](#fase-7--parte-2-serviço-de-alertas-aws).
  - [Validação AWS — Evidências complementares](#validação-aws--evidências-complementares).
- [Ir Além 1 — Amazon Rekognition](#ir-além-1--amazon-rekognition).
- [Testes e validações](#reprodução-dos-testes-e-validações).
- [Limitações e segurança](#resultados-limitações-e-segurança).
- [Documentação complementar](#documentação-complementar-e-repositórios-originais).
- [Fontes de dados e referências](#fontes-de-dados-e-referências).
- [Histórico de lançamentos](#histórico-de-lançamentos).
- [Créditos](#créditos-e-direitos-autorais) e [licença](#licença).

## Apresentação e resumo executivo

A FarmTech Solutions reúne gestão agrícola, sensores, persistência, análise de dados, modelos preditivos e visão computacional em uma plataforma acadêmica de apoio à decisão. A Fase 7 consolida os serviços anteriores na dashboard Streamlit da Fase 4, preservando os projetos de origem, seus dados, modelos, notebooks e evidências.

A entrega compreende duas partes:

### Entrega 1 — Sistema integrado e dashboard (Parte 1 da Fase 7)

Uma entrada local, uma página inicial e treze páginas funcionais, com as análises da F4, integrações das Fases 1, 2, 3 e 6 e a avaliação local dos alertas.

### Entrega 2 — Serviço de Alertas na AWS (Parte 2 da Fase 7)

- **Responsável:** Edemir Sufiatti.
- **Código da implementação:** [servicos/fase7-alertas-aws/](servicos/fase7-alertas-aws/).
- **Documentação técnica da Entrega 02, atualizada em 08/11/2026:** [servicos/fase7-alertas-aws/README.md](servicos/fase7-alertas-aws/README.md).

Serviço independente com duas validações documentadas em EC2/SNS: V1, em **05/11/2026**, com alerta meteorológico, e V2, em **08/11/2026**, com alerta baseado nos sensores simulados da Fase 2 no Wokwi. A dashboard oferece prévias locais, sem publicação SNS pela interface.

O sistema distingue dados acadêmicos, históricos de sensores, simulações, previsões externas e observações oficiais. Os resultados **não constituem validação agronômica, controle de irrigação em produção ou certificação dos modelos**.

## Problema abordado e objetivos

Dados e ferramentas agrícolas distribuídos entre programas, bancos e modelos dificultam a interpretação conjunta. A proposta centraliza a navegação e as análises sem apagar suas origens ou combinar fontes incompatíveis.

Os objetivos são permitir cálculos e consultas sob demanda, apresentar métricas verificáveis, preservar a rastreabilidade dos experimentos e comunicar condições que merecem atenção. Os ambientes incompatíveis permanecem separados, e a demonstração básica funciona sem credenciais AWS ou Oracle.

## Evolução nas Fases 1 a 6

| Fase | Contribuição técnica | Situação no consolidado | Documentação preservada |
|---|---|---|---|
| **1 — Gestão agrícola** | Geometria de talhões, áreas, conversões, linhas e insumos | Cálculos reutilizados na página Gestão agrícola; menus e ferramentas R preservados | [README F1](servicos/fase1-gestao/README.md) |
| **2 — IoT** | ESP32/Wokwi, irrigação didática, captura CSV, meteorologia e R | Consulta Open-Meteo, exportação e validação R explícita; histórico também alimenta Alertas | [README F2](servicos/fase2-iot/README.md) |
| **3 — Persistência** | Oracle, contrato dos sensores, consultas e indicadores | Consulta explícita a CSV ou Oracle; aplicação histórica e SQL preservados | [README F3](servicos/fase3-dashboard/README.md) |
| **4 — Análise e previsão** | Streamlit, SQLite, exploração, regressões, manejo, histórico e fontes oficiais | Núcleo da plataforma; sete páginas analíticas e integrações adicionais | [README F4](servicos/fase4-regressao/README.md) |
| **5 — ML e infraestrutura** | Rendimento agrícola, clusterização, regressões e custos AWS | Notebook, dataset e documentos históricos; **sem página integrada própria** | [README F5](servicos/fase5-ml/README.md) |
| **6 — Visão computacional** | YOLOv5 customizada para banana/milho e comparação com CNN | Upload/inferência YOLO e avaliação do teste; CNN preservada como experimento independente | [README F6](servicos/fase6-visao/README.md) |

## Arquitetura geral

```mermaid
flowchart TD
    Entrada["iniciar.py · controle local"] --> Dashboard["Streamlit · Python 3.11.9"]
    Dashboard --> F4["Análises F4 · SQLite e modelos preservados"]
    Dashboard --> Adaptadores["Adaptadores F1 / F2 / F3 / F6 / F7"]
    Adaptadores --> Runtime["Workers · JSON · timeout · trava por serviço"]
    Runtime --> F1["Gestão e insumos F1"]
    Runtime --> F2["Open-Meteo F2 · consulta explícita"]
    Runtime --> F3["CSV ou Oracle F3"]
    Runtime --> F6["YOLO F6 · Python 3.13.13 · CPU"]
    Runtime --> F7["Regras e prévia local F7"]
    CSV["Histórico de sensores F2"] --> F7
    F2 --> F7
    F7 --> Previa["Condição, ação e mensagem · sem SNS"]
    F4 --> Oficiais["NOAA / INMET / IBGE-SIDRA · fontes separadas"]
```

Os adaptadores retornam `Result(status, message, data, source)`, distinguindo sucesso, entrada inválida, indisponibilidade e erro. Workers usam processos com argumentos fixos, sem shell, comunicação JSON, limites e exclusão mútua por fase. A separação também evita colisões entre os pacotes `src` dos serviços.

A visão executa em outro ambiente Python; R depende de instalação própria. Captura serial, Wokwi, Oracle e consultas meteorológicas não são iniciados automaticamente. O publicador SNS independente e a prévia integrada possuem fluxos distintos.

### Estrutura de diretórios

```text
.
├── README.md
├── iniciar.py                     # entrada oficial e controle do servidor
├── requirements.txt               # perfil básico da dashboard
├── requirements-oracle.txt        # driver Oracle opcional
├── assets/                        # identidade e capturas AWS tratadas
├── docs/                          # contratos, validações e evidências
│   └── evidencias/                 # capturas da dashboard
├── farmtech_integracao/            # adaptadores, contratos e apresentação
│   └── workers/                    # execução isolada dos serviços
├── scripts/                       # procedimentos explícitos de validação
├── tests/integracao/               # testes da integração
└── servicos/
    ├── fase1-gestao/
    ├── fase2-iot/
    ├── fase3-dashboard/
    ├── fase4-regressao/
    ├── fase5-ml/
    ├── fase6-visao/
    └── fase7-alertas-aws/
```

Durante o uso, `.runtime/` recebe a base reconstruída, exportações, uploads temporários, travas e logs. Ambientes e caches são locais. Os serviços mantêm seus materiais de origem; arquivos fora do caminho principal podem ser necessários à reprodução histórica.

### Tecnologias utilizadas

| Camada | Tecnologias e contexto |
|---|---|
| Interface | Python 3.11.9, Streamlit 1.54.0, Plotly 6.1.1, Pandas 2.2.3 |
| Modelos tabulares | NumPy 2.2.6, scikit-learn 1.6.1 e joblib 1.5.0 |
| Persistência | SQLite local; Oracle com driver thin opcional; CSV/JSON |
| IoT | ESP32, C++/Arduino, Wokwi, PlatformIO e PySerial nos fluxos próprios |
| Análises | R executado explicitamente; fontes Open-Meteo, NOAA/USCRN, INMET e SIDRA |
| Visão | Python 3.13.13, PyTorch 2.15.0, torchvision 0.29.2 e YOLOv5 local; TensorFlow/Keras no experimento CNN |
| Mensageria AWS (V1/V2) | EC2 Linux, IAM e SNS Standard; boto3 opcional no serviço independente |

## Pré-requisitos, instalação e configuração

### Primeira execução

Este roteiro prepara a dashboard básica a partir de um clone novo. Abra o PowerShell na raiz do repositório, onde estão `iniciar.py` e `requirements.txt`; não é necessário configurar o VS Code nem utilizar um ambiente de outra pasta.

#### 1. Preparar o ambiente da dashboard básica

O perfil verificado é **Windows e Python 3.11.9**. Confirme a versão patch: `py -3.11` seleciona a família, não garante sozinho a versão exata.

```powershell
py -3.11 --version
```

Prossiga somente se a saída for `Python 3.11.9`; caso contrário, instale ou selecione essa versão antes de criar o ambiente. Crie a pasta prevista apenas se ela ainda não existir, preservando qualquer ambiente existente:

```powershell
if (-not (Test-Path -LiteralPath ".\servicos\fase4-regressao\.venv-f402")) {
    py -3.11 -m venv servicos/fase4-regressao/.venv-f402
}

$pythonDashboard = ".\servicos\fase4-regressao\.venv-f402\Scripts\python.exe"
& $pythonDashboard --version
```

Confirme também `Python 3.11.9` no executável do ambiente. Se a pasta existente estiver incompleta ou usar outra versão, preserve-a e configure um ambiente compatível por `FARMTECH_FASE4_PYTHON`, conforme [Como iniciar e utilizar a aplicação](#como-iniciar-e-utilizar-a-aplicação). A instalação das dependências é uma ação manual:

```powershell
& $pythonDashboard -m pip install pip==26.2.2 setuptools==84.1.0
& $pythonDashboard -m pip install -r requirements.txt
& $pythonDashboard -m pip check
```

O [perfil básico](requirements.txt) reutiliza os pins F4 e suas [constraints](servicos/fase4-regressao/constraints-f402.txt). Não reúne todas as bibliotecas dos serviços. Preserve scikit-learn **1.6.1**, exigido pelos carregadores dos artefatos históricos; upgrades gerais não são uma solução validada de compatibilidade.

Os manifests foram conferidos contra os ambientes existentes; os perfis básico/Oracle passaram em simulação offline de instalação. **Não foi executada instalação completa em computador limpo.** Disponibilidade de wheels e outros sistemas operacionais exigem nova verificação.

#### 2. Preparar e conferir o banco de demonstração

Na raiz, consulte as condições locais:

```powershell
python iniciar.py --status
```

Para utilizar o banco padrão, deixe `DB_PATH` sem configuração. Se `.runtime/demo/farmtech-demo.db` ainda não existir, prepare-o explicitamente e consulte novamente:

```powershell
if (-not (Test-Path -LiteralPath ".\.runtime\demo\farmtech-demo.db")) {
    python iniciar.py --preparar-demo
}
python iniciar.py --status
```

No resultado de `fase4`, confirme `status: "ok"` e as contagens iniciais: `culturas: 22`, `sensores: 1`, `leituras_sensores: 153`, `amostras_agronomicas: 2200` e `previsoes: 0`. Essas contagens descrevem a base recém-preparada; simulações e previsões posteriores podem alterá-las. As leituras iniciais vêm do CSV preservado, sem depender de iniciar uma nova simulação.

`--preparar-demo` cria somente o destino padrão e recusa qualquer arquivo já existente; não substitua nem apague uma base para repetir o roteiro. Uma `DB_PATH` explícita tem prioridade durante a execução: ela deve apontar para um banco F4 existente e compatível, pois esse comando não prepara o destino personalizado. Caminhos relativos de `DB_PATH` são resolvidos a partir de `servicos/fase4-regressao/`. Para voltar ao padrão apenas nesta sessão, use `Remove-Item Env:DB_PATH -ErrorAction SilentlyContinue` e consulte `--status` novamente.

#### 3. Abrir o menu interativo

```powershell
python iniciar.py
```

Escolha **1** para iniciar, **0** para solicitar o encerramento da dashboard e **S** para sair do menu. Os detalhes de portas, ambiente em outro worktree e inicialização direta estão em [Como iniciar e utilizar a aplicação](#como-iniciar-e-utilizar-a-aplicação).

### Oracle opcional

```powershell
& $pythonDashboard -m pip install -r requirements-oracle.txt
```

O [perfil Oracle](requirements-oracle.txt) inclui `oracledb==26.1.0`. A página recebe RM, senha e DSN por consulta; confirme os dados institucionais. A CLI utiliza `ORACLE_USER`, `ORACLE_PASS` e `ORACLE_DSN` no ambiente. Não versione seus valores. Instalar o driver não cria banco, tabela ou permissões.

Sem Oracle, selecione **CSV preservado**. Não há troca silenciosa de origem após erro.

### Visão computacional separada

Use um ambiente próprio da Fase 6, separado do F4. Para os comandos completos, escolha [A — ambiente virtual já existente](#a-ambiente-virtual-da-fase-6-já-existente) ou [B — instalação limpa do avaliador](#b-instalação-limpa-do-avaliador), na seção de solução de problemas. Isso evita reinstalar um ambiente funcional ou criar outro com o Python incorreto.

Disponibilize um **checkout Git local, íntegro e confiável da YOLOv5**, na revisão `4add2aff6e3d926586a3eab4659f3b498dd444a1`, e informe seu diretório em `FARMTECH_YOLO_REPO`. Cache do Hub sem `.git` não satisfaz a verificação. A aplicação não baixa automaticamente código, modelos ou dependências.

O checkpoint é [yolov5s_custom_exp60_best.pt](servicos/fase6-visao/entrega_2/modelos/yolov5s_custom_exp60_best.pt). Dataset, avaliador e pesos selecionados estão preservados no serviço. O requirements F6 também contempla o contexto CNN/notebook e não é um lock completo das transitivas. Não o instale no ambiente da dashboard.

### Configurações locais

| Configuração | Finalidade |
|---|---|
| `FARMTECH_FASE4_PYTHON` | Executável equivalente ao Python F4 validado; padrão no ambiente `.venv-f402` do serviço |
| `FARMTECH_FASE6_PYTHON` | Executável F6; padrão `.venv-fase6/Scripts/python.exe` |
| `FARMTECH_YOLO_REPO` | Diretório do checkout YOLO validado |
| `FARMTECH_RSCRIPT` | Executável Rscript, se não encontrado automaticamente |
| `DB_PATH` | SQLite escolhido; padrão na base reconstruída da integração |

Os executáveis configurados devem usar caminhos absolutos válidos na máquina de execução. Para R, disponibilize Rscript e os pacotes da [documentação F2](servicos/fase2-iot/README.md). Captura serial exige PySerial e fonte serial/Wokwi; firmware exige seu toolchain. Esses recursos não são necessários à abertura básica.

**AWS não é pré-requisito da dashboard:** seu perfil básico não exige boto3, chaves, ARN ou acesso à nuvem. A configuração do publicador independente está no [README dos Alertas](servicos/fase7-alertas-aws/README.md).

## Como iniciar e utilizar a aplicação

Após concluir a [Primeira execução](#primeira-execução), na raiz:

```powershell
python iniciar.py
```

Sem argumentos, `python iniciar.py` abre o menu interativo, procedimento principal de uso: **1 — Iniciar** inicia a dashboard, **0 — Parar** solicita seu encerramento e **S — Sair** sai do menu. O navegador é aberto no endereço informado; o controlador procura uma porta livre entre 8501 e 8510.

O inicializador localiza automaticamente `.venv-f402` em `servicos/fase4-regressao/`. Se `FARMTECH_FASE4_PYTHON` estiver definida, esse executável tem prioridade. Antes de abrir o servidor, são conferidas a versão Python 3.11.9, a presença das dependências e a disponibilidade do banco com as colunas necessárias. Configurações incompatíveis impedem a inicialização e apresentam instruções de correção; não há instalação de dependências nem preparação de banco automática.

Selecionar um interpretador em **Python: Select Interpreter** no VS Code não configura necessariamente a variável `FARMTECH_FASE4_PYTHON`, usada pelo inicializador para localizar o Python da dashboard. Ambientes virtuais não são compartilhados automaticamente entre worktrees Git. Quando o ambiente da Fase 4 estiver em outra pasta de trabalho, informe o caminho do executável por essa variável.

No PowerShell, a partir da raiz do projeto, informe o executável de um ambiente F4 já existente no seu computador. O caminho é resolvido localmente, sem depender das pastas dos desenvolvedores:

```powershell
$pythonFase4Existente = Read-Host "Caminho completo do python.exe do ambiente F4 (sem aspas)"
$env:FARMTECH_FASE4_PYTHON = (Resolve-Path -LiteralPath $pythonFase4Existente).Path

python iniciar.py
```

Essa definição vale somente para a sessão atual do terminal e para os processos iniciados a partir dele. Em um novo terminal, defina a variável novamente se precisar utilizar esse ambiente.

Como alternativa ao menu, para início direto:

```powershell
python iniciar.py --dashboard --port 8501
```

Acesse `http://127.0.0.1:8501`. Porta ocupada não é reutilizada. No modo direto, encerre com `Ctrl+C`; no menu, use **0** ou **S**. O controlador não encerra servidores de outras aplicações.

### Base reconstruída e uso offline

`--preparar-demo` cria `.runtime/demo/farmtech-demo.db` a partir dos dois CSVs F4, registra procedência/hashes e **recusa destino existente**. A carga inicial contém 22 culturas, 153 leituras registradas/simuladas e 2.200 amostras acadêmicas; não cria previsões fictícias. Previsões solicitadas depois podem ser persistidas no banco selecionado.

É uma base demonstrativa, não recuperação de histórico perdido. A preparação usa seu destino próprio; `DB_PATH` é respeitado na execução. A simulação inicia desativada e depende de controle explícito.

O carregamento das 153 leituras iniciais e a simulação são operações separadas. Na página **Sensores IoT**, **Iniciar simulação** habilita a geração de novas leituras sintéticas apenas na base de demonstração do modo integrado, após validar o banco. Use **Parar simulação** para interrompê-la. Um `DB_PATH` apontando para outro banco permite suas consultas, mas bloqueia esse controle de simulação; a ausência da base padrão recebe instruções de preparação. A simulação acrescenta registros e não é necessária para consultar o histórico inicial.

Sem rede ou credenciais, permanecem disponíveis cálculos, CSVs, modelos/fontes oficiais locais e demonstrações de alertas. A visão exige seu ambiente e checkout. Open-Meteo precisa de HTTPS; Oracle precisa de rede e autenticação. Falta de pré-condições é informada sem simular sucesso externo.

## Solução de problemas e execução para o avaliador

Esta seção complementa a [Primeira execução](#primeira-execução), sem substituir seu roteiro de instalação. Execute os comandos no PowerShell, na raiz do clone, onde estão `iniciar.py` e `requirements.txt`. Não é necessário reproduzir a estrutura de pastas dos desenvolvedores.

### Pré-requisitos e ambientes efetivamente utilizados

Use Windows AMD64, PowerShell, Git disponível no `PATH`, navegador e Python com `venv` e `pip`. O código não fixa uma versão mínima numérica de Windows, PowerShell ou Git; os exemplos usam sintaxe compatível com PowerShell 5.1. A pasta do projeto precisa permitir gravação em `.runtime/`. A instalação de pacotes e a obtenção do checkout YOLO exigem internet ou uma preparação local equivalente; isso é separado das operações que podem funcionar offline depois.

```powershell
$PSVersionTable.PSVersion
git --version
Get-Command python, py, git -ErrorAction SilentlyContinue
python --version
py -0p
Test-Path -LiteralPath ".\iniciar.py" -PathType Leaf
```

Espera-se uma versão do Git, os executáveis encontrados e `True` para `iniciar.py`. `py -0p` lista os Pythons registrados no launcher do Windows; se não listar uma versão necessária, não presuma que `py -3.11` ou `py -3.13` a localizará. Confira também o executável do ambiente escolhido: a versão de `python` no `PATH` pode ser diferente.

| Uso | Requisito confirmado no projeto |
|---|---|
| Dashboard, CLI integrada, cálculos F1, integração F2/F3 e prévias locais F7 | **CPython 3.11.9 exato** no ambiente F4, com o [perfil básico](requirements.txt). Não é necessário criar um ambiente para cada um desses adaptadores. |
| Inferência e avaliação YOLO integradas da F6 | Processo separado com **CPython 3.13.13 exato**, Windows AMD64/CPU e [dependências próprias](servicos/fase6-visao/requirements.txt). Outro patch 3.13 é recusado pelo worker. |
| API/notebooks originais da F3 | O manifest original declara Python mínimo 3.11, mas esse fluxo é separado da consulta integrada. Não substitui a exigência 3.11.9 da dashboard. |
| Notebooks e experimentos F5/F6 | Ambientes próprios, descritos nos READMEs das fases. O manifest F5 não fixa um patch Python. O Python 3.14.4 registrado em experimentos históricos da YOLO padrão não é o runtime da YOLO integrada. |
| Publicador AWS independente | O [procedimento do serviço](servicos/fase7-alertas-aws/README.md) usa Python 3.11+ e boto3; a captura EC2 registra 3.11.18. Esse ambiente não é necessário para abrir a dashboard. |

### Sequência recomendada e variáveis da sessão

1. Na [Primeira execução](#primeira-execução), prepare o Python F4, instale o `requirements.txt` raiz e execute `pip check`. Oracle e F6 possuem preparações adicionais, opcionais para a abertura básica.
2. Confira o banco com `python iniciar.py --status`; prepare a demonstração somente se faltar o destino padrão.
3. Inicie pelo menu:

```powershell
python iniciar.py
```

Escolha **1** para iniciar, **0** para parar a instância iniciada por esse menu e **S** para sair. Sair também encerra essa instância. Use o endereço mostrado em `Dashboard ativo:`; a porta pode variar de 8501 a 8510. Abrir o servidor não comprova acesso a Oracle, AWS, R ou inferência YOLO.

Variáveis definidas com `$env:` valem somente para aquele terminal e seus processos filhos. Configure `FARMTECH_FASE4_PYTHON`, `FARMTECH_FASE6_PYTHON`, `FARMTECH_YOLO_REPO`, `FARMTECH_RSCRIPT` e `DB_PATH`, quando necessárias, **antes de executar `python iniciar.py`**. Alterá-las em outro terminal não atualiza uma dashboard já aberta: pare, saia do controlador e inicie novamente no terminal configurado. Ativar um ambiente ou selecionar um interpretador no VS Code não substitui essas configurações.

### Quando o Python da Fase 4 não for encontrado

Descubra primeiro qual executável será selecionado:

```powershell
$pythonDashboard = if ($env:FARMTECH_FASE4_PYTHON) {
    $env:FARMTECH_FASE4_PYTHON
} else {
    Join-Path (Get-Location).Path "servicos\fase4-regressao\.venv-f402\Scripts\python.exe"
}
$pythonDashboard
Test-Path -LiteralPath $pythonDashboard -PathType Leaf
if (Test-Path -LiteralPath $pythonDashboard -PathType Leaf) {
    & $pythonDashboard --version
    & $pythonDashboard -m pip check
}
```

O esperado é `True`, **Python 3.11.9** e `No broken requirements found.`. O launcher confere a versão e a presença de módulos, mas não faz uma auditoria completa dos pins ou das dependências transitivas; `pip check` também não substitui a instalação pelo manifest correto.

Se não houver ambiente local, confirme primeiro `py -3.11 --version` e prossiga somente com **3.11.9**. A criação prevista é:

```powershell
if (-not (Test-Path -LiteralPath ".\servicos\fase4-regressao\.venv-f402")) {
    py -3.11 -m venv servicos/fase4-regressao/.venv-f402
}
```

Depois use os comandos de instalação e verificação da [Primeira execução](#primeira-execução). Se a pasta já existir, mas estiver incompleta ou com outra versão, preserve-a e selecione um ambiente compatível. Não reinstale tudo apenas porque o `python` do `PATH` tem outra versão.

Para reutilizar um ambiente externo, use o exemplo de [Como iniciar e utilizar a aplicação](#como-iniciar-e-utilizar-a-aplicação), que configura `FARMTECH_FASE4_PYTHON` com o caminho absoluto do `python.exe` escolhido. Repita o diagnóstico acima após a configuração. Uma variável incorreta tem prioridade e bloqueia o uso do ambiente local; para voltar ao padrão somente nesta sessão:

```powershell
Remove-Item Env:FARMTECH_FASE4_PYTHON -ErrorAction SilentlyContinue
```

Após alterar ou remover a variável, repita o bloco de diagnóstico para atualizar `$pythonDashboard`. Se a versão estiver correta e faltarem módulos, instale o perfil básico **nesse executável**, com `& $pythonDashboard -m pip install -r requirements.txt`, e repita `pip check`. Não use um `pip` solto, que pode pertencer a outro Python. Um ambiente existente que já atende ao perfil não precisa ser recriado.

### Quando o banco demonstrativo não existir

O diagnóstico completo depende primeiro do ambiente F4 válido:

```powershell
$env:DB_PATH
Test-Path -LiteralPath ".\.runtime\demo\farmtech-demo.db" -PathType Leaf
python iniciar.py --status
```

No JSON, examine `fase4.status`, `fase4.source.path` e `fase4.data.counts`. O esperado é `status: "ok"`; a saída do comando pode ter código zero mesmo com algum serviço `unavailable`, portanto leia os campos. A consulta não cria banco, não conecta Oracle e não executa YOLO.

Se `DB_PATH` não estiver definida e o arquivo padrão não existir:

```powershell
if (-not (Test-Path -LiteralPath ".\.runtime\demo\farmtech-demo.db")) {
    python iniciar.py --preparar-demo
}
python iniciar.py --status
```

A base recém-preparada deve informar **22 culturas, um sensor, 153 leituras, 2.200 amostras e zero previsões**. Previsões e simulações feitas depois podem alterar as contagens; isso não justifica apagar a base.

`--preparar-demo` cria exclusivamente o destino padrão, a partir dos CSVs F4, e recusa qualquer destino já existente. Não prepara o caminho personalizado de `DB_PATH`. Para usar o padrão, remova uma configuração externa somente se essa for a intenção:

```powershell
Remove-Item Env:DB_PATH -ErrorAction SilentlyContinue
```

Para conservar um banco personalizado, confira seu caminho e schema; caminhos relativos de `DB_PATH` partem de `servicos/fase4-regressao/`. Em caso de `error` ou `invalid`, preserve o arquivo para diagnóstico. Não execute ingestões históricas ou exclusão de banco como reparo genérico. A preparação exige os CSVs preservados, permissão de escrita e suporte aos hard links usados na publicação da base; falhas nessas condições dependem de preparação local.

### Quando aparecer “Inferência temporariamente indisponível”

Na página **Visão Computacional**, abra **Detalhes técnicos para manutenção**. Também é possível consultar as mesmas pré-condições, sem inferência:

```powershell
Get-Item Env:FARMTECH_FASE6_PYTHON -ErrorAction SilentlyContinue
python -X utf8 -B -c "import json; from farmtech_integracao.fase6 import infer_availability, availability; print(json.dumps({'inferencia': infer_availability().as_dict(), 'avaliacao': availability().as_dict()}, ensure_ascii=False, indent=2))"
```

| Indicador | Significado e providência |
|---|---|
| `python_existe` | Existe um arquivo no caminho Python F6 selecionado. Se for `False`, prepare o ambiente ou configure `FARMTECH_FASE6_PYTHON`. `True` não confirma versão ou bibliotecas. |
| `checkpoint_existe` | Existe `servicos/fase6-visao/entrega_2/modelos/yolov5s_custom_exp60_best.pt`. Ele acompanha a entrega; arquivo ausente ou divergente exige conferir a integridade da cópia. |
| `checkout_local` | Foram encontrados `.git` e `hubconf.py` no checkout selecionado. `True` não confirma a revisão, a integridade das fontes ou a autorização de acesso pelo Git. |

Todos os indicadores podem ser `True` e a execução ainda falhar. A avaliação também verifica avaliador, quatro JPGs com rótulos de banana e quatro de milho; `runtime_validado: false` no diagnóstico informa que essa consulta **não executou** o runtime.

Os dois erros observados correspondem a etapas diferentes:

| Mensagem | Diagnóstico e ação |
|---|---|
| **“Inferência temporariamente indisponível neste ambiente”** | Consulte `FARMTECH_FASE6_PYTHON` e os indicadores acima. No caso confirmado, a variável não estava configurada e o executável padrão não estava disponível. Selecione um ambiente F6 existente ou prepare o cenário B; a variável pode ficar ausente quando o ambiente padrão local já existe. |
| **“Dependências ou funções YOLO não disponíveis no ambiente validado”** | O processo foi acionado, mas houve falha de importação ou função indisponível. No caso confirmado, o Python global 3.13.13 não tinha `torch`, `torchvision` e `opencv-python`. Verifique as bibliotecas **no mesmo executável selecionado**; a mensagem também pode indicar dependências indiretas ou funções incompatíveis. |

#### A. Ambiente virtual da Fase 6 já existente

Antes de instalar novamente, procure o ambiente já preparado. O caminho padrão é `servicos/fase6-visao/.venv-fase6/Scripts/python.exe`. Para listar ambientes diretamente dentro de uma pasta conhecida, informe o diretório que os contém (por exemplo, a pasta do serviço F6 de outro clone):

```powershell
$pastaAmbientesFase6 = Read-Host "Pasta que contém seus ambientes virtuais F6 (sem aspas)"
Get-ChildItem -LiteralPath $pastaAmbientesFase6 -Directory -Force | ForEach-Object {
    $candidatoFase6 = Join-Path $_.FullName "Scripts\python.exe"
    if (Test-Path -LiteralPath $candidatoFase6 -PathType Leaf) {
        $candidatoFase6
    }
}
```

Essa busca examina somente as pastas filhas imediatas; se não houver saída, confira a pasta de busca ou informe diretamente o executável conhecido. `py -0p` localiza instalações registradas do Python, não todos os ambientes virtuais existentes.

Selecione o `python.exe` do ambiente e execute os diagnósticos sem alterar os pacotes:

```powershell
$pythonFase6Existente = Read-Host "Caminho completo do python.exe do ambiente F6 (sem aspas)"
$pythonFase6 = (Resolve-Path -LiteralPath $pythonFase6Existente).Path
Test-Path -LiteralPath $pythonFase6 -PathType Leaf
& $pythonFase6 -X utf8 -I -B -c "import sys, struct; print(sys.executable); print(sys.version.split()[0]); print('bits:', struct.calcsize('P') * 8); print('venv:', sys.prefix != sys.base_prefix)"
& $pythonFase6 -X utf8 -I -B -c "import importlib.util; print({m: importlib.util.find_spec(m) is not None for m in ('torch', 'torchvision', 'cv2')})"
& $pythonFase6 -m pip show torch torchvision opencv-python
& $pythonFase6 -m pip check
& $pythonFase6 -X utf8 -I -B -c "import torch, torchvision, cv2; from torchvision.ops import nms, box_iou; print('torch:', torch.__version__); print('torchvision:', torchvision.__version__); print('OpenCV:', cv2.__version__); print('CUDA:', torch.version.cuda)"
```

Espera-se `True` para o arquivo, **Python 3.13.13**, `bits: 64`, `venv: True` e os três módulos localizados. `opencv-python` é o nome da distribuição instalada pelo pip; seu módulo de importação é `cv2`. O manifest fixa `opencv-python==5.0.0.93`, enquanto o módulo pode informar `cv2.__version__ == "5.0.0"`, como no diagnóstico confirmado. Compare a distribuição com `pip show`, sem confundir esses dois identificadores.

O perfil exige **torch 2.15.0 e torchvision 0.29.2 em CPU**; o ambiente funcional confirmado informou **2.15.0+cpu**, **0.29.2+cpu** e OpenCV **5.0.0**. `torch.version.cuda` deve ser `None`, e `pip check` deve terminar com `No broken requirements found.`. Módulos localizados, metadados e imports são verificações complementares: não substituem a inferência com checkout e checkpoint válidos. Se uma verificação falhar, não considere o ambiente pronto.

Depois de conferir o ambiente e o [checkout YOLO](#disponibilizar-o-checkout-yolo-e-conferir-os-arquivos), configure o executável antes de iniciar a dashboard:

```powershell
$env:FARMTECH_FASE6_PYTHON = $pythonFase6
$env:FARMTECH_FASE6_PYTHON
python iniciar.py
```

Se a dashboard já estiver aberta, use **0** para pará-la e **S** para sair do controlador; então configure a variável no terminal e execute novamente `python iniciar.py`, opção **1**. A definição com `$env:` é **temporária**, válida somente para aquela sessão do PowerShell e seus processos filhos. Em outro terminal ou após fechar a sessão, configure-a novamente; uma dashboard em execução não recebe alterações feitas em outro processo.

No diagnóstico funcional informado, apontar para o Python global 3.13.13 habilitou a página porque `python_existe` passou a ser verdadeiro, mas a análise falhou pela falta das bibliotecas. A correção foi selecionar o ambiente virtual F6 que já tinha as dependências e reiniciar a dashboard; **a inferência funcionou nesse ambiente**. Isso confirma a reutilização daquele ambiente, sem comprovar uma instalação limpa. Se o ambiente existente funciona e atende aos requisitos, não é necessário recriá-lo.

#### B. Instalação limpa do avaliador

Para um avaliador sem ambiente F6, use um ambiente virtual próprio, separado do F4 e fora do checkout YOLO. O arquivo disponível para essa preparação é [servicos/fase6-visao/requirements.txt](servicos/fase6-visao/requirements.txt); não há um perfil YOLO mínimo separado. Ele inclui o índice adicional CPU do PyTorch, os pins YOLO e as dependências de CNN/notebook, como TensorFlow/Keras. O `requirements.txt` da raiz prepara a dashboard, não a F6.

Disponibilize primeiro **CPython 3.13.13 para Windows AMD64**. `py -0p` e `py -3.13 --version` ajudam a localizar e conferir uma instalação registrada. Se o launcher não a encontrar, informe o caminho do interpretador base instalado no computador do avaliador; não use outro patch apenas porque pertence à família 3.13.

Na raiz do projeto, o bloco abaixo valida o interpretador base, recusa uma pasta de ambiente preexistente e prepara o ambiente isolado:

```powershell
$pythonBaseFase6 = Read-Host "Caminho completo do Python base 3.13.13 (sem aspas)"
$pythonBaseFase6 = (Resolve-Path -LiteralPath $pythonBaseFase6).Path
& $pythonBaseFase6 -X utf8 -I -B -c "import sys, struct; assert sys.version_info[:3] == (3, 13, 13), 'Python 3.13.13 exigido'; assert struct.calcsize('P') == 8, 'Python de 64 bits exigido'; print('Interpretador base F6 conferido')"
if ($LASTEXITCODE -ne 0) { throw "Corrija o interpretador base antes de criar o ambiente." }

$ambienteNovoFase6 = ".\servicos\fase6-visao\.venv-fase6"
if (Test-Path -LiteralPath $ambienteNovoFase6) {
    throw "A pasta do ambiente já existe. Preserve-a e use o cenário A."
}
& $pythonBaseFase6 -m venv $ambienteNovoFase6
if ($LASTEXITCODE -ne 0) { throw "A criação do ambiente F6 falhou." }

$pythonFase6 = (Resolve-Path -LiteralPath (Join-Path $ambienteNovoFase6 "Scripts\python.exe")).Path
& $pythonFase6 -m pip install -r ".\servicos\fase6-visao\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "A instalação das dependências F6 não foi concluída." }
```

Com `$pythonFase6` definido, execute os comandos de versão, módulos, `pip show`, `pip check` e imports do [cenário A](#a-ambiente-virtual-da-fase-6-já-existente), sem repetir a busca. Só depois configure `FARMTECH_FASE6_PYTHON` e inicie a dashboard, como indicado naquele cenário. A criação do ambiente não fornece o checkout YOLO: conclua também a preparação da próxima subseção.

**Instalação limpa ainda não validada:** o sucesso informado ocorreu em um ambiente virtual já existente. A reprodução do cenário B continua dependente da disponibilidade de Python 3.13.13 Windows AMD64, das wheels compatíveis com todos os pins e dependências transitivas, dos índices de pacotes e do checkout Git íntegro na revisão exigida. O manifest é uma lista selecionada, não um lock completo. Falha de resolução, download ou carregamento exige preparação/correção técnica do ambiente; não se resolve habilitando apenas o botão ou instalando o perfil F4.

#### Disponibilizar o checkout YOLO e conferir os arquivos

O código YOLOv5 não acompanha este repositório. É preciso um checkout Git local na revisão **`4add2aff6e3d926586a3eab4659f3b498dd444a1`**, com fontes/configurações íntegras. Para obter uma cópia própria com internet, o exemplo abaixo usa uma pasta no perfil do avaliador e só clona se ela não existir:

```powershell
$checkoutYolo = Join-Path $env:USERPROFILE "yolov5-validacao-fase6"
if (-not (Test-Path -LiteralPath $checkoutYolo)) {
    git clone https://github.com/ultralytics/yolov5.git "$checkoutYolo"
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível obter o checkout YOLO." }
    git -C "$checkoutYolo" checkout --detach 4add2aff6e3d926586a3eab4659f3b498dd444a1
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível selecionar a revisão exigida." }
}
$env:FARMTECH_YOLO_REPO = (Resolve-Path -LiteralPath $checkoutYolo).Path
git -C "$env:FARMTECH_YOLO_REPO" rev-parse HEAD
git -C "$env:FARMTECH_YOLO_REPO" status --porcelain --untracked-files=all --ignored=matching -- "*.py" "*.yaml" "*.yml" "*.txt" "*.toml" "*.cfg" "*.ini" "*.json" "*.pyd" "*.so" "*.pth"
```

Se já houver um checkout próprio em outra pasta, atribua seu caminho absoluto a `FARMTECH_YOLO_REPO` em vez de clonar novamente. O primeiro comando Git de diagnóstico deve imprimir o SHA completo acima; o segundo deve ficar sem saída para as fontes/configurações verificadas. O exemplo não altera uma cópia preexistente: uma revisão diferente precisa ser preparada separadamente.

Não coloque o ambiente virtual dentro do checkout YOLO: seus arquivos Python/configurações podem fazer a verificação de integridade recusar a execução. Cache do Hub sem `.git` não basta. Se o Git recusar o acesso, inclusive por propriedade da pasta (`dubious ownership`), use uma cópia própria acessível ao avaliador; não interprete `checkout_local: true` como validação Git concluída.

Confira também o peso customizado sem carregá-lo:

```powershell
(Get-FileHash -Algorithm SHA256 -LiteralPath ".\servicos\fase6-visao\entrega_2\modelos\yolov5s_custom_exp60_best.pt").Hash -eq "93c086ad8e369cc295dced96b9d48db1524226207e82ab514148f02decad2f61"
```

Espera-se `True`. Checkpoint customizado, modelo CNN, imagens e rótulos de teste acompanham o projeto. Os pesos padrão `entrega_2/yolov5s.pt` e `entrega_2/yolov5su.pt` não acompanham esta cópia versionada; são de outros experimentos e não são necessários à inferência customizada integrada. O runtime não baixa checkout, pesos nem dependências automaticamente.

#### Reproduzir a avaliação das oito imagens

Com F4, F6 e checkout preparados, reinicie a dashboard no terminal configurado. Na página **Visão Computacional → Avaliação histórica: oito imagens de teste**, clique em **Avaliar YOLO customizada**. Alternativamente, pela CLI integrada:

```powershell
python iniciar.py --avaliar-yolo --yolo-repo "$env:FARMTECH_YOLO_REPO"
```

O resultado esperado é `status: "ok"`, `data.total_imagens: 8` e métricas para banana e milho. O worker usa Python 3.13.13, CPU, tamanho 640, confiança 0,25 e IoU de associação 0,50; confere revisão, fontes, hash, entradas e classes. Oito imagens se referem ao teste preservado, com quatro por classe. Essa ação produz **uma nova avaliação desse conjunto**, sem treinamento; tempos e resultados devem ser identificados como da nova execução, sem prometer os números históricos.

Para upload, use JPG/PNG de até 5 MiB, com no máximo 4096 pixels por dimensão. Essa inferência usa o mesmo ambiente F6, mas não depende da presença das oito imagens de teste.

### Testes rápidos e falhas de inicialização

Depois de resolver o ambiente F4, estas ações locais exercitam os adaptadores sem Oracle ou AWS:

```powershell
python iniciar.py --gestao --forma retangulo --medidas 100 50 --cultura Soja --espacamento 0.5
python iniciar.py --consultar-fase3 csv
```

Espera-se `status: "ok"`, com o cálculo solicitado e a consulta explicitamente identificada como CSV. Para testes existentes do launcher e dos contratos F6, use o `$pythonDashboard` selecionado no diagnóstico acima:

```powershell
& $pythonDashboard -X utf8 -B -m unittest discover -s tests/integracao -p test_launcher.py -v
& $pythonDashboard -X utf8 -B -m unittest discover -s tests/integracao -p test_fase6.py -v
```

O esperado é `OK`. Esses testes usam fixtures/mocks; passar neles não comprova inferência ou disponibilidade externa. Os demais comandos e limites continuam em [Reprodução dos testes e validações](#reprodução-dos-testes-e-validações). A suíte completa dos alertas precisa também do objeto Git local `d9dabed`; uma cópia sem histórico pode impedir esse teste.

Se a opção 1 falhar, confira a mensagem do controlador e, após uma tentativa que tenha criado o log:

```powershell
Get-Content -LiteralPath ".\.runtime\logs\dashboard.log" -Tail 24
```

Ausência do log pode indicar que Python ou banco foram recusados antes de iniciar o Streamlit. Se a porta estiver ocupada, use o menu, que procura outra porta livre; no modo direto, uma porta ocupada é recusada. Para corrigir variáveis ou encerrar uma instância, use 0/S no controlador que a iniciou.

### Dependências externas e alternativas de demonstração

| Funcionalidade | Preparação ou acesso adicional | Alternativa quando indisponível |
|---|---|---|
| Gestão, CSV F3, análises F4 e fontes oficiais locais | Ambiente F4 e arquivos preservados; banco compatível nas páginas que o consultam | Usar o banco demonstrativo e as cópias locais. Dados Oficiais lê os CSVs preservados; não representa nova coleta externa. |
| Open-Meteo | Internet/HTTPS para geocodificação e previsão | Cenários meteorológicos sintéticos da página Alertas, identificados como demonstração; não apresentar uma previsão antiga como consulta atual. |
| Oracle | [Perfil Oracle](#oracle-opcional), rede, RM/senha/DSN válidos e permissões/tabela na instituição | Escolher **CSV preservado** na página Consultas e Oracle. Não há troca silenciosa de fonte. |
| Nova captura dos sensores F2 | PySerial, fonte serial/COM ou Wokwi/RFC2217 ativo; PlatformIO/toolchain ESP32 para compilar o firmware | Ler o CSV histórico ou usar cenário sintético, com a origem indicada. Não declarar nova captura de hardware. |
| Validação R F2 | R/Rscript instalado e arquivos F2; o validador integrado usa pacotes base de R | Consultar resultados preservados ou demonstrar CSV/alertas sem executar R. Scripts originais de outras fases podem exigir pacotes próprios. |
| YOLO integrada | Ambiente F6, checkout externo, Git, peso customizado e entradas conferidas | Apresentar capturas/métricas como **evidências históricas**, mantendo a indicação de inferência indisponível nesta execução. |
| SNS → e-mail | Publicador independente, boto3, internet, recursos AWS, permissões, tópico e assinatura confirmada | Página Alertas oferece avaliação e prévia local sem envio. As capturas AWS documentam as validações anteriores; não comprovam um novo envio. |
| Rekognition — Ir Além 1 | Acesso manual ao console AWS e internet; não há cliente integrado na dashboard | Consultar capturas e JSONs do experimento preservado, sem declarar nova chamada à AWS. |
| Notebooks, treinamento e fluxos originais F5/F6 | Ambientes próprios, arquivos e serviços descritos nos READMEs; Colab/Drive/GPU conforme o experimento | Examinar notebooks/resultados preservados. Preparar a dashboard ou o Python F6 não reproduz automaticamente esses treinamentos. |

Ambientes virtuais, checkout YOLO, credenciais, recursos de nuvem e o banco gerado em `.runtime/` não são entregues prontos pelo Git. A documentação orienta a preparação; ela não corrige incompatibilidades de wheels, falta do Python exato, permissões ou indisponibilidade de serviços externos.

Na revisão documental anterior, foram conferidos o código, os diagnósticos locais e os comandos existentes; **não foi executada instalação limpa**. No ambiente disponível, faltavam os ambientes F4/F6 locais e o launcher informou a falta do Python F4. A base local existente foi inspecionada sem alteração; o diagnóstico F6 confirmou arquivos preservados, mas não validou execução. Os 20 testes do launcher e 13 de contratos F6 passaram no Python 3.14.4 disponível, com fixtures/mocks, sem iniciar uma dashboard real, instalar dependências ou executar inferência.


## Fase 7 — Parte 1: dashboard final e serviços integrados

A página inicial e as treze páginas são registradas pela aplicação. Os caminhos seguintes têm prefixo `servicos/fase4-regressao/src/frontend/`.

| Página | Arquivo | Funcionalidade |
|---|---|---|
| Visão Geral | `app.py` | Apresentação, navegação e contexto da base/simulação |
| Sensores IoT | `pages/1_Sensores_IoT.py` | Leituras, gráficos, histórico e controle de simulação |
| Análise Exploratória | `pages/2_Analise_Exploratoria.py` | Filtros, estatísticas, correlação e distribuições |
| Pipeline ML | `pages/3_Pipeline_ML.py` | Comparação de modelos, métricas e resíduos |
| Previsão Agrícola | `pages/4_Previsao.py` | Estimativas acadêmicas de rainfall/umidade e pH |
| Recomendações de Manejo | `pages/5_Recomendacoes.py` | Comparações didáticas de cenário e leituras |
| Histórico de Previsões | `pages/6_Historico_Previsoes.py` | Resultados persistidos, gráficos e exportação |
| Dados Oficiais | `pages/7_Dados_Oficiais.py` | NOAA/USCRN, INMET e IBGE/SIDRA |
| Visão Geral dos Serviços | `pages/8_Servicos_Integrados.py` | Cinco serviços, pré-condições locais e contagens |
| Gestão Agrícola | `pages/9_Gestao_Agricola.py` | Geometria e insumos F1 |
| IoT e Meteorologia | `pages/10_IoT_Meteorologia.py` | Open-Meteo, CSV e validação R F2 |
| Consultas e Oracle | `pages/11_Oracle_Consultas.py` | Consulta CSV ou Oracle F3 |
| Visão Computacional | `pages/12_Visao_Computacional.py` | Upload/inferência YOLO e avaliação do teste F6 |
| Alertas — Fase 7 | `pages/13_Alertas_Fase7.py` | Avaliação de sensores/meteorologia e prévia sem SNS |

Para demonstrar: prepare a base, calcule um talhão, consulte o CSV F3, explore os modelos F4, analise uma imagem com F6 e avalie o histórico na página Alertas. Solicite meteorologia, Oracle e R quando suas pré-condições estiverem disponíveis.

## Indicadores, métricas e resultados do sistema integrado

Os valores são exemplos verificáveis de fontes preservadas e capturas identificadas. Contagens, filtros, tempos e previsões variam conforme a execução. **Indicador operacional, previsão meteorológica e métrica de IA não são medidas equivalentes.**

### Indicadores operacionais e cenários

| Serviço / página | Valores representativos | Contexto e fonte |
|---|---|---|
| Visão Geral / Serviços | **Cinco serviços** na página 8; base inicial com **22 culturas, 153 leituras e 2.200 amostras**, sem previsões artificiais | [Preparação da base](farmtech_integracao/workers/fase4_worker.py). Contagens mudam com o uso; prontidão local não comprova acesso externo |
| Gestão F1 | Soja, retângulo **10 × 20 m**, espaçamento **0,50 m**: **200 m²**, **0,0200 ha**, **0,0083 alqueire**, **20 linhas** | [Captura F1](docs/evidencias/fase1_gestao_geral.png). Área = largura × comprimento; ha = m²/10.000; alqueire preservado = 24.200 m². Custos/quantidades usam catálogo ilustrativo |
| Meteorologia F2 | Temperatura **°C**, umidade do ar **%**, precipitação **mm** e vento **m/s**, em série horária para **Irecê, 05–11/11/2026** | [Captura meteorológica](docs/evidencias/fase2_meteorologia_temperatura_umidade.png). Valores dependem da cidade e consulta; não são medições dos sensores locais |
| Validação R F2 | **153 registros históricos analisados**, **três registros sintéticos integrados** | [Captura R](docs/evidencias/fase2_r_integracao_validada.png). Demonstração temporalmente compatível, separada do histórico de maio e da previsão real de novembro |
| Consultas F3 | **153 registros**; última leitura **03/05/2026 20:17:18**: **80,5%**, **27,6 °C**, **pH 5,15** na tela, bomba desligada | [CSV F3](docs/evidencias/fase3_csv_consulta_geral.png). Sem fuso declarado, não se presume UTC. A [captura Oracle](docs/evidencias/fase3_oracle_consulta_real.png) registra consulta de 153 linhas naquela sessão |
| Sensores F4 | Em **04/11/2026, 23:57:30, Bahia**: **82,7%**, **37,3 °C**, **pH simulado 10,500**, **LDR 1830**, bomba desligada | [Leituras F4](docs/evidencias/fase4_iot_leituras.png). Registros/simulações acadêmicas, não comprovação de medição física atual |
| Exploração F4 | **100 amostras por cultura**. Filtro banana/apple/coconut/cotton: **400 amostras**, médias **25,35 °C**, **86,84%**, **pH 6,20**, **rainfall 118,34 mm** | [Estatística do filtro](docs/evidencias/fase4_analise_exploratoria_estatistica_e_contagem.png). Médias do recorte, não da base inteira |
| Previsão F4 | Banana; N/P/K **38/60/93 kg/ha**, **22,5 °C**, pH **6,3** → **rainfall 148,47 mm**, **umidade 91,93%** | [Cenário da captura](docs/evidencias/fase4_previsao_parametros_e_resultados.png). Proxy acadêmico, sem horizonte meteorológico datado ou volume operacional de irrigação |
| Estimativa de pH F4 | Cenário distinto: banana; N/P/K **60/55/44 kg/ha**, **25 °C**, umidade **70%**, rainfall **100 mm** → **pH 5,900** | [Captura pH](docs/evidencias/fase4_previsao_estimativa_ph.png). O pH não é entrada desse modelo |
| Manejo F4 | Umidade **58,3%** versus limite **60%**: déficit **1,7 p.p.**; pH **7,798** versus faixa apple **5,5–6,5**: excesso **1,298** | [Recomendações](docs/evidencias/fase4_recomendacoes_manejo.png). Referências didáticas; não calculam dose, duração ou volume |
| Histórico F4 | Em **05/11/2026**: **30 previsões**, **três tipos** e **um nome de algoritmo, Ridge** | [Histórico](docs/evidencias/fase4_historico_previsoes_grafico_umidade.png). Um nome não significa um único arquivo para todos os alvos. Consulta até 500 registros; total dinâmico |
| NOAA/USCRN e INMET | NOAA: **8.756 observações horárias**, GA Newton 11 SW, série 2025; solo em **m³/m³**, profundidades **5/10/20/50/100 cm**. INMET: **8.713 observações horárias**, A701 São Paulo–Mirante, **2025** | [CSVs/metadados](servicos/fase4-regressao/src/dados/official/); [NOAA](docs/evidencias/fase7_dados_oficiais_uscrn_umidade_solo.png) e [INMET](docs/evidencias/fase7_dados_oficiais_inmet_temperatura.png). Gráficos diários: médias das horas válidas e soma da precipitação, sem imputação de ausências |
| IBGE/SIDRA | **180 registros nacionais**, **36 anos × cinco culturas**, **1990–2025**; recorte municipal 2025 com **27.820 linhas**, não municípios distintos. Milho **6.376 kg/ha** e soja **3.470 kg/ha**, Brasil/2025 | [Série nacional](servicos/fase4-regressao/src/dados/official/sidra1612_rendimento_brasil.csv). Teste temporal 2021–2025 teve R² negativo nas cinco culturas; mantém-se a consulta histórica, **sem previsão de rendimento disponibilizada** |
| Alertas F7 | Histórico F2: **153 registros de 03/05/2026**. Última recepção **20:17:18**, declarada em −03:00 → **23:17:18 UTC**. **80,5%**, **27,6 °C**, pH simulado **5,147**, N/P/K **1/0/1**, bomba **0** | [Avaliação IoT](docs/evidencias/fase7-alertas-02-avaliacao-iot.png). **Três condições**: umidade alta principal, pH fora da faixa e P ausente. Origem física/simulada não comprovada; não é medição atual |

As fontes tabulares estão em [dados F4](servicos/fase4-regressao/src/dados/), [histórico F3](servicos/fase3-dashboard/src/dados/historico_irrigacao.csv) e [histórico F2](servicos/fase2-iot/dados/historico_irrigacao.csv). DHT22 mede umidade do ar; pH derivado do LDR e N/P/K dos botões são representações didáticas, não análises laboratoriais. Fontes oficiais mantêm suas localidades e unidades próprias.

### Modelos de regressão F4

| Modelo / alvo | MAE | RMSE | R² no teste | R² na CV |
|---|---:|---:|---:|---:|
| Ridge — rainfall | 14,3467 mm | 23,1551 mm | 0,8219 | 0,8515 ± 0,0180 |
| Ridge — humidity | 3,0978 p.p. | 4,5398 p.p. | 0,9617 | 0,9659 ± 0,0083 |
| Ridge — pH | 0,4279 unidades de pH | 0,6021 unidades de pH | 0,3291 | 0,3574 |

Fontes: [métricas históricas](servicos/fase4-regressao/src/ml/models/metricas.json), [métricas pH](servicos/fase4-regressao/src/ml/models/metricas_ph.json) e [metadados pH](servicos/fase4-regressao/src/ml/models/modelo_ph_metadata.json). São **2.200 amostras**, divididas em **1.760 de treino e 440 de teste**, com cinco dobras de CV.

**MAE** é a média do erro absoluto; **RMSE** é a raiz da média dos erros quadráticos, penalizando mais erros grandes. Ambos conservam a unidade do alvo. **R²** compara o resultado com a referência baseada na média: pode ser negativo e não é percentual de acurácia. **CV** significa validação cruzada; `±` indica o desvio entre dobras quando registrado.

Nos modelos históricos rainfall/humidity, o teste participou da seleção e foi incluído na CV: os números preservados **não constituem avaliação independente de generalização**. O modelo pH tem protocolo separado, com seleção na CV do treino e teste reservado; seu resultado continua experimental e praticamente iguala a referência de média de pH por cultura. Rainfall é variável acadêmica usada como proxy, sem validação de necessidade hídrica real.

### Visão computacional: detecção e classificação

O dataset F6 preserva **64 imagens de treino, oito de validação e oito de teste**, para banana e milho. A avaliação integrada YOLO usa CPU, imagem 640, confiança mínima **0,25** e IoU de associação **0,50**.

| Classe — YOLO customizada | TP | FP | FN | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Banana | 2 | 1 | 7 | 66,67% | 22,22% | 33,33% |
| Milho | 4 | 4 | 3 | 50,00% | 57,14% | 53,33% |

A [captura da avaliação](docs/evidencias/fase6_yolo_metricas.png) apresenta **oito imagens e 256,86 ms/imagem** nessa execução. Precisão = TP/(TP+FP); recall = TP/(TP+FN); F1 é a média harmônica entre ambos. As contagens são de objetos associados aos rótulos, não de imagens corretas. **Não são mAP**; confiança de uma detecção também não é acurácia geral.

A CNN classifica a imagem inteira. A [validação independente de 03/11/2026](servicos/fase6-visao/CHANGELOG.md#2026-11-03--validação-funcional-dos-modelos-preservados) registra **seis acertos em oito imagens, acurácia de 75% e 17,33 ms/imagem**. Não é opção da página integrada. Classificação e detecção têm tarefas e medições diferentes; esses tempos não formam benchmark uniforme.

O [complemento de 06/11/2026](docs/VALIDACAO_COMPLEMENTAR_CPP_YOLO.md) documenta duas inferências reais pelo upload: uma imagem de banana também produziu falso positivo de milho. Carregamento e comunicação funcionaram, mas a qualidade preditiva permaneceu limitada. Pesos e limiares não foram alterados para melhorar a demonstração.

### Resultados históricos F5

O [experimento F5](servicos/fase5-ml/README.md) preserva **156 registros, quatro culturas e 39 cenários climáticos**. Com `GroupKFold` de cinco dobras por cenário, a Random Forest obteve **R² médio ≈ 0,9884**, próximo do baseline por cultura **≈ 0,9872**. O melhor R² usando somente clima ficou em **≈ 0,0107**. A cultura domina esse conjunto; não há ganho climático robusto ou generalização em produção comprovados. Esses modelos não alimentam página própria da dashboard.

## Demonstrações visuais da dashboard

As capturas registram sessões específicas. Filtros, dados e disponibilidade podem mudar. Imagens com prefixo `fase7_dados_oficiais_` pertencem à página Dados Oficiais da F4 na plataforma consolidada, não ao SNS.

### Acervo completo de evidências

As imagens incorporadas neste README são uma seleção representativa. Os diretórios abaixo reúnem as demais evidências da dashboard e das validações AWS V1 e V2:

- [Capturas da dashboard integrada](docs/evidencias/).
- [Capturas da validação AWS V2 — sensores simulados da Fase 2 (08/11/2026)](assets/aws-notifications/).
- [Capturas históricas da validação AWS V1 — alerta meteorológico (05/11/2026)](assets/bkp/aws-notifications/).

### Serviços e gestão agrícola

![Visão geral dos serviços integrados](docs/evidencias/fase7_servicos_visao_geral.png)

*Registro anterior à inclusão de Alertas, com quatro serviços. A página atual oferece cinco; as capturas F7 abaixo mostram a nova entrada.*

![Cálculo do talhão de soja](docs/evidencias/fase1_gestao_geral.png)

*Talhão de 200 m², conversões e 20 linhas. A [captura complementar](docs/evidencias/fase1_gestao_grafico_e_tabela.png) mostra a comparação de insumos do catálogo ilustrativo.*

### Meteorologia e consultas

![Temperatura e umidade previstas para Irecê](docs/evidencias/fase2_meteorologia_temperatura_umidade.png)

*Open-Meteo horária, com local e unidades. A [validação R](docs/evidencias/fase2_r_integracao_validada.png) distingue histórico original e integração sintética.*

![Consulta Oracle na integração F3](docs/evidencias/fase3_oracle_consulta_real.png)

*Registro de conexão, consulta de 153 linhas e encerramento naquela sessão. O [modo CSV](docs/evidencias/fase3_csv_consulta_geral.png) funciona sem credenciais.*

### Análise e previsão

![Métricas do modelo histórico de umidade](docs/evidencias/fase4_pipeline_humidity.png)

*Comparação de algoritmos e erros com as ressalvas do protocolo histórico.*

![Parâmetros e resultados da previsão agrícola](docs/evidencias/fase4_previsao_parametros_e_resultados.png)

*Cenário banana: rainfall como proxy e umidade estimada. A [estimativa de pH](docs/evidencias/fase4_previsao_estimativa_ph.png) usa outro modelo e outras entradas.*

![Umidade volumétrica do solo USCRN](docs/evidencias/fase7_dados_oficiais_uscrn_umidade_solo.png)

*Observações oficiais por profundidade e localidade, em m³/m³; não são leituras ESP32 ou previsões F4.*

### Visão computacional

![Inferência de banana com o modelo customizado](docs/evidencias/fase6_yolo_banana.png)

*Resultado experimental do upload. Consulte também [milho](docs/evidencias/fase6_yolo_milho.png) e [métricas do teste](docs/evidencias/fase6_yolo_metricas.png); detecções isoladas não estabelecem acurácia geral.*

### Alertas locais

![Avaliação do histórico na página Alertas](docs/evidencias/fase7-alertas-02-avaliacao-iot.png)

*Recepção de maio/2026, histórica e de origem não comprovada, com umidade alta principal. A [configuração](docs/evidencias/fase7-alertas-01-configuracao.png) explicita o fuso e a reprodução histórica.*

![Condições simultâneas e prévia da mensagem](docs/evidencias/fase7-alertas-03-condicoes-notificacao.png)

*pH simulado fora da faixa e P ausente como condições secundárias. A prévia preserva os selos de histórico/origem; a captura é um recorte e não representa envio.*

## Fase 7 — Parte 2: serviço de alertas AWS

### Objetivo e contextos de execução

O serviço transforma dados em condições de atenção e orientações ao funcionário. A entrada IoT reutiliza o contrato CSV dos sensores F2. A Open-Meteo é uma fonte meteorológica externa complementar. A comprovação do envio com as fontes exigidas pelo requisito acadêmico está centralizada em [Validação AWS — Evidências complementares](#validação-aws--evidências-complementares).

| Contexto | Funcionamento comprovado | Limite |
|---|---|---|
| **Implementação original (V1)** | Criação do ambiente AWS, execução em EC2 e publicação/recebimento de e-mail SNS em **05/11/2026**, com previsão meteorológica | Alerta meteorológico; recursos reutilizados na V2. Veja a [validação de 08/11/2026](#validação-aws--evidências-complementares) |
| **Integração atual** | CSV F2, cenários sintéticos e meteorologia são avaliados localmente; condição, ação, assunto e corpo aparecem na página 13 | A dashboard não possui envio real ao SNS |
| **Serviço independente atual (V2)** | CLI com publicação somente com `--enviar`; em **08/11/2026**, Edemir Sufiatti fez o deploy manual de seis arquivos do serviço na EC2 e publicou um alerta baseado nos sensores simulados da Fase 2 | Validação pontual AWS da entrada IoT com origem Wokwi declarada; os testes locais usam mocks |

```mermaid
flowchart LR
    Sensores["CSV dos sensores F2"] --> Regras["Regras e validação temporal"]
    Previsao["Previsão F2 / Open-Meteo"] --> Regras
    Regras --> Mensagem["Condição · ação · assunto e corpo"]
    Mensagem --> Local["Dashboard: prévia local"]
    Mensagem --> CLI["CLI independente: envio explícito e autorizado"]
    CLI --> SNS["SNS · e-mail · V1 meteorologia / V2 sensores simulados F2"]
```

A infraestrutura criada na V1 utiliza **Amazon Linux 2023, EC2 t3.micro, região sa-east-1 (São Paulo) e SNS Standard**; o EBS gp3 de 8 GiB é registro histórico, não revalidado em 08/11. Na V2, a EC2 `farmtech-alertas` foi iniciada (3/3 verificações aprovadas), o SSH foi restrito ao IP do responsável e a role IAM `farmtech-alertas` estava associada; o conteúdo da política IAM não foi auditado nessa data. O diagrama resume as validações V1 e V2, sem comprovar disponibilidade contínua dos recursos AWS.

### Validação AWS — Evidências complementares

**STATUS: VALIDAÇÃO PONTUAL COMPROVADA EM 08/11/2026**

**Responsável:** Edemir Sufiatti.

O envio pelo Amazon SNS foi comprovado na V1 (05/11/2026), com previsão meteorológica, e na V2 (08/11/2026), com dados dos sensores simulados da Fase 2 no Wokwi, conforme o requisito.

- **Fluxo:** firmware ESP32 da F2 no simulador Wokwi → CSV do coletor serial → `scp` para a EC2 → `monitorar.py --iot-csv` → tópico SNS Standard `farmtech-alertas-funcionarios` → e-mail.
- **Leitura publicada:** recebida às 17:45:03 (Brasília), umidade **39,5%** (< 45%), 230 s de idade na publicação, dentro do limite de cinco minutos. Origem declarada `wokwi`: simulação, não medição física nem validação agronômica.
- **Publicação:** MessageId `0fc7e8a7-03b2-5e11-82ec-8bcde1c7af3a`.
- **Recebimento:** e-mail às 17:48 (Brasília), assunto "FarmTech [SIMULAÇÃO WOKWI]: Umidade do DHT22/protótipo abaixo de 45% para o tomate".
- **Ação corretiva:** "Conferir no protótipo a irrigação prevista pela regra de umidade baixa. Não acionar bomba física com base neste alerta."

A dashboard continua apenas com prévia local, sem envio ao SNS. Passo a passo, comandos, prints e anexo da V1: [README do serviço de alertas](servicos/fase7-alertas-aws/README.md).

### Regras e ações corretivas

Os critérios são didáticos, sem calibração agronômica. O serviço informa: não envia comandos ao firmware nem aciona bomba física.

| Fonte | Condição | Ação apresentada |
|---|---|---|
| IoT F2 | Umidade <45% | Conferir no protótipo a irrigação prevista pela regra de umidade baixa; não acionar bomba física com base no alerta |
| IoT F2 | Umidade >80% | Conferir no protótipo a bomba desligada pela regra de umidade alta |
| IoT F2 | pH corrigido fora de [6,0; 6,8] | Conferir a simulação do LDR e o pH corrigido |
| IoT F2 | Algum N/P/K igual a zero | Conferir os botões de presença; não representam concentrações de nutrientes |
| Meteorologia | Chuva horária ≥1 mm na janela | Manter a bomba de irrigação desligada |
| Meteorologia | Umidade do ar <45%, sem chuva prioritária | **Verificar a umidade do solo e as necessidades da cultura antes de decidir pelo acionamento da irrigação.** |
| Meteorologia | Umidade do ar >80%, sem condições prioritárias | Manter a bomba de irrigação desligada |

Nos sensores, a prioridade é umidade, depois pH, depois N/P/K. Todas as condições coexistentes são apresentadas, com um único alerta principal. Na meteorologia, chuva precede umidade baixa e alta. A janela considera **agora inclusive até 12 horas exclusive, em UTC**; chuva é horária, não soma da janela. Valores iguais a 45% ou 80% não disparam alerta de umidade.

O CSV preserva os onze campos `ts_iso,t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw`. O timestamp é de recepção no computador, sem certificar instante/qualidade da aquisição. Sem offset, exige fuso informado. Registros recentes admitem até **cinco minutos**; antigos exigem reprodução histórica e futuros são recusados. Origem declarada não comprova medição física.

A CLI controla repetição por **seis horas por tipo e local**, incluindo dispositivo/origem para IoT. Dry-run não altera esse estado. Na página, mudar fonte ou cenário invalida a avaliação anterior e exige novo clique, sem rede automática. Consulta à fonte, avaliação local e evento previsto possuem horários separados; metadados ausentes aparecem como indisponíveis.

### Evidências da validação de 08/11/2026

![Publicação SNS com MessageId a partir dos sensores F2](assets/aws-notifications/20-iot-publicado-sns-messageid.png)

*Publicação na EC2 com a leitura Wokwi de 39,5% e o MessageId retornado pelo SNS.*

![E-mail do alerta IoT recebido](assets/aws-notifications/21-email-alerta-iot-recebido.png)

*E-mail recebido do SNS, identificado como simulação Wokwi. A criação do ambiente na V1 (05/11/2026) está documentada no anexo do [README do serviço](servicos/fase7-alertas-aws/README.md).*

### Demonstração segura

Na página **Alertas — Fase 7**, escolha demonstração sintética ou CSV, confira origem/fuso e clique em avaliar. Para o histórico de maio, mantenha reprodução histórica. Upload CSV admite até **1 MiB** e exige esquema/conteúdo válidos. Meteorologia depende de consulta explícita ou previsão já consultada.

A CLI também permite demonstração offline, sem boto3 ou credenciais:

```powershell
$pythonDashboard = ".\servicos\fase4-regressao\.venv-f402\Scripts\python.exe"

# Novo CSV marcado como sintético
$csv = & $pythonDashboard -B servicos/fase7-alertas-aws/gerar_exemplo_iot.py --tipo umidade_baixa
& $pythonDashboard -B servicos/fase7-alertas-aws/monitorar.py --iot-csv "$csv"

# Meteorologia sintética, com horário válido para avaliação
$exemplo = & $pythonDashboard -B servicos/fase7-alertas-aws/gerar_exemplo.py --tipo chuva
& $pythonDashboard -B servicos/fase7-alertas-aws/monitorar.py --arquivo "$exemplo"
```

Os comandos não usam `--enviar` e não publicam. Os geradores recusam sobrescrita e identificam dados sintéticos. O JSON histórico pode estar fora da janela e não deve receber datas fictícias para aparentar atualidade. Configuração, exceções e envio independente estão no [README do serviço AWS](servicos/fase7-alertas-aws/README.md).

## Ir Além 1 — Amazon Rekognition

Atividade exploratória com imagens de milho e banana utilizando **Amazon Rekognition Label Detection**, com análise dos resultados e das identificações secundárias incorretas. Inclui comparação conceitual com a YOLO utilizada na Fase 6 e um estudo de caso com proposta conceitual de tratamento das detecções em aplicações agrícolas.

[**Acessar documentação completa do Ir Além 1**](IR-ALEM/ir-alem-1-rekognition/README.md)

**Vídeo demonstrativo:** pendente de gravação e publicação no YouTube como não listado, com duração máxima de quatro minutos.

## Reprodução dos testes e validações

Use o ambiente da dashboard, a partir da raiz. SNS é substituído por mocks e não exige credenciais. A suíte completa do serviço também usa Git para consultar o objeto local `d9dabed`.

```powershell
$pythonDashboard = ".\servicos\fase4-regressao\.venv-f402\Scripts\python.exe"

# Adaptador e worker dos alertas
& $pythonDashboard -X utf8 -B -m unittest discover -s tests/integracao -p test_fase7.py -v

# Apresentação, condições simultâneas, estado e horários
& $pythonDashboard -X utf8 -B -m unittest discover -s tests/integracao -p test_alertas_apresentacao.py -v

# Regras, mensagens, registros e SNS simulado
& $pythonDashboard -X utf8 -B -m unittest discover -s servicos/fase7-alertas-aws -p "test_*.py" -v

# HTTP local; encerra a instância de validação
& $pythonDashboard -X utf8 -B scripts/validar_dashboard_local.py
```

Para reproduzir os testes focados de inicialização, banco e simulação, no mesmo ambiente:

```powershell
& $pythonDashboard -X utf8 -B -m unittest discover -s tests/integracao -p test_launcher.py -v
& $pythonDashboard -X utf8 -B -m unittest discover -s tests/integracao -p test_first_run.py -v
& $pythonDashboard -X utf8 -B -m unittest discover -s tests/integracao -p test_database_preflight.py -v
& $pythonDashboard -X utf8 -B -m unittest discover -s tests/integracao -p test_demo_integrity.py -k reconstructed_database -k publication_never -k missing_and_invalid -k demo_command -k integrated_configuration -v
& $pythonDashboard -X utf8 -B -m unittest discover -s servicos/fase4-regressao/tests -p test_sensor_simulation.py -v
& $pythonDashboard -X utf8 -B -m unittest discover -s tests/integracao -p test_dashboard.py -k all_fourteen -v

# Os testes históricos do scheduler usam a raiz do serviço F4.
$pythonDashboard = (Resolve-Path $pythonDashboard).Path
Push-Location servicos/fase4-regressao
try {
    & $pythonDashboard -X utf8 -B -m unittest discover -s tests -p 'test_scheduler*.py' -v
} finally {
    Pop-Location
}
```

A validação local desta correção utilizou o ambiente F4 já existente, com **50 testes focados aprovados**. A preparação em banco temporário conferiu as 153 leituras contra o CSV, 22 culturas e 2.200 amostras. O menu iniciou um servidor real, que respondeu HTTP 200 em `/_stcore/health`, e a opção 0 o encerrou. No AppTest do Streamlit, as 14 telas foram renderizadas; na página Sensores IoT, o job real do scheduler acrescentou uma leitura sintética (153 → 154) e o controle de parada o encerrou. Também foram exercitados os casos de base ausente e banco personalizado, sem gravar no banco do projeto. **Isso não equivale a uma instalação ou primeira execução em máquina limpa nem a uma inspeção visual em navegador real.**

Esses comandos selecionam as regressões desta correção. A verificação integral do manifesto histórico de arquivos já apresentava hashes divergentes e dois pesos YOLO ausentes; esses materiais e seus resultados não foram alterados. Portanto, não se declara aprovação de toda a suíte histórica.

Os registros distinguem execuções reais, mocks e rodadas sobrepostas; seus totais não devem ser somados:

| Registro | Resultado documentado | Alcance |
|---|---|---|
| [Integração de 03/11/2026](docs/VALIDACAO.md) | 230 aprovações e nove casos C++ inicialmente ignorados | Integração, F1, F2 e seleção F4 sem treino; verificações externas predominantemente simuladas |
| [Auditoria de 06/11/2026](docs/AUDITORIA_LOTE1.md) | 243 testes Python e 16 grupos R aprovados | Consolidação posterior, com escopo próprio |
| [Complemento C++/YOLO](docs/VALIDACAO_COMPLEMENTAR_CPP_YOLO.md) | **Nove testes C++ aprovados**, 13 testes específicos F6 e duas inferências reais pelo upload | C++ exercita funções no host, não GPIO/hardware; inferência sem retreinamento |
| Alertas locais | Testes de CSV/demonstrações, condições simultâneas, mensagens, seleção, horários e bloqueio SNS | [Adaptador](tests/integracao/test_fase7.py), [apresentação](tests/integracao/test_alertas_apresentacao.py) e [isolamento](tests/integracao/test_fase7_isolamento_seguranca.py); não demonstram novo envio AWS |

Os documentos indicam comandos adicionais e limites. Avaliação YOLO real e análises R são ações separadas das suítes com mocks. Os resultados históricos não foram recalculados para esta apresentação.

## Resultados, limitações e segurança

- A navegação mantém os serviços preservados sem iniciar automaticamente captura, treinamento, consulta remota ou inferência. As páginas F4 conservam efeitos explícitos, inclusive persistência de previsões e simulação controlada.
- A aplicação escuta em **loopback** e não implementa autenticação geral. Exposição em rede exige autenticação, autorização e HTTPS antes do uso externo. Autenticação Oracle é por consulta.
- Não versione credenciais nem exponha senhas, tokens ou URLs de assinatura. As capturas AWS selecionadas possuem tratamento dos dados sensíveis. IAM e acesso SSH devem ser revisados pelo responsável antes de reativar recursos.
- Uploads/workers têm limites e validações. Visão aceita JPG/PNG de até **5 MiB**, com limite de **4096 pixels por dimensão** no worker. Código e pesos locais devem ser confiáveis; isolamento de processo não é sandbox universal.
- Há viés no protocolo histórico F4, teste visual pequeno e falsos positivos YOLO. Os modelos e as recomendações não autorizam atuação física automática.
- Fontes oficiais mantêm locais, períodos e unidades próprios; não validam automaticamente sensores simulados ou recomendações.
- A V1 demonstrou o alerta meteorológico em **05/11/2026**. Na validação pontual de **08/11/2026**, documentada por Edemir Sufiatti, a V2 demonstrou o deploy manual do serviço, a publicação do alerta baseado nos sensores simulados da Fase 2 no SNS, o recebimento do e-mail com a ação corretiva recomendada. As evidências não comprovam disponibilidade contínua da AWS. Veja [Validação AWS — Evidências complementares](#validação-aws--evidências-complementares). Recursos podem gerar custos e exigem gestão pelo responsável.

## Documentação complementar e repositórios originais

| Documento | Conteúdo |
|---|---|
| [Arquitetura](docs/ARQUITETURA.md) | Contratos, workers, persistência e proveniência |
| [Serviços](docs/SERVICOS.md) | APIs e operações das integrações |
| [Validação inicial](docs/VALIDACAO.md) | Execuções e limitações da integração |
| [Auditoria consolidada](docs/AUDITORIA_LOTE1.md) | Correções e verificações posteriores |
| [Complemento C++/YOLO](docs/VALIDACAO_COMPLEMENTAR_CPP_YOLO.md) | Compilação host e inferências reais |
| [Alertas AWS](servicos/fase7-alertas-aws/README.md) | Contrato IoT, regras, mensagens e validações V1 (alerta meteorológico, 05/11/2026) e V2 (sensores simulados F2, 08/11/2026) |
| [Relatório F4](servicos/fase4-regressao/document/relatorio.md) | Modelos, fontes oficiais e banco |
| [Rastreabilidade F2](servicos/fase2-iot/document/RASTREABILIDADE_F2.md) | Contrato dos sensores e materiais preservados |

Documentos anteriores registram o estado de suas rodadas: trechos sobre ausência de R/Oracle, upload ou página 13 não substituem a descrição atual. O enunciado integral F7 não está incluído nesta cópia; os documentos preservam a síntese dos requisitos utilizada pelo projeto.

| Fase | Repositório de origem |
|---|---|
| 1 | [EdeSufiatti/farmtech](https://github.com/EdeSufiatti/farmtech) |
| 2 | [EdeSufiatti/EdeSufiatti-FIAP_IA_FASE2_CAP1](https://github.com/EdeSufiatti/EdeSufiatti-FIAP_IA_FASE2_CAP1) |
| 3 | [EdeSufiatti/FASE3_AT1_Farmtech_dashboard](https://github.com/EdeSufiatti/FASE3_AT1_Farmtech_dashboard) |
| 4 | [jojocamdb/FarmTech-Solutions-Fase4](https://github.com/jojocamdb/FarmTech-Solutions-Fase4) |
| 5 | [jojocamdb/fiap-fase5-farmtech-ml](https://github.com/jojocamdb/fiap-fase5-farmtech-ml) |
| 6 | [EdeSufiatti/farmtech_neural_vision](https://github.com/EdeSufiatti/farmtech_neural_vision) |

## Fontes de dados e referências

As fontes abaixo distinguem observações oficiais, previsões de APIs, datasets públicos, históricos acadêmicos e dados simulados ou sintéticos. Os links locais identificam os materiais usados nos experimentos; as referências externas identificam sua origem quando documentada. Uma cópia preservada ou seu hash não comprovam, por si só, autoria, aquisição física ou licença de redistribuição.

| Fonte ou conjunto de dados | Dados utilizados e finalidade | Origem e período, quando identificáveis | Link da fonte original ou caminho do arquivo preservado |
|---|---|---|---|
| **Catálogo acadêmico — insumos F1** | Produtos, doses, unidades e preços utilizados nos cálculos ilustrativos de insumos e custos | Vetor estático preservado no projeto. Fonte comercial, data de cotação e validação agronômica das doses não documentadas | [Catálogo em código](servicos/fase1-gestao/src/vetor_produtos.py) |
| **Histórico do projeto — talhões F1** | Cadastros de áreas/culturas e exportações dos cálculos por talhão e produto | Entradas e resultados da aplicação; sem período, localidade ou levantamento de campo comprovados | [Dados da fazenda](servicos/fase1-gestao/config/dados_fazenda.csv) e [insumos por talhão](servicos/fase1-gestao/config/insumos_por_talhao.csv) |
| **Histórico do projeto — sensores F2, reutilizado em F3/F4/F7** | Umidade, temperatura, LDR, pH didático, indicadores N/P/K e bomba; consultas, análises e reprodução histórica de alertas | **153 leituras de 03/05/2026, 20:03:40–20:17:18**, sem offset no arquivo. Contrato ESP32/Wokwi; o CSV não comprova uso de placa física ou simulador. `ts_iso` registra recepção no computador | [Histórico F2](servicos/fase2-iot/dados/historico_irrigacao.csv), [cópia F3](servicos/fase3-dashboard/src/dados/historico_irrigacao.csv), [cópia F4](servicos/fase4-regressao/src/dados/historico_irrigacao.csv) e [capturador serial](servicos/fase2-iot/scripts/serial_grava_csv.py) |
| **API — Open-Meteo** | Geocodificação por cidade e previsão horária de temperatura, umidade relativa do ar, precipitação e vento; meteorologia F2 e alertas F7 | Previsão externa por coordenadas, com período dependente da resposta da consulta. A integração registra o instante de consulta em UTC; não é aquisição de sensores locais | [Documentação da API](https://open-meteo.com/en/docs), [cliente F2](servicos/fase2-iot/scripts/weather_forecast.py) e [metadados da consulta no worker](farmtech_integracao/workers/fase2_worker.py) |
| **Dataset acadêmico — Cap10, F3/F4** | **2.200 amostras e 22 culturas**, com N, P, K, temperatura, umidade, pH, rainfall e cultura; exploração e modelos de regressão F4 | O código declara fornecimento pela **FIAP**, com uso anterior na F3. **Autoria externa original, URL de aquisição, período e localidade não comprovados**; não se atribui uma fonte pública por semelhança do conteúdo | [CSV F4](servicos/fase4-regressao/src/dados/Atividade_Cap10_produtos_agricolas.csv), [CSV F3](servicos/fase3-dashboard/src/dados/Atividade_Cap10_produtos_agricolas.csv) e [declaração no importador](servicos/fase4-regressao/scripts/init_db.py) |
| **Dados oficiais — NOAA/NCEI, USCRN** | Meteorologia e umidade volumétrica do solo em cinco profundidades, em m³/m³; consulta de observações reais na página Dados Oficiais | Estação **GA Newton 11 SW**, Georgia/EUA, **WBAN 63829**; série horária de **2025**. A cópia normalizada vai de 01/01/2025 01:00 UTC a 01/01/2026 00:00 UTC | [Arquivo oficial hourly02](https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/2025/CRNH0203-2025-GA_Newton_11_SW.txt), [CSV local](servicos/fase4-regressao/src/dados/official/noaa_uscrn_ga_newton_2025.csv) e [metadados](servicos/fase4-regressao/src/dados/official/noaa_uscrn_ga_newton_2025_metadata.json) |
| **Dados oficiais — INMET** | Temperatura e umidade relativa do ar, com precipitação; observações meteorológicas exibidas separadamente dos sensores | Estação **A701 — São Paulo/Mirante, SP**; série horária de **2025**, selecionada do arquivo anual oficial | [ZIP oficial de 2025](https://portal.inmet.gov.br/uploads/dadoshistoricos/2025.zip), [CSV local](servicos/fase4-regressao/src/dados/official/inmet_sp_a701_2025.csv) e [metadados com o nome do arquivo da estação](servicos/fase4-regressao/src/dados/official/inmet_sp_a701_2025_metadata.json) |
| **Dados oficiais — IBGE/SIDRA** | Rendimento médio da produção, em **kg/ha**, para arroz, feijão, milho, soja e cana; consulta histórica e avaliação temporal de produtividade | **Tabela 1612, variável 112, classificação c81**. Séries nacionais de **1990–2025** e recortes municipais preservados de **2023 e 2025**; estatísticas agregadas, sem identificação de uma propriedade FarmTech | [Tabela oficial](https://sidra.ibge.gov.br/tabela/1612), [CSV nacional](servicos/fase4-regressao/src/dados/official/sidra1612_rendimento_brasil.csv), [metadados nacionais](servicos/fase4-regressao/src/dados/official/sidra1612_metadata.json) e [municipais 2023](servicos/fase4-regressao/src/dados/official/sidra1612_metadata_municipios_2023.json)/[2025](servicos/fase4-regressao/src/dados/official/sidra1612_metadata_municipios_2025.json) |
| **Dataset acadêmico — crop_yield, F5** | **156 registros, seis colunas, quatro culturas e 39 cenários climáticos**; regressões e clusterização históricas | Origem primária externa e URL não comprovadas; sem datas ou localização. As unidades originais e a escala de `Yield` têm ressalvas documentadas; a conversão de apresentação não comprova a unidade de origem | [CSV preservado](servicos/fase5-ml/src/crop_yield.csv), [notebook histórico](servicos/fase5-ml/src/JocastaBortolacci_rm564730_pbl_fase4.ipynb) e [contexto metodológico F5](servicos/fase5-ml/README.md) |
| **Dataset público — banana, F6** | **40 imagens** da classe banana para os experimentos de detecção YOLO e classificação CNN | Kaggle, **Fruits Dataset (Images)**, identificador `shreyapmaher/fruits-dataset-images`, pasta `images/banana fruit`. Versão/snapshot e data de download não identificados | [Dataset original](https://www.kaggle.com/datasets/shreyapmaher/fruits-dataset-images), [imagens e rótulos preservados](servicos/fase6-visao/dataset/) e [registro de curadoria](servicos/fase6-visao/README.md#fontes-das-imagens) |
| **Imagens públicas com curadoria — milho, F6** | **40 fotografias** selecionadas manualmente para a classe milho, com anotações de detecção do projeto | Plataformas **Pixabay e Pexels**. URLs individuais das fotografias finais não estão preservadas; datas de aquisição e atribuições por imagem não foram identificadas nos materiais consultados | [Pixabay](https://pixabay.com/), [Pexels](https://www.pexels.com/), [acervo local](servicos/fase6-visao/dataset/) e [limites da curadoria](servicos/fase6-visao/README.md#fontes-das-imagens) |
| **Dados simulados — sensores F4** | Leituras geradas por distribuições e indicadores aleatórios, persistidas quando a simulação é ativada; demonstração da dashboard | Geração local pelo scheduler, conforme os parâmetros do código e o momento de execução. Não são medições físicas nem novas amostras do dataset Cap10 | [Gerador da simulação](servicos/fase4-regressao/src/frontend/scheduler.py) |
| **Dados sintéticos — exemplos F7** | CSV IoT e JSON meteorológico de cenários controlados para avaliar regras e prévias locais | Geração em Python com timestamps relativos à execução e identificação sintética. Não representam captura ESP32/Wokwi, consulta real Open-Meteo ou comprovação de envio SNS | [Gerador IoT](servicos/fase7-alertas-aws/gerar_exemplo_iot.py) e [gerador meteorológico](servicos/fase7-alertas-aws/gerar_exemplo.py) |

Na F6, as 80 imagens locais formam as mesmas partições de **64 para treino, oito para validação e oito para teste** nos experimentos YOLO/CNN; as caixas foram anotadas no MakeSense.ai e exportadas no formato YOLO. A curadoria e suas limitações estão no [README F6](servicos/fase6-visao/README.md#dataset-e-curadoria). O pré-treinamento COCO dos pesos YOLO padrão é uma referência externa da comparação, não a origem das imagens locais de banana e milho.

O [relatório F4](servicos/fase4-regressao/document/relatorio.md) detalha importação, normalização e limites das fontes oficiais. NOAA e INMET representam estações externas, e SIDRA contém estatísticas agregadas; seus períodos e unidades não devem ser fundidos com os sensores do protótipo. As lacunas de procedência acima permanecem explícitas, sem atribuição de fontes ou licenças não comprovadas.

## Histórico de lançamentos

As versões abaixo são declarações dos projetos de origem. Datas de auditoria e consolidações não representam automaticamente tags ou GitHub Releases.

| Período / registro | Evolução documentada | Fonte |
|---|---|---|
| 18/03/2026 — F1 | Desenvolvimento original da gestão agrícola | [README F1](servicos/fase1-gestao/README.md) |
| Abril/2026 — F2 | Versões declaradas **0.1.0–0.1.4**: ESP32, captura, previsão e análises. Fontes divergem entre 12 e 13/04 para 0.1.4 | [CHANGELOG F2](servicos/fase2-iot/CHANGELOG.md) |
| 02–05/05/2026 — F3 | Linha documentada **1.0.0–1.0.21**, persistência, consultas e indicadores | [Histórico F3](servicos/fase3-dashboard/README.md) |
| 11 e 15/06/2026 — F4 | Versões declaradas **1.0.0 e 1.1.0**, SQLite, modelos, dashboard e menu/CLI | [Histórico F4](servicos/fase4-regressao/README.md) |
| 30/08–06/09/2026 — F5 | Versões documentadas **0.5.0–1.1.0**, análises, revisão metodológica e custos AWS | [Histórico F5](servicos/fase5-ml/README.md) |
| 02–07/10/2026 — F6 | Dataset, experimentos YOLO de 30/60 épocas e execução Colab | [Histórico F6](servicos/fase6-visao/README.md) |
| Outubro–01/11/2026 | Correções e rastreabilidade de cálculos, contratos temporais, persistência e configuração | [F1](servicos/fase1-gestao/CHANGELOG.md), [F2](servicos/fase2-iot/CHANGELOG.md), [F4](servicos/fase4-regressao/README.md) |
| 02–03/11/2026 — F6 | Complementação YOLO/CNN e validação dos modelos preservados | [CHANGELOG F6](servicos/fase6-visao/CHANGELOG.md) |
| 03–06/11/2026 — Integração | Registros de validação, consolidação Git `d9dabed` e complemento C++/YOLO | [Validação](docs/VALIDACAO.md) e [complemento](docs/VALIDACAO_COMPLEMENTAR_CPP_YOLO.md) |
| Novembro/2026 — F7 | Integração dos serviços, alertas locais, segurança, dependências e documentação final | [Auditoria](docs/AUDITORIA_LOTE1.md), [Alertas](servicos/fase7-alertas-aws/README.md) e este README |

O estágio consolidado de novembro de 2026 não recebe número de versão, tag ou release não documentado. Datas de validação e de commit são eventos distintos.

## Créditos e direitos autorais

A consolidação preserva o trabalho e os créditos anteriores. Além dos integrantes atuais, a autoria histórica inclui **Daniel Abreu dos Santos — RM570844** e **Jocasta de Kacia Bortolacci — RM564730**, conforme os READMEs das respectivas fases. A reorganização documental não substitui sua autoria.

Agradecimentos à FIAP, à tutoria e à coordenação identificadas no início. Bibliotecas, plataformas, fontes de dados, imagens e modelos de terceiros mantêm suas atribuições.

## Licença

O [modelo institucional FIAP](https://github.com/agodoi/template) e sua variante [templateFiapVfinal](https://github.com/agodoi/templateFiapVfinal) preservam a atribuição à [FIAP](https://www.fiap.com.br/) sob [Creative Commons Attribution 4.0 International — CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

O serviço F4 contém declaração própria de **CC BY 4.0**, copyright © 2026 Equipe FarmTech Solutions — FIAP, em seu [arquivo de licença](servicos/fase4-regressao/LICENSE). Essa declaração e a licença institucional **não são estendidas automaticamente ao repositório inteiro**. Código e documentação autorais das demais fases preservam titulares, créditos e condições de origem; esta reescrita não escolhe nova licença para esses materiais.

Bibliotecas, implementações YOLO/Ultralytics, componentes TensorFlow/Keras e pesos externos permanecem sujeitos às respectivas licenças. Os checkpoints treinados não recebem, por este README, autorização irrestrita de redistribuição.

As imagens de banana provêm do [Fruits Dataset (Images)](https://www.kaggle.com/datasets/shreyapmaher/fruits-dataset-images); as de milho foram obtidas no [Pixabay](https://pixabay.com/) e [Pexels](https://www.pexels.com/). Aplicam-se as condições das plataformas e fontes. Dados [NOAA/NCEI](https://www.ncei.noaa.gov/), [INMET](https://portal.inmet.gov.br/) e [IBGE/SIDRA](https://sidra.ibge.gov.br/) mantêm proveniência e condições próprias, identificadas nos metadados.

A finalidade acadêmica e a presença de arquivos no repositório não equivalem à concessão de uma licença única para todos os componentes.
