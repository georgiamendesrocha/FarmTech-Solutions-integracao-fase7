# INT-02 / INT-03 — Validação da Parte 1

Data: 03/11/2026. Implementação sobre a dashboard existente da Fase 4.
Os resultados abaixo correspondem às execuções desta integração, separados dos
registros históricos das fases. Falhas intermediárias foram corrigidas e as
verificações afetadas repetidas; os números são da bateria final.

## Resultado dos testes

| Suíte | Casos | Aprovados | Ignorados | Falhas/erros |
|---|---:|---:|---:|---:|
| Adaptadores, runtime, banco e dashboard da integração | 55 | 55 | 0 | 0 |
| Fase 1 original | 16 | 16 | 0 | 0 |
| Fase 2 Python original | 40 | 31 | 9 | 0 |
| Fase 4: seleção de regressões sem treinamento | 128 | 128 | 0 | 0 |
| **Total** | **239** | **230** | **9** | **0** |

Os nove ignorados são cenários C++ da Fase 2: nenhum compilador host compatível
foi localizado; não houve instalação. Rscript também não foi localizado no PATH;
testes R não foram executados nesta etapa. Os 16 grupos R documentados na Fase 2
continuam sendo evidência histórica, não são contabilizados acima.

A seleção F4 está explícita em [`scripts/validar_testes.py`](../scripts/validar_testes.py).
Abrange fontes, publicação/recuperação, SQLite/rollback, launcher, scheduler,
interface, histórico, recomendações, contratos e procedência dos modelos.
Exclui testes científicos que treinam estimadores em diretórios temporários.
Os testes de proteção confirmam recusa antes do treino/gravação.

Reprodução, a partir da raiz, sem instalar dependências:

```powershell
.\servicos\fase4-regressao\.venv-f402\Scripts\python.exe -X utf8 -B scripts/validar_testes.py --suite integracao
.\servicos\fase4-regressao\.venv-f402\Scripts\python.exe -X utf8 -B scripts/validar_testes.py --suite fase1
.\servicos\fase4-regressao\.venv-f402\Scripts\python.exe -X utf8 -B scripts/validar_testes.py --suite fase2
.\servicos\fase4-regressao\.venv-f402\Scripts\python.exe -X utf8 -B scripts/validar_testes.py --suite fase4
```

Logs e JSONs por suíte: `.runtime/validation/`, ignorados para distribuição.
Resumo saneado permanente: [`evidencias-int02.json`](evidencias-int02.json).

## Verificações efetivas

- Python F4: **3.11.9**; Python F6: **3.13.13**, conferidos executando os
  interpretadores existentes. Não houve instalação ou atualização.
- Streamlit AppTest renderizou **13 telas**: home, sete páginas F4 originais e
  cinco páginas adicionais. A abertura não executou workers de serviço e não
  acrescentou leituras ou previsões à fixture SQLite; scheduler desativado.
- Botão F1 executou cálculo real por subprocesso e exibiu quatro indicadores,
  tabela e gráfico, preservando os CSVs. Casos inválidos e Unicode exercitados.
- Botão F3 executou consulta real ao CSV preservado em subprocesso; seleção de
  origem, limite e quatro gráficos verificados. Oracle foi mockado, com SELECT
  parametrizado e sem commit. Nenhuma conexão Oracle real foi feita.
- F2: geocodificação/previsão foram simuladas por fixtures de rede. Contratos
  UTC/m/s, limites HTTP, dados ausentes, erros e ausência de persistência foram
  testados. **Consulta Open-Meteo real não foi executada.**
- Runtime: timeout real de processo de teste, limite de stdout, stdin bloqueado,
  exclusão mútua, UTF-8, argumentos fixos e erros saneados exercitados.
- Inicialização HTTP real pelo launcher respondeu `200 /_stcore/health` em
  `127.0.0.1`. A árvore de processos de validação foi encerrada. Não houve
  publicação em rede nem inspeção visual por navegador.

Para repetir apenas o teste HTTP local:

```powershell
.\servicos\fase4-regressao\.venv-f402\Scripts\python.exe -X utf8 -B scripts/validar_dashboard_local.py
```

## Avaliação YOLO real pelo botão

O diretório de checkout informado pela responsável existe. Antes da avaliação,
foram conferidos HEAD completo e ausência de alterações nos arquivos de código
e configuração selecionados pelo avaliador:

`4add2aff6e3d926586a3eab4659f3b498dd444a1`.

A tentativa de consulta Git dentro do sandbox encontrou bloqueio por diferença
de proprietário. A validação foi então executada com a aprovação da execução
fora do sandbox; nenhuma configuração global `safe.directory` foi alterada.

Fluxo efetivamente exercitado:

`Streamlit AppTest → botão Avaliar YOLO customizada → adaptador → worker Python
3.13.13 → avaliar_yolo.py → checkpoint preservado, CPU`.

| Classe | TP | FP | FN | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Banana | 2 | 1 | 7 | 66,67% | 22,22% | 33,33% |
| Milho | 4 | 4 | 3 | 50,00% | 57,14% | 53,33% |

Oito imagens de teste; confiança 0,25, IoU de associação 0,50, tamanho 640.
Tempo médio desta execução após aquecimento: **344,72 ms/imagem**. Não é um
benchmark uniforme entre ambientes nem mAP. Uma figura Plotly foi renderizada;
zero exceções de interface. Modelos e checkout permaneceram preservados.

Não houve treinamento, instalação, download ou substituição de pesos.
Configurações/caches das bibliotecas do worker ficam em `.runtime/fase6/`.
O resultado não valida desempenho operacional em uma fazenda ou generalização
além desse pequeno teste. Inferência por upload não foi incluída.

Reprodução com checkout existente informado pelo usuário:

```powershell
.\servicos\fase4-regressao\.venv-f402\Scripts\python.exe -X utf8 -B scripts/validar_yolo_integrada.py --yolo-repo "<checkout-Git-local>"
```

O caminho pessoal não está codificado na aplicação ou nesta documentação.

## Integridade e reconstrução SQLite

O SQLite padrão histórico da F4 estava ausente no diretório inventariado.
Foi criada uma base nova em `.runtime/demo/farmtech-demo.db`, com marcador
`integracao_proveniencia`, fontes e hashes. Contagens iniciais verificadas:
22 culturas, um sensor, 153 leituras registradas/simuladas, 2.200 amostras
acadêmicas e zero previsões. É uma base reconstruída, não histórico recuperado.

Os testes exercitam criação em staging, publicação exclusiva e recusa de destino
existente, inclusive preservação byte a byte. O procedimento não é executado ao
abrir a aplicação. O destino da demonstração já criado foi inspecionado em modo
somente leitura e preservado ao solicitar nova preparação.

O manifesto [`integridade-int02.json`](integridade-int02.json) contém hashes
anteriores à implementação para **203 arquivos**: dados, metadados, modelos,
imagens/rótulos e sete páginas originais selecionados. Todos foram comparados
após os testes, sem divergências. Os modelos YOLO e CNN também foram comparados
antes/depois da avaliação real, sem alteração.

## Limites e pendências externas

- Oracle real: driver `oracledb` ausente no Python F4; exige ambiente/credenciais
  e permissões de leitura. CSV é alternativa explícita, sem fallback silencioso.
- Open-Meteo real: requer acesso HTTPS; validação desta etapa usou fixtures.
- R, Wokwi, serial e hardware físico não foram executados. Pré-condições reais
  são mostradas na página IoT; os CSVs de análise R estão ausentes.
- A CNN não foi inferida novamente; seu artefato foi preservado por hash. A
  integração obrigatória de visão utiliza a YOLO customizada.
- Avisos legados de `use_container_width` e compatibilidade histórica sklearn
  apareceram nos testes F4. As sete páginas e os modelos foram preservados;
  avisos não foram ocultados nem tratados como garantia entre versões.
- Não foi feita nova auditoria de vulnerabilidades de dependências ou teste de
  acesso público. A aplicação permanece local; exposição futura exige
  autenticação, autorização e HTTPS na infraestrutura.
