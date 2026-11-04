# FIAP - Faculdade de Informática e Administração Paulista

> **Integração Fase 7 — INT-02/03:** esta dashboard é a base da aplicação
> integrada. As sete páginas abaixo permanecem preservadas; as páginas 8–12
> acrescentam acesso às Fases 1, 2, 3 e 6. Para iniciar sem simulação automática,
> preparar exclusivamente uma base reconstruída e consultar os testes atuais,
> siga o [README da integração](../../README.md) na raiz. O restante deste
> documento mantém a descrição e os registros próprios da Fase 4.

<p align="center">
  <img src="assets/logo_fiap.webp" alt="FIAP" width="40%">
</p>

<br>

# FarmTech Solutions — Assistente Agrícola Inteligente

**Repositório original — Fase 4:** [https://github.com/jojocamdb/FarmTech-Solutions-Fase4](https://github.com/jojocamdb/FarmTech-Solutions-Fase4)

**Avaliação acadêmica informada pela equipe:** 13,5/15. O feedback recomendou ampliar as previsões para pH e rendimento agrícola e complementar dados simulados com dados reais.

---

## 📹 Vídeos do Projeto

Materiais acadêmicos referenciados no histórico do projeto. Os temas abaixo correspondem às descrições da equipe; o conteúdo e a disponibilidade atual dos vídeos não puderam ser verificados nesta conferência.

| Parte | Descrição | Vídeo |
|:-----:|-----------|-------|
| **1** | Integração de ML com Scikit-Learn e Streamlit em dashboard estático e online para gestores agrícolas | [Assistir](https://youtu.be/iBmst3sGG7I) |
| **2** | Implementação de algoritmos preditivos para sugerir ações futuras de irrigação e manejo agrícola | [Assistir](https://youtu.be/xsXyGMQjZ_0) |
| **3** | **Ir além 1** — Integração dos dados reais ou simulados IoT com o banco de dados | [Assistir](https://youtu.be/tG93NozbL6s) |
| **4** | **Ir além 2** — Dashboard analítico com previsões interativas e visualização online | [Assistir](https://youtu.be/uMGGZbTQKAc) |

As Partes 1 e 4 apontam para o mesmo endereço, também presente no histórico original. Não foi encontrada evidência de um link distinto para a Parte 4 nem de que a repetição seja intencional; os endereços foram preservados. A equipe precisa confirmar a correspondência entre partes e vídeos.

### Detalhamento por etapa

**Parte 1 — Integração de ML com Scikit-Learn e Streamlit**  
Tema registrado: integração do pipeline de Machine Learning (Scikit-Learn) com o dashboard Streamlit e apresentação estática/online para acompanhamento agrícola por gestores. Essa descrição não comprova uma implantação pública atual.

**Parte 2 — Algoritmos preditivos para irrigação e manejo**  
Tema registrado: implementação de modelos preditivos para apoiar ações de irrigação e manejo agrícola com base nos dados processados.

**Parte 3 — Ir além 1: IoT e banco de dados**  
Tema registrado: integração de dados reais ou simulados provenientes de dispositivos IoT com o banco de dados SQLite do projeto. No módulo atual, o fluxo IoT é identificado como simulação acadêmica.

**Parte 4 — Ir além 2: Dashboard analítico interativo**  
Tema registrado: dashboard analítico interativo, reunindo sensores, modelos de ML e recomendações de manejo. A correspondência desse tema ao vídeo repetido permanece não verificada.

---

## 👨‍🎓 Integrantes

- Jocasta de Kacia Bortolacci — RM564730
- Marina Leme Soares — RM570461
- Carlos Magnus Costa Amaral — RM573978
- Georgia Mendes Rocha — RM573281
- Edemir Sufiatti — RM571375

## 👩‍🏫 Professores

### Tutor(a)

- Nicolly Cândida Rodrigues de Souza

### Coordenador(a)

- André Godoi Chiovato

---

## 📜 Descrição

O **FarmTech Solutions** é um Assistente Agrícola Inteligente desenvolvido para a Fase 4 do projeto FarmTech
da FIAP. A solução consolida dados de sensores IoT simulados no Wokwi em fases anteriores
com um pipeline de Machine Learning supervisionado (Scikit-Learn), entregando um dashboard interativo em
Streamlit apoiado por um banco de dados SQLite modelado de forma relacional e normalizada.
O Streamlit foi adotado por estar alinhado à orientação principal de dashboard interativo em Streamlit,
Power BI ou ferramenta similar.

O sistema parte de dois conjuntos de dados utilizados no protótipo: um conjunto de 153 leituras registradas/simuladas no contexto do ESP32/Wokwi (umidade, temperatura, pH, luminosidade, presença de N/P/K e estado da bomba de irrigação) e uma base agronômica de referência com 2.200 amostras de 22 culturas (N, P, K, temperatura, umidade, pH e precipitação). No módulo IoT, N/P/K são indicadores simplificados de presença do protótipo; no modelo de ML, N, P e K são valores numéricos do dataset agrícola usados como features de entrada.

Esses dados alimentam um banco SQLite com cinco tabelas normalizadas (`culturas`, `sensores`, `leituras_sensores`, `amostras_agronomicas`, `previsoes`), com integridade referencial garantida por chaves estrangeiras e consultas parametrizadas, reduzindo significativamente o risco de SQL injection.

Para simular a operação contínua do protótipo, um **scheduler** (APScheduler 3.x) gera novas leituras de sensor
a cada 30 segundos. A geração usa parâmetros aproximados definidos a partir do conjunto de leituras simuladas/registradas do protótipo e mantém a lógica de acionamento da bomba simulando a regra utilizada no firmware do ESP32 (liga quando a umidade cai abaixo do limiar configurado).

O núcleo original mantém **dois modelos de regressão** treinados independentemente: um para
`rainfall` — interpretado como **proxy de necessidade hídrica** da cultura — e outro para `humidity` — a
umidade ambiental esperada. Cada modelo é resultado da comparação entre três algoritmos: `LinearRegression`
(baseline), `Ridge` (com `GridSearchCV` para ajuste do `alpha`) e `RandomForestRegressor`. As features (N, P,
K, temperatura, pH e cultura) passam por um `ColumnTransformer` com `OneHotEncoder` dentro de um `Pipeline`
do Scikit-Learn. Os artefatos e as métricas históricas foram preservados sem retreinamento. A seleção original usou o conjunto de teste e a validação cruzada incluiu esse conjunto; as métricas têm viés de seleção e não demonstram generalização independente. Essa ressalva acompanha os indicadores na interface.

Como evolução separada, foi acrescentado um modelo experimental para estimar pH. A cultura é informada previamente
no formulário; o próprio pH não é utilizado como entrada. A seleção do pipeline ocorre por validação cruzada no
treino, com teste reservado independente e comparação contra baseline. A avaliação do teste ficou em
MAE 0,4279, MSE 0,3625, RMSE 0,6021 e R² 0,3291; o resultado permanece experimental e não tem validação local
de campo. O baseline simples da média por cultura atinge MAE 0,42784 e R² 0,32881: o ganho do Ridge é praticamente nulo frente a essa referência. As entradas devem estar disponíveis no momento da estimativa; a cultura precisa ser conhecida previamente.

O dashboard tem a Home e **sete páginas**: monitoramento
de leituras registradas/simuladas do protótipo ESP32/Wokwi; análise exploratória (heatmaps, distribuições, boxplots e scatter);
pipeline de ML com tabela comparativa, resíduos, feature importance quando aplicável e retreinamento protegido; previsão interativa com formulário validado; recomendações de manejo que cruzam a previsão do modelo com as leituras registradas no banco (indicativos de bomba, ajuste de NPK e correção de pH, sempre com justificativa numérica
explícita); histórico de previsões com exportação em CSV; e uma página de dados oficiais com observações NOAA/USCRN
e INMET, além de histórico de produtividade IBGE/SIDRA. As fontes oficiais são exibidas separadamente das
leituras simuladas e das estimativas de ML.

Uma premissa importante e documentada é que `rainfall` é tratado como **proxy de necessidade hídrica**,
e não como medição direta de lâmina de irrigação aplicada em campo. A série oficial de produtividade é analisada
separadamente; como o teste temporal reservado não superou o baseline de forma suficiente, o sistema não publica
previsões de rendimento. Da mesma forma, reconhece-se
que o dataset de 153 leituras de sensor é pequeno — por isso os modelos de ML são treinados exclusivamente
sobre o dataset agronômico de 2.200 amostras, reduzindo o risco de alta variância associado ao uso de uma
base muito pequena. Essas e outras limitações estão detalhadas em
`document/relatorio.md`.

### Dados reais, simulados e previstos

- **Observações de campo:** cópia local de 8.756 registros horários da NOAA/NCEI USCRN, estação GA Newton 11 SW
  (Georgia, EUA), em 2025 ([arquivo oficial](https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/2025/CRNH0203-2025-GA_Newton_11_SW.txt)).
  Inclui umidade volumétrica do solo em cinco profundidades (m³/m³), além de variáveis meteorológicas. É uma estação
  de referência, não uma propriedade FarmTech.
- **Observações meteorológicas:** 8.713 registros horários do arquivo histórico oficial INMET de 2025, estação
  A701 — São Paulo/Mirante (SP; coordenadas e altitude no arquivo de proveniência; [ZIP oficial](https://portal.inmet.gov.br/uploads/dadoshistoricos/2025.zip)).
  Temperatura, precipitação e umidade relativa do ar não são medições de umidade do solo.
- **Estatística agrícola:** IBGE/SIDRA, [tabela 1612](https://sidra.ibge.gov.br/tabela/1612), variável 112, rendimento médio em kg/ha, cinco culturas.
  A cópia local contém 36 anos nacionais (1990–2025) e recortes municipais de 2023 e 2025. Estatísticas municipais
  não representam uma fazenda individual.
- **Dados simulados:** o dataset acadêmico Cap10 e o fluxo IoT ESP32/Wokwi/APScheduler continuam identificados
  como fontes acadêmicas ou simuladas; não são mesclados às observações oficiais.
- **ISMN:** não foram incorporados arquivos da rede. O acesso/seleção de dados exige ação do usuário na plataforma;
  [página de dados](https://ismn.earth/en/data/) explica a disponibilização do conjunto. A aquisição autenticada
  não é automatizada e o importador de arquivos ISMN ainda não foi implementado. A
  observação NOAA/USCRN foi incorporada como fonte alternativa de medições reais de solo. ISMN permanece ausente;
  não foi autenticado um requisito acadêmico original que obrigue sua incorporação.

As rotinas reproduzíveis de ingestão e validação estão em `src/data_sources.py` e
`scripts/importar_dados_oficiais.py`. Após a ingestão, o dashboard usa apenas cópias locais, sem exigir internet
na demonstração. Os arquivos `*_metadata*.json` registram fonte, consulta/estação, período, unidades, tratamento,
limitações e hashes SHA-256 para rastreabilidade. Na NOAA, sentinelas são tratadas por campo conforme a especificação hourly02 (por exemplo, −9999,0 para temperatura do ar e −99,000 para umidade do solo); três temperaturas ausentes foram corrigidas na cópia derivada, sem imputação nem alteração do número de registros.

### Produtividade oficial e validação temporal

O modelo temporal separado compara regressão linear por ano com persistência do último ano observado, usando
walk-forward para seleção e os cinco anos de 2021–2025 como teste reservado. No teste, o R² foi negativo para
as cinco culturas: arroz −1,714; feijão −0,463; milho −0,094; soja −0,425; cana-de-açúcar −0,933. Como não foi
demonstrada habilidade preditiva suficiente, somente o histórico oficial e as métricas são exibidos; não se
apresentam estimativas futuras como previsões confiáveis.

O **`main.py`** na raiz do projeto centraliza a execução em um **menu interativo** que segue a ordem lógica
do pipeline (ingestão → ML → dashboard), exibe o status de cada etapa e permite rodar o fluxo completo ou
etapas isoladas, tanto pelo menu quanto por argumentos de linha de comando.

---

## 📁 Estrutura de pastas

A estrutura funcional abaixo omite caches e ambientes virtuais. Os nomes agrupados correspondem a arquivos efetivos; `farmtech.db` é criado pela ingestão e não é distribuído como histórico original.

```text
fase4-regressao/
├── main.py
├── README.md, LICENSE, requirements.txt, constraints-f402.txt
├── .gitignore
├── .github/dependabot.yml
├── .streamlit/config.toml
├── config/.env.example
├── assets/logo_fiap.webp
├── document/der.md, relatorio.md
├── scripts/init_db.py, importar_dados_oficiais.py
├── src/
│   ├── atomic_files.py, data_sources.py, validation.py
│   ├── dados/
│   │   ├── Atividade_Cap10_produtos_agricolas.csv, historico_irrigacao.csv
│   │   └── official/  (NOAA, INMET e SIDRA: CSVs e metadados JSON)
│   ├── db/database.py
│   ├── ml/
│   │   ├── train.py, ph_model.py, productivity.py, artifact_security.py
│   │   └── models/  (4 joblib, métricas/metadados JSON, resíduos/previsões CSV)
│   └── frontend/
│       ├── app.py, scheduler.py, feedback.py, assets.py
│       └── pages/  (1_Sensores_IoT, 2_Analise_Exploratoria, 3_Pipeline_ML,
│                   4_Previsao, 5_Recomendacoes, 6_Historico_Previsoes,
│                   7_Dados_Oficiais: arquivos .py)
└── tests/
    ├── test_data_sources.py, test_data_safety.py
    ├── test_db_safety.py, test_scheduler.py
    ├── test_ph_model.py, test_productivity.py, test_model_safety.py
    └── test_frontend_safety.py, test_launcher_safety.py, test_assets_safety.py
```

`atomic_files.py` publica grupos de arquivos com recuperação de falhas; `validation.py` aplica os contratos também fora da interface; `artifact_security.py` verifica procedência, integridade e perfil de execução antes de carregar modelos. Os módulos de frontend centralizam mensagens públicas e a leitura do logotipo verificado.

`.github/dependabot.yml` é configuração preservada do módulo independente, com manifestos em `/`. No consolidado, sua presença nesta subpasta não ativa a automação: a configuração precisa ser avaliada na `.github/` da raiz, apontando para os manifestos da Fase 4. Isso não foi implantado nesta conferência. Consulte a [referência do Dependabot](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#directories-or-directory).

## 🔧 Instalação e execução

Perfil verificado: **Windows, Python 3.11.9, Scikit-Learn 1.6.1 e Streamlit 1.54.0**. Preserve o ambiente anterior e use outro ambiente virtual. `constraints-f402.txt` registra as versões efetivamente testadas, inclusive dependências indiretas. Outros sistemas operacionais e versões exigem nova validação.

```powershell
cd <pasta-do-modulo-fase4>
python -m venv .venv-f402
.\.venv-f402\Scripts\python.exe -m pip install pip==26.2.2 setuptools==84.1.0
.\.venv-f402\Scripts\python.exe -m pip install -r requirements.txt -c constraints-f402.txt
.\.venv-f402\Scripts\python.exe -m pip check
.\.venv-f402\Scripts\python.exe main.py --pipeline
```

O menu continua disponível com `python main.py` no ambiente ativado. O pipeline cria o SQLite **somente quando ausente**, valida os artefatos existentes e abre o dashboard. Um banco inválido exige ação explícita; modelos ausentes, adulterados ou incompatíveis exigem recuperação dos backups verificados. Não há retreinamento automático para substituir os modelos preservados.

| Opção CLI | Comportamento |
|---|---|
| `--pipeline` | Cria a base ausente a partir dos CSVs acadêmicos, verifica os modelos e abre o dashboard. |
| `--ingestao` | Importação explícita: valida os dois CSVs e prepara uma base isolada antes de publicar. |
| `--dashboard` | Verifica banco e modelos antes de iniciar o Streamlit. |
| `--treinar` | Mantido para diagnóstico; a substituição dos artefatos empacotados está bloqueada. |
| `--permitir-rede` | Somente junto a `--dashboard` ou `--pipeline`: habilita escuta em `0.0.0.0`. |
| `--help` | Mostra as opções. Erros de uma operação solicitada retornam código diferente de zero. |

Uma **recarga explícita bem-sucedida** substitui o conteúdo das cinco tabelas, inclusive previsões e leituras adicionais. Antes dela, a base anterior é preservada por backup SQLite em `backups/` ao lado do banco. A publicação usa transação na mesma base, respeitando conexões abertas, journal/WAL e rollback; erros de validação, backup ou publicação preservam o estado anterior. A base gerada dos CSVs não constitui recuperação do histórico ausente da auditoria.

`DB_PATH` pode ser configurado explicitamente; o padrão é `src/db/farmtech.db` em relação ao módulo. Caminhos relativos dessa variável também são ancorados no módulo, independentemente do diretório do consumidor. `config/.env.example` contém os parâmetros públicos; uma configuração local `.env` é opcional e não deve conter dados a distribuir.

### Serviço local, rede e simulação

O padrão é `http://127.0.0.1:8501`, com CORS e proteção XSRF habilitados. `PORT` define **apenas a porta**, um inteiro de 1 a 65535, sem mudar o endereço de escuta. A configuração oculta detalhes de exceções na interface. O launcher controla o processo filho e seu encerramento com Ctrl+C.

A exposição em rede exige a opção explícita `--permitir-rede`. Esse modo não acrescenta autenticação; uma implantação precisa fornecer controle de acesso e transporte protegido na infraestrutura. A implantação pública e a comunicação entre módulos da Fase 7 não fazem parte da validação deste módulo.

O scheduler é compartilhado entre sessões **do mesmo processo** e permite encerramento e reinício. O padrão continua em 30 segundos; os parâmetros estão no exemplo de ambiente. Processos distintos não compartilham essa coordenação: em execução com vários workers, desabilite a simulação com `FARMTECH_SIMULACAO=0` e mantenha um único produtor explicitamente controlado. As leituras são sintéticas.

### Modelos preservados e compatibilidade

Os modelos históricos de chuva/umidade têm referência no commit original `d0a916858590c89ab8812baf1c45d48f923f0566`. O carregamento verifica hashes de referência fixados no código, schema e **440 previsões de referência por alvo**. Os artefatos indicam serialização com Scikit-Learn 1.9.0; seu uso foi restringido ao runtime 1.6.1 que reproduziu essas previsões, com diagnóstico e aviso explícito. Isso é uma mitigação local: a [documentação do Scikit-Learn](https://scikit-learn.org/stable/model_persistence.html) não dá suporte ao carregamento entre versões e não garante resultados para outros dados ou ambientes. O pH foi serializado e validado em 1.6.1.

`joblib` pode executar código ao carregar. Os loaders recusam arquivos que não correspondam às referências verificadas; metadados junto ao modelo não autenticam sua origem. Os hashes no código dependem da integridade da distribuição e não protegem contra a troca conjunta de código e artefatos por alguém com acesso de escrita. Não carregue modelos externos. Recuperação deve usar o backup verificado; substituição dos históricos depende de autorização específica.

O treino direto no diretório empacotado é bloqueado tanto para os históricos quanto para pH. A reprodução científica dos testes usa diretórios temporários; não altera os artefatos distribuídos. As ressalvas metodológicas dos históricos e o caráter experimental do pH acompanham os indicadores da interface.

### Dados oficiais e testes

O dashboard lê as cópias locais, sem exigir conexão durante a apresentação. As atualizações abaixo são operações explícitas sobre arquivos derivados, separadas do SQLite:

```powershell
.\.venv-f402\Scripts\python.exe scripts\importar_dados_oficiais.py --noaa
.\.venv-f402\Scripts\python.exe scripts\importar_dados_oficiais.py --inmet
.\.venv-f402\Scripts\python.exe scripts\importar_dados_oficiais.py --sidra
.\.venv-f402\Scripts\python.exe -m unittest discover -s tests -v
```

`--inmet-zip <caminho>` usa um ZIP oficial já obtido; `--todos` solicita as três fontes. Identificadores, estação/localização, unidades, datas, timestamps, schemas e valores são validados. CSVs e metadados de cada conjunto são publicados com trava, journal e recuperação; leitores do módulo usam o mesmo protocolo. Essa garantia pressupõe arquivos locais e leitores cooperantes, não edição concorrente por programas externos ou armazenamento em rede entre máquinas.

O relatório [document/relatorio.md](document/relatorio.md) registra a matriz A01–A21, os testes, as métricas reproduzidas, os backups e as ressalvas de segurança. A suíte usa fixtures e bancos temporários, incluindo falhas de conexão, corrupção, rollback, sessões concorrentes, interface e CLI. A reconstrução de um banco de demonstração é uma operação de instalação, separada dos testes.

Streamlit foi atualizado para corrigir os alertas aplicáveis, em especial o [problema de SSRF no Windows corrigido em 1.54.0](https://github.com/streamlit/streamlit/security/advisories/GHSA-7p48-42j8-8846). Permanecem alertas de Pillow 12.3.0 incompatíveis com atualização para 13 no perfil atual do Streamlit. A interface decodifica somente o logotipo WebP de bytes previamente verificados, sem upload de imagens; a ressalva e seus limites estão no relatório. Não há garantia absoluta de segurança.

A licença do projeto não substitui as condições das fontes externas. Preserve a atribuição NOAA/NCEI, INMET e IBGE/SIDRA e os metadados. Não foi estabelecida autorização irrestrita de redistribuição para todo arquivo externo; confira as condições institucionais antes de redistribuir conjuntos fora do uso previsto.

### Higiene e rastreabilidade da entrega

Os ambientes `.venv/` e `.venv-f402/` e caches podem existir localmente, mas são excluídos pelas regras do `.gitignore`; não compõem os arquivos de código, dados e documentação a distribuir. As regras também cobrem SQLite local e auxiliares, segredos, logs, temporários, backups operacionais e staging de recuperação. Arquivos necessários à reprodução — quatro modelos, datasets, metadados, métricas, resíduos, scripts e testes — permanecem elegíveis. Antes de qualquer limpeza de staging ou backups, preserve o que for necessário à recuperação.

Uma regra de exclusão não apaga arquivos nem retira arquivos já rastreados, conforme a [documentação do Git](https://git-scm.com/docs/gitignore). As evidências e cópias de recuperação das auditorias são mantidas em diretório local externo ao módulo; não fazem parte da árvore resumida da entrega.

O relatório técnico relaciona implementações, achados A01–A21, testes, evidências e limitações. Os 124 testes aprovados pertencem à F4-02; a F4-03 conferiu documentação, estrutura e integridade, sem repetir a suíte funcional. O enunciado acadêmico original e uma confirmação primária da nota/feedback não estavam disponíveis para conferência: a nota 13,5/15 e as recomendações são atribuídas à equipe.

Os créditos de autoria foram preservados. Os RMs são identificadores acadêmicos pessoais; sua obrigatoriedade na versão pública não foi comprovada. Recomenda-se manter os nomes e submeter a exposição dos RMs à decisão da equipe e à exigência da entrega acadêmica, antes de publicação.

---

## 🗃 Histórico de lançamentos

- **F4-03 — conferência documental em 01/11/2026** (registro de trabalho): nomes e histórico de páginas esclarecidos, árvore e DER corrigidos, vídeos duplicados identificados, referências pessoais de caminhos removidas da documentação e regras de exclusão ampliadas. Código funcional, dados e artefatos científicos preservados.
- **F4-02 — correções auditadas em 01/11/2026** (registro de trabalho, sem novo número de versão): transações SQLite e publicação de dados recuperáveis, validação de entradas/fontes, configuração local segura, dependências testadas, scheduler por processo, diagnóstico dos modelos preservados e mensagens controladas. Matriz e evidências no relatório técnico.
- **F4-01 — evolução acadêmica:** pH experimental, análise temporal de produtividade, fontes oficiais NOAA/INMET/SIDRA e testes iniciais; sem alteração dos artefatos históricos de chuva/umidade.

- 1.1.0 — 15/06/2026
  - Menu interativo no `main.py` com pipeline ordenado (ingestão → ML → dashboard).
  - Atalhos CLI: `--pipeline`, `--ingestao`, `--treinar`, `--dashboard`.
  - Encerramento do Streamlit com Ctrl+C corrigido no Windows.
  - Documentação de execução atualizada no README.

- 1.0.0 — 11/06/2026
  - Dashboard Streamlit com Home e seis páginas funcionais (sete telas). A página de dados oficiais foi acrescentada na F4-01.
  - Banco SQLite normalizado (5 tabelas) com carga dos dois datasets.
  - Pipeline de ML com 3 modelos comparados para 2 targets (rainfall e humidity).
  - Scheduler IoT (APScheduler) com simulação de leituras a cada 30s.
  - Recomendações de manejo baseadas em regras agronômicas simplificadas para fins de protótipo acadêmico.
  - Documentação completa (DER e relatório técnico).

As versões 1.0.0 e 1.1.0 são registros do README histórico, com implementação correspondente em commits de junho de 2026. Na consulta desta conferência, não havia tags ou GitHub Releases; não se atribui número de versão às etapas F4-01, F4-02 ou F4-03.

---

## 📋 Licença

<p>
  <img src="https://licensebuttons.net/l/by/4.0/88x31.png" alt="CC BY 4.0">
</p>

Este projeto FarmTech Solutions foi desenvolvido no contexto acadêmico da FIAP e está licenciado sob
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
