# Serviços integrados

## Entrada e comandos

Use o diretório `C:\Users\Georgia\Desktop\farmtech-integracao` como diretório de
trabalho. [`iniciar.py`](../iniciar.py) seleciona o Python validado da Fase 4;
`FARMTECH_FASE4_PYTHON` permite indicar outro caminho absoluto para **Python
3.11.9**, com as dependências F4 já disponíveis. Não há instalação automática.

```powershell
python iniciar.py --help
python iniciar.py --status
python iniciar.py --preparar-demo
python iniciar.py --dashboard --port 8501
```

Sem opção, o comando abre a dashboard F4. Ações da CLI são mutuamente exclusivas.
`--preparar-demo` é uma ação explícita que cria uma base reconstruída nova e
recusa um destino existente. `--status` informa pré-condições locais e consulta
o SQLite existente em modo somente leitura. Use `Ctrl+C` no terminal para
encerrar a dashboard; a CLI encerra sua árvore de processos. Os workers de cada
operação terminam após devolver o resultado ou são encerrados pelo timeout.

## Fase 1 — gestão agrícola

**Página:** `9_Gestao_Agricola.py` na dashboard F4.
**API Python:**
[`calculate_plot(shape, measurements, *, crop="Soja", spacing=0.5)`](../farmtech_integracao/fase1.py).

```powershell
python iniciar.py --gestao --forma retangulo --medidas 100 50 --cultura Soja --espacamento 0.5
```

O worker reutiliza `calcular_area`, `converter_area`, `dimensao_para_linhas`,
`comprimento_linha` e `dose_ha_para_por_metro` de
[`src/farm.py`](../servicos/fase1-gestao/src/farm.py), sem iniciar o menu
interativo e sem salvar CSV.

| Entrada | Regras |
|---|---|
| Geometria | Círculo, triângulo, retângulo, pentágono, hexágono, heptágono ou octógono regular |
| Medidas em metros | Raio: 1 valor; retângulo: 2; triângulo: 3 lados; demais: todos os lados, iguais entre si |
| Cultura | Soja, Milho, Café, Trigo ou Cana-de-açúcar |
| Espaçamento em metros | Número finito e positivo; medidas e espaçamento limitados a 1.000.000 |

A saída informa área em m², hectares e alqueires, linhas estimadas, quantidades,
doses por metro e custos do catálogo original. A conversão preservada de
alqueire é 24.200 m². Quatro lados usam a hipótese de um terreno retangular.
As linhas são estimativas geométricas; preços/doses são exemplos acadêmicos, e
a comparação de menor custo é feita dentro de cada categoria de insumo.

**Pré-condições:** fontes da F1 e módulos locais utilizados por `farm.py`;
Python F4. Não exige rede, hardware ou banco. Timeout: 30 s. O resultado permanece
na sessão/saída JSON, sem persistência de talhões.

## Fase 2 — IoT e meteorologia

**Página:** `10_IoT_Meteorologia.py`.
**API Python:** [`forecast(city)`](../farmtech_integracao/fase2.py).

```powershell
python iniciar.py --meteorologia "Irecê"
```

O worker carrega somente
[`scripts/weather_forecast.py`](../servicos/fase2-iot/scripts/weather_forecast.py)
e reutiliza construção de URLs, consulta JSON e normalização. Faz duas consultas
HTTPS explícitas: geocodificação e previsão Open-Meteo. A cidade deve conter de
2 a 120 caracteres, sem caracteres de controle. A primeira localização
retornada é selecionada; a interface exibe nome, região, país e coordenadas para
conferência.

A resposta contém previsão horária com temperatura em °C, umidade relativa em
%, precipitação em mm e vento em m/s, além de coordenadas, fonte e instante UTC
de consulta. Os gráficos convertem os horários UTC para `America/Bahia`.
Não são gravados JSON ou CSV operacionais da F2. Timeout da operação: 40 s.

**Pré-condições da previsão:** acesso HTTPS aos endpoints
`geocoding-api.open-meteo.com/v1/search` e `api.open-meteo.com/v1/forecast`, além
do script preservado. A consulta não exige ESP32 ou R.

**Componentes externos preservados:** captura serial depende de PySerial,
porta COM ou Wokwi/RFC2217 ativo a 115200 baud; análises R dependem de
`Rscript`, CSVs legítimos e diretório de saída exclusivo. A interface informa
essas condições e não inicia captura, firmware ou R.

No ambiente desta entrega, `Rscript` não foi localizado no `PATH`; os arquivos
`servicos/fase2-iot/dados/historico_irrigacao.csv` e
`servicos/fase2-iot/dados/previsao_tempo/previsao_tempo.csv` estão ausentes.
Essa ausência não é preenchida com dados inventados nem com uma cópia silenciosa
da F3/F4. A previsão meteorológica não controla o firmware de irrigação.

## Fase 3 — consultas Oracle ou CSV

**Página:** `11_Oracle_Consultas.py`.
**API Python:**
[`query_sensors(source, *, limit=500, python=None, timeout=30)`](../farmtech_integracao/fase3.py).

```powershell
python iniciar.py --consultar-fase3 csv
python iniciar.py --consultar-fase3 oracle
```

A origem é obrigatoriamente `csv` ou `oracle`. A API Python e a página aceitam
limite inteiro de 1 a 1.000 registros; a CLI usa o padrão de 500. A consulta só
acontece após a ação do usuário. Não há fallback automático de Oracle para CSV.

| Origem | Recurso e seleção |
|---|---|
| CSV | `servicos/fase3-dashboard/src/dados/historico_irrigacao.csv`; até o limite de primeiras linhas do arquivo preservado |
| Oracle | `SENSORES_FARMTECH`; últimos registros por ID, com `FETCH FIRST :limit ROWS ONLY` parametrizado |

O CSV permitido é fixo e deve ter até 20 MiB. Não são aceitos caminhos ou SQL
arbitrários. A consulta Oracle seleciona `INSTANTE`, `TS_ISO`, `UMIDADE`,
`TEMP_C`, `PH_CORR`, `N`, `P`, `K` e `BOMBA_FW`, com ordenação por `ID`. Portanto,
o schema efetivo precisa fornecer esses campos, como no DDL preservado da F3.
O adaptador executa somente SELECT e não executa esse DDL.

A saída contém até o limite de registros normalizados, contagem, unidades,
seleção e origem. Os gráficos apresentam umidade (%), temperatura (°C), pH e
estado 0/1 da bomba. Os timestamps mantêm a informação da origem; fuso ausente
não é inferido. A normalização histórica preenche flags N/P/K e bomba ausentes
com zero; esse comportamento aparece na interface.

**Pré-condições Oracle:** driver `oracledb` no Python selecionado, rede para o
servidor e credencial com permissão de SELECT. Forneça `ORACLE_USER`,
`ORACLE_PASS` e `ORACLE_DSN` pelo ambiente do processo, sem colocar seus valores
nos comandos de exemplo ou no repositório. O adaptador não lê `.env` nem devolve
credenciais ou mensagens brutas de exceção. O timeout padrão do worker é 30 s,
e o timeout de chamada da conexão é 10 s.

No Python F4 inspecionado, o driver `oracledb` está ausente. Oracle real não foi
validado nesta integração. O caminho CSV funciona independentemente desse
driver. Falta de configuração, dependência ausente e falha de consulta geram
diagnóstico de indisponibilidade, preservando a origem solicitada.

O worker não importa as páginas Streamlit, `src.api.main`, o coletor ou o
scheduler F3. O launcher histórico `run.py` da F3, sua API FastAPI e o DDL
destrutivo não fazem parte do caminho integrado.

## Fase 6 — avaliação da YOLO customizada

**Página:** `12_Visao_Computacional.py`.
**API Python:**
[`evaluate_customizada(yolo_repo=None, *, python=None, timeout=120)`](../farmtech_integracao/fase6.py).

```powershell
python iniciar.py --avaliar-yolo --yolo-repo C:\caminho\para\checkout-yolov5
```

O exemplo indica um checkout **já existente**. A aplicação não o clona, baixa
dependências ou realiza treinamento. `FARMTECH_YOLO_REPO` pode fornecer o caminho
em vez de `--yolo-repo`. `FARMTECH_FASE6_PYTHON` permite indicar o executável da
F6; o padrão é
`servicos/fase6-visao/.venv-fase6/Scripts/python.exe`.

**Pré-condições exatas:**

- Python **3.13.13**, com as dependências da F6 já disponíveis; executado em
  processo separado do Python F4 3.11.9.
- Checkout Git local e íntegro da YOLOv5, contendo `.git` e `hubconf.py`, na
  revisão `4add2aff6e3d926586a3eab4659f3b498dd444a1`. Cache do PyTorch Hub não
  atende a essa condição.
- Avaliador preservado `servicos/fase6-visao/entrega_2/avaliar_yolo.py` e pesos
  `entrega_2/modelos/yolov5s_custom_exp60_best.pt`.
- SHA-256 esperado dos pesos:
  `93c086ad8e369cc295dced96b9d48db1524226207e82ab514148f02decad2f61`.
- Oito imagens fixas de teste: quatro JPG de banana e quatro de milho em
  `dataset/test/images/<classe>`, com rótulos correspondentes em
  `dataset/test/labels/<classe>`.
- Git local disponível para as verificações do avaliador e dependências de
  visão computacional compatíveis no ambiente F6.

`availability()` verifica apenas metadados locais; não abre os pesos nem executa
Git/Python adicional. A versão Python, revisão Git, integridade e entradas são
verificadas no processo da avaliação. A inferência usa carregamento local, CPU,
imagem 640, confiança 0,25 e IoU de associação 0,50. O avaliador bloqueia rede e
restringe subprocessos; o worker descarta logs de bibliotecas e devolve apenas
os campos previstos no contrato.

A saída apresenta TP/FP/FN, precisão, recall, F1 por classe e tempo médio em
milissegundos por imagem. Esses números se referem à execução solicitada sobre
o pequeno teste preservado; não são mAP nem comprovação de desempenho geral.
Não há upload arbitrário de imagem nesta integração. Resultados históricos não
são reescritos.

O checkout fornecido pela responsável foi conferido na revisão completa exigida,
sem alterações nos fontes/configurações selecionados pelo avaliador. A avaliação
real passou pelo botão da página, em Python 3.13.13/CPU, sem alterar modelos ou
checkout; ver `VALIDACAO.md`. O caminho continua configurável localmente, sem
valor pessoal fixado na aplicação. Não se deve inferir funcionamento em outro
ambiente com base apenas nos testes com mocks ou na presença dos artefatos
preservados.

## Contrato, efeitos e validação

Todos os adaptadores retornam `Result(status, message, data, source)`. Consulte
[`ARQUITETURA.md`](ARQUITETURA.md) para os limites do runtime, trava por fase,
variáveis de ambiente e proveniência da base reconstruída. Os cálculos F1 e a
previsão F2 não persistem resultados; a F3 lê sua origem; a avaliação F6 retorna
novas métricas na sessão. O runtime cria/adquire arquivos de trava em
`.runtime/locks` durante ações solicitadas.

O diagnóstico `--status` não substitui testes externos. Os testes efetivamente
realizados e suas limitações são registrados em [`VALIDACAO.md`](VALIDACAO.md).
