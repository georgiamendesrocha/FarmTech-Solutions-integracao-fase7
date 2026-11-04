# Relatório Técnico — FarmTech Solutions
## Fase 4 — Assistente Agrícola Inteligente

**FIAP — Tecnólogo em Inteligência Artificial**
Base acadêmica: junho de 2026 · Revisão técnica F4-02 e conferência documental F4-03: 01/11/2026

As seções 1–12 consolidam a implementação e a homologação da F4-02. Os resultados de execução nelas descritos pertencem àquela etapa. A seção 13 registra a conferência documental F4-03, sem reexecução da suíte funcional.

---

## 1. Modelagem do Banco de Dados

### Estrutura relacional

O schema SQLite (`farmtech.db`, gerado na instalação) é composto por cinco tabelas normalizadas:

- **culturas** — catálogo de 22 culturas do dataset agronômico.
- **sensores** — cadastro de sensores IoT; permite registrar múltiplos dispositivos.
- **leituras_sensores** — 153 leituras registradas/simuladas do protótipo ESP32/Wokwi na carga inicial; leituras adicionais são sintéticas, geradas pelo APScheduler.
- **amostras_agronomicas** — 2.200 amostras do dataset Cap10, vinculadas às culturas.
- **previsoes** — histórico das previsões registradas via interface.

A separação em tabelas distintas reduz redundância e organiza a integridade referencial por meio de chaves estrangeiras. Na camada de acesso ao banco, o projeto habilita `PRAGMA foreign_keys = ON`, e as operações revisadas utilizam consultas parametrizadas, reduzindo o risco de SQL injection.


### Script de inicialização

`scripts/init_db.py` valida integralmente os dois CSVs antes de construir e verificar uma base isolada. Para uma base existente, cria backup pela API SQLite e publica os conteúdos em transação na mesma base, respeitando conexões e arquivos auxiliares. Uma falha anterior ao commit preserva os registros anteriores. A linha separadora do CSV de irrigação é reconhecida pelo parser. Uma recarga explícita bem-sucedida substitui as cinco tabelas, incluindo o histórico adicional, que permanece no backup. Nenhum SQLite histórico foi recebido ou reconstruído nesta revisão.

---

## 2. Premissas dos Targets de ML

### rainfall — proxy de necessidade hídrica

**Importante:** `rainfall` representa a precipitação pluviométrica histórica associada às condições de cultivo do dataset agronômico. Neste projeto, a variável é usada como proxy para apoiar a análise de necessidade hídrica, mas não corresponde diretamente ao volume de irrigação que deve ser aplicado no campo.

Essa interpretação é uma aproximação prática para fins de protótipo acadêmico. Valores mais altos de `rainfall` podem indicar culturas ou condições historicamente associadas a maior disponibilidade hídrica, mas a decisão de irrigação deve considerar também as leituras dos sensores, a umidade do solo, o estágio da cultura e a validação agronômica local.

### humidity — umidade ambiental esperada

`humidity` representa a umidade relativa do ar associada às condições de cultivo registradas no dataset agronômico, considerando N, P, K, temperatura, pH e cultura. No protótipo, essa previsão é usada como referência comparativa em relação às leituras simuladas dos sensores, apoiando recomendações simplificadas de manejo. A variável não deve ser interpretada como medição em tempo real nem como recomendação agronômica conclusiva.

---

## 3. Metodologia de Machine Learning

### Pipeline Scikit-Learn

Cada target (`rainfall`, `humidity`) tem seu próprio pipeline independente:

```
ColumnTransformer
├── passthrough   → N, P, K, temperatura, pH
└── OneHotEncoder → cultura (22 categorias)
         ↓
    Estimador
```

### Modelos comparados

| Modelo | Tipo | Hiperparâmetros |
|---|---|---|
| LinearRegression | Baseline | — |
| Ridge | Regularização L2 | alpha: [0.1, 1, 10, 100] via GridSearchCV |
| RandomForestRegressor | Ensemble | n_estimators=100, random_state=42 |

### Protocolo de avaliação

- **Split treino/teste:** 80/20, `random_state=42` fixo para reprodutibilidade.
- **Validação cruzada:** K-Fold, k=5, métrica R². Reporta média ± desvio padrão.
- **Métricas no teste:** MAE, MSE, RMSE, R².
- **Análise de resíduos:** gráfico resíduo vs previsto + histograma de resíduos.
- **Feature importance:** exibida apenas quando o modelo selecionado permite esse tipo de interpretação, como no caso do `RandomForestRegressor`. Nos treinamentos em que o modelo selecionado for linear ou regularizado, essa análise não é apresentada como explicação principal.

### Persistência

Os pipelines históricos de chuva e umidade permanecem em `src/ml/models/modelo_<target>.joblib`, com métricas em `src/ml/models/metricas.json`. Esses artefatos aprovados foram preservados sem retreinamento. O script original seleciona o modelo pelo R² do teste e calcula sua validação cruzada sobre a base completa; por isso, os números existentes são mantidos como resultados históricos do protótipo, e não como uma avaliação independente sem viés. Essa limitação não foi corrigida no pipeline original para evitar alterar os resultados aprovados.


---

## 4. Interpretação das Métricas e Limitações

### Limitações conhecidas

1. **Dataset de sensores pequeno:** o CSV de irrigação contém apenas 153 leituras registradas/simuladas do protótipo ESP32/Wokwi.
   Modelos de classificação ou regressão treinados diretamente sobre esses dados teriam alta variância.
   Por isso, o ML é treinado exclusivamente no dataset agronômico Cap10 (2.200 amostras).

2. **Domínio de aplicação:** os modelos foram treinados no dataset acadêmico Cap10; não há evidência primária de validação de campo desse conjunto no módulo. As
   leituras do sensor ESP32 têm faixas de pH e temperatura que podem se afastar da distribuição de
   treino, reduzindo a confiabilidade das previsões nesses extremos.

3. **rainfall como proxy:** a variável-alvo não mede diretamente o volume de irrigação necessário por
   dia — é um indicador baseado em precipitação histórica associada à cultura. Recomendações baseadas
   nesse valor devem ser validadas por agrônomo.

4. **Dados simulados pelo scheduler:** as leituras geradas pelo APScheduler usam parâmetros baseados
   no conjunto de leituras registradas/simuladas do protótipo, mas são sintéticas. Não substituem validação agronômica com medições de campo.

### Interpretação dos resultados do treinamento

Nos artefatos históricos preservados, o modelo `Ridge` consta como selecionado para os dois targets. Para `rainfall`, obteve MAE de aproximadamente 14,35, RMSE de 23,16 e R² de 0,8219. Para `humidity`, obteve MAE de aproximadamente 3,10, RMSE de 4,54 e R² de 0,9617. Esses resultados foram reproduzidos nesta revisão usando os modelos preservados e os 440 exemplos de teste por alvo, sem retreinamento. A reprodução numérica não elimina o viés da seleção original.

A diferença entre `LinearRegression` e `Ridge` foi pequena nos dois casos, o que indica que a regularização L2 trouxe ganho marginal, mas suficiente para ser selecionada pelo critério definido no pipeline. O `RandomForestRegressor`, embora útil como modelo comparativo, apresentou R² inferior para os dois targets neste treinamento.

O desempenho de `humidity` foi mais alto que o de `rainfall`, sugerindo que a umidade apresenta relação mais estável com as variáveis disponíveis no dataset. Já `rainfall` tende a ser mais variável, pois representa precipitação histórica associada às condições da cultura e não um volume direto de irrigação recomendado.

---

## 5. Simulação IoT com APScheduler

O `APScheduler` (versão 3.x, `BackgroundScheduler`) tem instância compartilhada, protegida por lock, entre as sessões do mesmo processo. Os holders são associados ao produtor comum; o encerramento controlado permite reinício e há limpeza em `atexit`. Não existe coordenação entre processos: em múltiplos workers, use `FARMTECH_SIMULACAO=0` nos consumidores e apenas um produtor controlado. A cada 30 segundos, um job gera valores sintéticos com parâmetros baseados no conjunto de leituras registradas/simuladas do protótipo ESP32/Wokwi, considerando média e desvio por variável, e insere os registros na tabela `leituras_sensores`.

A lógica de `bomba_fw` simula o critério utilizado no protótipo: a bomba é acionada quando `umidade < UMIDADE_LIMIAR`, com limiar padrão de 60%. Essa simulação apoia a visualização do fluxo IoT no dashboard, mas não substitui validação agronômica com medições de campo.

---

## 6. Evolução F4-01: estimativa experimental de pH

O pipeline adicional está em `src/ml/ph_model.py`. Utiliza o dataset acadêmico Cap10 (2.200 linhas), com pH como alvo e as entradas `N`, `P`, `K`, temperatura, umidade, precipitação e cultura. O pH é excluído explicitamente das features; a cultura é selecionada previamente pelo usuário no formulário, não inferida a partir do alvo.

- Split estratificado por cultura: 1.760 linhas de treino e 440 de teste, `random_state=42`.
- Seleção por R² médio da validação cruzada estratificada de cinco folds, somente no conjunto de treino.
- Comparação entre baseline da média, `LinearRegression`, `Ridge` e `RandomForestRegressor`.
- Modelo selecionado: `Ridge`, `alpha=1`; R² médio de CV 0,3574.
- Teste reservado: MAE 0,4279; MSE 0,3625; RMSE 0,6021; R² 0,3291. O baseline da média teve MAE 0,5622 e R² −0,0009 no mesmo teste.
- Artefatos: `modelo_ph.joblib`, `modelo_ph_metadata.json`, `metricas_ph.json` e `residuos_ph.csv`; o carregador valida o hash do modelo e as features esperadas.

O resultado supera a média global, mas a referência simples da **média por cultura** obteve MAE 0,4278357606 e R² 0,3288132456 no mesmo teste. O Ridge não demonstra ganho relevante frente a ela (seu MAE é ligeiramente maior). Não há validação agronômica independente nem observações locais de pH pareadas com as mesmas features. A interface e os metadados o classificam como experimental. Não é uma recomendação de correção de solo nem evidência causal de que uma intervenção alterará o pH.

---

## 7. Observações oficiais, ingestão e produtividade

### NOAA/NCEI USCRN — observações de solo

Foi incorporada uma série real da estação GA Newton 11 SW, Georgia, EUA (WBAN 63829; 31,19° N, 84,45° O), referente a 2025 ([arquivo oficial NOAA/NCEI](https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/2025/CRNH0203-2025-GA_Newton_11_SW.txt)). O arquivo horário oficial foi validado e normalizado para **8.756 observações** entre 2025-01-01 01:00 UTC e 2026-01-01 00:00 UTC. São registradas umidades volumétricas em cinco profundidades (m³/m³), temperatura do solo e variáveis meteorológicas. Sentinelas são tratadas por campo conforme a [especificação NOAA hourly02](https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/README.txt): por exemplo, −9999,0 para temperatura do ar e −99,000 para umidade do solo. Medições fora das faixas físicas e observações com flags inválidos são rejeitadas ou mantidas ausentes conforme o campo; não há imputação. A revisão corrigiu três temperaturas −9999 na cópia derivada, antes incluídas indevidamente em médias diárias. A quantidade de linhas foi preservada.

Os dados estão em `src/dados/official/noaa_uscrn_ga_newton_2025.csv`, com fonte, hash do arquivo e hash da cópia normalizada em `noaa_uscrn_ga_newton_2025_metadata.json`. A estação é real, mas está nos Estados Unidos e não representa a propriedade FarmTech; sua umidade volumétrica não é comparável diretamente à escala percentual do protótipo.

### INMET — meteorologia observada

Do [ZIP histórico oficial INMET de 2025](https://portal.inmet.gov.br/uploads/dadoshistoricos/2025.zip) foram selecionados os dados da estação A701 — São Paulo/Mirante (SP; −23,4962888°, −46,6200666°; altitude 785,64 m). O CSV foi interpretado com cabeçalho de metadados, delimitador `;` e decimais com vírgula; sentinelas −9999 e campos vazios permanecem ausentes. A cópia normalizada contém **8.713 observações horárias** entre 2025-01-01 00:00 UTC e 2025-12-31 23:00 UTC. As variáveis são temperatura do ar (°C), precipitação (mm/h) e umidade relativa do ar (%).

Arquivos locais: `inmet_sp_a701_2025.csv` e `inmet_sp_a701_2025_metadata.json`; o metadado registra URLs, nome e SHA-256 do ZIP/CSV selecionado e da cópia local. São observações meteorológicas de estação, não umidade do solo e não necessariamente condições da propriedade do projeto. O dashboard apresenta a agregação diária separadamente.

### IBGE/SIDRA — rendimento médio agregado

A importação reproduzível consulta o IBGE/SIDRA [tabela 1612](https://sidra.ibge.gov.br/tabela/1612), variável 112 (rendimento médio da produção, kg/ha), para arroz, feijão, milho, soja e cana-de-açúcar. Foram preservadas 180 observações anuais nacionais, distribuídas em cinco séries de 1990 a 2025, além de dois recortes municipais de 2023 e 2025 (27.820 registros em cada recorte). CSVs e metadados de cada período ficam em `src/dados/official/`. Ausências oficiais não são imputadas. Estatísticas municipais são separadas dos sensores e não representam rendimento de uma propriedade.

O modelo temporal de `src/ml/productivity.py` usa ano como única variável preditora observável, compara tendência linear e persistência do último ano, seleciona por walk-forward em 2016–2020 e reserva 2021–2025 para teste. Os R² do método selecionado no teste foram: arroz −1,714; feijão −0,463; milho −0,094; soja −0,425; cana −0,933. Como não houve habilidade suficiente frente ao baseline, o dashboard exibe somente histórico e métricas, sem previsão publicada. O pipeline não usa o próprio rendimento como feature e não afirma causalidade. O `modelo_produtividade.joblib` guarda regressões lineares ajustadas por cultura, mesmo quando o método escolhido na avaliação é a persistência. Sua existência não habilita previsão: os consumidores devem respeitar o método selecionado, as métricas e `previsao_disponivel=false` dos artefatos de diagnóstico e usar o carregador validado de previsões.

### ISMN e atualização offline

Não foi importado dado da International Soil Moisture Network (ISMN). A plataforma oficial [disponibiliza informações de acesso e dados](https://ismn.earth/en/data/); a obtenção requer seleção e ação do usuário. O projeto não automatiza autenticação nem contorna restrições, e ainda não há parser ou upload para arquivos ISMN. A alternativa efetivamente incorporada para medições reais de solo é NOAA/NCEI USCRN, com origem e limitações explícitas. **Não há incorporação de ISMN nem mecanismo de importação de seus arquivos; não foi autenticado um requisito acadêmico original que obrigue essa funcionalidade.**

`scripts/importar_dados_oficiais.py` oferece atualização das fontes NOAA, INMET e SIDRA (`--noaa`, `--inmet`/`--inmet-zip`, `--sidra` ou `--todos`). A rotina valida schema, estação, unidades/faixas e registra proveniência. As cópias locais permitem apresentar a página sem conexão; a atualização requer acesso às fontes oficiais. Não foram combinados municípios IBGE, estações externas, observações de solo e leituras simuladas como se fossem uma mesma unidade de campo.

---

## 8. Correções controladas F4-02 e validação

A revisão da Etapa B parte do diagnóstico independente da Etapa A, não das declarações do implementador. Referência arquivada: `auditoria-etapa-a/F4-02_RELATORIO_ETAPA_A.md`; evidências originais em `F4-02-evidencias-etapa-a-final.zip`. Esses caminhos, assim como os caminhos `auditoria-etapa-b/` citados adiante, são relativos ao diretório local externo de evidências `F4-02-20261101`, não à árvore do código. A localização pessoal desse diretório permanece nos manifestos privados de entrega. A nota acadêmica **13,5/15** e o feedback são informações históricas comunicadas pela equipe; não equivalem a validação agronômica nem foram substituídos por uma nova avaliação acadêmica.

O escopo da homologação é o módulo independente em `servicos/fase4-regressao`, no perfil Windows/Python 3.11.9 testado. Não houve alteração das Fases 1–3, substituição de modelos históricos ou publicação de serviços. Os testes utilizaram fixtures, cópias isoladas e SQLite temporário. O SQLite histórico estava ausente e continua ausente; nenhum banco de demonstração foi apresentado como histórico recuperado.

### Arquivos alterados e finalidade

| Arquivos | Correções e justificativa |
|---|---|
| `scripts/init_db.py`, `src/db/database.py` | A01/A07/A08/A11/A13/A14/A19: validação prévia, staging e backup SQLite, publicação transacional sem apagar a base, rollback, conexão fechada, contratos, ordenação UTC com desempate e gravação conjunta de previsões. |
| `src/data_sources.py`, `scripts/importar_dados_oficiais.py`, novo `src/atomic_files.py` | A04/A05/A06: sentinelas por campo, identidade/período/unidade/finitude, consistência local e publicação recuperável de conjuntos de arquivos. |
| CSV e metadados `src/dados/official/noaa_uscrn_ga_newton_2025*` | A04: somente três células de temperatura corrigidas para ausente, hashes e descrição atualizados; fonte bruta preservada. |
| `main.py`, `.streamlit/config.toml`, `config/.env.example` | A02/A10/A14: localhost por padrão, CORS/XSRF, opção explícita de rede, validação real dos artefatos, código de saída de erro e controle do processo filho. |
| `src/frontend/app.py`, sete páginas, novo `feedback.py` | A07–A12/A15/A19: falhas esperadas com mensagens públicas, validação e transação no fluxo da interface, N=0, histórico e ressalvas científicas junto aos indicadores. |
| `src/frontend/scheduler.py` | A12: produtor único entre sessões do processo, encerramento e reinício seguros, limpeza controlada. |
| `src/ml/train.py`, `ph_model.py`, `productivity.py`, novos `src/validation.py` e `src/ml/artifact_security.py` | A10/A11/A15–A18: contratos no backend, JSON estrito, schemas/finitude, confiança antes da desserialização, diagnóstico de versão, referências de predição e proteção de treino no diretório empacotado. Os quatro joblib ficaram intactos. |
| Novo `src/frontend/assets.py` | A03: aceita somente os bytes do logotipo conhecido antes da decodificação WebP, sem imagens fornecidas pelo usuário. |
| `requirements.txt`, novo `constraints-f402.txt`, `.gitignore` | A03: perfil isolado verificado, atualizações selecionadas e exclusão do novo ambiente virtual dos arquivos de projeto. |
| Testes em `tests/` | Três arquivos existentes mantidos/adaptados; sete novos arquivos de regressão dos defeitos e segurança. |
| `README.md`, `document/relatorio.md` | A20: execução, estrutura efetiva, métricas/limitações, alterações e parecer final. DER e LICENSE preservados. |

### Matriz dos achados A01–A21

A gravidade abaixo é a da Etapa A. “Corrigido e validado” se refere aos cenários reproduzíveis exercitados e não constitui garantia absoluta.

| ID / gravidade original | Antes | Depois e evidência reproduzível |
|---|---|---|
| A01 · Alto | Banco apagado antes de validar CSV | **Corrigido e validado.** Entradas validadas antes da publicação; staging, backup API SQLite e transação na mesma base. Testes com CSV ausente/inválido, falha de backup, trigger, conexão aberta/WAL e rollback preservam o conteúdo anterior. |
| A02 · Alto conforme exposição | CORS/XSRF desligados; PORT expunha interfaces | **Corrigido e validado.** Proteções ligadas, 127.0.0.1 padrão, PORT validada e rede somente por opção explícita. Testes da configuração e comando; implantação pública não realizada. |
| A03 · Médio | Dependências com vulnerabilidades conhecidas | **Mitigado com ressalvas.** Streamlit e ferramentas/componentes aplicáveis atualizados em ambiente separado. `pip check` aprovado; pip-audit remanescente apenas Pillow. Restrições e controle de imagem descritos na seção 10. |
| A04 · Médio | −9999 tratado como temperatura NOAA | **Corrigido e validado.** Sentinelas por campo e três células corrigidas no derivado, com hash e metadados coerentes; parser e agregações testados. |
| A05 · Médio | Respostas externas inconsistentes aceitas | **Corrigido e validado.** Estação/identificadores/localização/datas/unidades/schema e valores verificados na importação e leitura; fixtures inválidas são recusadas sem publicação. |
| A06 · Médio | CSV publicado sem metadado correspondente | **Corrigido e validado.** Trava, staging, backups e journal do conjunto; testes de falha em troca, marcador de commit/fsync, limpeza e recuperação mantêm conjunto anterior ou novo completo. |
| A07 · Médio | Histórico ordenado textualmente | **Corrigido e validado.** Conversão semântica UTC, equivalência entre formatos/fusos e desempate `id`; nenhum timestamp histórico foi reescrito. |
| A08 · Médio | Chuva gravada mesmo se umidade falhava | **Corrigido e validado.** Backend de lote em transação única e interface usando esse lote; falha no segundo INSERT desfaz ambos. |
| A09 · Médio | N=0 ignorado | **Corrigido e validado.** Zero é número válido, ausência é diferenciada e N/P/K avaliados separadamente; cenário original N=0 exercitado pela interface. |
| A10 · Médio | Exceções internas chegavam ao usuário | **Corrigido e validado.** Falhas de modelo, métricas, arquivos e persistência têm mensagens controladas; logs públicos não incluem o texto bruto da exceção. AppTest e CLI conferem ausência de traceback e caminhos internos nos cenários exercitados. |
| A11 · Médio | Validação restrita aos widgets | **Corrigido e validado.** Contratos independentes para tipos, campos, categorias, faixas e finitude; NaN/inf, strings, booleanos e categorias desconhecidas são recusados antes de prever ou gravar. |
| A12 · Médio | Produtor duplicado entre sessões; sem reinício | **Corrigido e validado.** Instância compartilhada no processo e ciclo de vida testado entre holders, encerramento, novo início e limpeza. Sem coordenação global entre processos. |
| A13 · Médio | SQLite dependia do cwd | **Corrigido e validado.** Caminho padrão e configuração relativa resolvidos pelo módulo; caminho absoluto explícito preservado. Testes com cwd diferente. |
| A14 · Médio | Arquivo vazio era pronto; falha retornava 0 | **Corrigido e validado.** Integridade/schema do banco e artefatos verificados; falha solicitada retorna código não zero sem mensagem de conclusão. |
| A15 · Médio | Teste usado na seleção e CV histórica | **Histórico ou limitação aceita.** Defeito metodológico permanece nos experimentos históricos preservados; ressalva explícita na UI/documentação e treino de substituição bloqueado. Métricas reproduzidas não são validação independente. |
| A16 · Médio | Pickles 1.9.0 no runtime 1.6.1; avisos ocultos | **Mitigado com ressalvas.** Perfil restrito a 1.6.1, hashes/schema e 440 predições de referência por alvo antes de disponibilizar modelo, avisos capturados localmente e diagnóstico exposto. Não há garantia de compatibilidade entre versões; demais runtimes são recusados. |
| A17 · Médio | Previsões de produtividade NaN/inf aceitas | **Corrigido e validado.** Schema completo, datas/culturas/finitude e habilitação por desempenho conferidos; CSV vazio representa ausência. As cinco previsões reais seguem bloqueadas. |
| A18 · Médio condicionado | Joblib histórico sem verificação prévia | **Mitigado com ressalvas.** Referências confiáveis no código, procedência remota verificada na A e hash dos bytes antes de carregar via memória; adulteração recusada antes do desserializador. Hash adjacente não autentica origem. A distribuição/código precisam permanecer protegidos contra escrita não autorizada. |
| A19 · Baixo | pH gravava `label`, tela lia `cultura` | **Corrigido e validado.** Novas linhas têm aliases coerentes; apresentação aceita `label` legado e `cultura`. Persistência e exibição testadas em SQLite temporário. |
| A20 · Baixo/Médio | Divergências de instruções e afirmações | **Corrigido e validado.** README, árvore, execução, sentinelas, métricas, baseline por cultura, compatibilidade, fontes e histórico atualizados conforme código e evidências; sem novo número de versão. |
| A21 · Alto na ocorrência | INMET truncado e depois restaurado na A | **Histórico ou limitação aceita.** Incidente recuperado com autorização e hash inicial. Nenhuma nova substituição na B; causa não determinada. Registro específico na seção 11. |

## 9. Testes, reprodução científica e limites de validação

Ambiente novo `.venv-f402`: Python 3.11.9, Scikit-Learn 1.6.1, NumPy 2.2.6, pandas 2.2.3, Streamlit 1.54.0. Instalação conforme README e constraints do perfil testado; `.venv` anterior preservado para recuperação. Comandos reproduzíveis no novo ambiente:

```powershell
.\.venv-f402\Scripts\python.exe -m pip check
.\.venv-f402\Scripts\python.exe -m unittest discover -s tests -v
```

Na F4-02 Etapa B, a suíte final executou **124 testes: 124 aprovados, zero falhas, zero erros e zero ignorados**. Inclui os 16 existentes e 108 adicionais. Logs e resultados completos estão em `auditoria-etapa-b/unittest-final.log` e `unittest-final.json` no diretório permanente de evidências. As primeiras execuções e verificações intermediárias também foram preservadas; suas falhas diagnosticadas não foram contadas como aprovações. Os seis testes afetados pela proteção final do treino pH também passaram separadamente.

| Grupo de teste | Evidência coberta |
|---|---|
| SQLite e ingestão | CSV inválido/ausente, schema/FK/CHECK, falha de backup e publicação, rollback de lote, trigger, base anterior preservada com conexão/WAL, ordenação UTC/id, contrato de leitura/previsão e cwd. |
| Dados oficiais | Dez testes originais mais regressões de sentinelas por campo, estação/ano/unidade/coordenadas, não finitos e timestamps, hash/proveniência local, respostas corrompidas/falha de conexão e recuperação de publicação. |
| ML e artefatos | Seis originais mais adulteração antes do loader, versões não validadas, schema/JSON inválido, entradas fora do contrato, saídas não finitas, proteção do treino empacotado e produtividade sem habilidade. |
| Scheduler | Compartilhamento entre sessões, job efetivo em base temporária, encerramento e reinício seguros, disable e limpeza. |
| Streamlit AppTest | Home e sete páginas, previsões válidas de chuva/umidade/pH, persistência e rollback, recomendação N=0, legado `label`, arquivos/modelos/métricas ausentes ou corrompidos e mensagens públicas. |
| CLI/configuração/assets | localhost, PORT e opt-in de rede, CORS/XSRF, banco vazio/inválido, códigos de erro, artefatos incompatíveis, logotipo conhecido e adulterado rejeitado antes de decodificar. |

A renderização e ações foram testadas por AppTest, sem abertura de serviço público. Não se verificaram aparência visual em navegador real, carga/performance, durabilidade sob corte de energia real, rede compartilhada entre máquinas, autenticação externa ou comunicação com as Fases 1–3. A recuperação de arquivos foi testada por injeção de falhas e retomada do journal; leitores de terceiros que ignorem a trava não têm atomicidade entre arquivos garantida.

### Métricas reproduzidas, sem substituir artefatos

| Modelo preservado | MAE | MSE | RMSE | R² |
|---|---:|---:|---:|---:|
| Chuva · Ridge histórico | 14,3466669457 | 536,1589039846 | 23,1551053546 | 0,8218952462 |
| Umidade · Ridge histórico | 3,0978188203 | 20,6098057345 | 4,5398023894 | 0,9616926709 |
| pH · Ridge experimental | 0,4279210986 | 0,3625344616 | 0,6021083471 | 0,3291079490 |

Chuva/umidade: 440 previsões de teste por alvo reproduzidas com tolerância absoluta de 1e−8, sem alterar os joblib ou resíduos. Essas amostras são referência de compatibilidade, não teste científico novo. O uso do teste na seleção/CV histórica permanece uma limitação científica. As recomendações são indicativas de protótipo e não prescrição de irrigação ou fertilização.

pH: treino em diretório temporário e carregamento do artefato preservado reproduzem as métricas conhecidas; a serialização de um novo treino pode diferir em bytes, por isso não substitui o modelo distribuído. O baseline global tem MAE 0,5622 e R² −0,0009; o baseline por cultura, MAE 0,4278357606 e R² 0,3288132456, praticamente iguala o Ridge. Cultura é conhecida a priori no cenário manual; não há comprovação de disponibilidade de todas as features pareadas em campo. Não há validação agronômica local nem causalidade demonstrada.

Produtividade: experimento reproduzido em saída temporária, mantendo a seleção walk-forward 2016–2020, teste 2021–2025 e baseline de persistência. R² do método selecionado no teste: arroz −1,7139096814; feijão −0,4634325474; milho −0,0939235676; soja −0,4249481859; cana −0,9327480882. Todos permanecem sem previsão publicada. Valores positivos em alguns folds de seleção não foram confundidos com aprovação do teste temporal. O rendimento é agregado nacional/municipal, não produtividade de talhão.

## 10. Segurança e dependências

Atualizações selecionadas e testadas: Streamlit 1.45.1 → **1.54.0**, python-dotenv 1.1.0 → **1.2.2**, Pillow 11.3.0 → **12.3.0**, pip → **26.2.2** e setuptools → **84.1.0** no ambiente novo. As versões das bibliotecas de ML foram mantidas. A resolução das dependências indiretas do novo ambiente está registrada em `constraints-f402.txt`; a instalação anterior não foi atualizada.

O [advisory do Streamlit para Windows](https://github.com/streamlit/streamlit/security/advisories/GHSA-7p48-42j8-8846) identifica correção em 1.54.0. O diagnóstico considerou aplicabilidade, não classificou toda ocorrência como explorável. A configuração local com XSRF/CORS foi testada; o launcher exige versão mínima de Streamlit antes de iniciar o servidor. Implantação em rede depende de proteção externa e não foi realizada.

**pip-audit 2.10.1:** 46 pacotes consultados; 39 avisos remanescentes, todos em Pillow 12.3.0, sem avisos nos outros 45 na consulta registrada. A versão 13 indicada para correções não é aceita pela restrição `<13` do Streamlit 1.54.0. Não foi forçada combinação incompatível. A aplicação não oferece upload de imagem: verifica o SHA-256 dos bytes do único logotipo empacotado antes de chamar o decodificador, limita o formato a WEBP e usa fallback se a verificação falhar. Dois testes confirmam a leitura esperada e a recusa de imagem alterada antes de `Image.open`. Isso reduz a superfície aplicável, mas não corrige as vulnerabilidades da biblioteca nem comprova a segurança de todas as suas dependências internas. Novos fluxos de imagem ou dependências exigem reavaliação. Lista integral e identificadores no JSON de auditoria, sem filtros para ocultá-los.

**Bandit 1.9.4:** 28 alertas, sendo 19 baixos e nove médios; nenhum alto e nenhuma falha de análise. Destes, 16 estão no código de execução (nove baixos/sete médios) e 12 em testes. Alertas foram revisados individualmente: subprocessos usam argumentos em lista e destinos controlados; random é simulação, não criptografia; SQL dinâmico é limitado a nomes definidos no código; joblib é tratado como execução de código condicionada a procedência/integridade; ZIPs de aquisição são lidos sem extração arbitrária. Permanecem alertas baixos condicionados ao ambiente local (resolução de `taskkill` pelo Windows/PATH) e ao diagnóstico opcional histórico de importância de variáveis; não se demonstrou exploração remota. Não se interpreta o retorno não zero do scanner como falha funcional, nem seus alertas como prova automática de exploração. Detalhes e limites no relatório de segurança das evidências.

Os modelos não são recebidos por upload. Antes de desserializar, o loader compara bytes com referências de confiança mantidas no código e usa esses mesmos bytes em memória. A confiança deriva da procedência examinada e da distribuição íntegra, não de um JSON adjacente ao modelo. Escrita maliciosa no código e nos hashes simultaneamente continua fora dessa proteção. Não se declarou assinatura digital ou autenticação independente inexistente.

A [documentação do Scikit-Learn](https://scikit-learn.org/stable/model_persistence.html) não suporta carregamento entre versões. Para os históricos serializados em 1.9.0, a estratégia é **mitigação no perfil 1.6.1 estritamente testado**, com diagnóstico de avisos, schema e predições de referência; não é suporte geral ou garantia de equivalência. Troca do runtime/modelos exige validação e autorização própria; retreinamento do diretório empacotado é recusado. Não há supressão global de avisos.

Consultas de valores SQLite são parametrizadas, contratos rejeitam dados inválidos antes de persistir, caminhos padrão são controlados pelo módulo e os scripts consultam fontes oficiais fixas. Credenciais não foram adicionadas; backups excluem `.env`, secrets, ambientes e caches. Mensagens públicas não interpolam a exceção bruta. Os controles descritos não constituem afirmação de que o sistema seja impossível de comprometer.

## 11. Preservação, dados e incidente A21

Destino de backups local permanente: diretório externo `F4-02-20261101`, fora da integração, da sessão de ferramenta e dos caminhos sincronizados examinados na Etapa A. O endereço específico do operador é registrado nos manifestos privados e não é necessário para executar o módulo. Os seguintes hashes foram reconferidos antes das correções, com leitura e CRC de todas as entradas:

| Backup | SHA-256 |
|---|---|
| `fase4-regressao-pre-remocao-final.zip` | `3CA607AB9A7729355B8DB19B1309A53A52B6F9B1A5912466E18CF32819CAAD5B` |
| `fase4-regressao-estado-completo-etapaA.zip` | `C66EF9B2ED4B71EB22D8F7F21DBCF42E8E6E717C4A9C692E9FB3540B868C320D` |
| `fase4-antes-etapaB.zip` | `D06B673AC6440FDD14C1BF1B62F8A6C2DA2F78F9BABE040A5AEB7EB869896979` |

O pré-B recupera os 60 arquivos iniciais, comparados individualmente ao manifesto; o estado recebido coincidia com o encerramento recuperado da Etapa A. O backup completo da A também preserva esse estado. Ambientes virtuais anteriores permanecem locais, separados dos arquivos recuperáveis de projeto.

A entrega preserva ainda `fase4-regressao-pos-etapaB.zip` e `F4-02-evidencias-etapa-b-final.zip` no mesmo destino local permanente. O manifesto `auditoria-etapa-b/entrega-final.json` registra os hashes desses arquivos, leitura/CRC e restauração verificada do backup final. O relatório técnico é também copiado para `auditoria-etapa-b/F4-02_RELATORIO_ETAPA_B.md`, com os logs e inventários usados neste parecer.

Na F4-02, as Fases 1, 2 e 3 tiveram respectivamente **21, 43 e 119 arquivos** comparados ao baseline: todos preservados. Os quatro modelos, métricas e resíduos permaneceram idênticos. Os testes conferem hashes dos dados e artefatos antes/depois e não criam banco histórico no módulo. A única regeneração de dados na B foi o derivado NOAA e seu metadado, a partir do arquivo oficial bruto já preservado nas evidências da A.

| Arquivo / conteúdo | SHA-256 final ou comparação |
|---|---|
| NOAA bruto, não alterado | `735085d1262507541df3c9696803a6f78b2ccabd74e3bffb47c7601f59cc76d4` |
| NOAA CSV anterior, preservado nos backups | `e0e715ddb47c747d8c9b6f985ae5a79b6656e3171b144b0a4c0110a1ed29be90` |
| NOAA CSV corrigido | `aee9b38f0353a4e8f185e8309153772391f08259b16585c0195347a3f86b26c8` |
| NOAA metadado corrigido | `f9f5e35425ad2f6d5b23e5b58939f29f9cbc3a09c0b92062cf056f9ff72960f9` |
| INMET, preservado na B | `b227d9699d79148083d64002608c4be028d20e1e2015fadb2a63a1899dd0f1b7` |

Na NOAA, 8.756 linhas antes/depois; três diferenças de conteúdo, todas `air_temperature_c`, de −9999 para ausente: 05/02/2025 16:00, 26/03/2025 15:00 e 16/11/2025 14:00 UTC. As médias diárias afetadas passaram de aproximadamente −399, −398 e −400 °C para 18,0174, 19,0391 e 17,2826 °C. As demais células permaneceram iguais. INMET: 8.713 registros; SIDRA: 180 observações nacionais e 27.820 linhas por recorte municipal; arquivos não substituídos nesta etapa. A validação offline verifica hashes/proveniência e a separação entre solo real nos EUA, meteorologia, estatística agregada, sensores simulados e previsões.

As condições de redistribuição de todos os arquivos externos não foram comprovadas integralmente; não se atribui licença universal aos dados institucionais. Mantenha fontes/metadados, atribua NOAA/NCEI, INMET e IBGE/SIDRA e verifique os termos antes de redistribuição externa. A licença CC BY 4.0 do projeto, créditos e repositório original permanecem preservados.

### A21 — evento recuperado, causa não determinada

Durante a Etapa A, o CSV INMET, inicialmente com 766.863 bytes, foi encontrado com zero bytes. A causa da escrita **não foi determinada**. Após autorização explícita da responsável, somente esse CSV foi restaurado dos bytes do backup verificado, e a conferência final voltou a 60/60 arquivos iguais ao estado inicial. A restauração não foi repetida nesta etapa. O SHA-256 atual coincide com o inicial. O registro original `incidente_integridade.json`, a divergência e `restauracao_inmet.json` permanecem nas evidências da A; esta revisão não atribui a ocorrência a um teste, ferramenta ou pessoa sem prova.

## 12. Parecer e preparação para a Fase 7

**Homologado com ressalvas para execução independente no perfil testado e preparação da integração.** Não permaneceram defeitos bloqueadores demonstrados nos cenários de segurança, perda de dados, integridade e funcionamento essencial exercitados. Os riscos remanescentes são explicitados: alertas Pillow mitigados pelo fluxo restrito, carregamento histórico entre versões com referência numérica, viés de avaliação original e ausência de coordenação do scheduler entre processos. Uma alteração dessas condições exige nova avaliação.

O módulo resolve imports e caminhos a partir de sua localização, usa persistência configurável, pode apresentar os dados oficiais offline e oferece funções de consulta/inferência com contratos verificados. Consumidores devem preservar a transação de previsões associadas, usar os loaders coerentes dos dados e definir um único produtor de simulação. Estar na pasta consolidada não comprova integração funcional: **a comunicação com os outros módulos e o dashboard consolidado da Fase 7 não foi verificada**.

A estimativa de pH continua experimental; a produtividade permanece somente histórica. Permanecem ausentes neste escopo: validação agronômica externa/local, previsão confiável de rendimento e incorporação efetiva de ISMN. Esses limites científicos não foram ocultados nem convertidos em funcionalidades novas. A revisão preserva a autoria e o histórico acadêmico, sem atribuir novo número de versão ou resultado de campo.


## 13. F4-03 — conferência documental e higiene

Foram confrontados os documentos, configurações, fontes e inventários físicos com o manifesto final e os backups da F4-02. Os 73 arquivos de projeto recebidos coincidiam com esse manifesto; seis ZIPs de preservação/evidências passaram em hash, leitura e CRC. Antes de editar, foi preservada uma cópia verificada de dez documentos/configurações. A F4-03 modificou somente README, este relatório, DER e `.gitignore`; código Python, dependências, configuração de execução, datasets, quatro joblib, métricas, licença e créditos foram preservados. **Os 124 testes da F4-02 não foram reexecutados.**

### História, fontes e privacidade

A primeira implementação original, no [commit 5a6a4e75 de 11/06/2026](https://github.com/jojocamdb/FarmTech-Solutions-Fase4/tree/5a6a4e75d647adc8884ba1e3d121dad8490a00d2/src/frontend), contém Home e seis páginas funcionais: sete telas. A evolução F4-01 acrescentou Dados Oficiais, resultando em Home e sete páginas: oito telas. O [commit ddc6244a de 15/06/2026](https://github.com/jojocamdb/FarmTech-Solutions-Fase4/commit/ddc6244a154a4793a1cda486de4c0f0ca11117a6) sustenta o registro 1.1.0 e o menu/CLI. As versões são registros históricos do README; não havia tags ou GitHub Releases nas consultas desta conferência. As etapas F4-01–F4-03 não receberam versões inventadas.

As Partes 1 e 4 do README repetem o mesmo vídeo também no histórico original. As 14 revisões do README examinadas não forneceram um link distinto para a Parte 4. Conteúdo, títulos e intenção da repetição não foram verificados; os links e a autoria foram preservados. O enunciado acadêmico original, a avaliação primária e a obrigatoriedade de publicar RMs não estavam disponíveis nas fontes examinadas. A nota 13,5/15 e o feedback são atribuídos à equipe, sem afirmar conformidade integral com requisitos não autenticados.

Não foram identificadas credenciais nos arquivos de projeto examinados; isso não é garantia de ausência de vulnerabilidades. Caminhos pessoais absolutos foram retirados da cópia distribuível deste relatório; as evidências privadas originais foram preservadas. Os nomes e RMs dos integrantes continuam no README. Recomenda-se preservar o crédito nominal e decidir a necessidade de expor os RMs na versão pública conforme a entrega acadêmica, sem removê-los sem autorização.

### Cadeia de rastreabilidade

A primeira coluna representa funcionalidades declaradas e escopo técnico auditado, não requisitos acadêmicos inventados. E-B significa o diretório externo `auditoria-etapa-b/` da F4-02; E-A, `auditoria-etapa-a/`. Os testes nominais abaixo existem nos fontes e no `E-B/unittest-final.log`; os resultados são históricos da F4-02, apenas conferidos documentalmente na F4-03.

| Escopo | Implementação / arquivo | Teste de referência | Evidência / resultado | Limitação |
|---|---|---|---|---|
| A01 · recuperação SQLite | `inicializar_banco`, `_publicar` em `scripts/init_db.py` | `test_missing_csv_preserves_all_previous_records`; `test_existing_wal_and_open_connection_are_preserved_and_backup_is_readable` | E-B/db/test_db_safety.log e log final: aprovados | SQLite histórico ausente; recarga válida substitui conteúdo com backup anterior. |
| A07/A13 · tempo e caminho | `normalizar_timestamp`, `resolve_db_path` em `src/db/database.py` | `test_prediction_history_uses_utc_and_id_without_rewriting_historical_values`; `test_relative_path_does_not_depend_on_consumer_cwd` | E-B/unittest-final.log: aprovados | Legado sem offset assumido UTC; exportação textual tem precisão de segundos. |
| A08/A19 · persistência e histórico | `inserir_previsoes` em `src/db/database.py`; páginas 4 e 6 | `test_pair_prediction_transaction_rolls_back_on_second_insert`; `test_history_displays_old_and_new_ph_culture_keys` | E-B/unittest-final.log: aprovados | Cultura no JSON não tem FK SQL. |
| A02/A14 · configuração e CLI | `comando_streamlit`, `ensure_database`, `ensure_models` em `main.py` | `test_port_does_not_expose_service_and_protections_are_enabled`; `test_missing_database_dashboard_and_training_return_nonzero` | E-B/unittest-final.log: aprovados | Rede pública e autenticação externa não homologadas. |
| A03 · dependências e imagem | `requirements.txt`, `constraints-f402.txt`, `src/frontend/assets.py` | `test_verified_logo_remains_readable`; `test_altered_bytes_are_rejected_before_decoding` | E-B/pip-audit-final.json, seguranca-final.md e log: fluxo verificado, 39 avisos Pillow | Mitigação não corrige a biblioteca. |
| A04/A05 · dados oficiais | Parsers e validadores em `src/data_sources.py` | `test_noaa_official_sentinels_are_missing_per_field`; `test_inmet_rejects_bad_identity_coordinates_dates_units_and_values`; `test_sidra_rejects_invalid_rows_including_after_first` | E-B/data/noaa-correction-results.json e log: três células corrigidas, testes aprovados | Estações externas/agregados; redistribuição não comprovada integralmente. |
| A06 · publicação de conjunto | `publish_files` em `src/atomic_files.py` | `test_commit_marker_fsync_failure_restores_previous_group`; `test_publication_recovery_after_process_termination` | E-B/data/data-tests-final.log e log final: aprovados | Leitores locais cooperantes; sem teste de corte real de energia ou múltiplos hosts. |
| A09/A10/A11 · contratos e mensagens | `src/validation.py`, `src/frontend/feedback.py` e páginas | `test_recommendations_consider_n_zero_independently`; `test_nan_input_is_rejected_without_exception_or_record`; `test_corrupt_metric_json_has_actionable_public_error` | E-B/unittest-final.log: aprovados | Manejo de protótipo, sem prescrição agronômica validada. |
| A12 · scheduler | `iniciar_scheduler`, `encerrar_scheduler` em `src/frontend/scheduler.py` | `test_multiple_sessions_share_only_one_producer`; `test_stop_and_restart_are_idempotent` | E-B/db/test_scheduler.log e log final: aprovados | Coordenação restrita ao processo. |
| A15/A16/A18 · históricos e confiança | `src/ml/train.py`, `src/ml/artifact_security.py` | `test_originals_reproduce_440_predictions_and_metrics_without_retraining`; `test_corrupt_original_is_refused_before_deserialization` | E-B/ml/ml_results.json e log: 440 previsões/alvo e integridade conferidos | Viés histórico de seleção/CV preservado; compatibilidade entre versões mitigada no perfil testado. |
| Evolução pH · experimental | `src/ml/ph_model.py` e `ModeloValidado` | `test_ph_metrics_and_crop_mean_baseline_are_preserved`; `test_ph_training_refuses_packaged_directory_before_loading_or_writing` | E-B/ml/ml_results.json e ml-final/affected-results.json: métricas e proteção verificadas | Ganho praticamente nulo frente à média por cultura; sem validação de campo. |
| A17 · produtividade | `src/ml/productivity.py` | `test_productivity_temporal_metrics_and_block_are_preserved`; `test_empty_forecast_artifact_represents_no_public_predictions` | E-B/unittest-final.log e métricas persistidas: cinco R² negativos, sem previsão | Agregados oficiais; somente cinco anos de teste por cultura. |
| A20/A21 · documentação e recuperação | Documentos e registros externos do incidente | Revisão estática F4-03; conferências de hash F4-02 | E-A/incidente_integridade.json, restauracao_inmet.json; E-B/entrega-final.json | Causa do truncamento não determinada; evidência histórica preservada. |
| Preparação Fase 7 | Caminhos e funções disponíveis | `test_relative_path_does_not_depend_on_consumer_cwd` | E-B/unittest-final.log: consumo com cwd externo testado | Comunicação entre módulos não verificada. |

### Higiene e parecer documental

Os ambientes virtuais e caches existentes são locais e ignorados; não foram removidos. SQLite, auxiliares, logs, temporários e backups operacionais não foram encontrados entre os 73 arquivos de projeto. O `.gitignore` passou a cobrir os auxiliares SQLite, ambientes similares, variantes privadas de `.env`, staging e backups, preservando `config/.env.example`, modelos, dados oficiais, metadados e testes. Regras de exclusão não removem arquivos nem desfazem rastreamento anterior. A configuração Dependabot permanece como material do módulo independente; sua adoção na raiz consolidada exige avaliação específica.

**Documentação e preparação para versionamento: Aprovado com ressalvas.** A árvore resumida corresponde aos componentes existentes, a cronologia foi esclarecida e a cadeia técnica está documentada. Permanecem decisões sobre os RMs públicos e vídeos, ausência de fontes acadêmicas primárias, condições de redistribuição externa e as ressalvas de segurança/ciência já registradas. A integração funcional com a Fase 7 não foi afirmada. A conferência não alterou funcionalidades homologadas e não exige um CHANGELOG separado do histórico existente.
