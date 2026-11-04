# Documentação Do Projeto - Ir Além

Esta documentação complementa o `README.md` do diretório `ir_alem` e descreve a arquitetura local da atividade opcional da Fase 5.

A solução foi implementada e validada de ponta a ponta em ambiente simulado com Wokwi e serviços locais. A validação em ESP32 físico não foi realizada devido à indisponibilidade do hardware no grupo.

## Arquitetura

```text
ESP32/Wokwi + DHT22 + LDR
|
Wi-Fi
|
HTTP POST
|
Flask API
|
SQLite
|
Streamlit Dashboard
```

A implementação utiliza comunicação HTTP local. Não há MQTT, cloud ou componente de Machine Learning neste módulo opcional.

## Status de Validação

### Validado

- PlatformIO Build com sucesso;
- ESP32 simulado no Wokwi;
- DHT22 e LDR no circuito;
- conexão via `Wokwi-GUEST`;
- POST HTTP para `/telemetria`;
- Flask API;
- gravação no SQLite;
- leitura no Streamlit;
- identificação `esp32-farmtech-01`.

### Limitação

- Teste em ESP32 físico não realizado por indisponibilidade do hardware no grupo.

Essa limitação é de validação física e não indica falha técnica da implementação.

## Sensores

| Sensor | Variáveis | GPIO |
|---|---|---|
| DHT22 | temperatura e umidade | GPIO15 |
| LDR | luminosidade normalizada de 0 a 100% | GPIO34 |

O GPIO34 é usado para leitura analógica do LDR. O valor lido pelo ESP32 em 0 a 4095 é normalizado no firmware para 0 a 100% antes do envio à API. Registros legados com valores de `light` acima de 100 são preservados e identificados como históricos, sem conversão automática.

## Circuito Wokwi

O `diagram.json` representa o circuito usado na simulação:

| Componente | Conexão |
|---|---|
| DHT22 VCC | 3V3 |
| DHT22 GND | GND |
| DHT22 DATA | GPIO15 |
| LDR VCC | 3V3 |
| LDR GND | GND |
| LDR AO | GPIO34 |

O pino digital `DO` do módulo LDR permanece desconectado porque a implementação utiliza a saída analógica `AO`.

O arquivo `circuito_wokwi.png` registra visualmente o circuito e a execução utilizados na validação simulada.

## Firmware

O firmware está em `src/main.cpp`. Ele lê os sensores, valida as leituras do DHT22 com `isnan()`, conecta ao Wi-Fi e envia JSON para `POST /telemetria`.

As credenciais e a URL da API não ficam no código versionado. Para configurar:

1. copiar `src/secrets.example.h` para `src/secrets.h`;
2. preencher `WIFI_SSID`, `WIFI_PASSWORD` e `API_URL`;
3. usar, no `API_URL`, o endereço adequado ao ambiente de execução.

Para a simulação no Wokwi, o `src/secrets.h` local pode usar:

```cpp
#define WIFI_SSID "Wokwi-GUEST"
#define WIFI_PASSWORD ""
#define API_URL "http://host.wokwi.internal:5000/telemetria"
```

Essa configuração é específica da simulação Wokwi. O arquivo `src/secrets.h` permanece ignorado pelo Git, não deve ser versionado e não deve receber credenciais reais no repositório. O arquivo `src/secrets.example.h` continua sendo a referência versionada.

Em outra rede ou em hardware físico, o usuário deve usar seu próprio SSID, senha e IP da máquina que executa a API. Não use `localhost` no `API_URL` do ESP32, pois nesse contexto ele aponta para o próprio microcontrolador.

## API E Persistência

A API Flask está em `api.py` e expõe:

- `GET /health`;
- `POST /telemetria`.

Payload esperado:

```json
{
  "device_id": "esp32-farmtech-01",
  "temperature": 25.4,
  "humidity": 61.2,
  "light": 73
}
```

A API é responsável pela entrada da telemetria. As leituras válidas são gravadas em `sensores.db`, na tabela `leituras`, usando consultas SQL parametrizadas. Em novos bancos, `light` é armazenado como inteiro com luminosidade normalizada de 0 a 100%. Se a coluna `device_id` ainda não existir em um banco legado, a API adiciona essa coluna de forma idempotente. Registros históricos anteriores podem conter valores fora dessa escala e não são convertidos automaticamente.

## Dashboard

O dashboard oficial é `app.py`. Ele consulta o SQLite e exibe última leitura, histórico, tabela e gráficos. Ele não simula sensores, não possui sliders e não insere leituras manualmente.

Durante a validação integrada, o dashboard exibiu leitura originada do dispositivo `esp32-farmtech-01`. Como evidência pontual de execução, foi observada uma leitura com temperatura de 24.0 °C, umidade de 40.0% e luminosidade de 24.0%. Esses valores não são requisito permanente do sistema.

Não há dashboard legado versionado neste componente; o dashboard oficial é `app.py`.

## Execução

Terminal 1:

```bash
python api.py
```

Terminal 2:

```bash
streamlit run app.py
```

Firmware no Wokwi:

1. configurar `src/secrets.h` com `Wokwi-GUEST`, senha vazia e `http://host.wokwi.internal:5000/telemetria`;
2. compilar pelo PlatformIO usando `platformio.ini`;
3. executar a simulação no Wokwi;
4. validar conexão Wi-Fi virtual, envio HTTP, gravação pela API e leitura no dashboard.

## Validação Integrada

O fluxo validado foi:

```text
ESP32 simulado no Wokwi
|
Wi-Fi virtual Wokwi-GUEST
|
HTTP POST
|
Flask API
|
SQLite sensores.db
|
Dashboard Streamlit
```

Evidências observadas:

- PlatformIO Build com sucesso;
- firmware executado no Wokwi;
- dispositivo identificado como `esp32-farmtech-01`;
- envio HTTP realizado pelo firmware simulado;
- API retornou registro com sucesso;
- SQLite recebeu novas leituras;
- dashboard Streamlit exibiu leitura originada do `esp32-farmtech-01`;
- novas leituras de luminosidade registradas na escala 0 a 100%.

Não foram validados ESP32 físico, Wi-Fi em hardware físico nem sensores físicos reais.

## Segurança E Limitações

A API foi preparada para demonstração acadêmica em rede local. Ela não deve ser exposta publicamente sem autenticação, TLS, controle de acesso e endurecimento operacional.

A validação final disponível nesta entrega é a simulação integrada com Wokwi e serviços locais. A validação em ESP32 físico não foi realizada por indisponibilidade do hardware no grupo.
