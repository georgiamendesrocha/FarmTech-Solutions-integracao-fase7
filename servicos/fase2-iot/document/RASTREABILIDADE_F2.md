# Rastreabilidade — FarmTech Solutions, Fase 2

Registro da auditoria técnica de **01/11/2026** (America/Bahia) dos requisitos, da implementação e das evidências da Fase 2. Os requisitos do módulo são apresentados pela [síntese autoral](#síntese-autoral-proposta-para-os-requisitos) e pela [matriz de rastreabilidade acadêmica](#matriz-de-rastreabilidade-acadêmica). O enunciado institucional FIAP foi consultado no projeto de origem e não integra esta seleção. A referência de código usada na auditoria na origem foi `b37f8f2`, acompanhada das correções e evidências preexistentes descritas neste documento. Os registros até a F2-94 descrevem a origem; a seleção do módulo integrado está identificada na F2-95.

Este documento registra a implementação inspecionada e as evidências disponíveis na origem em 01/11/2026. Não substitui avaliação acadêmica nem comprova resultados agronômicos. A autoria e os créditos originais permanecem no [README](../README.md) e no [documento técnico](ai_project_document_fiap.md); as correções da auditoria estão separadas no [CHANGELOG](../CHANGELOG.md).

A revisão documental **F2-78**, de 01/11/2026, tornou explícito o caráter histórico desses registros. Na consulta Git local do projeto de origem, `main` continha um commit (`b37f8f2`, de 20/04/2026) e o conjunto de referências locais alcançava dois commits, incluindo `origin/master` em `1e58f2b`, de 11/04/2026. A consulta usou as referências disponíveis na origem, sem fetch; nenhuma tag foi encontrada nesse recorte. As versões `0.1.0` a `0.1.4` e as datas divergentes declaradas nos READMEs são detalhadas no histórico de alterações, sem serem tratadas como releases comprovadas.

## Seleção F2-95 e política de acesso — 01/11/2026

Para o módulo `servicos/fase2-iot/`, a seleção F2-95 inclui os fontes, configurações, testes, documentação autoral, imagens de identidade/circuito e somente os três relatórios TXT históricos abaixo. Os requisitos estão na síntese autoral e na matriz deste documento.

| Relatório incluído | Natureza da evidência |
|---|---|
| [analise_historico.txt](../dados/analises/iot/analise_historico.txt) | Histórico IoT inspecionado na origem; não comprova execução do código integrado |
| [analise_previsao.txt](../dados/analises/previsao/analise_previsao.txt) | Histórico meteorológico da origem; a unidade antiga de vento exige o contexto descrito na auditoria de segurança |
| [analise_integrada.txt](../dados/analises/integrada/analise_integrada.txt) | Histórico de integração da origem, com limites de método, fuso e proveniência |

Os outros **25 arquivos de dados da origem — 19 PNGs, um JSON e cinco CSVs — foram omitidos da seleção F2-95**, assim como o enunciado institucional integral. Eles permanecem preservados na origem. As referências históricas a 28 arquivos, 23 rastreados, JSON e gráficos descrevem as inspeções na origem, não o conteúdo fornecido neste módulo. As figuras em `assets/` são distintas dos PNGs de dados omitidos e acompanham o módulo.

Os TXT não substituem as entradas CSV das análises. Para executar os fluxos de R, é necessário gerar novas capturas e/ou previsões pelos procedimentos documentados. Não há CSV de exemplo distribuído.

**Política do projeto integrado:** acesso privado até a avaliação, com o professor como colaborador autorizado. Trata-se da política de entrega; a preparação local não comprova configuração de acesso remota nem concessão efetiva de colaboração. A visibilidade pública citada no histórico refere-se somente ao repositório original da Fase 2.

**Limite de verificação do controle de versão:** na preparação local autorizada pelo usuário em 01/11/2026, a raiz existente do projeto integrado não continha diretório `.git`. Não há histórico, branch ou remoto consolidado verificado nesse recorte. Inicializar Git está fora do escopo autorizado da F2-95; as referências Git deste histórico pertencem à origem. As verificações `git status`, `git diff`, `git check-ignore` e `git check-attr` são **não aplicáveis ao diretório de consolidação nesta etapa**; não constituem falhas de homologação.

## Critério das evidências

| Categoria | Significado |
|-----------|-------------|
| Inspeção local | Conteúdo efetivamente lido nos arquivos; demonstra implementação, não execução |
| Histórico informado | Teste anterior relatado pelo usuário; não é apresentado como reexecutado na auditoria de 01/11/2026 |
| Artefato inspecionado na origem | Arquivo existente na origem em 01/11/2026; não garante sua procedência, data exata ou reprodução naquela auditoria, nem sua inclusão na F2-95 |
| Teste da auditoria de 01/11/2026 | Comando efetivamente executado naquela auditoria e resultado registrado abaixo |
| Pendente / não executado | Verificação não executada ou sem evidência suficiente na auditoria de 01/11/2026 |

## Requisitos da Fase 2

### Síntese autoral proposta para os requisitos

A síntese abaixo foi redigida em linguagem própria para resumir os requisitos e acompanhar a matriz de rastreabilidade acadêmica. O conteúdo integral de `ENUNCIADO_F2.md`, de autoria FIAP, permanece preservado no projeto de origem e foi omitido da seleção F2-95.

| Categoria documental | Origem e finalidade |
|---|---|
| Fonte institucional | Material da atividade FIAP consultado na origem. A autoria do enunciado pertence à instituição; o texto integral não acompanha esta seleção. Os requisitos do módulo são registrados na síntese autoral e na matriz abaixo. |
| Registro acadêmico das exigências | A síntese e a matriz desta documentação relacionam os requisitos compreendidos pela auditoria aos arquivos, evidências e limitações. Sua redação é autoral e não constitui uma nova versão do enunciado institucional. |
| Documentação autoral da implementação | O [README](../README.md), os guias e os registros técnicos explicam as escolhas e o funcionamento do projeto, preservando os créditos originais do módulo. |

**Síntese autoral dos requisitos:**

> Construir e documentar um protótipo acadêmico de irrigação com simulação de umidade, pH e disponibilidade de nutrientes, além do comando de um atuador por regras explícitas. Organizar os fontes, explicar o circuito e demonstrar seu comportamento. Tratar consulta meteorológica e análise estatística como extensões, identificando entradas, saídas e limites das evidências.

Nas auditorias na origem, não foi localizada comprovação da autorização para reprodução integral do material FIAP; eventual reprodução futura exige confirmação humana. O texto integral foi omitido da seleção F2-95. Também não foi identificada licença específica para o código e a documentação da equipe. Cabe aos respectivos titulares registrar as condições pretendidas de distribuição e reutilização e, se escolhida, uma licença específica. A atribuição do template é registrada separadamente desses materiais. A síntese autoral mantém o registro dos requisitos sem atribuir à equipe a autoria institucional.

### Matriz de rastreabilidade acadêmica

| Requisito sintetizado | Arquivos relacionados | Evidência e situação | Limitação |
|-----------------------|----------------------|----------------------|-----------|
| Simular coleta em dispositivo eletrônico | [src/prog1.ino](../src/prog1.ino), [diagram.json](../diagram.json), [platformio.ini](../platformio.ini), [wokwi.toml](../wokwi.toml) | Código e circuito inspecionados; compilação ESP32 e cenários Wokwi aprovados no histórico informado | Sem nova simulação ou hardware físico por esta evidência |
| Umidade representada pelo DHT22 | [src/prog1.ino](../src/prog1.ino), [src/readme.md](../src/readme.md) | Leitura DHTesp a cada 2000 ms; comportamento validado no histórico informado | DHT22 mede umidade do ar; solo apenas didático; não há calibração de solo |
| N, P e K representados por botões | [src/prog1.ino](../src/prog1.ino), [diagram.json](../diagram.json) | GPIO 25/26/27, INPUT_PULLUP, toggle na borda de descida e intervalo maior que 180 ms | Flags booleanas; não medem concentração nem excesso de nutrientes |
| pH representado por LDR e relacionado ao NPK | [src/prog1.ino](../src/prog1.ino) | GPIO 34; `14 - ADC/4095 × 14`; ausência de N/P/K subtrai 0,3/0,2/0,2 | Transformação didática; pH final limitado a 0–14; não é química validada |
| Decisão documentada para cultura escolhida | [README](../README.md), [src/readme.md](../src/readme.md), [documento técnico](ai_project_document_fiap.md) | Tomate Débora; umidade menor que 45% liga; de 45% a 80% depende de pH 6,0–6,8 e NPK; acima de 80% desliga | Temperatura é registrada, sem participar da decisão; limiares não validados em campo na auditoria de 01/11/2026 |
| Relé representando bomba | [src/prog1.ino](../src/prog1.ino), [diagram.json](../diagram.json) | GPIO 14 ativo em LOW, LED no GPIO 2 acompanha a decisão; cenários aprovados no histórico informado | Não há medição de vazão, consumo ou ensaio elétrico físico |
| Fontes organizados no repositório | [README](../README.md), pastas [src](../src/), [scripts](../scripts/), [config](../config/), [monitor](../monitor/), [r](../r/) e [document](./) | Estrutura inspecionada e preservada na auditoria de 01/11/2026 | Preservar a estrutura interna e os caminhos relativos no módulo `servicos/fase2-iot/` |
| README com funcionamento e especificidades | [README](../README.md), [instalação](../config/SETUP_INSTRUCTIONS.md) | Fluxos Python/R, dependências, serial e limites descritos | Requisitos externos continuam dependendo da instalação local do usuário |
| Imagem das conexões no README | [assets/circuito_wokwi.png](../assets/circuito_wokwi.png), [README](../README.md) | Imagem adicionada nas correções anteriores e referência preservada na auditoria de 01/11/2026 | Não constitui execução do Wokwi naquela auditoria |
| Código C/C++ do ESP32 | [src/prog1.ino](../src/prog1.ino) | Fonte presente e preservado na auditoria de 01/11/2026 | Compilação histórica informada, sem equivaler a revalidação de campo |
| Opcional 1: integração meteorológica | [scripts/weather_forecast.py](../scripts/weather_forecast.py), [app.r](../app.r), [r/02_integrar_previsao.R](../r/02_integrar_previsao.R) | Consulta Open-Meteo, JSON/CSV e análise implementados; consulta Irecê-BA aprovada no histórico informado | Implementação cobre consulta e análise; não transmite previsão nem suspende automaticamente a bomba do firmware |
| Opcional 2: análise estatística em R | [app.r](../app.r), [r/01_carregar_dados.R](../r/01_carregar_dados.R), [r/02_integrar_previsao.R](../r/02_integrar_previsao.R) | Estatísticas, relatórios e gráficos implementados; execuções anteriores informadas | R apoia análise posterior; não decide nem comanda diretamente o relé; amostra pequena limita inferência |
| Vídeo de até 5 minutos, sem listagem | [README](../README.md) | Link de vídeo original preservado | Acesso, duração, privacidade e conteúdo não foram verificados na auditoria de 01/11/2026 |

## Fluxos e contratos de dados

O menu Python possui quatro opções: **1** auxilia a abertura do diagrama, aguarda a porta do Wokwi e executa o capturador Python; **2** executa `Rscript app.r`; **3** consulta previsão por cidade; **4** encerra. A compilação e o início da simulação são etapas manuais. Enter/Ctrl+C encerram a captura e devolvem o controle ao menu. O monitor interativo do PlatformIO é um fluxo independente.

O menu R possui quatro opções: **1** análise de IoT; **2** análise de previsão; **3** integração IoT/previsão; **4** retorno ao menu principal (ou término quando executado diretamente). O carregamento de IoT procura `dados/historico_irrigacao.csv` e depois `dados/captura_serial.csv`. Não havia exemplo CSV disponível no checkout inspecionado em 01/11/2026.

| Etapa | Entrada | Saída / contrato |
|-------|---------|------------------|
| ESP32 | Sensores simulados | `CSV_HDR` e `CSV_ROW` a 115200 baud; `t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw` |
| Capturador Python | Porta COM ou `rfc2217://127.0.0.1:4000` do Wokwi | Acrescenta `ts_iso` de recepção no PC e persiste histórico CSV por append |
| Filtro PlatformIO | Fluxo do monitor PlatformIO | Mesmo esquema de histórico; alternativa ao capturador Python, preservada por ter função distinta |
| Previsão Python | Cidade → geocodificação → previsão horária | JSON e CSV em `dados/previsao_tempo/`; depende de internet; sem chave de API no código |
| Análises R | CSV IoT e/ou previsão | Relatórios/CSVs em `dados/analises/` e PNGs em `dados/plots/`; saídas com mesmo nome podem ser sobrescritas |

Execute um capturador serial por vez. O painel serial do Wokwi sozinho não passa pelo filtro do PlatformIO nem persiste o histórico no PC. `ts_iso` é horário de recepção, sujeito a atraso e configuração do computador; `t_rel_ms` reinicia com o ESP32.

### Associação temporal e limites estatísticos

Em `app.r`, cada horário IoT recebe a previsão de menor distância absoluta no tempo; empates usam a primeira linha da previsão. Não existe janela máxima de tolerância, e observações fora do horizonte recebem a extremidade mais próxima. A mesma previsão horária pode ser repetida para vários registros IoT. Isso pode gerar dados constantes e não aumenta o número de observações meteorológicas independentes.

O script independente `r/02_integrar_previsao.R` interpola linearmente variáveis contínuas entre limites finitos e repete os extremos fora da cobertura, sem janela máxima. Na F2-91, passou a ordenar timestamps válidos, ignorar inválidos e manter a primeira linha original em duplicatas. Categoria e metadados usam o vizinho mais próximo, com empate pelo horário anterior após a ordenação; o menu mantém empate pela primeira linha do CSV recebido. A interpolação não atravessa limites ausentes. Os métodos continuam distintos e gravam o mesmo caminho de CSV integrado.

**Pendência histórica resolvida pela F2-91:** o script independente interpretava previsão sem `Z` como horário local, produzindo diferença de três horas em `America/Bahia`. Ambos os fluxos agora usam o contrato compartilhado de [r/temporal_utils.R](../r/temporal_utils.R): previsão sem sufixo é UTC; IoT sem sufixo conserva a interpretação no fuso do computador, com fallback explícito UTC. Não houve ajuste artificial de horas nem conversão de arquivos históricos.

Nas novas saídas R, horários IoT/integrados são apresentados em `America/Bahia` com offset, e os meteorológicos em UTC. O exemplo `2026-10-31T21:33:50`, interpretado no fuso Bahia, é mostrado como `2026-10-31T21:33:50-03:00`; seu instante equivale a `2026-11-01T00:33:50Z`. Os testes comparam segundos absolutos e índices de associação antes/depois da formatação. Capturas sem offset exigem o fuso de origem correto ao analisar em outro computador.

Após as correções da auditoria de 01/11/2026, o menu R considera apenas pares finitos e verifica quantidade mínima, variação de ambas as variáveis, viabilidade numérica e R² antes de gerar uma regressão. Dados constantes não recebem estimativa de densidade. Os dados de origem/exportação são preservados; os resumos usam uma cópia com valores não finitos tratados como ausentes. O parsing do menu trata `Z`, offsets e horários sem fuso por linha; os últimos usam o fuso local no IoT e UTC na previsão. Isso não torna uma amostra pequena adequada para inferência causal.

As novas consultas meteorológicas solicitam e validam vento em m/s e UTC/offset zero antes de persistir registros; novos CSVs identificam UTC com `Z`. Na origem, o JSON histórico inspecionado declara km/h; seus dados e resultados foram preservados lá, sem conversão retroativa. O JSON e os CSVs históricos não integram a seleção F2-95. Verificar os metadados antes de comparar vento entre coletas. Não existem evidências de economia de água, acurácia agronômica, produtividade, disponibilidade contínua ou latência média medidas.

## Testes anteriores à auditoria na origem de 01/11/2026 informados pelo usuário

| Teste histórico | Resultado informado | Evidência disponível / limite |
|-----------------|---------------------|-------------------------------|
| Compilação ESP32 no PlatformIO | Aprovada | Relato do usuário; não equivale a execução na auditoria de 01/11/2026 |
| Sensores, botões NPK e bomba em cenários Wokwi | Validados | Relato do usuário e imagem do circuito; não há contagem de cenários ou taxa de acerto comprovada |
| Open-Meteo em Irecê-BA e geração JSON/CSV | Aprovada | Arquivos meteorológicos preservados na origem; API não acessada para reproduzir o teste na auditoria de 01/11/2026 |
| Análise meteorológica em R | Aprovada com 168 registros | Relato e relatório local em `dados/analises/previsao/`; sem inferir duração de monitoramento |
| Wokwi → RFC2217:4000 → Python → histórico CSV | Aprovada | Histórico local preservado; não comprova ausência universal de perda |
| Análise IoT em R | Aprovada com 5 registros após tratar regressões inviáveis | Relatório e gráficos locais preservados; amostra pequena |
| Integração IoT + previsão em R | Executada com 5 registros | Artefatos locais em `dados/analises/integrada/`; execução não demonstra controle meteorológico da bomba |

## Validações executadas na auditoria na origem de 01/11/2026

Os testes abaixo foram executados na auditoria na origem em 01/11/2026 e usaram inspeção local, dados sintéticos ou processos simulados. Eles não equivalem a executar o Wokwi, uma porta COM/RFC2217 real ou a API meteorológica, nem foram reexecutados pela revisão documental F2-78. Não representam validação do módulo integrado F2-95.

| Verificação | Resultado registrado na origem em 01/11/2026 |
|-------------|----------------------------------|
| Leitura de enunciado, fontes, configurações e documentação | Executada por inspeção local |
| Correspondência de limiares, pinos, baud, fórmula de pH e esquema CSV | Conferida com `src/prog1.ino`; documentação auxiliar corrigida |
| Sintaxe Python | **Sucesso:** `ast.parse` de 9 arquivos Python (fontes e ferramentas de teste), sem executar serviços externos |
| Suíte Python | **Sucesso após correção:** `python -X utf8 -m unittest discover -s tests -p "test_*.py" -v`; 18 testes, sendo 6 do menu, 8 do capturador serial e 4 meteorológicos; dependências externas simuladas |
| Falha inicial identificada na suíte Python | **Falha corrigida:** o teste de `--out` apontando a um diretório demonstrou conexão serial antes da rejeição do destino. Foi acrescentada validação do destino antes de conectar; a suíte completa foi reexecutada com os 18 testes aprovados |
| Sintaxe e testes R | **Sucesso:** 10 grupos em `tests/test_app_r.R`, com R 4.5.3 local; inclui parse dos três scripts R, estatísticas, regressões, datas, EOF e os três fluxos com fixtures isoladas em `tests/.tmp_r_audit/` |
| Menus reais, somente saída | **Sucesso:** entrada `4` por stdin em `python -X utf8 app.py` e no executável local Rscript com `app.r`; menus exibidos e processos encerrados, sem executar captura, consulta ou análise sobre dados existentes |
| Ajuda do capturador | **Sucesso:** `python -X utf8 scripts/serial_grava_csv.py --help`, sem conexão serial |
| Proteções do Git | Sucesso: `git check-ignore --no-index -z --stdin`; 13 caminhos locais protegidos e 6 exceções/fontes não ignorados |
| Setup Windows | Sucesso com pip simulado: execução da raiz e de `config/`; requirements localizado corretamente; nenhuma instalação real |
| Setup Bash | Tentativa falhou por indisponibilidade do ambiente (`WSL E_ACCESSDENIED`) ao executar `bash -n config/setup.sh`; sintaxe/execução Bash pendentes |
| Documentação e caminhos | **Sucesso:** verificador reutilizável `python -X utf8 tests/validar_documentacao.py`; 165 links relativos, imagens e âncoras dos 12 documentos Markdown conferidos, zero erros; nenhuma consulta a URLs externas |
| Preservação de evidências e firmware | **Sucesso:** SHA-256 de 30 arquivos comparado com o início da auditoria de 01/11/2026; todos idênticos. Inclui os 23 gerados versionados, dois CSVs locais, a imagem do circuito, o firmware e os arquivos de circuito/configuração |
| `git diff --check` dos 14 arquivos versionados de fonte/documentação alterados na auditoria de 01/11/2026 | **Sucesso**, sem erros nesses arquivos |
| `git diff --check` global | **Falha preexistente preservada em 01/11/2026:** código de saída 2, com 91 ocorrências de espaços finais nos três relatórios TXT que já estavam alterados antes da auditoria. Não foram limpos para evitar modificar as evidências |
| Compilação ESP32, Wokwi, placa física, COM/RFC2217 real e API meteorológica | **Não executados na auditoria de 01/11/2026**; os relatos anteriores permanecem separados acima |
| Instalação real de dependências | **Não executada**; os testes de setup Windows usaram pip simulado |

O Rscript usado nos testes de 01/11/2026 foi localizado na instalação existente, sem alteração do PATH permanente. Os testes não substituíram os dados de `dados/`. A leitura pontual da documentação oficial Open-Meteo, registrada na auditoria de segurança para confirmar a unidade de vento, não foi uma chamada à API de previsão.

Comando reproduzível da verificação sintática Python, executado na auditoria de 01/11/2026 a partir da raiz com resultado `9 arquivos Python: sintaxe OK`:

```powershell
python -X utf8 -c "import ast; from pathlib import Path; paths = [Path('app.py'), Path('config/setup.py'), *Path('scripts').glob('*.py'), *Path('monitor').glob('*.py'), *Path('tests').glob('*.py')]; [ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path)) for path in paths]; print(len(paths), 'arquivos Python: sintaxe OK')"
```

## Validação documental F2-78 na origem — 01/11/2026

A F2-78 revisou os 12 documentos Markdown na origem para consulta pública, mantendo os resultados técnicos da auditoria anterior separados das verificações documentais abaixo. Na origem, foram alterados dez documentos; código, testes, firmware, configurações de execução e evidências existentes permaneceram inalterados.

| Verificação da F2-78 | Resultado histórico na origem |
|---|---|
| Visibilidade do repositório original | Consulta aos metadados pelo conector GitHub retornou `visibility: public` para `EdeSufiatti/EdeSufiatti-FIAP_IA_FASE2_CAP1`; README corrigido |
| `git log --all`, `git rev-list` e `git tag --list` | Um commit alcançável em `main`, dois em todas as referências locais e nenhuma tag local; versões documentais distinguidas de commits, sem fetch |
| `python -X utf8 tests/validar_documentacao.py` | **Sucesso:** 12 documentos, 169 links relativos/imagens/âncoras, zero erros |
| Projeção virtual em `servicos/fase2-iot/` | **Sucesso:** as mesmas 169 referências permanecem dentro do módulo e apontam para destinos/âncoras existentes, com capitalização exata; sem cópia de arquivos |
| `git diff --check` dos documentos revisados | **Sucesso:** nenhum erro nos documentos; os arquivos novos também foram inspecionados diretamente quanto a espaços finais |
| `git diff --check` global | Resultado registrado na F2-78: saída 2, com 91 espaços finais nos três relatórios TXT preservados; nenhum desses arquivos foi alterado por essa revisão |
| Preservação por SHA-256 | O registro inicial contou 89 entradas de caminho e 79 entradas inalteradas. A recontagem normalizada da F2-91 identificou 23 aliases de caminhos Windows para os mesmos arquivos de dados: eram 66 arquivos físicos, dos quais dez Markdown mudaram e 56 permaneceram idênticos, sem adição ou exclusão |
| Suítes Python/R, compilação, simulador, portas reais e API meteorológica | Não reexecutados pela F2-78; resultados históricos mantidos nas seções anteriores |

Os ajustes documentais da F2-78 abrangeram README e CHANGELOG, este registro, a auditoria de segurança, o documento acadêmico, os dois guias de `config/`, os guias de `scripts/` e `src/` e o então existente índice `document/other/readme.md`, removido na F2-93. Referências legítimas a execução local, arquivos locais e RFC2217 na porta 4000 foram mantidas.

A retificação de contagem acima mantém os números originalmente registrados e explica sua origem. Ela corrige a contagem de arquivos físicos, sem invalidar os hashes nem atribuir alteração aos dados preservados.

## Correções e validações F2-91 na origem — 01/11/2026

A F2-91 revisou a árvore de trabalho na origem, preservando as alterações anteriores e os 28 arquivos que existiam em `dados/` na origem, incluindo CSVs locais ignorados. O firmware, a pinagem e a lógica agronômica permaneceram intactos. As execuções de análise naquela revisão usaram apenas fixtures sob `tests/.tmp*/`; os relatórios e gráficos históricos na origem não foram substituídos. A seleção F2-95 inclui somente os três TXT identificados no início deste documento.

### Correções comprovadas

- Inicialização Wokwi documentada uma única vez no README: abrir a pasta no VS Code, compilar o ambiente `esp32`, Ctrl + Shift + P, **Wokwi: Start Simulator**, conferir circuito/console e iniciar a opção 1 de `python app.py` para capturar. O comando pode iniciar sem nova aba `diagram.json`; o console isolado não persiste CSV e a captura depende do RFC2217 configurado.
- Relatórios e CSVs processados R passaram a identificar o fuso/offset. O exemplo Bahia `21:33:50-03:00` conserva o mesmo instante de `00:33:50Z` do dia seguinte; os testes verificam o epoch e a associação, sem aritmética artificial de horas.
- O script independente passou a tratar previsão sem sufixo como UTC, ordenar referências, ignorar inválidos e resolver duplicatas pela primeira linha original. Interpolação, vizinho mais próximo e repetição de extremos continuam identificados; não foi introduzida janela máxima.
- Novas respostas meteorológicas com registros são validadas quanto à unidade m/s e UTC/offset zero antes da persistência; CSVs novos usam `Z` e JSONs preservam a resposta bruta. Metadados incompatíveis são recusados sem substituir os destinos existentes. Os arquivos históricos em km/h não foram convertidos.

### Cenário isolado de nitrogênio e alcance dos testes

| Categoria de evidência | Resultado F2-91 na origem | Limite |
|---|---|---|
| Modelo Python da regra | Quatro testes aprovados. Umidade 70%, pH corrigido 6,3 e N=0/P=1/K=1 → bomba ligada; mantendo umidade/pH e somente mudando N para 1 → desligada. O caso pH base 6,6 menos ajuste de N=0,3 mantém pH corrigido ideal. | É uma reprodução da regra em Python com constantes lidas do `.ino`; não executa o firmware. |
| Inspeção estática e extração | Quatro testes aprovados verificam condições, constantes e extração literal de sete constantes e três funções do firmware atual. | Confirma conteúdo e preparação do harness, sem execução C++. |
| Execução C++ host das funções reais | Nove cenários preparados, mas todos **ignorados por ausência de compilador host disponível**. Não houve instalação. | Não foi realizado teste efetivo de execução C++. Um futuro teste host ainda cobrirá somente funções puras, não GPIO, relé, DHT22 ou firmware ESP32 completo. |
| Wokwi/ESP32/hardware | Não reexecutados na F2-91; os testes manuais anteriores permanecem como histórico informado. | O modelo e a inspeção não encerram homologação direta do firmware. |

O harness aceita `FARMTECH_CXX` apontando a compilador host já instalado. Se encontrar compilador e a compilação falhar, o teste falha; não converte erro de compilação em sucesso ou em skip. O único toolchain localizado nesta revisão foi Xtensa/ESP32, inadequado para executar um programa host. Artefatos C++ de teste ficam sob `tests/.tmp_firmware*/`, ignorados pelo Git.

### Validações automatizadas e verificações de ambiente

| Comando / verificação | Resultado F2-91 na origem |
|---|---|
| `python -X utf8 -m unittest discover -s tests -p "test_*.py" -v` | **40 casos: 31 aprovados e nove ignorados.** Aprovados: seis do menu, oito seriais, nove meteorológicos, quatro de inspeção/extração C++ e quatro do modelo Python. Os nove ignorados são exclusivamente os cenários C++ host. Zero falhas. |
| `Rscript tests/test_app_r.R` com R 4.5.3 existente | **16 grupos aprovados**, incluindo sintaxe de quatro fontes R, datas mistas, exemplo Bahia, preservação de instante/vizinho, referências desordenadas/duplicadas/inválidas, bordas e fluxos IoT/previsão/integração isolados. Quatro subprocessos R verificaram CLI/source e localização do helper fora da raiz. |
| Portabilidade dos testes R | Execução iniciada com `TZ=UTC` aprovada. As fixtures fixam `America/Bahia` e restauram o ambiente anterior; o caso específico em UTC testa que a apresentação em Bahia não reinterpreta uma captura feita em outro fuso. |
| Sintaxe Python | **12 arquivos aprovados** por `ast.parse`; inclui fontes e ferramentas de teste. |
| Sintaxe Bash | **Sucesso:** Bash já instalado com Git (`C:\Program Files\Git\bin\bash.exe --noprofile --norc -n config/setup.sh`), código 0. Resolve a verificação antes impedida pelo WSL; o instalador não foi executado. |
| Porta RFC2217 4000 | `Get-NetTCPConnection` retornou acesso negado; `netstat -ano -p tcp` não apresentou linha da porta 4000. Sem iniciar simulador nem alterar firewall; bind permanece não comprovado. |
| `.gitignore` e privacidade | 13 caminhos protegidos e seis exceções/fontes conferidos sem criar arquivos. Varredura heurística e inspeção da imagem sem novos achados de credenciais/PII pelos padrões descritos na auditoria de segurança; créditos originais preservados. |
| Proveniência das saídas | Na origem, a leitura encontrou oito registros IoT, 168 meteorológicos e cinco integrados. São arquivos históricos da origem, sem prova de mesma captura. Identificados PNGs remanescentes para regressões ignoradas e nomes compartilhados; nenhuma exclusão ou regeneração naquela revisão. |
| Preservação por SHA-256 | Baseline normalizado na origem: **66 arquivos físicos**, dos quais 54 permaneceram idênticos e 12 foram alterados; quatro fontes de apoio/testes foram criados. Nenhum arquivo excluído na revisão. Todos os 28 arquivos de dados da origem, firmware, imagem e configurações de execução permaneceram idênticos. |
| `git diff --check` global | Resultado registrado na F2-91: código 2, com 91 ocorrências de espaços finais nos três relatórios TXT preexistentes. Os três arquivos foram preservados; o problema não foi introduzido nessa revisão. |
| Documentação e inclusão em subpasta | **Sucesso:** `python -X utf8 tests/validar_documentacao.py`, 12 documentos e 209 referências locais, sem erros. Projeção virtual das mesmas referências em `servicos/fase2-iot/` aprovada com capitalização exata e âncoras, sem cópia. |
| `git diff --check` das fontes/documentos revisados | **Sucesso:** nenhum erro; helper/testes/documentos novos também conferidos diretamente, sem espaços finais. |

Para reproduzir no Windows, use o executável Rscript da instalação existente ou configure o PATH conforme o guia de `config/`. Na execução auditada, `TMPDIR` apontou para `tests/.tmp_r_audit/` e `LC_ALL=English_United States.utf8` evitou o locale incompatível herdado. Nenhuma dependência foi instalada; API meteorológica, serial real e Wokwi não foram acessados para repetir os testes manuais.

### Arquivos da F2-91

| Arquivos alterados em relação ao início da F2-91 | Finalidade |
|---|---|
| [README.md](../README.md), [CHANGELOG.md](../CHANGELOG.md) | Wokwi, contratos de dados e histórico F2-91 |
| [app.r](../app.r), [r/02_integrar_previsao.R](../r/02_integrar_previsao.R) | Apresentação explícita e correções temporais |
| [scripts/weather_forecast.py](../scripts/weather_forecast.py) | Validação dos metadados e UTC explícito antes da persistência |
| [tests/test_app_r.R](../tests/test_app_r.R), [tests/test_weather_forecast.py](../tests/test_weather_forecast.py) | Regressões temporais e meteorologia offline |
| [AUDITORIA_SEGURANCA_F2.md](AUDITORIA_SEGURANCA_F2.md), [RASTREABILIDADE_F2.md](RASTREABILIDADE_F2.md) | Achados, evidências, seleção de saídas, resultados e limites |
| [documento técnico](ai_project_document_fiap.md), [scripts/readme.md](../scripts/readme.md), [src/readme.md](../src/readme.md) | Contratos corrigidos e referência ao procedimento único Wokwi |

| Arquivos criados | Finalidade |
|---|---|
| [r/temporal_utils.R](../r/temporal_utils.R) | Parsing, apresentação, vizinho e interpolação compartilhados |
| [tests/firmware_host_harness.py](../tests/firmware_host_harness.py) | Preparar trechos literais do `.ino` para compilador host |
| [tests/test_firmware_cpp.py](../tests/test_firmware_cpp.py) | Separar inspeção/extração de cenários C++ executáveis quando houver compilador |
| [tests/test_firmware_model.py](../tests/test_firmware_model.py) | Modelo Python explicitamente separado da execução C++ |

### Pendências e recomendação

**Apto com ressalvas para integração acadêmica dos fontes** em `servicos/fase2-iot/`. A avaliação F2-91 considera a estrutura, as dependências, os testes e a documentação do módulo, com as limitações técnicas descritas a seguir.

Continuam pendentes a comprovação do bind da porta 4000 com servidor disponível, a execução dos cenários C++ host e a validação serial real, sem repetir os testes manuais Wokwi já relatados. A seleção de evidências históricas exige identificar método, unidade, fuso e proveniência; gerados não devem ser apresentados como homologação do código atual. As saídas JSON/CSV não são transacionais em falha de disco, os métodos temporais continuam distintos e fora da cobertura repetem extremos sem tolerância máxima. Execução real de instaladores e análise de vulnerabilidades de dependências não foram realizadas; a sintaxe Bash foi validada sem instalar nada.

Os limites de sensores didáticos, umidade inicial e leitura antiga após falha DHT22, além da ausência de validação elétrica/agronômica, **impedem recomendar acionamento de bomba física real**. A aprovação de modelos e testes no PC não remove essa restrição. A F2-91 preservou o firmware e as evidências anteriores.

## Estrutura e higiene documental F2-93 na origem — 01/11/2026

- Na origem, enunciado realocado da raiz para `document/ENUNCIADO_F2.md`, com conteúdo integral e atribuição institucional à FIAP preservados. Esse arquivo foi omitido da seleção F2-95; os requisitos deste módulo estão na síntese autoral e na matriz acima.
- Remoção do antigo `document/other/readme.md`, sem conteúdo técnico específico. A documentação complementar permanece concentrada em `document/`.
- README simplificado como entrada do módulo, com acesso aos procedimentos, documentos técnicos e evidências nas respectivas páginas. Os detalhes de captura serial, esquema CSV, timeout meteorológico e caminhos das análises R estão no guia de `scripts/`.
- Regras de TSV/XLS/XLSX limitadas a `dados/`, preservando fixtures e documentos dessas extensões fora da pasta de dados. Mantidos `secrets.*` global, as regras de `.vscode/` e o destino reservado `dados/irrigacao_exemplo.csv` para exemplo sintético/revisado; esse CSV permanece ausente.
- `.gitattributes` mantém `* text=auto` e define `*.sh text eol=lf` e `*.bat text eol=crlf`, sem renormalizar arquivos existentes.

A reprodução integral do enunciado na origem preservou sua atribuição institucional, mas a auditoria não encontrou comprovação da autorização para essa reprodução. A confirmação humana aplicável a eventual reprodução está registrada na [auditoria de segurança](AUDITORIA_SEGURANCA_F2.md). Os resultados técnicos e inventários históricos na origem não foram substituídos por novas medições na F2-93.

| Verificação F2-93 | Resultado histórico na origem |
|---|---|
| Integridade do enunciado | Na origem, corpo original preservado byte a byte sob o prefixo de atribuição FIAP; SHA-256 do corpo: `4892a31288dfe920806291284e89128c0b13b65a918832a85c6a36f586446c20`. O arquivo integral não foi incluído na seleção F2-95. |
| Links, imagens e âncoras | `python -X utf8 tests/validar_documentacao.py`: 11 documentos Markdown, 217 referências locais e zero erros |
| Regras de ignore | 52 casos aprovados por `git check-ignore --no-index -z --stdin`: 33 caminhos protegidos e 19 legítimos; os caminhos hipotéticos não foram criados |
| Atributos de texto e EOL | 12 verificações de `git check-attr` aprovadas: LF para shell, CRLF para batch; demais fontes/PNG mantêm `text=auto` e EOL não especificado; sem renormalização |

## Finalização documental F2-94 na origem — 01/11/2026

A F2-94, realizada na origem, distingue fonte institucional, registro acadêmico dos requisitos e documentação autoral da implementação. Acrescentou uma proposta de síntese pública e orientações de proveniência para a integração. O enunciado integral permaneceu preservado na origem; os créditos originais acompanham o módulo selecionado.

Os resultados de execução mantidos são os da F2-91 na origem: **31 testes Python aprovados, nove cenários C++ host ignorados por ausência de compilador e 16 grupos R aprovados**. A F2-94 foi documental e não reexecutou essas suítes nem acrescentou validação de simulador, hardware ou API meteorológica. Esses números não são resultados de execução na F2-95.

### Origem dos módulos na integração

Cada módulo deve identificar seu repositório original e preservar seus créditos no próprio README. Para o README principal do projeto integrado, a orientação é usar uma tabela de fase, módulo e repositório original. A linha de origem identificada para a Fase 2 é:

| Fase | Módulo | Repositório original |
|---|---|---|
| 2 | `servicos/fase2-iot/` | [EdeSufiatti/EdeSufiatti-FIAP_IA_FASE2_CAP1](https://github.com/EdeSufiatti/EdeSufiatti-FIAP_IA_FASE2_CAP1) |

A consulta de metadados do GitHub em 01/11/2026 confirmou o nome do repositório original, visibilidade pública e branch padrão `main`. Essa é a única linha de origem confirmada para esta orientação. A disponibilidade pública descreve exclusivamente o repositório original, não o projeto integrado, cuja política é privada até a avaliação. A confirmação das condições de distribuição e reutilização permanece com os titulares.

### Verificações documentais da F2-94 na origem

| Verificação | Resultado histórico F2-94 na origem |
|---|---|
| Links, imagens e âncoras | 11 documentos Markdown, 215 referências locais e zero erros no verificador documental. A projeção virtual em `servicos/fase2-iot/` conferiu as 215 referências e 23 fragmentos com capitalização, âncoras e contenção válidas. |
| Prévia local | Renderização MarkdownIt em memória confirmou um link com o rótulo `Repositório original — Fase 2`, imagem do circuito, seis passos Wokwi e sete créditos originais: cinco integrantes e dois docentes. PNG verificado em 926 × 436 pixels e inspecionado visualmente, sem alteração. |
| Regras do Git e preservação | 52 casos de ignore aprovados: 33 protegidos e 19 legítimos; 12 verificações de atributos aprovadas. Os 54 arquivos protegidos de código, dados e configuração permaneceram idênticos, assim como o enunciado integral, `.gitignore` e `.gitattributes`. |
| Qualidade do diff | Baseline de 69 arquivos: cinco Markdown alterados, 64 idênticos e nenhum arquivo adicionado ou excluído. O `git diff --check` dos documentos revisados foi aprovado, assim como a conferência direta dos documentos não rastreados. O diff global mantém código 2 por 91 ocorrências preexistentes nos relatórios: 38 no integrado, 28 no IoT e 25 no meteorológico, sem outro erro. |
| Inventário de evidências | Na origem, tabela com cobertura exata dos 28 arquivos: três recomendados para manter, 14 opcionais e 11 não recomendados para publicação, preservando os originais e as ressalvas de proveniência. A F2-95 selecionou somente os três TXT históricos. |

## Inventário histórico da auditoria na origem de 01/11/2026

Os **14 arquivos versionados alterados ou complementados na auditoria na origem de 01/11/2026** são os seguintes. README, menus e capturador já continham correções locais no início daquela auditoria, que foram preservadas. Este inventário registra a entrega técnica na origem; não é uma contagem da seleção F2-95 nem do diff após revisões posteriores.

| Arquivo | Alteração |
|---------|-----------|
| [.gitignore](../.gitignore) | Remoção de duplicidade e proteção de caches, ambientes, builds, dados locais, credenciais e temporários |
| [README.md](../README.md) | Menus atuais, fluxos seriais, dependências/PATH, documentação técnica, limites e evidências |
| [app.py](../app.py) | Nomes internos, subprocessos, diretório de execução, encerramento e tratamento de falhas/EOF |
| [app.r](../app.r) | Dados não finitos/constantes, regressões, datas, associação temporal, relatório e EOF |
| [config/SETUP_INSTRUCTIONS.md](../config/SETUP_INSTRUCTIONS.md) | Instalação e execução didáticas, especialmente PATH do Rscript/Python no Windows |
| [config/readme.md](../config/readme.md) | Dependências reais por fluxo e responsabilidades dos instaladores |
| [config/setup.bat](../config/setup.bat) | Localização do requirements pelo próprio script e mensagens atualizadas |
| [config/setup.py](../config/setup.py) | Mensagens de uso e captura Python atualizadas |
| [config/setup.sh](../config/setup.sh) | Caminhos de projeto/requirements derivados do script e mensagens atualizadas |
| [document/ai_project_document_fiap.md](ai_project_document_fiap.md) | Descrição técnica coerente com fonte, métricas/depoimentos sem comprovação retirados e limites de evidências |
| [scripts/readme.md](../scripts/readme.md) | Captura independente, alternativa PlatformIO, meteorologia, retorno e códigos de erro |
| [scripts/serial_grava_csv.py](../scripts/serial_grava_csv.py) | Validação de entrada/destino, linhas parciais, erros e preservação de histórico, mantendo COM/RFC2217 |
| [scripts/weather_forecast.py](../scripts/weather_forecast.py) | Escape CSV e solicitação explícita de vento em m/s |
| [src/readme.md](../src/readme.md) | Fórmula LDR, debounce, esquema CSV, compilação/simulação e limites do firmware |

Foram **criados oito arquivos de auditoria/validação**:

| Arquivo | Finalidade |
|---------|------------|
| [CHANGELOG.md](../CHANGELOG.md) | Separar funcionalidades originais e correções da auditoria |
| [document/AUDITORIA_SEGURANCA_F2.md](AUDITORIA_SEGURANCA_F2.md) | Achados, classificação de risco, medidas e pendências |
| [document/RASTREABILIDADE_F2.md](RASTREABILIDADE_F2.md) | Matriz de requisitos, resultados, evidências e inventário da auditoria de 01/11/2026 |
| [tests/test_app.py](../tests/test_app.py) | Testes do menu e ciclo de vida de subprocessos |
| [tests/test_serial_capture.py](../tests/test_serial_capture.py) | Testes de protocolo, append, conexão, erros e integridade da captura |
| [tests/test_weather_forecast.py](../tests/test_weather_forecast.py) | Testes offline de parâmetros, URL e estrutura CSV meteorológica |
| [tests/test_app_r.R](../tests/test_app_r.R) | Testes com R base e fixtures isoladas |
| [tests/validar_documentacao.py](../tests/validar_documentacao.py) | Verificação reproduzível de links relativos, imagens e âncoras |

**Evidências preservadas na origem em 01/11/2026:** a imagem `assets/circuito_wokwi.png` e os artefatos que existiam em `dados/` na origem mantiveram seu conteúdo. A inspeção na origem identificou 23 saídas geradas versionadas: três relatórios TXT, 19 PNGs e um JSON. Os CSVs locais estavam abrangidos pelas regras de ignore. Os temporários dos testes foram gravados sob `tests/.tmp*/`, sem substituir os artefatos na origem. Na seleção F2-95, somente os três TXT acompanham o módulo como dados históricos.

## Organização e pendências identificadas na origem em 01/11/2026

- Há sobreposição intencional de persistência entre `monitor/filter_irrigation_csv.py` e `scripts/serial_grava_csv.py`: o primeiro depende do monitor PlatformIO, o segundo executa diretamente com PySerial. Ambos foram preservados.
- Na origem, relatórios, gráficos e JSON gerados já constavam no versionamento. **23 arquivos gerados versionados na origem** foram identificados na inspeção de 01/11/2026; nenhum foi excluído ou restaurado naquela auditoria. A seleção F2-95 inclui os três TXT e omite os demais dados. Regras de ignore não removem o rastreamento de arquivos de um repositório existente.
- `dados/irrigacao_exemplo.csv` e `.vscode/tasks.json`, citados em instruções antigas, não estavam presentes. Não são tratados como evidências ou pré-requisitos existentes; use os comandos diretos documentados.
- O antigo `document/other/readme.md` era um placeholder na auditoria técnica inicial e foi convertido em índice na F2-78. A F2-93 removeu esse arquivo; o caminho é mencionado apenas como registro histórico.
- `config/readme.md` detalha dependências e `config/SETUP_INSTRUCTIONS.md` detalha instalação. `src/readme.md` detalha firmware; o documento técnico registra contexto e limites. Há conteúdo relacionado, sem necessidade de reorganizar pastas ou quebrar referências.
- O documento técnico conserva a bibliografia original, mas informa que as referências não foram verificadas externamente. Depoimentos e métricas sem evidência foram retirados como resultados demonstrados.
- O enunciado institucional de autoria FIAP permanece no projeto de origem, fora da seleção F2-95. Os requisitos do módulo são documentados na síntese autoral e na matriz deste registro. A autorização para eventual reprodução integral não foi comprovada pela auditoria e exige confirmação humana.
- As condições pretendidas de distribuição/reutilização do código e da documentação da equipe dependem de registro pelos titulares. Uma licença específica não foi identificada e poderá ser definida se escolhida por eles; a licença atribuída ao template é documentada separadamente.
- Validação em campo, execução direta dos cenários C++, confirmação da interface RFC2217 e verificação acadêmica do vídeo têm os limites de evidência descritos neste documento. A situação de cada verificação está nas seções de testes e em [AUDITORIA_SEGURANCA_F2.md](AUDITORIA_SEGURANCA_F2.md).

## Homologação automatizada F2-95 — 01/11/2026

Execução a partir da raiz integrada servicos/fase2-iot/, com fixtures isoladas. Os resultados abaixo são desta execução; os registros F2-78–94 permanecem como histórico da origem.

| Verificação | Resultado F2-95 |
|---|---|
| Python | 40 casos: 31 aprovados e 9 ignorados; os ignorados são cenários C++ host sem compilador compatível |
| R | 16 grupos aprovados com o Rscript instalado; entradas e saídas em fixtures |
| Documentação | 10 documentos; 216 links relativos/imagens/ancoras; 0 erros. |
| Menus | Opção 4 de Python e R executada; retorno 0, sem captura ou consulta meteorológica |
| Integridade | 43 arquivos selecionados; três TXT idênticos à origem, incluindo seus espaços finais; origem e os 25 arquivos preexistentes da Fase 1 preservados |
| Git do consolidado | **Não aplicável ao diretório de consolidação nesta etapa:** `git status`, `git diff`, `git check-ignore` e `git check-attr`. A pasta existente foi utilizada conforme autorização, sem inicializar Git; essa condição não é falha de homologação. |

**Parecer: aprovada com ressalvas** para integração acadêmica. Permanecem os limites documentados de RFC2217, C++ host, sensores didáticos e condições de distribuição; não impedem esta avaliação acadêmica.

**Fase 2 — auditoria concluída e módulo integrado à estrutura da Fase 7.**
