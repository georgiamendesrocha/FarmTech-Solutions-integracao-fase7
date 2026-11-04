# Auditoria de segurança e higiene — FarmTech Solutions, Fase 2

**Auditoria de 01/11/2026. Escopo histórico:** projeto de origem `farmtech-fase2` e preparação documental para a Fase 7. Os inventários, referências Git e resultados das revisões até a F2-94 descrevem a origem. A seleção F2-95 para `servicos/fase2-iot/` inclui somente três TXT de dados; os outros 25 arquivos de dados e o enunciado institucional integral foram omitidos, preservados na origem. Este registro não substitui avaliação de segurança em ambiente real.

Foram inspecionados os menus Python/R, coletores seriais, consulta meteorológica, firmware e configurações, scripts de instalação, documentos e regras do Git. Os créditos originais permanecem no [README principal](../README.md). As correções desta auditoria não transferem autoria das funcionalidades originais.

## Critério de classificação

- **Alto:** exposição comprovada de credencial ou execução indevida com impacto relevante.
- **Médio:** perda/corrupção de dados, conclusão analítica inadequada ou exposição dependente da configuração de rede.
- **Baixo:** limitação operacional ou de prevenção com impacto restrito ao uso local.

As classificações abaixo consideram um protótipo didático executado localmente. Não há validação de instalação em campo, controle de bomba real ou infraestrutura pública.

## Achados e tratamento

| ID | Risco | Evidência e impacto | Medida aplicada / situação |
|---|---|---|---|
| SEG-01 | Médio, condicionado à rede | `app.py` conecta a `rfc2217://127.0.0.1:4000`; `wokwi.toml` define a porta 4000. A configuração de cliente não prova a interface de escuta do servidor. A URL usada não configura TLS nem autenticação. | Mantido cliente em loopback. Documentado uso local; não encaminhar a porta no roteador nem expô-la à Internet. Na leitura local da F2-91, `Get-NetTCPConnection` retornou acesso negado (`0x80041003`) e `netstat -ano -p tcp` não mostrou linha da porta 4000. Não foi iniciado servidor/simulador. Interface efetiva de escuta e regras do firewall permanecem pendentes de verificação com simulador ativo. |
| SEG-02 | Médio | Dados recebidos por serial tornam-se entrada de CSV e análises. Uma linha incompleta ou adulterada pode invalidar colunas e relatórios. O filtro PlatformIO aceita conteúdo após `CSV_ROW,` sem validação de esquema/tipos. | Coletor Python passa a validar dez campos numéricos finitos, faixas do protocolo e flags 0/1; acumula leituras parciais e descarta linhas acima de 4096 bytes. Cabeçalho incompatível impede append. Testes registrados na [rastreabilidade](RASTREABILIDADE_F2.md). Filtro independente preservado; usar somente firmware/fonte confiável, pois endurecê-lo permanece pendência se receber dados não confiáveis. |
| SEG-03 | Médio | Dois coletores escrevendo simultaneamente em `dados/historico_irrigacao.csv` podem duplicar/amalgamar registros. Não há bloqueio entre o filtro PlatformIO e o coletor Python. | Ambos preservados porque têm funções distintas: filtro integrado ao monitor e coletor autônomo usado pelo menu. Executar apenas um coletor por vez. Não foi adicionada infraestrutura de bloqueio. |
| SEG-04 | Médio | `scripts/weather_forecast.py` escrevia CSV por concatenação. Vírgulas, aspas e quebras de linha em nomes podiam alterar a estrutura. | Substituído por `csv.DictWriter`; teste de ida e volta com esses caracteres aprovado sem rede. |
| SEG-05 | Médio, integridade analítica | O JSON meteorológico preservado na auditoria de 01/11/2026 declara `hourly_units.windspeed_10m = km/h`, embora a coluna e os rótulos R usem `wind_ms`/m/s. | A consulta solicita `wind_speed_unit=ms`, conforme a [documentação oficial Open-Meteo](https://open-meteo.com/en/docs). Na F2-91, a normalização passou a exigir metadados de vento em m/s e UTC com deslocamento zero antes de abrir as saídas; incompatibilidade é rejeitada, sem converter nem substituir os arquivos existentes. O CSV novo explicita UTC com segundos e `Z`; o JSON guarda a resposta bruta. Os artefatos históricos foram preservados sem conversão e exigem conferência de unidade antes de comparar coletas. |
| SEG-06 | Baixo | `.gitignore` repetia `.pio` e não prevenia inclusão de vários caches, ambientes, segredos locais e novos relatórios/gráficos. O padrão global `*.csv` também ocultava CSV fora da pasta de dados. | Regras organizadas, sem duplicação, com proteção de ambientes/caches Python e R, builds, credenciais comuns, temporários e saídas em `dados/`. CSV fora de `dados/` deixa de ser ocultado indiscriminadamente; dados locais devem permanecer nessa pasta. Exceções preservam tarefas compartilháveis e exemplo CSV caso venha a ser fornecido. |
| SEG-07 | Médio, preservação de evidências | A auditoria de 01/11/2026 identificou dados e resultados já rastreados pelo Git, incluindo modificações anteriores à inspeção. Ignorar um caminho não interrompe seu rastreamento. Gráficos antigos podem sobreviver quando uma regressão deixa de ser viável. | Nenhum dado, relatório ou gráfico existente foi excluído, restaurado, convertido ou sobrescrito pela auditoria. Inventário abaixo; decisão sobre seleção/remoção do versionamento fica para revisão humana. |
| SEG-08 | Baixo | `--fresh` no coletor e as saídas de previsão/análise permitem substituição dos arquivos escolhidos. `--out`, `--out-json` e `--out-csv` são caminhos fornecidos pelo operador local. A gravação meteorológica ocorre primeiro em JSON e depois em CSV; uma falha de I/O na segunda saída pode deixar arquivos de coletas distintas. | Mantido o comportamento explícito de ferramenta local. O menu usa append para a captura. Guardar cópia das evidências antes de executar opções que regravam saídas e, para outra coleta, preferir destinos identificados. Conferir o sucesso das duas gravações; a validação prévia de unidade/UTC não torna o par transacional. Não fornecer caminhos de fontes não confiáveis. Os testes registrados em 01/11/2026 usaram temporários dentro de `tests/`. |
| SEG-09 | Baixo | Setups `.bat`/`.sh` buscavam `requirements.txt` a partir da pasta corrente, podendo falhar ou ler outro arquivo. As dependências aceitam versões mínimas sem lock completo. | Setups corrigidos referenciam `config/requirements.txt` pela localização do próprio script; teste Windows com pip simulado aprovado. Permanecem versões abertas, sem promessa de reprodução exata nem auditoria de vulnerabilidades das dependências. Nenhuma dependência foi instalada durante a auditoria de 01/11/2026. |
| SEG-10 | Baixo | CSV com texto externo pode ser interpretado como fórmula ao ser aberto por programas de planilha. Escape CSV mantém a estrutura, mas não é proteção contra fórmulas. | O fluxo atual usa leitura de dados em R e não executa texto do CSV como código. Ao abrir arquivos de terceiros em planilha, importar campos como texto. Não foram alterados dados originais nem adicionada conversão silenciosa de conteúdo. |
| SEG-11 | Médio, condicionado ao uso físico | A umidade inicia em zero antes da primeira leitura DHT22, cujo intervalo é de 2000 ms. Leituras `NaN` conservam o valor anterior; o firmware não impõe expiração dessa leitura. Uma decisão pode, portanto, usar valor inicial ou informação antiga. | Firmware preservado no escopo do protótipo simulado. A limitação está descrita no [guia do firmware](../src/readme.md). Antes de acionar hardware real, revisar validade/frescor das leituras, comportamento em falha e condições elétricas e agronômicas com validação própria. |
| SEG-12 | Médio, integridade temporal; defeitos de fuso/ordenação corrigidos na F2-91 | Na inspeção inicial, o script independente interpretava previsão sem `Z` no fuso local e pressupunha ordenação, podendo deslocar a associação em três horas em `America/Bahia`. A apresentação em R também podia ocultar o fuso do instante preservado. | A F2-91 adicionou [r/temporal_utils.R](../r/temporal_utils.R): IoT sem fuso segue o fuso local com fallback UTC; previsão sem sufixo é UTC. A apresentação/exportação usa `America/Bahia` com offset explícito, preservando o instante. O script independente ignora timestamps inválidos, ordena a previsão e preserva a primeira linha original em duplicatas. Dezesseis grupos de testes R foram aprovados com fixtures. Permanecem os métodos distintos, a ausência de tolerância máxima e o caminho de CSV compartilhado entre menu e script independente; identificar o método e a cobertura antes de comparar saídas. |
| SEG-13 | Baixo, proveniência documental | A origem contém `document/ENUNCIADO_F2.md`, reprodução integral de material institucional da FIAP cuja autorização não foi comprovada pela auditoria. | O arquivo institucional foi omitido da seleção F2-95. Os requisitos são apresentados pela [síntese autoral](RASTREABILIDADE_F2.md#síntese-autoral-proposta-para-os-requisitos) e pela matriz acadêmica. A omissão evita distribuir essa reprodução no módulo; não comprova autorização de reprodução nem transfere autoria institucional. |

## Controles observados

- Subprocessos recebem argumentos em listas, sem `shell=True`; a cidade informada é passada como argumento e codificada com `urllib.parse.urlencode` nas URLs.
- O menu executa subprocessos na raiz do projeto. Ao encerrar a captura, aguarda o processo após `terminate` e, se necessário, `kill`; sondagens TCP repetidas durante a captura foram removidas. O coletor faz flush a cada registro e fecha a serial em `finally`. `--fresh` somente abre a saída para substituição após a conexão serial ter sido estabelecida.
- A consulta usa endpoints HTTPS fixos e timeout de 15 segundos por requisição. Erros de consulta são tratados; não existe mecanismo de envio da previsão para acionar o firmware.
- O firmware transmite leituras e calcula a irrigação localmente; DHT22 e LDR têm papéis didáticos. Esta auditoria não alterou pinos, lógica agronômica nem firmware.
- Não foram encontradas chaves privadas, tokens de formatos conhecidos, atribuições de credenciais ou credenciais em URLs na varredura heurística textual da árvore de trabalho. Os valores dos arquivos não foram incluídos no relatório. Isso não certifica ausência de segredos: o histórico completo do Git, arquivos binários, caches/builds, perfis externos e serviços não foram auditados.
- Os caminhos de execução são derivados da raiz/do arquivo ou relativos ao projeto. Exemplos de instalação devem usar caminhos genéricos, sem registrar o perfil pessoal da máquina na documentação.

## Inventário de dados na origem e seleção F2-95

Na auditoria da origem em 01/11/2026, `git ls-files dados` identificou **23 arquivos gerados rastreados: três relatórios TXT, 19 PNGs e um JSON**. Os PNGs se dividem em oito de IoT, quatro de previsão e sete de regressão. Todos foram preservados na origem. Esse inventário não descreve arquivos distribuídos no módulo integrado: a F2-95 selecionou somente os três TXT.

Na auditoria de 01/11/2026, foram encontrados CSV locais ignorados pelo Git, incluindo histórico, previsão e resultados de análise/integração. O caminho `dados/irrigacao_exemplo.csv` era citado pela documentação anterior, mas o arquivo não foi localizado naquela inspeção; ele não foi fabricado para preencher essa ausência.

### Recontagem e limites das evidências na F2-91 — 01/11/2026

A recontagem confirmou os **23 gerados versionados: três relatórios TXT, 19 PNGs e um JSON**. A inspeção somente de leitura encontrou oito registros no histórico IoT e no relatório IoT, 168 no CSV de previsão e cinco no CSV integrado. Essas quantidades descrevem os arquivos encontrados pela F2-91; não substituem os testes históricos com cinco registros relatados na auditoria anterior. Os artefatos não devem ser tratados automaticamente como saídas da mesma captura ou versão do código.

Ignorar um ajuste não apaga o arquivo anterior. O relatório IoT registra três ajustes ignorados, e o integrado registra dois. O relatório meteorológico registra salvamento de três regressões, mas isso não comprova a versão que as produziu. O nome do PNG, sua presença ou o estado modificado no Git não bastam para determinar sua coleta. A F2-91 não regenerou esses artefatos para tentar conciliar as diferenças.

<a id="seleção-final-dos-28-arquivos-de-dados"></a>

### Inventário histórico dos 28 arquivos e seleção F2-95

A revisão F2-94, em 01/11/2026, considerou os **28 arquivos existentes na origem: os 23 rastreados e cinco CSV locais ignorados**. A tabela preserva essa recomendação histórica: **manter** significa conservar como registro histórico; **incluir opcionalmente** exige finalidade e contexto identificados; **não publicar** recomenda não distribuir o arquivo na forma inspecionada. A coluna **Seleção F2-95** define o conteúdo desta seleção: três incluídos e 25 omitidos. Todos os originais permanecem na origem. As classificações não comprovam licença, procedência completa ou validação do código integrado.

Os três TXT são **registros históricos inspecionados em 01/11/2026**, com data de geração não comprovada. Seus formatos antigos de horário, unidades e registros de ajustes ignorados precisam acompanhar a interpretação; não representam as novas saídas do código revisado. Essa distinção também se aplica aos demais derivados: a inspeção não estabelece que foram produzidos juntos. A inspeção visual dos dois PNGs de vento confirmou rótulos `m/s`, enquanto o JSON histórico declara `km/h`; os números antigos não foram convertidos.

| Caminho na origem | Tipo / rastreamento na origem | Recomendação F2-94 | Justificativa técnica | Decisão humana sobre uso futuro | Seleção F2-95 |
|---|---|---|---|---|---|
| `dados/analises/integrada/analise_integrada.txt` | TXT rastreado | **Manter** | Registro histórico inspecionado em 01/11/2026; geração não comprovada. Documenta integração e ajustes ignorados; não valida o código atual. | Confirmar a identificação histórica e as lacunas de método/fuso antes de usá-lo como evidência. | **Incluído** |
| `dados/analises/iot/analise_historico.txt` | TXT rastreado | **Manter** | Registro histórico inspecionado em 01/11/2026; geração não comprovada. Descreve oito registros e regressões ignoradas; não é homologação atual. | Preservar o contexto da captura e distinguir os oito registros dos cinco do teste anteriormente relatado. | **Incluído** |
| `dados/analises/previsao/analise_previsao.txt` | TXT rastreado | **Manter** | Registro histórico inspecionado em 01/11/2026; geração não comprovada. Descreve 168 previsões; o vento histórico é km/h, apesar de `wind_ms`. | Identificar a unidade histórica e a ausência de comprovação de versão/data de geração. | **Incluído** |
| `dados/plots/iot/barra_bomba_agua.png` | PNG rastreado | **Incluir opcionalmente** | Frequências de estados da bomba no conjunto histórico; não mede vazão ou economia de água. | Selecionar apenas com identificação da captura e essa limitação. | **Omitido** |
| `dados/plots/iot/barra_k.png` | PNG rastreado | **Incluir opcionalmente** | Frequência da flag K simulada; não representa concentração de potássio. | Confirmar finalidade didática e contexto da coleta. | **Omitido** |
| `dados/plots/iot/barra_n.png` | PNG rastreado | **Incluir opcionalmente** | Frequência da flag N simulada; não representa concentração de nitrogênio. | Confirmar finalidade didática e contexto da coleta. | **Omitido** |
| `dados/plots/iot/barra_p.png` | PNG rastreado | **Incluir opcionalmente** | Frequência da flag P simulada; não representa concentração de fósforo. | Confirmar finalidade didática e contexto da coleta. | **Omitido** |
| `dados/plots/iot/grafico_ph_corrigido.png` | PNG rastreado | **Incluir opcionalmente** | Descreve pH didático derivado de LDR/NPK, sem medição química ou calibração real. | Identificar o cálculo simulado e não apresentar como ensaio de solo. | **Omitido** |
| `dados/plots/iot/grafico_temperatura_c.png` | PNG rastreado | **Incluir opcionalmente** | Descritivo histórico da temperatura do DHT22; temperatura não controla a bomba. | Vincular à captura histórica e não apresentar como nova execução. | **Omitido** |
| `dados/plots/iot/grafico_tempo_relativo_ms.png` | PNG rastreado | **Incluir opcionalmente** | `millis()` é tempo desde reset, não horário civil; sessões podem conter reinicializações. | Identificar sessões/resets antes de interpretar continuidade temporal. | **Omitido** |
| `dados/plots/iot/grafico_umidade.png` | PNG rastreado | **Incluir opcionalmente** | DHT22 mede umidade do ar, usada didaticamente como solo; o conjunto histórico é limitado. | Declarar a substituição didática e o contexto da captura. | **Omitido** |
| `dados/plots/previsao/grafico_chuva_mm.png` | PNG rastreado | **Incluir opcionalmente** | Descreve precipitação prevista, sem comprovar chuva observada ou resposta da bomba. | Identificar local/período da previsão e ausência de controle meteorológico do firmware. | **Omitido** |
| `dados/plots/previsao/grafico_temperatura_c.png` | PNG rastreado | **Incluir opcionalmente** | Descritivo de temperatura prevista; não é aferição de campo nem reprodução do código revisado. | Identificar a coleta meteorológica e sua finalidade ilustrativa. | **Omitido** |
| `dados/plots/previsao/grafico_umidade.png` | PNG rastreado | **Incluir opcionalmente** | Umidade meteorológica prevista, distinta da variável didática de solo do IoT. | Explicitar a diferença entre as duas fontes de umidade. | **Omitido** |
| `dados/plots/previsao/grafico_vento_ms.png` | PNG rastreado | **Não publicar** | Os rótulos visíveis indicam m/s, mas a fonte histórica declara km/h; publicar sem correção induziria erro de unidade. | Escolher uma saída futura com unidade verificada; preservar este original sem conversão silenciosa. | **Omitido** |
| `dados/plots/regressao/regressao_temperatura_c_vs_chuva_mm.png` | PNG rastreado | **Incluir opcionalmente** | Há registro de salvamento no relatório meteorológico; origem/versão exatas não comprovadas, sem inferência causal. | Vincular explicitamente ao histórico meteorológico e conferir o contexto antes de selecionar. | **Omitido** |
| `dados/plots/regressao/regressao_temperatura_c_vs_ph_corrigido.png` | PNG rastreado | **Não publicar** | O relatório IoT inspecionado informa ajuste ignorado; o PNG remanescente não comprova regressão para aquele conjunto. | Preservar como remanescente; só reconsiderar com identificação da execução produtora. | **Omitido** |
| `dados/plots/regressao/regressao_temperatura_c_vs_temperatura_prevista_c.png` | PNG rastreado | **Não publicar** | O relatório integrado inspecionado informa ajuste ignorado; a existência do PNG não comprova ajuste válido da integração. | Preservar como remanescente; só reconsiderar com proveniência independente comprovada. | **Omitido** |
| `dados/plots/regressao/regressao_temperatura_c_vs_umidade.png` | PNG rastreado | **Incluir opcionalmente** | Caminho compartilhado: IoT registra ajuste ignorado e meteorologia registra salvamento. Proveniência ambígua, sem classificação automática como obsoleto. | Identificar a execução produtora; se selecionado sem confirmação, declarar expressamente a ambiguidade histórica. | **Omitido** |
| `dados/plots/regressao/regressao_temperatura_c_vs_vento_ms.png` | PNG rastreado | **Não publicar** | O relatório meteorológico registra salvamento, mas os rótulos visíveis indicam m/s para fonte histórica em km/h. | Escolher uma saída futura com unidade verificada; preservar o original identificado como inadequado para divulgação. | **Omitido** |
| `dados/plots/regressao/regressao_tempo_relativo_ms_vs_umidade.png` | PNG rastreado | **Não publicar** | O relatório IoT inspecionado informa ajuste ignorado; o PNG não demonstra regressão válida para esse conjunto. | Preservar como remanescente e exigir identificação da execução antes de reconsiderar. | **Omitido** |
| `dados/plots/regressao/regressao_umidade_vs_forecast_umidade.png` | PNG rastreado | **Não publicar** | O relatório integrado inspecionado informa ajuste ignorado; o PNG remanescente não valida a integração histórica. | Preservar como remanescente e exigir identificação da execução antes de reconsiderar. | **Omitido** |
| `dados/previsao_tempo/previsao_tempo.json` | JSON rastreado | **Incluir opcionalmente** | Resposta meteorológica histórica com metadados úteis: GMT, offset zero e vento em km/h; não prova chamada nova à API. | Selecionar como fonte histórica identificada, conferindo proveniência e condições aplicáveis ao conteúdo externo. | **Omitido** |
| `dados/historico_irrigacao.csv` | CSV local ignorado | **Não publicar por padrão** | Histórico operacional com oito registros e horário local sem offset; não é exemplo distribuído com proveniência completa. | Avaliar separadamente eventual amostra revisada, com origem/fuso identificados; preservar o original local. | **Omitido** |
| `dados/previsao_tempo/previsao_tempo.csv` | CSV local ignorado | **Não publicar por padrão** | 168 previsões históricas em UTC sem sufixo; coluna `wind_ms` contém vento histórico em km/h. | Selecionar apenas como histórico contextualizado ou preparar exemplo separado com unidade/fuso explícitos. | **Omitido** |
| `dados/analises/iot/analise_historico.csv` | CSV local ignorado | **Não publicar por padrão** | Derivado operacional com oito registros; representação antiga de horário pode ocultar o fuso. | Identificar método, versão e fuso antes de eventual seleção de amostra. | **Omitido** |
| `dados/analises/previsao/analise_previsao.csv` | CSV local ignorado | **Não publicar por padrão** | Derivado de 168 previsões com a incompatibilidade histórica de nome/unidade do vento. | Identificar a unidade real e a execução produtora antes de eventual seleção de amostra. | **Omitido** |
| `dados/analises/integrada/dados_integrados_iot_previsao.csv` | CSV local ignorado | **Não publicar por padrão** | Derivado operacional de cinco registros; menu e script independente compartilham esse destino e usam métodos distintos. | Identificar método, origem, fuso e cobertura antes de eventual seleção de amostra. | **Omitido** |

A recomendação F2-94 era de **três registros a manter, 14 inclusões opcionais e 11 recomendações de não publicar**. A seleção F2-95 adotou somente os três TXT: **19 PNGs, um JSON e cinco CSVs foram omitidos**. Não existe `dados/irrigacao_exemplo.csv`; as fixtures codificadas nos testes são reproduzíveis, mas não são medições reais nem um exemplo CSV distribuído.

### Seleção recomendada para entrega à Fase 7

| Grupo | Conteúdo recomendado e finalidade |
|---|---|
| Fontes | `app.py`, `app.r`, [src/](../src/), [scripts/](../scripts/), [monitor/](../monitor/) e [r/](../r/), preservando os dois fluxos de captura e os métodos de análise identificados. |
| Configuração e instalação | `platformio.ini`, `wokwi.toml`, `diagram.json`, `.gitignore`, `.gitattributes` e [config/](../config/), incluindo requirements e instaladores. Manter caminhos relativos e documentar dependências externas. |
| Documentação e identidade | [README](../README.md), [síntese autoral dos requisitos](RASTREABILIDADE_F2.md#síntese-autoral-proposta-para-os-requisitos), [CHANGELOG](../CHANGELOG.md), [document/](./), guias auxiliares e [assets/](../assets/), com créditos originais e imagem do circuito. O enunciado FIAP integral foi omitido; isso não equivale a autorização para reproduzi-lo. |
| Validação reproduzível | Fontes dos testes e verificadores em [tests/](../tests/). Caches, relatórios temporários e pastas `tests/.tmp*/` não integram os fontes de validação. |
| Dados selecionados | Somente os três TXT históricos identificados na coluna F2-95 da tabela acima. Não representam validação do código integrado. Novas capturas, previsões e análises geram os CSVs, JSONs, relatórios e gráficos nos destinos descritos pelos guias. |

Esta seleção orienta a preparação dos fontes e das evidências para a Fase 7. Eventuais exclusões ou mudanças de rastreamento dependem de revisão da responsável e de autorização específica, preservando os originais. `.pio/`, ambientes virtuais, caches, credenciais e dados locais ignorados não devem ser incorporados à entrega por simples cópia integral da pasta.

A seleção técnica não comprova direitos de reprodução. Os créditos originais devem ser preservados; a atribuição do modelo FIAP não define automaticamente a licença do código autoral da equipe nem autoriza a reprodução integral do enunciado ou de conteúdo externo. A equipe responsável deve registrar as condições pretendidas de distribuição e reutilização e, se escolhida, a licença específica do código, além de confirmar os direitos aplicáveis aos demais materiais.

### Espaços finais nos relatórios TXT — F2-94

A inspeção somente de leitura distinguiu os **91 avisos do diff** — 38 no relatório integrado, 28 no IoT e 25 no meteorológico — dos **123 finais de linha com espaço ASCII `0x20` nos arquivos completos**: 43, 41 e 39, respectivamente. Não foram encontrados TABs nos finais de linha; há um TAB interno no IoT e um no meteorológico. Os arquivos preservam 189, 187 e 160 terminações CRLF, respectivamente, sem BOM.

Uma comparação em memória indicou que retirar apenas os espaços finais removeria **344 bytes**: 213 do integrado, 63 do IoT e 68 do meteorológico. Tokens, textos, números, alinhamento interno e terminações CRLF seriam preservados, mas os três SHA-256 mudariam. Trata-se de uma ressalva de higiene e preservação da evidência, sem defeito funcional demonstrado por esses espaços.

A recomendação é **manter os originais**. Uma eventual normalização autorizada deve produzir uma saída separada e identificada, registrar hashes antes/depois e confirmar que o diff contém somente remoções de espaços finais. Não aplicar `rstrip` aos originais nem alterar `.gitattributes` para suprimir os avisos.

### Privacidade e regras do Git conferidas na F2-91

A varredura F2-91 considerou os candidatos à publicação retornados por `git ls-files -co --exclude-standard`: **65 arquivos**, dos quais **44 textuais** no momento da inspeção. Não foram encontradas assinaturas de chaves privadas, tokens conhecidos, credenciais atribuídas ou em URLs, e-mails, rótulos de CPF/telefone ou caminhos pessoais de perfil nos textos examinados. Nomes e RMs dos créditos originais foram preservados. A imagem do circuito foi inspecionada visualmente e não apresentou identificadores pessoais visíveis; seus três metadados textuais contêm autoria coincidente com os créditos já preservados e datas, sem assinaturas de segredo identificadas. Os valores dos metadados não são reproduzidos neste documento; a imagem original foi preservada.

Essa busca é heurística e não certifica ausência de dados sensíveis em todo o histórico Git, em todos os formatos binários ou em alterações posteriores. A F2-91 também repetiu `git check-ignore --no-index -z --stdin`: **13 caminhos locais protegidos e seis exceções/fontes não ignorados**, sem criar os caminhos consultados. Arquivos já rastreados continuam versionados apesar das regras de ignore.

## Validações de segurança e higiene da auditoria técnica inicial — 01/11/2026

| Verificação executada | Resultado |
|---|---|
| Quatro testes em `tests/test_weather_forecast.py`, executados por `python -X utf8 -m unittest discover -s tests -p test_weather_forecast.py -v` | **Sucesso:** unidade solicitada/UTC, codificação de cidade, escape CSV e cabeçalho de previsão vazia; sem rede. |
| Análise sintática Python com `ast.parse` do script meteorológico e seu teste | **Sucesso.** |
| `git check-ignore --no-index -z --stdin` | **Sucesso:** 13 caminhos locais protegidos e 6 exceções/fontes não ignorados. Não cria os arquivos consultados. |
| `config/setup.bat` executado da raiz e de `config/` | **Sucesso com pip simulado:** o módulo simulado foi verificado antes da execução; os argumentos apontaram ao requirements correto. Instalação real não executada. |
| `bash -n config/setup.sh` | **Tentativa sem conclusão:** o Bash disponível depende de WSL, que retornou `E_ACCESSDENIED`. Validação de sintaxe/execução em Bash fica pendente. O instalador Unix não foi executado. |
| `git diff --check` dos arquivos de segurança, higiene, consulta meteorológica e setups alterados na auditoria de 01/11/2026 | **Sucesso.** A verificação global encontrou espaços finais em relatórios TXT modificados antes daquela auditoria; preservados como evidência. |
| Busca heurística local de segredos | **Sem achados pelos padrões descritos**, com limites de cobertura indicados acima. |

Na consolidação da auditoria técnica inicial de 01/11/2026, **18 testes Python** e **10 grupos de testes R** foram aprovados. A comparação SHA-256 confirmou preservação de **30 arquivos de evidência** em relação ao início daquela auditoria. O `git diff --check` dos **14 arquivos versionados alterados na auditoria** foi aprovado; a verificação global apontou **91 ocorrências de espaços finais em três relatórios TXT preexistentes**, mantidos intactos. Os comandos e limites constam na [rastreabilidade](RASTREABILIDADE_F2.md). Esses resultados pertencem à execução inicial e não são as contagens ampliadas da F2-91.

Durante a auditoria técnica inicial de 01/11/2026, não houve teste de simulador, porta RFC2217 real, dispositivo COM, API meteorológica ou instalação. O único acesso externo dessa auditoria foi a leitura pontual da documentação oficial da Open-Meteo para confirmar o parâmetro de unidade; isso não equivale a testar a API. As validações históricas informadas pela responsável e os testes da auditoria de 01/11/2026 estão discriminados na [rastreabilidade](RASTREABILIDADE_F2.md).

### Validações complementares F2-91 — 01/11/2026

| Verificação | Resultado |
|---|---|
| Leitura de sockets TCP, sem iniciar servidor | `Get-NetTCPConnection` falhou por acesso negado (`0x80041003`); `netstat -ano -p tcp` foi executado e não apresentou linha da porta 4000. O bind do Wokwi não foi confirmado. |
| Regras do Git | **Sucesso:** 13 caminhos protegidos e seis exceções/fontes, via `git check-ignore --no-index -z --stdin`, sem criar os arquivos consultados. |
| Inventário e proveniência | **Executados por leitura:** 23 gerados versionados, unidade histórica de vento, oito registros IoT, 168 meteorológicos e cinco integrados, excluindo os cabeçalhos. Relatórios de regressões ignoradas comparados com PNGs remanescentes, sem regenerar as saídas. |
| Segredos e privacidade | **Sem achados pelos padrões e limites descritos** nos candidatos textuais ao GitHub e na inspeção da imagem/metadados do circuito; créditos originais preservados. |
| Suíte Python ampliada | **40 casos: 31 aprovados e nove ignorados.** Os aprovados cobrem menu (seis), captura serial (oito), meteorologia (nove), inspeção/extração estática do C++ (quatro) e modelo Python das regras (quatro). Os nove ignorados correspondem exclusivamente à execução do C++ por ausência de compilador de host; não foram apresentados como testes do firmware executado. |
| Meteorologia com respostas simuladas | **Sucesso:** nove testes offline confirmados na F2-91, incluindo validação de unidade/UTC, timestamp com `Z`, fluxo completo com resposta simulada e preservação de arquivos quando a resposta é incompatível. Nenhuma API real acessada. |
| Correções temporais R | **Sucesso:** 16 grupos em `tests/test_app_r.R`, com R 4.5.3 já instalado, sem warnings; parse dos quatro scripts R, preservação de instantes/vizinhos após apresentação em Bahia, offsets mistos, UTC, ordenação/duplicatas e quatro subprocessos locais CLI/source com helper localizado fora da raiz. Fixtures isoladas; sem substituir os dados históricos. |
| Sintaxe do setup Bash | **Sucesso:** `C:\Program Files\Git\bin\bash.exe --noprofile --norc -n config/setup.sh`, código 0. A F2-91 usou o Bash já instalado com Git, evitando o comando `bash` do PATH que dependia do WSL indisponível. O instalador não foi executado e nenhuma dependência foi instalada. |

A F2-91 não iniciou o Wokwi, não abriu conexão RFC2217/COM, não alterou firewall e não instalou dependências. As leituras da tabela de sockets não equivalem a validar a comunicação com o simulador. Os testes novos usam respostas e arquivos isolados; os gerados históricos continuam separados das evidências de validação do código revisado.

## Estrutura documental F2-93 — 01/11/2026

Na origem, o enunciado institucional foi realocado para `document/ENUNCIADO_F2.md` com conteúdo e autoria FIAP preservados. O antigo `document/other/readme.md`, que funcionou como índice na F2-78, foi removido daquela estrutura. Na seleção F2-95, o enunciado integral foi omitido e os requisitos estão na [síntese autoral](RASTREABILIDADE_F2.md#síntese-autoral-proposta-para-os-requisitos). O inventário histórico dos 23 gerados continua descrevendo a origem; somente três TXT acompanham o módulo.

As regras de higiene da F2-93 delimitam os formatos de dados sem ocultar fixtures e documentação fora de `dados/`:

- Os padrões globais `*.tsv`, `*.xls` e `*.xlsx` foram restritos a `/dados/**` para essas extensões.
- `secrets.*` permanece global, sem exceções adicionais. Os documentos de segurança existentes não são abrangidos por esse nome de arquivo.
- A exceção `/dados/irrigacao_exemplo.csv` permanece reservada a um exemplo sintético ou revisado; o arquivo não foi criado. As regras `.vscode/*` e `!.vscode/tasks.json` foram mantidas.
- `.gitattributes` conserva `* text=auto` e acrescenta `*.sh text eol=lf` e `*.bat text eol=crlf`, sem renormalização dos arquivos existentes.

| Verificação de higiene F2-93 | Resultado |
|---|---|
| `git check-ignore --no-index -z --stdin` | **52 casos aprovados:** 33 caminhos protegidos e 19 legítimos, incluindo fixtures/documentos TSV/XLS/XLSX fora de `dados/`, as exceções revisadas e os formatos variados `secrets.*`. Os caminhos hipotéticos não foram criados. |
| `git check-attr` | **12 verificações aprovadas:** shell com LF, batch com CRLF; Python, R, firmware e PNG mantêm `text=auto` e EOL não especificado. Nenhuma renormalização foi executada. |

## Conclusão para integração acadêmica

A avaliação F2-91 considera o módulo **apto com ressalvas para integração dos fontes na Fase 7, em contexto acadêmico**, acompanhado dos testes, da documentação e dos limites de evidência registrados. As pendências abaixo não impedem integrar os fontes, mas precisam permanecer identificadas na entrega.

O módulo não está validado para controlar uma bomba física. A umidade inicial, o uso de leitura antiga após falha do DHT22, as substituições didáticas de sensores e a ausência de validação elétrica/agronômica impedem recomendar operação física real com base nesta auditoria. Inspeção estática e testes de um modelo Python não substituem execução do firmware, simulação ou ensaio de hardware; os nove cenários C++ permanecem sem execução.

## Pendências para revisão humana

1. Confirmar interface de escuta/firewall da porta 4000 com o Wokwi ativo e manter o acesso restrito à máquina local. A F2-91 encontrou acesso negado na leitura por CIM e nenhuma linha da porta no `netstat`; não há confirmação de bind.
2. Validar captura RFC2217/COM e interação Enter/Ctrl+C após as correções do aplicativo, com apenas um coletor ativo.
3. Interpretar os três TXT incluídos como registros históricos da origem, com os alertas de unidade, fuso e geração não comprovada. Os demais 25 arquivos de dados não acompanham a seleção F2-95.
4. Para qualquer ampliação futura das evidências distribuídas, identificar sua proveniência e aplicar os critérios da tabela; os originais da origem devem ser preservados.
5. Rever versões efetivamente instaladas e vulnerabilidades das dependências quando necessário. A verificação de sintaxe Bash foi resolvida pela F2-91 com o Bash do Git; execução real dos instaladores permanece não realizada, sem instalar dependências para esse fim.
6. Antes de qualquer uso físico, revisar o valor inicial de umidade, a ausência de expiração após falha DHT22 e as condições elétricas/agronômicas; a validação registrada em 01/11/2026 corresponde ao protótipo simulado.
7. Identificar qual método temporal gerou cada saída e avaliar tolerância máxima/cobertura. A F2-91 corrigiu UTC, apresentação em Bahia e ordenação do script independente, mas menu e script continuam com critérios distintos e compartilham o caminho do CSV integrado.
8. Executar os nove cenários C++ host quando houver compilador compatível disponível. O harness extrai funções reais do `.ino`, mas a F2-91 aprovou apenas a inspeção estática e o modelo Python; isso não encerra a homologação direta do firmware.
9. Manter a distinção entre a síntese autoral distribuída e o enunciado FIAP integral omitido. Uma eventual reprodução futura do material institucional depende da confirmação dos direitos aplicáveis; a omissão não comprova autorização.

