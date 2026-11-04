# FarmTech Solutions — Fase 7 · Parte 1

Integração das Fases 1, 2, 3 e 6 **na dashboard existente da Fase 4**.
Os programas completos permanecem separados em `servicos/`. As sete páginas
originais da F4 foram preservadas; as páginas 8 a 12 acrescentam visão geral,
gestão agrícola, meteorologia, consultas Oracle/CSV e avaliação da YOLO customizada.

## Abrir localmente

Na raiz deste projeto, com os ambientes previamente existentes:

```powershell
python iniciar.py --status
python iniciar.py --preparar-demo
python iniciar.py --dashboard
```

Abra **http://127.0.0.1:8501**. `Ctrl+C` encerra os processos da entrada integrada.
Outra porta pode ser escolhida com `--port 8502`. Nenhuma instalação é executada.

`iniciar.py` seleciona o Python 3.11.9 da F4 em
`servicos/fase4-regressao/.venv-f402/Scripts/python.exe`. Um ambiente equivalente
pode ser indicado por `FARMTECH_FASE4_PYTHON`, com caminho absoluto. A versão é
verificada. A F6 usa **outro processo**, Python 3.13.13, sem unificar dependências.

A abertura integrada fixa `FARMTECH_SIMULACAO=0`; não inicia Wokwi, captura serial,
coletor Oracle, treinamento, instalação ou recarga de banco. As ações adicionais
dependem de botão ou comando explícito. Os carregamentos/diagnósticos de modelos
da F4 continuam protegidos e podem executar suas previsões de referência,
sem treinamento. As fontes oficiais mantêm seu protocolo de trava/recuperação.

## Base reconstruída, sem sobrescrever

`--preparar-demo` cria exclusivamente `.runtime/demo/farmtech-demo.db` a partir dos
CSVs preservados da F4. O procedimento usa staging e publicação que **falha se o
destino já existir**, inclusive em corrida. Não substitui uma base inválida.

A base é identificada na interface e em `integracao_proveniencia` como
**reconstruída de demonstração**, com fontes e hashes. Não representa histórico
real recuperado. A carga inicial contém 22 culturas, 153 leituras
registradas/simuladas e 2.200 amostras acadêmicas. Não cria previsões fictícias.
Se já foi preparada, o comando recusa uma nova publicação; use `--status`.

`DB_PATH` definido explicitamente no ambiente é respeitado pela dashboard. A
preparação de demonstração continua limitada ao destino próprio acima. A
integração não chama `--pipeline`, `--ingestao`, DDL ou recargas históricas.
Resultados de previsão solicitados nas páginas originais continuam sendo
registrados no banco selecionado, conforme a funcionalidade preservada da F4.

## Ações por terminal

```powershell
python iniciar.py --gestao --forma retangulo --medidas 100 50 --cultura Soja --espacamento 0.5
python iniciar.py --consultar-fase3 csv
python iniciar.py --consultar-fase3 oracle
python iniciar.py --meteorologia "Irecê"
python iniciar.py --avaliar-yolo --yolo-repo "<checkout-Git-local>"
```

O comando meteorológico consulta a rede explicitamente. Os outros exemplos
informam erros ou pré-condições ausentes sem iniciar serviços históricos.

## Pré-condições reais

- **F1:** cálculos funcionam com o Python F4; não iniciam menu nem alteram CSVs.
- **F2:** previsão requer HTTPS para Open-Meteo. Rscript não foi localizado no
  PATH e os CSVs de análise R não acompanham o módulo atual. R, serial e Wokwi
  permanecem externos e não são iniciados pela página integrada.
- **F3:** CSV preservado é uma alternativa explícita e funcional. Oracle exige
  `ORACLE_USER`, `ORACLE_PASS`, `ORACLE_DSN`, acesso de leitura e `oracledb` no
  interpretador selecionado. O driver está ausente no ambiente F4 examinado.
  Nenhum segredo é incluído neste projeto; não há fallback silencioso de Oracle.
- **F6:** configure o checkout no campo da página ou em `FARMTECH_YOLO_REPO`.
  Ele deve ser um checkout Git local limpo na revisão
  `4add2aff6e3d926586a3eab4659f3b498dd444a1`. O cache do Hub sem `.git` não atende
  esse requisito. O Python padrão é o ambiente existente
  `servicos/fase6-visao/.venv-fase6/Scripts/python.exe`; alternativa:
  `FARMTECH_FASE6_PYTHON`. A avaliação exige Python 3.13.13, pesos e oito imagens
  preservadas. Revisão, hash e runtime são conferidos antes da inferência.

O checkout fornecido pela responsável foi conferido na revisão completa exigida
e a avaliação real passou pelo botão integrado: oito imagens, métricas e gráfico,
sem alteração dos modelos ou do checkout. Configure o caminho no campo da página
ou em `FARMTECH_YOLO_REPO` a cada ambiente; caminhos pessoais não estão fixados
no código. Não foram feitos downloads nem alterações nas bibliotecas instaladas.

## Dados, segurança e validação

NOAA, INMET e IBGE/SIDRA permanecem identificados por origem, unidade, período e
localidade, separados dos dados acadêmicos, das simulações e das previsões.
Modelos externos não são aceitos. A avaliação YOLO é experimental sobre teste
fixo; inferência por upload de imagem não integra este incremento.

A aplicação escuta somente em `127.0.0.1`. Não foi publicado serviço. Exposição
futura em rede exige autenticação, autorização e HTTPS na infraestrutura; não há
login improvisado. Workers usam comandos fixos sem shell, JSON por stdin,
timeouts, limite de saída e exclusão mútua por fase. Credenciais não passam por
argumentos de linha de comando nem por resultados públicos.

- [Arquitetura](docs/ARQUITETURA.md)
- [Serviços e contratos](docs/SERVICOS.md)
- [Testes executados e limitações](docs/VALIDACAO.md)
- [Manifesto anterior à implementação](docs/integridade-int02.json)

Para repetir os testes de integração, no Python F4:

```powershell
.\servicos\fase4-regressao\.venv-f402\Scripts\python.exe -X utf8 -B -m unittest discover -s tests/integracao -v
```

Os testes unitários usam fixtures/mocks para rede, Oracle e YOLO. Cálculos F1,
leitura CSV F3, preparação SQLite isolada, limites de subprocessos e renderização
Streamlit são exercitados efetivamente. Também foi executada, separadamente,
a avaliação YOLO real pelo botão. A documentação de validação distingue os casos.
