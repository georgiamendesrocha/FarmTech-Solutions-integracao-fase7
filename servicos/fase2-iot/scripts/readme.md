# 📡 Scripts auxiliares — FarmTech Solutions

Execute a partir da raiz do módulo, que contém `app.py` e `platformio.ini`. Na estrutura `servicos/fase2-iot/`, use essa pasta como diretório de trabalho. Fluxos integrados em [app.py](../app.py) e no [README](../README.md).

## Captura serial independente

[serial_grava_csv.py](serial_grava_csv.py) recebe COM ou URL RFC2217 via `serial.serial_for_url`. Requer PySerial:

```powershell
python -m pip install -r scripts/requirements-serial.txt
python scripts/serial_grava_csv.py --port rfc2217://127.0.0.1:4000 --baud 115200
# Ou porta real:
python scripts/serial_grava_csv.py --port COM6 --baud 115200
```

Inicie Wokwi antes e configure a porta 4000 em [wokwi.toml](../wokwi.toml). O leitor não compila/inicia o simulador.

- Destino padrão: `dados/historico_irrigacao.csv` na raiz do módulo, mesmo se chamado de outra pasta.
- `--out caminho.csv`: outro destino; relativo ao terminal.
- `--fresh`: substitui o destino após conectar; use somente quando for aceitável perder seu conteúdo.
- **Ctrl+C** fecha a serial; Enter não é comando no uso independente.
- Cabeçalho único, append entre sessões e flush por registro. Falha ao conectar não apaga histórico.
- Aceita `CSV_ROW` com dez campos numéricos finitos e faixas compatíveis com firmware. Remonta fragmentos e limita linhas a 4096 bytes.
- Acrescenta `ts_iso` local do PC sem fuso explícito; `t_rel_ms` vem do ESP32.
- Códigos: 0 ao encerrar com Ctrl+C; 1 dependência ausente; 2 conexão inválida/indisponível; 3 desconexão; 4 erro de arquivo/leitura ou cabeçalho incompatível. Argumentos inválidos usam argparse.

Cabeçalho persistido pelo Python:

```csv
ts_iso,t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw
```

`N/P/K/bomba_fw` são 0 ou 1. O cabeçalho só é escrito ao criar um arquivo vazio; cabeçalho incompatível impede append. Mensagens de status e valores não finitos são descartados. O instante de recebimento não é um relógio civil do ESP32, e `millis()` reinicia com o firmware.

A opção 1 do Python usa esse leitor com 115200 baud e URL local fixa. Nela, **Enter ou Ctrl+C** encerram o subprocesso e retornam ao menu. Não há reconexão automática.

O menu tenta abrir `diagram.json` pelo aplicativo associado; essa ação pode apenas abrir um editor. Ele não compila nem inicia Wokwi: siga o [procedimento no README](../README.md#iniciar-o-wokwi-no-vs-code). Aguarda até 12 tentativas de conexão, com pausa de 1 s e timeout de 0,5 s por tentativa; ao falhar, informa e retorna ao menu. Desconexão serial ou erro do leitor também encerram a captura. Ctrl+C no prompt principal encerra o Python; durante uma operação, cancela a operação e retorna ao menu.

[gravar_historico.ps1](gravar_historico.ps1) muda para a raiz e chama o leitor, aceitando COM ou URL:

```powershell
.\scripts\gravar_historico.ps1 COM6
.\scripts\gravar_historico.ps1 rfc2217://127.0.0.1:4000
```

## Alternativa PlatformIO

O [filtro PlatformIO](../monitor/filter_irrigation_csv.py) grava o mesmo esquema quando seu Monitor Serial está aberto:

```powershell
pio device monitor -e esp32 -p rfc2217://127.0.0.1:4000 -b 115200
```

Depende do PlatformIO e do filtro configurado em [platformio.ini](../platformio.ini); é independente do menu Python. Use **Ctrl+C** para sair; Enter é entrada serial. O filtro legado confia no payload e não aplica toda a validação do leitor Python. Não use ambos na mesma porta/arquivo. O painel Wokwi sozinho não grava CSV.

## Previsão meteorológica

[weather_forecast.py](weather_forecast.py) usa biblioteca padrão e HTTPS, sem chave de API:

```powershell
python scripts/weather_forecast.py --city "Irecê"
```

O padrão independente é `São Paulo`; a opção 3 de `app.py` pede a cidade. O primeiro resultado da geocodificação é escolhido; confira a localização no JSON.

Salva/substitui `dados/previsao_tempo/previsao_tempo.json` e `previsao_tempo.csv`. `--out-json` e `--out-csv` mudam destinos. Nas novas consultas, solicita vento em m/s e UTC; para respostas com registros horários, exige metadados de vento `m/s`, fuso UTC e deslocamento zero antes de persistir. Uma incompatibilidade é informada sem converter unidades. O JSON conserva a resposta e seus metadados; os timestamps do novo CSV são normalizados em UTC com sufixo `Z`.

Os arquivos históricos inspecionados permanecem intactos **na origem**: a previsão antiga usa UTC sem sufixo no CSV e o JSON declara vento em km/h. Esses CSVs, JSON e PNGs não acompanham o módulo integrado. Não interprete esse vento como m/s nem misture resultados sem conferir a unidade da coleta; as correções não convertem retroativamente esses artefatos.

CSV usa escape de vírgulas, aspas e quebras de linha. Textos vêm de serviço externo: não habilite avaliação de fórmulas ao importar em planilha. Timeout por requisição: 15 s; sem retry automático. **Previsão é analisada em R e não controla firmware.**

## Análises e associação temporal em R

Execute `Rscript app.r` na raiz ou use a opção 2 do Python. O menu gera medidas descritivas, quartis, gráficos e regressões exploratórias quando viáveis. As opções 1–3 concluem ou informam erro e retornam ao submenu; a opção 4 retorna ao Python, ou ao terminal quando R foi iniciado diretamente.

O módulo integrado inclui somente três relatórios TXT históricos. Os CSVs de entrada precisam ser gerados por captura serial e consulta meteorológica antes das análises; os diretórios de saída são criados pelos programas. Os TXT preservados não são entradas para os cálculos nem comprovação de execução da versão integrada.

| Opção R | Entrada | Saídas |
|---|---|---|
| 1 — IoT | `dados/historico_irrigacao.csv`, ou `dados/captura_serial.csv` se o primeiro estiver ausente | `dados/analises/iot/analise_historico.txt` e `analise_historico.csv`; gráficos em `dados/plots/iot/` e `dados/plots/regressao/` |
| 2 — Previsão | `dados/previsao_tempo/previsao_tempo.csv` | `dados/analises/previsao/analise_previsao.txt` e `analise_previsao.csv`; gráficos em `dados/plots/previsao/` e `dados/plots/regressao/` |
| 3 — Integração | Os dois conjuntos | `dados/analises/integrada/dados_integrados_iot_previsao.csv` e `analise_integrada.txt`; regressões possíveis em `dados/plots/regressao/` |

Os scripts em `r/` são independentes do menu: `Rscript r/01_carregar_dados.R` carrega histórico/captura e imprime análise no console, sem gerar os relatórios do menu; `Rscript r/02_integrar_previsao.R` gera o CSV integrado pelo método descrito abaixo.

O menu [app.r](../app.r) e o script [r/02_integrar_previsao.R](../r/02_integrar_previsao.R) compartilham [r/temporal_utils.R](../r/temporal_utils.R). IoT sem sufixo mantém a interpretação no fuso local do computador, com fallback UTC se indisponível; previsão sem sufixo é UTC. `Z` e offsets explícitos preservam o instante informado. Confirme o fuso do PC que capturou o histórico.

Nos relatórios e CSVs processados pelo menu, IoT e integração são apresentados em `America/Bahia`, com offset explícito, e a previsão é apresentada em UTC. O integrado do script independente também usa Bahia com offset. Isso altera a apresentação, sem somar ou subtrair horas do instante absoluto; o histórico bruto não é regravado.

- **Menu:** associa a previsão de menor distância absoluta em segundos; em empate, usa a primeira linha válida do CSV, sem interpolação.
- **Script independente:** ignora timestamps meteorológicos inválidos, ordena por instante e mantém a primeira linha original em duplicatas. Interpola as variáveis contínuas entre limites finitos; valores ausentes nos limites resultam em `NA`. Categoria e metadados usam o horário mais próximo; em empate, o anterior.

Ambos repetem a borda mais próxima fora da cobertura, sem janela máxima de tolerância, e informam limitações da associação. O script independente e o menu gravam o mesmo CSV integrado; identifique o método antes de substituir ou comparar resultados. Relatórios e gráficos usam nomes fixos. IoT e previsão podem compartilhar o mesmo PNG de regressão; ajustes ignorados preservam PNGs antigos. Confira a execução e o relatório correspondentes antes de tratar um gráfico como atual.

## Testes locais

Na raiz:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Os testes simulam serial, subprocessos e dados meteorológicos; não exercitam Wokwi nem API. Os testes R estão em `tests/test_app_r.R`. Temporários ficam em `tests/`, sem substituir evidências. O histórico da auditoria e as validações da F2-91 estão separados na [rastreabilidade](../document/RASTREABILIDADE_F2.md).
