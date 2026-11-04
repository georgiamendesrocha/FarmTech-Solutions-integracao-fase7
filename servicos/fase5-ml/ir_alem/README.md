# FarmTech Solutions - Ir Além

## ESP32/Wokwi + Wi-Fi + Sensores + Flask API + SQLite + Streamlit

Atividade opcional da Fase 5. Esta implementação recebe leituras de sensores ambientais, registra os dados em SQLite por meio de uma API Flask e exibe as leituras em um dashboard Streamlit.

A solução foi implementada e validada de ponta a ponta em ambiente simulado com Wokwi e serviços locais. A validação em ESP32 físico não foi realizada devido à indisponibilidade do hardware no grupo.

## Objetivo

Construir um fluxo IoT local, simples e auditável:

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

Não há MQTT, cloud ou Machine Learning neste componente.

## Status de validação

### Validado

- PlatformIO Build com sucesso;
- ESP32 simulado no Wokwi;
- DHT22 e LDR no circuito;
- conexão via Wi-Fi virtual `Wokwi-GUEST`;
- POST HTTP para `/telemetria`;
- Flask API recebendo leituras;
- SQLite local recebendo registros;
- dashboard Streamlit exibindo dados;
- identificação `esp32-farmtech-01`.

### Limitação

- Teste em ESP32 físico não realizado por indisponibilidade do hardware no grupo.

Essa limitação não representa falha técnica da implementação; apenas delimita o escopo da validação física.

## Componentes

| Componente | Função |
|---|---|
| ESP32/Wokwi | Microcontrolador simulado responsável pela leitura dos sensores e envio HTTP |
| DHT22 | Temperatura e umidade do ar |
| LDR | Luminosidade normalizada |
| Flask API | Recebe telemetria via HTTP POST e grava no SQLite |
| SQLite | Persistência local em `sensores.db`, criado em runtime e ignorado pelo Git |
| Streamlit | Dashboard para consulta e visualização dos dados gravados |

## Justificativa Dos Sensores

O DHT22 mede temperatura e umidade do ar, variáveis que ajudam a caracterizar condições ambientais relevantes ao monitoramento agrícola.

O LDR representa uma leitura simples de luminosidade e permite demonstrar a aquisição de uma variável ambiental adicional de baixo custo no protótipo.

O objetivo desta escolha é demonstrar a integração IoT entre sensores, firmware, API, banco local e dashboard. Não se afirma que apenas esses sensores sejam suficientes para um diagnóstico agronômico completo.

## Sensores, Variáveis E Escala

| Variável | Origem | Escala |
|---|---|---|
| `temperature` | DHT22 | graus Celsius |
| `humidity` | DHT22 | 0 a 100% |
| `light` | LDR analógico no ESP32 | 0 a 100% nas novas leituras |
| `device_id` | Firmware | identificador do dispositivo |

O ESP32 lê o LDR no GPIO34 em escala analógica de 0 a 4095 e normaliza a luminosidade para 0 a 100% antes do envio à API. Bancos locais reaproveitados podem conter registros históricos com `light` acima de 100; eles são preservados e tratados como históricos, sem conversão automática.

## Circuito Wokwi

O `diagram.json` define o circuito virtual utilizado pelo Wokwi na validação simulada:

| Componente | Conexão |
|---|---|
| DHT22 VCC | 3V3 |
| DHT22 GND | GND |
| DHT22 DATA | GPIO15 |
| LDR VCC | 3V3 |
| LDR GND | GND |
| LDR AO | GPIO34 |

O GPIO34 é usado como entrada analógica. O pino digital `DO` do módulo LDR não é usado.

O arquivo `circuito_wokwi.png` registra visualmente o circuito e a execução utilizada na validação simulada.

## Firmware

Arquivo principal: [`src/main.cpp`](src/main.cpp).

O firmware:

- lê DHT22 no GPIO15;
- lê LDR analógico no GPIO34;
- valida temperatura e umidade com `isnan()`;
- conecta o ESP32 simulado ao Wi-Fi virtual no Wokwi;
- tenta reconectar quando a conexão cai;
- envia leituras periodicamente para `POST /telemetria`;
- não registra SSID, senha ou IP local no código versionado.

## PlatformIO

O `platformio.ini` define o ambiente de compilação do firmware ESP32.

Configuração documentada:

- plataforma Espressif32;
- placa `esp32dev`;
- framework Arduino;
- biblioteca `adafruit/DHT sensor library`;
- biblioteca `adafruit/Adafruit Unified Sensor`.

Para reproduzir a compilação:

1. abra a pasta `ir_alem` no VS Code;
2. garanta que a extensão PlatformIO esteja instalada/disponível;
3. execute `PlatformIO: Build`;
4. confirme a mensagem `SUCCESS`.

## Integração Com Wokwi

O `wokwi.toml` integra o projeto compilado pelo PlatformIO ao simulador Wokwi. Ele aponta para os artefatos de firmware gerados em `.pio/build/esp32dev/`, usados pelo simulador durante a execução.

## Configuração Wi-Fi E API

O arquivo `src/secrets.example.h` é o template versionado. Ele contém apenas valores de exemplo/placeholders e serve como referência para criar a configuração local.

O arquivo `src/secrets.h` é local. Ele contém a configuração da rede e da API, não deve ser versionado e permanece protegido pelo `.gitignore`.

Para criar a configuração local, copie:

```bash
cp src/secrets.example.h src/secrets.h
```

No Windows, o mesmo passo pode ser feito copiando o arquivo pelo Explorer ou pelo terminal.

Para a simulação no Wokwi, a configuração local pode usar:

```cpp
#define WIFI_SSID "Wokwi-GUEST"
#define WIFI_PASSWORD ""
#define API_URL "http://host.wokwi.internal:5000/telemetria"
```

Esses valores são específicos da simulação Wokwi.

Para uso em outra rede ou em hardware físico, substitua `WIFI_SSID`, `WIFI_PASSWORD` e `API_URL` pelo SSID próprio, pela senha própria e pelo IP/endereço da máquina que executa a API Flask. Nesse cenário, não use `localhost` no `API_URL` do ESP32, pois ele apontaria para o próprio microcontrolador.

Nunca coloque credenciais reais no GitHub, no README ou em qualquer arquivo versionado.

## API HTTP

Arquivo: [`api.py`](api.py).

### `GET /health`

Resposta esperada:

```json
{
  "status": "online",
  "projeto": "FarmTech Solutions - Ir Além"
}
```

### `POST /telemetria`

Payload esperado:

```json
{
  "device_id": "esp32-farmtech-01",
  "temperature": 25.4,
  "humidity": 61.2,
  "light": 73
}
```

A API é responsável pela entrada da telemetria. Ela valida campos obrigatórios, números finitos e faixas esperadas: temperatura de -40 a 80 °C, umidade de 0 a 100% e luminosidade de 0 a 100%. Payload inválido retorna HTTP 400. Payload válido é gravado no SQLite com timestamp do servidor e retorna o identificador da leitura.

## Banco SQLite

Banco local padrão: `sensores.db`.

Esse arquivo não é versionado. Ele é um artefato local de execução, ignorado pelo Git. A API cria automaticamente o banco SQLite e a tabela necessária quando executada ou quando recebe uma leitura válida.

Tabela oficial:

| Campo | Tipo |
|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT |
| `timestamp` | TEXT |
| `temperature` | REAL |
| `humidity` | REAL |
| `light` | INTEGER |
| `device_id` | TEXT |

A aplicação cria a tabela se o banco ainda não existir. Novas leituras armazenam luminosidade normalizada de 0 a 100% no campo `light`. Se a tabela `leituras` já existir sem `device_id`, a API aplica uma migração idempotente com `ALTER TABLE` apenas para adicionar essa coluna. Bancos locais reaproveitados podem conter registros históricos fora dessa escala; esses registros não são apagados nem convertidos automaticamente.

É possível usar outro banco em testes definindo a variável de ambiente `FARMTECH_DB`.

## Dashboard Streamlit

Arquivo oficial: [`app.py`](app.py).

O dashboard somente consulta o `sensores.db`. Ele não simula sensores, não possui sliders e não insere leituras manualmente.

Exibe:

- última temperatura;
- última umidade;
- última luminosidade;
- `device_id`, quando disponível;
- horário da última leitura;
- histórico;
- tabela de dados;
- gráficos.

Durante a validação integrada, o dashboard exibiu leitura originada do dispositivo `esp32-farmtech-01`. Como evidência pontual de execução, foi observada uma leitura com temperatura de 24.0 °C, umidade de 40.0% e luminosidade de 24.0%. Esses valores não são requisito permanente do sistema.

## Execução Local

Execute os passos a partir do diretório `ir_alem`.

1. Abra `ir_alem` no VS Code.
2. Instale as dependências Python:

```bash
pip install -r requirements.txt
```

3. Crie `src/secrets.h` a partir de `src/secrets.example.h`.
4. Configure os valores para Wokwi no `src/secrets.h`.
5. No terminal 1, inicie a API:

```bash
python api.py
```

6. No terminal 2, inicie o dashboard:

```bash
streamlit run app.py
```

7. Acesse [http://localhost:8501](http://localhost:8501). O Streamlit normalmente também exibe esse endereço no terminal.
8. Execute `PlatformIO: Build`.
9. Abra o circuito no Wokwi.
10. Clique em Play.
11. Acompanhe o Serial Monitor.
12. Verifique o envio HTTP com resposta `201` e status `registrado`.
13. Atualize o dashboard e observe as leituras recebidas.

O `sqlite3` faz parte da biblioteca padrão do Python e não deve ser instalado via `pip`.

## Validação

Validações de software recomendadas:

```bash
python -m py_compile api.py app.py
```

Teste manual da API:

```bash
curl http://localhost:5000/health
```

```bash
curl -X POST http://localhost:5000/telemetria \
  -H "Content-Type: application/json" \
  -d "{\"device_id\":\"esp32-farmtech-01\",\"temperature\":25.4,\"humidity\":61.2,\"light\":73}"
```

A validação integrada já realizada cobriu o fluxo:

```text
ESP32 simulado no Wokwi
|
Wi-Fi virtual Wokwi-GUEST
|
HTTP POST
|
Flask API
|
SQLite local criado automaticamente
|
Dashboard Streamlit
```

O teste em ESP32 físico, Wi-Fi em hardware físico e sensores físicos reais não foi realizado por indisponibilidade do hardware no grupo.

## Segurança

Esta API é adequada para demonstração acadêmica em rede local. Ela não deve ser exposta como serviço público de produção sem autenticação, controle de acesso, TLS e endurecimento operacional.

Não coloque credenciais reais no Git, no README ou em logs. O firmware não imprime a senha Wi-Fi.

## Estrutura De Arquivos

```text
ir_alem/
|-- .gitignore
|-- api.py
|-- app.py
|-- requirements.txt
|-- diagram.json
|-- circuito_wokwi.png
|-- platformio.ini
|-- wokwi.toml
|-- README.md
|-- docs/
|   `-- documento_do_projeto.md
`-- src/
    |-- main.cpp
    `-- secrets.example.h
```

## Limitações

- A validação de ponta a ponta foi realizada em simulação integrada com Wokwi e serviços locais.
- A validação em ESP32 físico não foi realizada devido à indisponibilidade do hardware no grupo.
- `sensores.db` é um artefato local de execução e não é versionado.
- Não há autenticação porque o escopo é demonstração acadêmica local.

## Vídeo

Vídeo demonstrativo: link será inserido após a gravação.
