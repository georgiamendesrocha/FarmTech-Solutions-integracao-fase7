# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
  <a href="https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP" width="40%" height="40%"></a>
</p>

<br>

# FarmTech Solutions · Dashboard de dados IOT e Previsão do tempo.

- **Repositório original — Fase 3:** [https://github.com/EdeSufiatti/FASE3_AT1_Farmtech_dashboard](https://github.com/EdeSufiatti/FASE3_AT1_Farmtech_dashboard)
- **Integração Fase 7:** módulo em `servicos/fase3-dashboard`.
- **Vídeo https://youtu.be/Ds_Ag9mhRvE**

Monitoramento agrícola com **painel Streamlit**, **Oracle Database** e **machine learning em Python**, alimentados pelos dados de sensores desenvolvidos na **Fase 2** (ESP32 FarmTech).

**Versão do projeto documentada:** `1.0.21` — ver **Histórico de versões** e a política de marcação na mesma secção.

---

## Índice

1. Conformidade com as entregas FIAP (mapeamento)  
2. Nome do grupo · Integrantes · Professores  
3. Descrição e contexto  
4. O que este repositório entrega  
5. Arquitetura de dados  
6. Contrato do ficheiro CSV  
7. Contrato da tabela Oracle  
8. Estrutura de pastas  
9. Pré‑requisitos  
10. Instalação · dependências principais  
11. Configuração — `.env` (âncora: `#configuracao-env`)  
12. Como executar (raiz · Oracle · notebook Jupyter · SQL)  
13. Painel Streamlit — funcionalidades  
14. Exemplos visuais do dashboard (capturas estáticas)  
15. Machine Learning  
16. SQL no Oracle  
17. Histórico de versões  
18. Controle de versão Git e dados  
19. Resolução de problemas  
20. Documentação complementar · Licença  

---

## Conformidade com as entregas FIAP

Abaixo indico **onde** cada exigência da Fase 3 (entrega obrigatória e Ir Além) é coberta neste repositório.

**Entrega obrigatória**

- **Relatório e prints Oracle** — **`src/docs/relatorio.md`** e pasta **`assets/rel/`** (importação / `SELECT *`).
- **Dados da Fase 2 na importação** — descrito no relatório; operacional em **`SENSORES_FARMTECH`** e CSV em **`src/dados/historico_irrigacao.csv`**.
- **Repositório organizado e `README.md`** — estrutura **`src/`**, **`scripts/`**, **`assets/`**; comandos na secção **Como executar**.
- **Consultas SQL** — **`src/sql/consultas.sql`** (sensores e `WTH_*`).
- **Vídeo (≤5 min, YouTube não listado)** — link no topo deste README e/ou no relatório quando publicado.

**Ir além — Opção 1 (dashboard)**

- **Umidade, P, K e pH** — página **Sensores IoT** (`iot.py`).
- **Estado da irrigação** — mesma página; alvo **`bomba_fw`** / Oracle.
- **Sugestões de irrigação com base no clima** — **Previsão do tempo** (`forecast.py`); **Painel IA · soluções** com tabela de **cinco dias** (`painel_solucoes_ia.py`).
- **Exportação do relatório em PDF** — página **Exportar relatório PDF** (`exportar_relatorio_pdf.py`), a partir de **`src/docs/relatorio.md`**.

**Ir além — Opção 2 (ML)**

- **EDA (≥5 gráficos), 3 culturas, 5 modelos, comparação** — **`notebook_ml.py`**, **`Edemir_RM571375_fase3_cap1.ipynb`**, dados **`src/dados/Atividade_Cap10_produtos_agricolas.csv`** (variáveis: **N, P, K, temperatura, umidade, pH, chuva, label**).

---

## Nome do grupo

**FarmTech Solutions**

## Integrantes

- Edemir Sufiatti — RM571375
- Carlos Magnus Costa Amaral — RM573978
- Georgia Mendes Rocha — RM573281
- Marina Leme Soares — RM570461

## Professores

**Tutor(a):** Nicolly Cândida Rodrigues de Souza  

**Coordenador(a):** André Godoi Chiovato

---

## Descrição e contexto

A **FarmTech Solutions** é a startup fictícia do PBL de **Inteligência Artificial** da FIAP. Na **Fase 2**, o firmware no ESP32 envia pela **USB serial** linhas CSV (`CSV_ROW`) com telemetria de campo: solo, ambiente simulados, nutrientes N/P/K e comando da bomba. No PC da Fase 2, um script (**`serial_grava_csv.py`**) grava o ficheiro **`dados/historico_irrigacao.csv`** (não faz parte obrigatória deste repositório, mas é a **origem física dos dados brutos**).

Na **Fase 3**:

1. Exporta‑se esse histórico ou importa‑se para o **Oracle FIAP**, tabela modelo **`SENSORES_FARMTECH`** (o microcontrolador **não** liga ao servidor diretamente).
2. Este repositório reúne **consultas SQL**, **dashboard interativo** e **treino / avaliação de modelos** sobre o mesmo domínio de sensores.
3. O dataset operacional no dia a dia deste código é **`historico_irrigacao.csv`** em `src/dados/`, conforme descrito abaixo.

**Origem dos dados brutos (Fase 2):** típicamente firmware ESP32, `dados/historico_irrigacao.csv` e `scripts/serial_grava_csv.py` no repositório da Fase 2 (caminhos variam conforme o clone).

---

## O que este repositório entrega

| Entrega | Descrição |
|--------|-----------|
| **Dashboard** | `Streamlit` + `Plotly`: KPIs, histogramas, dispersão, vistas por bomba, pH, irrigação, NPK, correlação, tabela filtrada; **README** com capturas em `assets/readme/`. |
| **Fontes de dados** | Na aba **Sensores IoT**, a origem é explícita na sidebar (**Oracle** ou **CSV**). Quando Oracle está selecionado, o painel usa somente o banco; CSV é uma fonte alternativa manual. |
| **Filtros** | Período temporal por posição na sequência cronológica; irrigação; faixas de umidade e pH. |
| **ML** | Notebook **`src/ml/Edemir_RM571375_fase3_cap1.ipynb`** + **`notebook_ml.py`**: Parte A (sensores / **`bomba_fw`**, K-Means, cinco classificadores) e Parte B (**`Atividade_Cap10_produtos_agricolas.csv`**, cultura `label`, EDA, perfil de culturas, cinco modelos multiclasse com N, P, K, temperatura, umidade, pH, chuva). |
| **SQL** | **`src/sql/consultas.sql`** — exemplos sobre **`SENSORES_FARMTECH`**; DDL em **`src/sql/createtable.sql`**. |
| **Oracle** | **`scripts/test_connection.py`** — teste pontual de conectividade. |
| **Painel** | **`src/frontend/app.py`**: **Entrega** (Sensores IoT) · **Ir além** — **Painel IA · soluções**, previsão, análise, notebook ML, **Exportar relatório PDF**. |
| **Launchers (raiz)** | **`run.py`** — API + Streamlit (`--api-only`, `--dashboard-only`); **`app.py`** — atalho opcional `streamlit run`. |

---

## Arquitetura de dados

Os dados vêm do **Projeto 1 da Fase 2** (FIAP — simulação de IoT agrícola: ESP32 e registo de telemetria em CSV).

Neste repositório, a cópia usada pelo dashboard em modo CSV (leitura prioritária) está em:

**`src/dados/historico_irrigacao.csv`**

No código atual, a aba **Sensores IoT** consulta **`SENSORES_FARMTECH`** quando a opção **Oracle** está selecionada (variáveis `ORACLE_*` no `.env`). O ficheiro **`src/dados/historico_irrigacao.csv`** é usado somente quando a opção **CSV** é selecionada pelo utilizador.

---

## Contrato do ficheiro CSV (histórico de sensores)

O painel espera pelo menos as colunas abaixo (nomes conforme CSV da Fase 2; o código faz `lower()` aos cabeçalhos).

| Coluna (no CSV Fase 2 / export) | Tipo / domínio | Uso neste projeto |
|---------------------------------|------------------|-------------------|
| `ts_iso` | Texto (ISO 8601) | Marco temporal; obrigatório no CSV do painel; alimenta o eixo temporal e, no Oracle, costuma mapear para `TS_ISO` e/ou `INSTANTE`. |
| `umidade` | Número (%) | Umidade do solo. |
| `temp_c` | Número (°C) | Temperatura; no Oracle do DDL do repositório corresponde a **`TEMP_C`** (sinónimo possível: **`temperatura`** na leitura). |
| `ph_corr` | Número | pH corrigido; no DDL do repositório **`PH_CORR`** (alias **`ph`** na normalização Streamlit). |
| `n`, `p`, `k` | Inteiros **0** ou **1** | Nutrientes; no Oracle **`N`**, **`P`**, **`K`** com domínio 0/1. |
| `bomba_fw` | Inteiro **0** ou **1** (semântica booleana) | Alvo de irrigação: **0** desligada, **1** ligada. Na página **Sensores IoT** (`iot.py`) o rótulo textual **Ligada** / **Desligada** aparece numa coluna derivada **`irrigacao`** só para gráficos; o modelo numérico efetivo mantém **`bomba_fw`**. Na Oracle a coluna **`IRRIGACAO`** costuma guardar **0** ou **1** (ver **`src/sql/createtable.sql`**). |

Colunas opcionais não usadas pelo painel podem existir no CSV (por exemplo `t_rel_ms`, `ldr`, `ph_base`); não entram no pipeline padrão do notebook nem da página **Notebook ML**, salvo alteração explícita do código.

### Onde gravar cópias no repositório

| Caminho | Papel |
|---------|-------|
| **`src/dados/historico_irrigacao.csv`** | Dataset de exemplo para a fonte **CSV** da aba IoT; deve ser versionado se a equipa decidir incluir amostra no repositório (ajustar `.gitignore` conforme a política do grupo). |

Recomenda-se ignorar **`.env`**, **`.venv/`** e pastas de cache do Jupyter (**`.ipynb_checkpoints/`**) no controlo de versão.

---

## Contrato da tabela Oracle `SENSORES_FARMTECH`

A página **Sensores IoT** usa `SELECT * FROM SENSORES_FARMTECH`; o `DataFrame` padroniza cabeçalhos em minúsculas e aliases (ex.: **`temperatura` → `temp_c`**, **`ph` → `ph_corr`**, **`irrigacao`/binário → `bomba_fw`**). Tipos alinhados ao script **`src/sql/createtable.sql`**:

| Coluna (Oracle) | Tipo (DDL em `src/sql/createtable.sql`) | Conteúdo |
|-----------------|----------------------------------------|----------|
| `ID` | `NUMBER` (IDENTITY) | Chave surrogate. |
| `INSTANTE` | `TIMESTAMP(6)` | Instante do registo (preenchível a partir de `TS_ISO` via *trigger* no DDL). |
| `TS_ISO` | `VARCHAR2(50)` | Marco temporal em texto (formato alinhado ao CSV da Fase 2). |
| `T_REL_MS` | `NUMBER` | Opcional — tempo relativo (ms), se existir no *export*. |
| `UMIDADE` | `NUMBER` | Umidade (%). |
| `TEMP_C` | `NUMBER` | Temperatura (°C). |
| `LDR`, `PH_BASE`, `PH_CORR` | `NUMBER` | Luz / pH base / pH corrigido; o painel usa **`PH_CORR`** como pH principal. |
| `N`, `P`, `K` | `NUMBER(1)` + *CHECK* 0/1 | Presença dos nutrientes. |
| `BOMBA_FW` | `NUMBER(1)` + *CHECK* 0/1 | Estado da bomba (**0**/**1**), homólogo ao **`bomba_fw`** do CSV. |

Importações ou esquemas institucionais mais antigos podem expor nomes alternativos (**`TEMPERATURA`**, **`PH`**, **`IRRIGACAO`** em vez de **`BOMBA_FW`**, **`NITROGENIO`**…). Desde que o `SELECT` devolva colunas reconhecíveis, **`iot.py`** tenta mapeá‑las para **`temp_c`**, **`ph_corr`**, **`bomba_fw`** e **`n`/`p`/`k`**.

**Campos úteis na origem Oracle:** `UMIDADE`, `TEMP_C` ou `TEMPERATURA`, `PH_CORR` ou `PH`, `N`/`P`/`K` (ou sinónimos), **`BOMBA_FW`** (ou **`IRRIGACAO`** legada), `TS_ISO`/`INSTANTE`.

Para o eixo temporal são tentados, por ordem: `instante`, `ts_iso`, `data_registro`, `datahora`, `dt_registro`, `dh`, `dh_registro`; se nenhum for válido, são geradas marcas sintéticas.

O ficheiro **`src/sql/consultas.sql`** trabalha com **`BOMBA_FW`** (0/1) e etiquetas derivadas em SQL; ajuste filtros se o vosso catálogo usar outro nome de coluna.

---

## Estrutura de pastas

Árvore alinhada ao repositório atual (`.env` e `.venv` são locais e não entram no Git):

```text
<raiz-do-repositório>/
├── run.py                      # API + dashboard ou --api-only / --dashboard-only
├── app.py                      # atalho opcional: streamlit run app.py
├── .gitattributes
├── .gitignore
├── requirements.txt
├── README.md                   # único .md na raiz
├── config/
│   └── .env.example            # modelo ORACLE_* (copiar para .env na raiz)
├── .github/
│   └── problem-report.md
├── assets/
│   ├── logo-fiap.png
│   ├── rel/                    # evidências Oracle (prints SQL Developer)
│   └── readme/                 # figuras do README (regeneráveis)
├── scripts/
│   ├── test_connection.py
│   ├── export_readme_iot_figures.py
│   ├── export_readme_forecast_figures.py
│   ├── export_readme_analysis_figures.py
│   ├── export_readme_notebook_ml_figures.py
│   ├── export_readme_painel_solucoes_ia_figures.py
│   └── export_readme_recomendador_demo.py
├── src/
│   ├── __init__.py
│   ├── api/                    # FastAPI — clima, coleta agendada, Oracle
│   │   ├── __init__.py
│   │   ├── main.py             # app FastAPI (uvicorn src.api.main:app)
│   │   ├── db.py
│   │   ├── collector.py
│   │   ├── schemas.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── forecast.py
│   │       └── admin.py
│   ├── frontend/               # Streamlit multipágina
│   │   ├── __init__.py
│   │   ├── app.py
│   │   └── pages/
│   │       ├── __init__.py
│   │       ├── iot.py
│   │       ├── painel_solucoes_ia.py
│   │       ├── forecast.py
│   │       ├── analysis.py
│   │       ├── notebook_ml.py
│   │       └── exportar_relatorio_pdf.py
│   ├── docs/
│   │   ├── relatorio.md        # relatório técnico (importação Oracle)
│   │   ├── executar.md         # guia passo a passo
│   │   └── auditoria_f3-01.md # auditoria e rastreabilidade F3-01/F3-02
│   ├── dados/
│   │   ├── historico_irrigacao.csv
│   │   └── Atividade_Cap10_produtos_agricolas.csv
│   ├── ml/
│   │   └── Edemir_RM571375_fase3_cap1.ipynb
│   ├── sql/
│   │   ├── createtable.sql
│   │   └── consultas.sql
│   └── utils/
│       └── relatorio_pdf.py
```

**Organização:** **`run.py`** na raiz orquestra API e dashboard; **`src/api`** REST e persistência meteorológica; **`src/frontend`** painel Streamlit; **`src/docs`** documentação académica; **`src/dados`** CSV; **`src/sql`** DDL e consultas; **`src/ml`** notebook Ir Além; **`src/utils`** utilitários (PDF). **`assets/rel/`** — evidências Oracle; **`assets/readme/`** — capturas do README.

---

## Pré-requisitos

| Requisito | Notas |
|-----------|-------|
| **Python** | 3.11 ou superior, conforme `requirements.txt`. Em **Python 3.14+**, use as versões declaradas para obter wheels compatíveis (pandas/numpy/streamlit). |
| **PIP** | Atualização recomendada: `python -m pip install --upgrade pip` |
| **Oracle** | Conta/host FIAP para dados reais na aplicação e no teste único (`oracledb` thin driver). |
| **Rede/VPN** | Conforme regras institucional para alcançar `oracle.fiap.com.br`. |

Opcionalmente: **Git**, **editor de código** (por exemplo **VS Code**), **SQL Developer**.

---

## Instalação

Na **raiz** do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**Pacotes na raiz** (`requirements.txt`): inclui dashboard (`streamlit`, `plotly`, `kaleido`, …), ML (`scikit-learn`, `matplotlib`, `seaborn`), Jupyter (`notebook`, `ipykernel`), Oracle (`oracledb`) — um único `pip install -r requirements.txt` cobre o projeto inteiro (ver comentários no ficheiro).

Em Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

<a id="configuracao-env"></a>

## Configuração — `.env` e opcionais

1. Copie **`config/.env.example`** para **`.env` na raiz do repositório** (nome exacto `.env`).
2. Preencha as variáveis:

| Variável | Descrição |
|----------|-----------|
| `ORACLE_USER` | Usuário Oracle (ex.: `RM123456` ) |
| `ORACLE_PASS` | Senha Oracle |
| `ORACLE_DSN` | DSN Oracle (ex.: `oracle.fiap.com.br:1521/ORCL` ou `localhost:1521/xepdb1`) |

Opcional:

| Variável | Significado por omissão |
|----------|-------------------------|
| **`DASHBOARD_CACHE_TTL`** | Segundos de cache do dashboard (quando configurado). |

O ficheiro **`.env` está ignorado pelo Git** (ver `.gitignore`).

---

## Como executar

**Contexto de trabalho:** **`cwd`** na **raiz** do clone (onde estão `requirements.txt`, **`run.py`** e `.env`).

### Arranque integrado (recomendado) — API + dashboard

Um único processo orquestrador na raiz inicia **uvicorn** (FastAPI) e **Streamlit** em paralelo; **Ctrl+C** encerra os dois.

```bash
python run.py
```

Por omissão:

- API: `http://127.0.0.1:8000` (documentação interativa: `/docs`)
- Dashboard: `http://127.0.0.1:8501`

Parâmetros úteis:

```bash
python run.py --api-port 8000 --streamlit-port 8501
python run.py --api-reload
python run.py --api-only
python run.py --dashboard-only
```

(`--api-reload` ativa o *hot reload* só na API; em geral prefira **sem** esta flag ao usar o arranque integrado.)

Guia detalhado: **`src/docs/executar.md`**.

### API FastAPI — só o backend (desenvolvimento ou depuração)

```bash
python run.py --api-only
python run.py --api-only --api-reload
```

Ao iniciar a API:

1. carrega o `.env` com credenciais Oracle;
2. garante a cidade base (`Pato Branco`) em `WTH_LOCATIONS`;
3. executa uma coleta inicial de previsão meteorológica;
4. agenda coletas recorrentes a cada 5 minutos.

URLs principais:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

### Endpoints do módulo API

Base prefix: `/api/v1`

**Forecast (`src/api/routers/forecast.py`)**

- `GET /forecast/locations`
- `GET /forecast/current?id_location=1`
- `GET /forecast/hourly?id_location=1&hours=24`
- `GET /forecast/hourly/history?id_location=1&days=7`
- `GET /forecast/daily?id_location=1`

**Admin (`src/api/routers/admin.py`)**

- `POST /admin/collect` (força coleta manual)
- `GET /admin/logs?limit=50`
- `GET /admin/health`

### Painel Streamlit — só o frontend

Quando a API **já** corre à parte (ou para isolar erros de UI), na **raiz** do clone:

```bash
streamlit run src/frontend/app.py
```

Atalho equivalente:

```bash
streamlit run app.py
```

**Windows (PowerShell):** idem, com o ambiente virtual ativo e **`cwd`** na raiz.

**Navegação:** **Entrega** ▸ **Sensores IoT** (inicial); **Ir além** ▸ **Painel IA · soluções**, **Previsão do Tempo**, **Análise para IA (meteorologia)** (`weather_01`…`07`), **Notebook ML (Ir Além)**, **Exportar relatório PDF**. Na página **Notebook ML**, é possível definir a porta do Jupyter e **Abrir notebook no navegador** para o ficheiro **`src/ml/Edemir_RM571375_fase3_cap1.ipynb`**.

### Teste single‑shot contra Oracle

```bash
python scripts/test_connection.py
```

**Saída** esperada em caso de sucesso: valor de **`SYSDATE`** e texto a indicar explicitamente que **não** haverá novas tentativas.

### Notebook Jupyter (Ir Além)

Ficheiro: **`src/ml/Edemir_RM571375_fase3_cap1.ipynb`**.

```bash
pip install -r requirements.txt
jupyter notebook src/ml/Edemir_RM571375_fase3_cap1.ipynb
```

O notebook procura o repositório pela presença de **`.env`** e da pasta **`src`**; trabalhe com **`cwd`** na **raiz** do clone para que o CSV em **`src/dados/historico_irrigacao.csv`** e as variáveis Oracle sejam resolvidos como no código.

Consultas SQL: secção **SQL no Oracle** mais abaixo.

---

## Painel Streamlit — funcionalidades

- **Arranque habitual com API:** na raiz use **`python run.py`** para ter **Streamlit** e **FastAPI** em simultâneo (páginas de previsão e análise consomem dados servidos pela API).
- **Código:** módulos em **`src/frontend/`** (`app.py` define a navegação); páginas em **`src/frontend/pages/`** (`iot.py`, `painel_solucoes_ia.py`, `forecast.py`, `analysis.py`, `notebook_ml.py`, `exportar_relatorio_pdf.py`).
- **Menu:** **`st.navigation`** com secções **Entrega** (Sensores IoT) e **Ir além** (Painel IA, previsão, análise meteorológica `weather_01`…`07`, notebook ML, exportar PDF).
- **Sensores IoT:** KPIs e gráficos Plotly sobre solo, nutrientes e irrigação; seleção de fonte na sidebar (Oracle ou CSV), sem fallback silencioso entre origens.
- **Painel IA · soluções:** comparação de **cinco modelos** (irrigação `bomba_fw` e culturas `produtos_agricolas`); tabela de sugestão de bomba para **cinco dias** com `WTH_DAILY_FORECAST` e média das probabilidades dos modelos na última leitura IoT.
- **Previsão do tempo:** indicação simples de irrigação e gráficos Open‑Meteo em Oracle; visibilidade em metros convertida para km na UI.
- **Notebook ML (Ir Além):** modo **Sensores** / **Produtos agrícolas**; espelho do `.ipynb` (EDA, K‑Means em sensores, cinco modelos, matrizes de confusão).
- **Exportar relatório PDF:** gera PDF a partir de **`src/docs/relatorio.md`** (formatação tipo ABNT NBR 14724 para texto + logo FIAP — ver `src/utils/relatorio_pdf.py`).
- **Notebook local:** sidebar na página ML com porta Jupyter configurável e abertura no navegador.

---

## Exemplos visuais do dashboard (capturas estáticas)

As imagens abaixo foram geradas automaticamente a partir do **`src/dados/historico_irrigacao.csv`** de exemplo (sem filtros da sidebar — a interface interativa pode diferir um pouco quando há filtros aplicados).

**Regenerar os PNG:**

```bash
pip install -r requirements.txt   # inclui kaleido para exportação Plotly

# Previsão do tempo (forecast_01 ... forecast_08)
python scripts/export_readme_forecast_figures.py

# Análise para IA (weather_01 ... weather_07)
python scripts/export_readme_analysis_figures.py

# IoT / sensores (readme_01 ... readme_14)
python scripts/export_readme_iot_figures.py

# Notebook ML (notebook_ml_01 ... notebook_ml_09)
python scripts/export_readme_notebook_ml_figures.py

# Painel IA · soluções (painel_ia_01 ... painel_ia_10 — requer Oracle para a fig. 10)
python scripts/export_readme_painel_solucoes_ia_figures.py

# Recomendador Inteligente de Cultura — demo animada (GIF) + hero PNG
python scripts/export_readme_recomendador_demo.py
```

### 🌱 Recomendador Inteligente de Cultura — solução de IA em destaque

> **A cereja do bolo do Painel IA · soluções.** Combina **dados de solo (N · P · K)**, **leituras IoT em tempo real** (temperatura · umidade · pH) e a **previsão meteorológica de 5 dias** (chuva acumulada) num único modelo Random Forest treinado sobre **2 200 amostras agrícolas** e **22 culturas**. Em segundos devolve a **cultura mais adequada**, o **top‑5 com probabilidade calibrada**, um **radar perfil‑ideal × solo‑atual** e a **lista de ajustes** (deltas) necessários para se aproximar do ideal.
Observação: O gif apresentado neste documento é uma simulação que não representa integralmente e fielmente a execução do código, apenas simula um resultado semelhante.

<p align="center">
  <img src="assets/readme/painel_ia_recomendador_demo.gif" alt="Demonstração animada do Recomendador Inteligente de Cultura" width="780"/>
</p>

<p align="center"><i>Fluxo simulado da aba <b>Culturas</b> em <code>painel_solucoes_ia.py</code> — entrada IoT + clima → 5 modelos comparados → Top‑5 + radar → recomendação final.</i></p>

**Por que é a cereja do bolo:**

- 🧠 **5 modelos competindo** (Reg. Logística, Random Forest, Gradient Boosting, k‑NN, Naive Bayes); o melhor por **F1 ponderado** vence e é usado em produção.
- 🛰️ **Integra o IoT real** do projeto (`SENSORES_FARMTECH`) — a média/mediana das últimas leituras pré‑preenche o formulário do recomendador.
- 🌦️ **Conectado ao clima** — o campo *chuva* sugere automaticamente a **soma da precipitação prevista para 5 dias** (`WTH_DAILY_FORECAST`).
- 📊 **Saída acionável**, não JSON cru:
    - Top‑5 culturas com **barras de probabilidade**.
    - **Radar** comparando o perfil ideal da cultura recomendada com o solo atual.
    - **Tabela de ajustes** (delta absoluto e relativo por nutriente/condição) para o agrónomo.
- ⚡ **Cache** com `st.cache_resource(ttl=600)` — primeiro carregamento treina os 5 modelos; subsequentes são instantâneos.

**Hero (frame final do fluxo, igual ao que aparece no dashboard):**

![Recomendador Inteligente — hero](assets/readme/painel_ia_recomendador_hero.png)

**Reproduzir no dashboard:** `python run.py` ▸ **Ir além** ▸ **Painel IA · soluções** ▸ aba **Culturas** (o Recomendador é a primeira secção).

### 💧 Sugestão de irrigação — previsão de ligação da bomba (5 dias)

Segunda solução de IA no mesmo painel (**`painel_solucoes_ia.py`**, secção **«2) Sugestão de irrigação — próximos 5 dias»**). Cruza **previsão meteorológica diária** (`WTH_DAILY_FORECAST`, alimentada pela API Open-Meteo) com a **tendência dos cinco modelos de ML** treinados sobre o histórico IoT da Fase 2.

**Objetivo:** apoiar a decisão de **ligar ou manter desligada** a bomba (`bomba_fw`: 0 = desligada, 1 = ligada) para cada um dos **próximos 5 dias**.

**Entradas**

| Fonte | Dados usados |
|-------|----------------|
| Clima (Oracle) | Prob. máxima de chuva no dia, precipitação prevista (mm), temperatura máxima |
| IoT (Oracle ou CSV) | Umidade do solo na **última leitura** |
| Modelos ML (separador *Irrigação · bomba_fw*) | Média de **P(bomba ligada)** dos 5 algoritmos na última leitura (Reg. Logística, Random Forest, Gradient Boosting, k-NN, Naive Bayes) |

**Legenda das sugestões**

| Sugestão | Significado |
|----------|-------------|
| **Ligada** | Tendência a ligar a irrigação (ex.: tempo seco e modelos favorecem ON) |
| **Desligada** | Manter a bomba desligada (ex.: chuva prevista no dia) |
| **Rever** | Confirmar no campo (solo, cultura) antes de decidir |

**Métricas exibidas no topo:** temperatura prevista agora, humidade do ar, probabilidade e mm de chuva na hora corrente.

**Barra de resumo:** *«Modelos (última leitura IoT): em média, tendem a ligar / não ligar a bomba (probabilidade média: X%)»* — sintetiza os cinco classificadores treinados com `umidade`, `temp_c`, `ph_corr`, `n`, `p`, `k`.

**Requisito:** executar **`python run.py`** para a API popular `WTH_DAILY_FORECAST` (sem dados diários, a tabela dos 5 dias fica vazia).

**Reproduzir:** `python run.py` ▸ **Ir além** ▸ **Painel IA · soluções** — role até à secção **2)** (abaixo da comparação de modelos).

![Sugestão de irrigação — próximos 5 dias](assets/readme/painel_ia_10_irrigacao_sugestao_5_dias.png)

> Regenerar figura: `python scripts/export_readme_painel_solucoes_ia_figures.py` (requer Oracle + API ativos).

**Complemento:** na página **Previsão do tempo** (`forecast.py`), há sugestão imediata para a **hora atual** com base em chuva, probabilidade e UV.

---

### Painel IA · soluções (`painel_solucoes_ia.py`)

Figuras em `assets/readme/painel_ia_*.png` (regenerar com o script acima). A imagem **10** (sugestão de irrigação para 5 dias) depende de **`WTH_DAILY_FORECAST`** preenchido (API **`python run.py`**). A aba **Culturas** foi redesenhada e agora cobre matriz de confusão multiclasse, importância das variáveis, métricas por cultura e o **Recomendador inteligente** — destacado na secção acima com demo animada.

**Aba Irrigação (`bomba_fw`)**

| Comparação bomba_fw (5 modelos) | Matriz de confusão (melhor modelo) |
|:---:|:---:|
| ![Painel IA — barras bomba](assets/readme/painel_ia_01_bomba_fw_comparacao_modelos.png) | ![Painel IA — matriz](assets/readme/painel_ia_02_bomba_fw_matriz_confusao.png) |

| P(bomba ligada) por modelo (última leitura) | Comparação culturas (5 modelos · multiclasse) |
|:---:|:---:|
| ![Painel IA — probs bomba](assets/readme/painel_ia_03_bomba_fw_prob_ultima_leitura.png) | ![Painel IA — barras culturas](assets/readme/painel_ia_04_culturas_comparacao_modelos.png) |

**Aba Culturas (`Atividade_Cap10_produtos_agricolas.csv`) — redesenhada**

| Matriz de confusão multiclasse (melhor modelo) | Importância das variáveis (melhor modelo) |
|:---:|:---:|
| ![Painel IA — matriz culturas](assets/readme/painel_ia_05_culturas_matriz_confusao.png) | ![Painel IA — importância features](assets/readme/painel_ia_06_culturas_feature_importance.png) |

| Métricas por cultura (precisão · recall · F1) | Recomendador · top 5 culturas (perfil mediano) |
|:---:|:---:|
| ![Painel IA — métricas por classe](assets/readme/painel_ia_07_culturas_metricas_por_classe.png) | ![Painel IA — recomendador top 5](assets/readme/painel_ia_08_culturas_recomendador_top5.png) |

| Radar · perfil ideal vs perfil mediano (cultura recomendada) | Sugestão de irrigação · 5 dias |
|:---:|:---:|
| ![Painel IA — radar perfil](assets/readme/painel_ia_09_culturas_radar_perfil.png) | ![Painel IA — 5 dias](assets/readme/painel_ia_10_irrigacao_sugestao_5_dias.png) |

### Evidências Oracle (entrega obrigatória)

As etapas de importação via SQL Developer e validação da tabela no Oracle estão documentadas com prints reais abaixo:

| Seleção do arquivo | Mapeamento de colunas |
|:---:|:---:|
| ![Importação passo 1](assets/rel/2026-05-05%2010_53_39-Oracle%20SQL%20Developer_1.png) | ![Importação passo 4](assets/rel/2026-05-05%2010_54_52-Oracle%20SQL%20Developer_4.png) |

| Conclusão da importação | Consulta final da tabela |
|:---:|:---:|
| ![Importação passo 7](assets/rel/2026-05-05%2010_55_43-Oracle%20SQL%20Developer_7.png) | ![Importação passo 8](assets/rel/2026-05-05%2010_55_57-Oracle%20SQL%20Developer%20_%20Tabela%20RM571375.SENSORES_FARMTECH@fiap_8.png) |

### Dashboard de previsão do tempo

O script `scripts/export_readme_forecast_figures.py` exporta os gráficos da página **Previsão do Tempo**:

- `forecast_01_temp_sensacao_precip_horaria.png`
- `forecast_02_humidade_horaria.png`
- `forecast_03_probabilidade_chuva_horaria.png`
- `forecast_04_vento_horario.png`
- `forecast_05_pressao_horaria.png`
- `forecast_06_amplitude_termica_diaria.png`
- `forecast_07_precipitacao_diaria_prob_max.png`
- `forecast_08_vento_uv_diario.png`

| Temp./sensação/precipitação por hora | Humidade por hora |
|:---:|:---:|
| ![Previsão horária](assets/readme/forecast_01_temp_sensacao_precip_horaria.png) | ![Humidade horária](assets/readme/forecast_02_humidade_horaria.png) |

| Probabilidade de chuva | Vento por hora |
|:---:|:---:|
| ![Probabilidade de chuva](assets/readme/forecast_03_probabilidade_chuva_horaria.png) | ![Vento horário](assets/readme/forecast_04_vento_horario.png) |

| Pressão ao nível do mar | Amplitude térmica diária |
|:---:|:---:|
| ![Pressão](assets/readme/forecast_05_pressao_horaria.png) | ![Amplitude térmica](assets/readme/forecast_06_amplitude_termica_diaria.png) |

| Precipitação diária + probabilidade máxima | Ventos e UV por dia |
|:---:|:---:|
| ![Precipitação diária](assets/readme/forecast_07_precipitacao_diaria_prob_max.png) | ![Ventos e UV](assets/readme/forecast_08_vento_uv_diario.png) |

### Dashboard de análise para IA (meteorologia)

O script `scripts/export_readme_analysis_figures.py` lê os dados Oracle (`WTH_*`) e exporta automaticamente todas as figuras da página **Análise para IA (meteorologia)** para `assets/readme/`:

- `weather_01_previsao_24h_temp_chuva.png` — linha de temperatura/sensação e barras de chuva (24h).
- `weather_02_umidade_24h.png` — área de umidade prevista nas próximas 24h.
- `weather_03_prob_chuva_24h.png` — barras de probabilidade de chuva (24h).
- `weather_04_amplitude_termica_7d.png` — faixa de temperatura mínima e máxima em 7 dias.
- `weather_05_serie_mensal_temperatura_precip.png` — série mensal com temperatura e precipitação total.
- `weather_06_correlacao_variaveis.png` — matriz de correlação (Pearson) das variáveis climáticas.
- `weather_07_vento_por_hora.png` — padrão médio de vento por hora do dia.

| Previsão 24h (temperatura/sensação/chuva) | Umidade 24h |
|:---:|:---:|
| ![Previsão 24h](assets/readme/weather_01_previsao_24h_temp_chuva.png) | ![Umidade 24h](assets/readme/weather_02_umidade_24h.png) |

| Probabilidade de chuva 24h | Amplitude térmica 7 dias |
|:---:|:---:|
| ![Probabilidade de chuva 24h](assets/readme/weather_03_prob_chuva_24h.png) | ![Amplitude térmica 7 dias](assets/readme/weather_04_amplitude_termica_7d.png) |

| Série mensal (temperatura e precipitação) | Correlação de variáveis climáticas |
|:---:|:---:|
| ![Série mensal](assets/readme/weather_05_serie_mensal_temperatura_precip.png) | ![Correlação clima](assets/readme/weather_06_correlacao_variaveis.png) |

| Vento por hora do dia |
|:---:|
| ![Vento por hora](assets/readme/weather_07_vento_por_hora.png) |

### Dashboard IoT e notebook ML

Os blocos abaixo mantêm as capturas do módulo IoT e do notebook, já documentadas no projeto.

Geração automática (por script, a partir do código atual):

- IoT: `scripts/export_readme_iot_figures.py` (gera `assets/readme/readme_*.png`)
- Notebook ML: `scripts/export_readme_notebook_ml_figures.py` (gera `assets/readme/notebook_ml_*.png`)

### Vista geral (primeira linha do painel)

| Distribuição da umidade do solo | Temperatura × umidade |
|:---:|:---:|
| ![Histograma da umidade do solo](assets/readme/readme_01_umidade.png) | ![Dispersão temperatura e umidade por estado da bomba](assets/readme/readme_02_dispersao.png) |

### Três vistas complementares (temperatura, umidade e bomba)

| Umidade por estado da bomba | Caixa — umidade | Caixa — temperatura |
|:---:|:---:|:---:|
| ![Histogramas de umidade sobrepostos](assets/readme/readme_03a_umidade_por_bomba.png) | ![Diagrama de caixa da umidade](assets/readme/readme_03b_box_umidade.png) | ![Diagrama de caixa da temperatura](assets/readme/readme_03c_box_temperatura.png) |

### pH, irrigação, NPK e correlação

| Distribuição do pH | Proporção irrigação | Nutrientes NPK (0 vs 1) |
|:---:|:---:|:---:|
| ![Histograma do pH](assets/readme/readme_04_ph.png) | ![Pizza irrigação](assets/readme/readme_05_irrigacao.png) | ![Barras NPK](assets/readme/readme_06_npk.png) |

| Matriz de correlação (Pearson) |
|:---:|
| ![Mapa de calor de correlação entre sensores](assets/readme/readme_07_correlacao.png) |

### Nutrientes N, P, K (secção completa da página IoT)

| Média NPK por irrigação | Perfis NPK |
|:---:|:---:|
| ![Média NPK por irrigação](assets/readme/readme_08_npk_media_por_irrigacao.png) | ![Perfis NPK](assets/readme/readme_09_npk_perfis.png) |

| Série temporal NPK | Heatmap irrigação x perfil |
|:---:|:---:|
| ![Série temporal NPK](assets/readme/readme_10_npk_serie_temporal.png) | ![Heatmap NPK](assets/readme/readme_11_npk_heatmap_perfil_irrigacao.png) |

| Pizza N | Pizza P | Pizza K |
|:---:|:---:|:---:|
| ![N pizza](assets/readme/readme_12_n_pizza.png) | ![P pizza](assets/readme/readme_13_p_pizza.png) | ![K pizza](assets/readme/readme_14_k_pizza.png) |

### Notebook Jupyter (`Edemir_RM571375_fase3_cap1.ipynb`) — Matplotlib / Seaborn

As figuras abaixo reproduzem **célula por célula** os gráficos gerados no notebook (Parte A com sensores **e** dados de cultura, Parte B com `Atividade_Cap10_produtos_agricolas.csv` e as 7 variáveis: N, P, K, temperatura, umidade, pH, chuva). Regenerar com `python scripts/export_readme_notebook_ml_figures.py`.

**Parte A — Sensores Fase 2 (bomba)**

| Umidade | Temperatura × umidade (bomba) | pH |
|:---:|:---:|:---:|
| ![Histograma umidade](assets/readme/notebook_ml_01_histograma_umidade.png) | ![Temp × umidade](assets/readme/notebook_ml_02_temp_umidade_bomba.png) | ![pH](assets/readme/notebook_ml_03_ph.png) |

| Proporção irrigação | Médias NPK por bomba | Correlações |
|:---:|:---:|:---:|
| ![Pizza irrigação](assets/readme/notebook_ml_04_pizza_irrigacao.png) | ![NPK médias](assets/readme/notebook_ml_05_npk_medias.png) | ![Heatmap correlação](assets/readme/notebook_ml_06_correlacoes.png) |

| K-Means (k=3): temperatura × umidade | Comparação dos cinco modelos | Matriz de confusão (melhor modelo) |
|:---:|:---:|:---:|
| ![Clusters K-Means](assets/readme/notebook_ml_07_kmeans_clusters.png) | ![Barras modelos](assets/readme/notebook_ml_08_comparacao_modelos.png) | ![Matriz confusão](assets/readme/notebook_ml_09_matriz_confusao.png) |

**Parte A 3.b — Dados de cultura reais (`Atividade_Cap10_produtos_agricolas.csv`)**

Apresentados em paralelo aos sensores, substituindo a tabela de referência fictícia "Milho/Soja/Tomate" por valores **observados** no CSV.

| Distribuição de classes | Perfil real por cultura (heatmap das médias) | Temperatura × umidade por cultura |
|:---:|:---:|:---:|
| ![Distribuição culturas](assets/readme/notebook_ml_10_culturas_distribuicao.png) | ![Perfil real](assets/readme/notebook_ml_11_culturas_perfil_real.png) | ![Temp × umidade culturas](assets/readme/notebook_ml_12_culturas_temp_umidade.png) |

**Parte B — Produtos agrícolas (multiclasse, alvo `label`)**

EDA com ≥5 gráficos cobrindo as 7 variáveis da atividade, perfil das 3 culturas mais frequentes, cinco modelos distintos e matriz de confusão multiclasse.

| Distribuição das culturas | Histograma da umidade | Temperatura × umidade por cultura |
|:---:|:---:|:---:|
| ![Distribuição B](assets/readme/notebook_ml_13_partB_distribuicao_culturas.png) | ![Hist umidade B](assets/readme/notebook_ml_14_partB_histograma_umidade.png) | ![Temp × umidade B](assets/readme/notebook_ml_15_partB_temp_umidade_por_cultura.png) |

| N por cultura | pH por cultura | Chuva (mm) por cultura |
|:---:|:---:|:---:|
| ![Box N](assets/readme/notebook_ml_16_partB_box_n.png) | ![Box pH](assets/readme/notebook_ml_17_partB_box_ph.png) | ![Box chuva](assets/readme/notebook_ml_18_partB_box_chuva.png) |

| Correlação (7 variáveis) | Perfil ideal — top 3 culturas | Comparação 5 modelos | Matriz de confusão multiclasse |
|:---:|:---:|:---:|:---:|
| ![Correlação B](assets/readme/notebook_ml_19_partB_correlacoes.png) | ![Perfil top3](assets/readme/notebook_ml_20_partB_perfil_top3.png) | ![Comparação B](assets/readme/notebook_ml_21_partB_comparacao_modelos.png) | ![Matriz B](assets/readme/notebook_ml_22_partB_matriz_confusao.png) |

---

## Machine Learning

| Onde | Conteúdo |
|------|-----------|
| **Notebook** `src/ml/Edemir_RM571375_fase3_cap1.ipynb` | **Parte A:** sensores Oracle/CSV , EDA , K‑Means (k=3) em **`umidade` · `temp_c` · `ph_corr`**, cinco classificadores para **`bomba_fw`**. **Parte B:** **`Atividade_Cap10_produtos_agricolas.csv`** (N, P, K, temperatura, umidade, pH, chuva, label), multiclasse com cultura **`label`**, EDA (≥5 gráficos), perfil de culturas, cinco algoritmos distintos, comparação de métricas. |
| **Dashboard** · *Notebook ML (Ir Além)* | **`notebook_ml.py`** — seletor Sensores / Produtos; visualizações Plotly alinhadas ao notebook. |
| **Painel IA · soluções** | **`painel_solucoes_ia.py`** — mesmos cinco modelos em duas abas (irrigação e culturas) + tabela de **cinco dias** (clima × IA). |

- **Alvo (`y`) — sensores:** **`bomba_fw`**; na Oracle **`BOMBA_FW`** (0/1); esquemas legados **`IRRIGACAO`** com mapeamento em **`iot.py`**.  
- **`X` — sensores:** **`umidade`**, **`temp_c`**, **`ph_corr`**, **`N`**, **`P`**, **`K`**.  
- **Alvo (`y`) — produtos agrícolas:** **`label`** (cultura). **`X`:** **`N`**, **`P`**, **`K`**, **`temp_c`** (temperatura), **`umidade`** (humidity), **`ph_corr`** (pH) e **`chuva`** (rainfall), lidas de `src/dados/Atividade_Cap10_produtos_agricolas.csv`.

---

## SQL no Oracle

- **`src/sql/consultas.sql`** — exemplos para **previsão do tempo** (`WTH_*`) e para **`SENSORES_FARMTECH`** (agregações por **`BOMBA_FW`**, contagens, leituras condicionais). Cliente sugerido: SQL Developer.  
- **`src/sql/createtable.sql`** — DDL das tabelas **clima** + **`SENSORES_FARMTECH`** (colunas **`TEMP_C`**, **`PH_CORR`**, **`BOMBA_FW`**, **`N`/`P`/`K`**, …).

---

## Histórico de versões

**Marcador de estado do repositório:** incrementa‑se **`PATCH`** (**`1.0.x`**) quando se documenta ou ajusta o projeto sem alterar o âmbito principal da disciplina (README, navegação, alinhamento de pastas ou pequenas correções nos painéis). **`MINOR`** reserva‑se para blocos funcionais novos perceptíveis; **`MAJOR`** para mudanças de contrato forte (por exemplo formato de dados ou ruptura da API).

| Versão | Data (ref.) | Resumo das mudanças |
|--------|-------------|---------------------|
| **1.0.21** | 2026‑05‑05 | Página **Exportar relatório PDF**; `fpdf2` + `src/utils/relatorio_pdf.py` (ABNT‑like + logo FIAP). |
| **1.0.20** | 2026‑05‑05 | README: mapeamento às entregas FIAP; figuras **Painel IA** e script `export_readme_painel_solucoes_ia_figures.py`. |
| **1.0.19** | 2026‑05‑05 | Iteração README com barema em tabela. |
| **1.0.18** | 2026‑05‑05 | Painel IA: tabela de irrigação **5 dias**; UX de previsão (visibilidade em km). |
| **1.0.17** | 2026‑05‑05 | **Painel IA · soluções** refeito (comparativos + irrigação × tempo; sem rubrica no dashboard). |
| **1.0.16** | 2026‑05‑05 | Barema no topo do README (iteração). |
| **1.0.15** | 2026‑05‑05 | Jupyter reestruturado para espelhar **`notebook_ml.py`**. |
| **1.0.14** | 2026‑05‑05 | Checklist de entregas FIAP; sugestões de irrigação em **`forecast.py`**; ML com **`Atividade_Cap10_produtos_agricolas.csv`**. |
| **1.0.13** | 2026‑05‑05 | Capturas do README sincronizadas com os dashboards atuais: novos scripts de export para **Previsão** e **Análise**, ampliação das capturas IoT para incluir toda a secção NPK e remoção do script meteorológico legado. |
| **1.0.12** | 2026‑05‑05 | **`run.py`** na raiz: arranque conjunto da API (**uvicorn**) e do **Streamlit**; README com fluxo recomendado. |
| **1.0.11** | 2026‑05‑05 | README alinhado à árvore real **`src/api`**, **`src/frontend`** e **`pages/`**; navegação **Entrega** / **Ir além**; remoção de referências obsoletas a scripts ou pastas inexistentes (`src/dashboard`, `generate_fase3_ml_notebook.py`, `farmtech_launch.py`); política de versão e contratos README revistos. |
| **1.0.10** | 2026‑05‑03 | Oracle: **`IRRIGACAO`** como **`NUMBER(1)`** (0/1); `consultas.sql` e loaders alinhados; README com contratos de tipo (CSV vs Oracle). Normalização de `irrigacao` legacy em texto. |
| **1.0.9** | 2026‑05‑03 | Ajustes à integração Jupyter com o painel Streamlit (iterações anteriores de launcher na raiz). |
| **1.0.8** | 2026‑05‑03 | README: fluxo Jupyter + Streamlit e organização `src/`; variáveis `.env`; checkpoints Jupyter no `.gitignore`. |
| **1.0.7** | 2026‑05‑03 | Variáveis de ambiente experimentais para arranque automático do Jupyter (supersedido pelo fluxo documentado na **1.0.11**). |
| **1.0.6** | 2026‑05‑03 | Simplificação da sidebar Jupyter (ações de abrir notebook). |
| **1.0.5** | 2026‑05‑03 | Esforço anterior de launcher unificado na raiz (múltiplos processos). |
| **1.0.4** | 2026‑05‑03 | Notebook Ir Além **`src/ml/Edemir_RM571375_fase3_cap1.ipynb`**; dependências **`notebook`** e **`ipykernel`**. |
| **1.0.3** | 2026‑05‑03 | Secção **Exemplos visuais** (`assets/readme/`); exportação Plotly (**kaleido**). |
| **1.0.2** | 2026‑05‑03 | Origem CSV/Oracle na **sidebar**; CSV em **`src/dados/`** primeiro; `paths.py`; README: **Arquitetura de dados** (Fase 2 / IoT + caminhos). |
| **1.0.1** | 2026‑05‑03 | Modularização do dashboard (estrutura antecedente à migração para **`src/frontend`**). |
| **1.0.0** | 2026‑05‑02 | Entrega consolidada FIAP: launchers na raiz, CSV + Oracle com **nitrogenio**, filtros temporais, gráficos NPK, modelo `.env`, teste único Oracle, ML em `.py`. |
| **0.1.0** | *antes de 2026‑05* | Protótipos e entregáveis intermediários antes da linha **`1.x`**. |

---

## Controle de versão (Git) e dados

- **Branches:** usar `main` como ramo principal e histórico linear do trabalho do grupo.
- **Segredos:** não versionar `.env`, senhas, chaves nem credenciais reais — apenas exemplos ou *placeholders* seguros.
- **CSV:** pelo `.gitignore`, em geral só **`src/dados/historico_irrigacao.csv`** acompanha o clone como exemplo versionado.
- **`.gitattributes`:** a regra `* text=auto` ajuda a normalizar quebras de linha entre Windows e Linux em equipes mistas.
- **Commits e pull requests:** mensagens objetivas em português.

Se o repositório incluir **`.github/problem-report.md`**, pode servir de modelo para reporte de incidentes no GitHub (FIAP).

---

## Resolução de problemas

| Sintoma | Verificação sugerida |
|---------|----------------------|
| `ModuleNotFoundError: streamlit` | `pip install -r requirements.txt` no ambiente ativo. |
| `python app.py` não abre o browser | Esperado: `app.py` só reexporta o módulo Streamlit. Use **`python run.py`** (API + UI) ou `streamlit run app.py` / `streamlit run src/frontend/app.py`. |
| Porta 8000 ou 8501 ocupada | Feche o outro processo ou execute `python run.py --api-port … --streamlit-port …`. |
| Mudanças no CSV não aparecem de seguida | No projeto atual, a fonte padrão é Oracle; CSV é fallback. Use o botão de atualização na página ou limpe cache para recarregar. |
| Pip tenta compilar C em Windows | Os pins da raiz favorecem *wheels*: **`python -m pip install --upgrade pip`** antes de reinstalar. |
| Teste único ao Oracle sempre falhar | Credenciais **`ORACLE_USER` / `ORACLE_PASS` / `ORACLE_DSN`**, firewall/VPN e serviço Oracle conforme FIAP. |
| Jupyter não inicia a partir do painel | Instalar `notebook` e `ipykernel`; confirmar porta livre na sidebar; ou iniciar manualmente: `jupyter notebook src/ml/Edemir_RM571375_fase3_cap1.ipynb`. |
| **404** no Jupyter (`/tree/…`) | Verificar URL, token e porta; na página **Notebook ML**, usar **Abrir notebook no navegador** após o servidor responder na porta indicada. |
| Histórico com uma única etiqueta **`bomba_fw`** | modelos binários precisam de duas classes; recolha mais períodos ligado/desligado. |

---

## Documentação complementar

**Outros ficheiros:**

| Artigo | Notas |
|--------|-------|
| **`run.py`** | Orquestra **uvicorn** + **Streamlit**; ver **Como executar** · *Arranque integrado*. |
| `document/ai_project_document_fiap.md` | (Se existir no clone) artefactos académicos de IA FIAP. |
| `config/readme.md`, `scripts/readme.md`, `src/readme.md` | (Opcional) notas por pasta. |
| `assets/logo-fiap.png` | Identidade institucional FIAP. |
| `assets/readme/*.png` · `*.gif` | Capturas: `readme_*.png` (IoT), `forecast_*.png`, `weather_*.png`, `notebook_ml_*.png`, `painel_ia_*.png` (Painel IA), **`painel_ia_recomendador_demo.gif`** + `painel_ia_recomendador_hero.png` (Recomendador inteligente). |
| `src/utils/relatorio_pdf.py` | Conversão **`src/docs/relatorio.md`** → PDF (uso na página **Exportar relatório PDF**). |
| `scripts/export_readme_forecast_figures.py` | Gera `forecast_*.png` com os gráficos da página Previsão do Tempo. |
| `scripts/export_readme_analysis_figures.py` | Gera `weather_*.png` com os gráficos da página Análise para IA (meteorologia). |
| `scripts/export_readme_painel_solucoes_ia_figures.py` | Gera `painel_ia_*.png` a partir da lógica do Painel IA. |
| `scripts/export_readme_recomendador_demo.py` | Gera **`painel_ia_recomendador_demo.gif`** (animação 10 s) e **`painel_ia_recomendador_hero.png`** — cereja do bolo do Painel IA. |

---

## Licença

O **modelo de repositório FIAP / PBL** segue políticas institucionais; licenciamento de materiais públicos (por exemplo **Creative Commons CC BY 4.0**) conforme orientação FIAP.

Este **README**, diagramas/textos **técnicos** e código **FarmTech Solutions** são mantidos pela equipe conforme a disciplina e regulamentos vigentes.
