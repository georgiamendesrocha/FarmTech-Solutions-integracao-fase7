# Histórico de alterações — FarmTech Solutions, Fase 2

Este histórico distingue a implementação original, já avaliada pela FIAP conforme informação do usuário, das correções da auditoria de **outubro/novembro de 2026**, consolidadas em **01/11/2026**. Os registros até a F2-94 descrevem o projeto de origem; a seleção do módulo integrado está identificada na F2-95. As datas e versões declaradas nos documentos originais são registros históricos; não identificam automaticamente releases, tags ou testes. A base Git da auditoria na origem foi `b37f8f2`.

## Funcionalidades originais — projeto da Fase 2

Autoria e créditos preservados no [README](README.md) e no [documento técnico](document/ai_project_document_fiap.md), incluindo todos os participantes originais, independentemente da composição atual da Fase 7.

- Firmware ESP32/Arduino para a simulação de irrigação do tomate Débora, com DHT22, LDR, botões NPK, relé e LED no circuito Wokwi.
- Decisão por regras de umidade, pH simulado e NPK; transformação didática do pH e estados de nutrientes por toggle.
- Configuração PlatformIO/Wokwi, transmissão serial prefixada e histórico CSV no PC, incluindo filtro para o monitor do PlatformIO e capturador Python.
- Menu principal Python e análises em R para dados IoT, meteorológicos e integrados.
- Consulta Open-Meteo por cidade, persistência JSON/CSV, relatórios e gráficos em R.
- Documentação acadêmica, logotipo FIAP, créditos da equipe e links originais de repositório e vídeo.

Essas funcionalidades pertencem ao trabalho original. A auditoria não assume sua autoria e não apresenta resultados agronômicos ou estatísticos sem evidência.

## Auditoria de outubro/novembro de 2026 — consolidação em 01/11/2026

### Correções anteriores à auditoria de 01/11/2026

As correções e os testes abaixo foram informados pelo usuário e/ou observados no diff inicial da auditoria de 01/11/2026. Foram preservados e não foram contabilizados como testes executados naquela auditoria.

- Adição de `assets/circuito_wokwi.png` e referência no README, corrigindo a ausência da imagem apontada na avaliação.
- Compatibilidade do capturador Python com URLs RFC2217 por `serial.serial_for_url`, mantendo portas COM.
- Fluxo de captura Wokwi → `127.0.0.1:4000` → Python → `dados/historico_irrigacao.csv`, a 115200 baud, com persistência local.
- Opção 1 do menu Python alterada para chamar diretamente `scripts/serial_grava_csv.py`, com retorno ao menu, sem depender do monitor interativo PlatformIO.
- Ajustes locais no menu R e proteção inicial para regressões inviáveis em dados constantes.
- Relatórios, gráficos e dados gerados nos testes anteriores, preservados no estado encontrado na origem.

### Correções realizadas na auditoria de 01/11/2026

- Revisão do README e dos guias para descrever as quatro opções dos menus Python/R, instalação, PATH no Windows, dependências e o fluxo serial atual.
- Distinção entre o capturador Python usado pelo menu e o monitor independente do PlatformIO; ambos os mecanismos de persistência foram mantidos.
- Renomeação de identificadores internos do menu para captura serial; subprocessos executados na raiz, saída UTF-8, espera de encerramento após terminate/kill e remoção de sondagens TCP concorrentes durante a captura. EOF/Ctrl+C no menu são tratados e falhas dos subprocessos passam a ser informadas.
- Validação dos dez campos numéricos do protocolo no capturador Python, com valores finitos, faixas e flags; recomposição de linhas parciais, limite de tamanho, preservação de CSV com cabeçalho incompatível e mensagens para falhas de serial/arquivo. Mantida compatibilidade COM/RFC2217 e append como padrão.
- Em R, tratamento de valores não finitos e dados constantes, proteção de ajustes inviáveis e R² indefinido, interpretação de timestamps mistos por linha, preservação de `t_rel_ms` como número além do limite de inteiro do R e encerramento do menu em EOF. O relatório integrado passa a declarar o critério temporal e seus limites.
- Persistência meteorológica com escape CSV e solicitação explícita de vento em m/s nas novas consultas. A unidade dos artefatos históricos não foi convertida; verificar metadados antes de interpretar vento.
- Correção dos atalhos de setup para localizar o requirements a partir do próprio script e organização do `.gitignore`. A auditoria de 01/11/2026 não instalou dependências.
- Correção documental da regra efetiva do firmware: limiar inferior de umidade de 45%, limite superior de 80%, intervalo de botões de 180 ms, mapeamento invertido do LDR e esquema serial sem horário civil no ESP32.
- Registro de que DHT22 representa umidade do solo apenas didaticamente, LDR simula pH, temperatura é registrada e previsão meteorológica participa da análise em R sem controlar diretamente o firmware.
- Substituição de métricas quantitativas e depoimentos sem comprovação por funcionalidades observáveis, limites e evidências identificadas. Economia de água, produtividade, acurácia, disponibilidade e latência não foram declaradas medidas.
- Descrição dos critérios distintos de associação temporal: vizinho mais próximo no menu R; interpolação numérica no script independente, com limites de horizonte, fuso e repetição de previsão horária.
- Revisão de higiene e segurança sem remover arquivos versionados nem evidências locais; registro de dados gerados já acompanhados pelo Git e de referências antigas a arquivos ausentes.
- Criação de [RASTREABILIDADE_F2.md](document/RASTREABILIDADE_F2.md) e [AUDITORIA_SEGURANCA_F2.md](document/AUDITORIA_SEGURANCA_F2.md), separando testes anteriores informados, testes executados em 01/11/2026 e pendências identificadas naquela auditoria.
- Adição de testes offline em `tests/test_app.py`, `tests/test_serial_capture.py`, `tests/test_weather_forecast.py` e `tests/test_app_r.R`; resultados e limites registrados na rastreabilidade.

O detalhamento dos ajustes e os resultados da auditoria de 01/11/2026 estão na [rastreabilidade](document/RASTREABILIDADE_F2.md) e na [auditoria de segurança](document/AUDITORIA_SEGURANCA_F2.md). Foram aprovados 18 testes Python e 10 grupos de testes R. Wokwi, compilação ESP32, hardware e API meteorológica não foram reexecutados nessa auditoria; os testes anteriores permanecem identificados como relatos recebidos.

A auditoria de 01/11/2026 preservou a lógica agronômica, pinagem, sensores e firmware ESP32.

## Revisão documental F2-78 na origem — 01/11/2026

- Organização do histórico documental por data de auditoria.
- Identificação das evidências e dos resultados de testes por revisão auditada, preservando sua origem.
- Separação das versões declaradas nos READMEs, das datas de commit e das referências Git disponíveis localmente, sem criação ou confirmação de releases.
- Correção da descrição do repositório original: visibilidade pública confirmada pelo GitHub em 01/11/2026.
- Atualização da estrutura de pastas com os documentos e testes da auditoria; o arquivo de documentação complementar passou de instrução provisória a índice.
- Definição da raiz do módulo e conferência dos links relativos para a estrutura de destino `servicos/fase2-iot/`.
- Preservação da autoria original, das evidências e das divergências históricas de data. O escopo da F2-78 é documental; não altera código, dados ou firmware.

## Correções e validação F2-91 na origem — 01/11/2026

- Procedimento único de inicialização Wokwi no README: pasta do módulo no VS Code, compilação PlatformIO no ambiente `esp32`, Ctrl + Shift + P e **Wokwi: Start Simulator**, console e captura pela opção 1 do Python. Esclarecidos pré-requisito de firmware compilado, dependência RFC2217 e ausência de persistência pelo console isolado.
- Apresentação dos horários IoT/integração em `America/Bahia` com offset explícito, preservando o instante absoluto e as associações. Previsão permanece UTC; o novo helper `r/temporal_utils.R` compartilha parsing e formatação. Históricos sem fuso continuam usando o fuso do computador, com fallback explícito UTC.
- Correção do script independente `r/02_integrar_previsao.R`: UTC para previsão sem sufixo, ordenação, descarte de timestamps inválidos, primeira linha original em duplicatas e interpolação entre limites finitos. Cobertura, extremos e método continuam explícitos; não foi imposta tolerância temporal nova.
- Coletor meteorológico valida metadados de vento em m/s e UTC antes da persistência e identifica UTC com `Z` nos novos CSVs. Respostas incompatíveis não substituem os destinos. JSONs, CSVs e demais evidências históricas foram preservados na origem sem conversão retroativa.
- Cenário isolado de N ausente validado em modelo Python e acompanhado de inspeção estática. O harness prepara C++ extraído literalmente do firmware; nove cenários de execução C++ não foram executados por ausência de compilador host, sem alegação de teste direto do firmware.
- Validação consolidada: 40 casos Python, com 31 aprovados e nove ignorados; 16 grupos R aprovados, usando dados temporários. Não houve repetição manual de Wokwi, compilação ESP32, hardware ou chamada à API meteorológica.
- Recontagem dos gerados e revisão de seleção para a Fase 7, privacidade, ignore e evidências remanescentes. Porta 4000 sem servidor identificado pelo `netstat`; leitura por CIM negada, mantendo a confirmação do bind pendente. Nenhum firewall foi alterado.
- Sintaxe do setup Bash aprovada com o Bash existente na instalação do Git, resolvendo a limitação anterior do comando que dependia de WSL. O instalador não foi executado.
- Retificação da contagem F2-78: 89 entradas de caminho incluíam 23 aliases Windows para os mesmos arquivos; correspondem a 66 arquivos físicos, com dez documentos alterados e 56 arquivos preservados. Os hashes e a preservação do conteúdo permanecem válidos.
- Recomendação técnica: **apto com ressalvas para integração acadêmica dos fontes**, preservando as pendências de homologação descritas na rastreabilidade e na auditoria de segurança. Firmware, autoria e evidências anteriores mantidos.

## Revisão documental F2-92 na origem — 01/11/2026

- Revisão recursiva da documentação e das referências cruzadas, com remoção de declarações transitórias sobre o estado do repositório. Preservados os créditos, a proveniência das versões, as evidências de validação e as pendências técnicas.
- Padronização das orientações de execução na raiz do módulo em `servicos/fase2-iot/`, mantendo o procedimento de inicialização Wokwi e os caminhos relativos.

## Estrutura e higiene documental F2-93 na origem — 01/11/2026

- Na origem, realocação do conteúdo integral do enunciado para `document/ENUNCIADO_F2.md`, preservando a atribuição institucional à FIAP. O arquivo institucional não integra a seleção F2-95; os requisitos do módulo estão na síntese e matriz da rastreabilidade.
- Remoção do antigo `document/other/readme.md`, sem conteúdo técnico específico, e simplificação do README como entrada para os guias e documentos do módulo. Detalhes de serial, CSV, previsão e caminhos R concentrados no guia de `scripts/`.
- Restrição dos padrões TSV/XLS/XLSX à pasta `dados/`, mantendo proteção global de `secrets.*`, regras de `.vscode/` e destino reservado ao exemplo CSV sintético/revisado. Definição de LF para scripts `.sh` e CRLF para `.bat` em `.gitattributes`, preservando `* text=auto` e sem renormalizar arquivos existentes.
- Registro da necessidade de confirmação humana sobre a autorização para reprodução integral do enunciado institucional, sem presumir essa autorização pela atribuição ou pela presença do arquivo no repositório.
- Validação documental na origem: 11 documentos Markdown, 217 referências locais e zero erros; 52 casos de ignore e 12 verificações de atributos aprovados. Corpo original do enunciado preservado byte a byte na origem sob a atribuição FIAP.

## Finalização documental F2-94 na origem — 01/11/2026

- Inclusão de proposta autoral de síntese dos requisitos na rastreabilidade, distinguindo a fonte institucional FIAP, o registro acadêmico das exigências e a documentação da implementação. O enunciado integral e sua atribuição foram preservados na origem.
- Orientação de proveniência por módulo e tabela para o README principal integrado, com a única linha de origem confirmada: Fase 2, `servicos/fase2-iot/` e repositório original `EdeSufiatti/EdeSufiatti-FIAP_IA_FASE2_CAP1`.
- Identificação do histórico do README como versões documentadas e ajuste da referência correspondente no guia de `src/`.
- Separação da atribuição do template, da autorização de reprodução do enunciado e das condições de distribuição/reutilização do código e da documentação da equipe, a serem registradas pelos titulares; licença específica, se escolhida, permanece decisão deles.
- Preservação dos resultados F2-91: 31 testes Python aprovados, nove cenários C++ host ignorados e 16 grupos R aprovados. A F2-94 não reexecutou essas suítes.
- Conferência documental na origem com 11 documentos, 215 referências locais e zero erros; prévia local do README e inventário dos 28 arquivos de evidência na origem, com três recomendados para manter, 14 opcionais e 11 não recomendados para publicação. Os originais foram preservados na origem.

## Seleção documental F2-95 — 01/11/2026

- Seleção de três relatórios TXT históricos em `dados/analises/`, mantendo seu conteúdo e os limites de proveniência. Os 25 outros arquivos de dados da origem — 19 PNGs, um JSON e cinco CSVs — não integram o módulo selecionado.
- Enunciado integral FIAP mantido na origem e omitido desta seleção. Os requisitos são apresentados pela [síntese autoral e matriz de rastreabilidade](document/RASTREABILIDADE_F2.md#síntese-autoral-proposta-para-os-requisitos), sem reprodução integral do material institucional.
- Preservação dos créditos originais, do circuito em `assets/`, dos seis passos Wokwi e da identificação do repositório original da Fase 2. Os resultados 31 Python aprovados, nove C++ host ignorados e 16 grupos R aprovados permanecem identificados como validação F2-91 na origem.
- Registro da política do projeto integrado: acesso privado até a avaliação e professor como colaborador autorizado. A política e os limites da verificação local do controle de versão estão separados da proveniência pública do repositório original.

## Proveniência das versões e do histórico Git

Na consulta local realizada no projeto de origem em 01/11/2026, `main` apontava para `b37f8f2`, com um commit alcançável. `git log --all` e `git rev-list --all --count` mostravam dois commits considerando todas as referências locais da origem. A consulta utilizou as referências já armazenadas localmente, sem fetch; ela não descreve o controle de versão do projeto integrado.

| Fonte local | Registro observado | Interpretação |
|-------------|-------------------|---------------|
| `main`, commit `b37f8f2` | 20/04/2026, mensagem `versão final!` | Data do commit, distinta das datas declaradas nas entradas do README |
| `origin/master`, commit `1e58f2b` | 11/04/2026, mensagem `altearções no README.md` | Outra referência local; seu README declara `0.1.0` em 11/04/2026 |
| README em `b37f8f2` | `0.1.1` em 11/04/2026; `0.1.2`, `0.1.3` e `0.1.4` em 12/04/2026 | Histórico declarado pelo documento, sem associação comprovada com releases ou tags |
| Entrada `0.1.2` do README original | Texto interno `Versão 1.2` | Inconsistência textual normalizada para `0.1.2`, sem introduzir outra versão |
| README original de `src/` | `0.1.4` em 13/04/2026 | Diverge de 12/04/2026 no README da raiz; ambas as declarações são preservadas como fontes históricas |
| `git tag --list` | Nenhuma tag local encontrada | Resultado limitado às tags disponíveis no checkout auditado |

As declarações `0.1.0` a `0.1.4` não são uma sequência de releases comprovada pelo histórico disponível. A revisão documental não atribui os testes de 01/11/2026 a essas versões.
