# 🚀 Firmware ESP32 - Sistema de Irrigação Inteligente

Este diretório contém o código-fonte do firmware que roda no microcontrolador **ESP32**. Os comandos de compilação e captura usam a raiz do módulo, onde estão `platformio.ini` e `app.py`; na estrutura `servicos/fase2-iot/`, essa é a pasta de execução.

Os parâmetros abaixo descrevem a simulação acadêmica implementada em [prog1.ino](prog1.ino). O DHT22 mede umidade relativa do ar, usada como representação didática de umidade do solo. O LDR simula pH; não é um sensor químico. Temperatura e previsão meteorológica não controlam a bomba: a temperatura é registrada e a previsão é analisada no PC em R.

## 📋 Arquivos Principais

```
src/
├── prog1.ino          # Firmware principal do ESP32
└── readme.md          # Este arquivo (documentação do firmware)
```

---

## 📝 prog1.ino - Firmware Principal

O arquivo `prog1.ino` implementa a lógica completa do sistema de irrigação automática para o tomate variedade Débora.

### O que o firmware faz?

1. **Lê sensores:**
   - DHT22 → Umidade e temperatura
   - LDR (ADC) → Simula pH do solo
   - Botões → Indicam presença de N, P, K

2. **Processa dados:**
   - Converte a leitura do LDR para pH simulado (0-14), sem calibração química
   - Calcula pH corrigido com base em nutrientes faltantes
   - Avalia condições da planta

3. **Decide irrigação:**
   - Compara umidade, pH e NPK contra faixas ideais
   - Ativa/desativa bomba (relé)
   - Sinaliza com LED

4. **Comunica com PC:**
   - Envia status via serial (115200 baud)
   - Formato CSV para análise em R
   - Monitor integrado no PlatformIO

---

## 🔌 Pinos Utilizados

### Entrada (Input)

| Sensor | Pino | Tipo | Descrição |
|--------|------|------|-----------|
| DHT22 (Umidade/Temp) | 15 | GPIO/input | Sensor de umidade relativa do ar |
| LDR (pH simulado) | 34 | ADC (A6) | Simula variações de pH (0-4095 → 0-14) |
| Botão N | 25 | GPIO/INPUT_PULLUP | Indicador de nitrogênio |
| Botão P | 26 | GPIO/INPUT_PULLUP | Indicador de fósforo |
| Botão K | 27 | GPIO/INPUT_PULLUP | Indicador de potássio |

### Saída (Output)

| Atuador | Pino | Tipo | Descrição |
|---------|------|------|-----------|
| Relé (Bomba) | 14 | GPIO/output | Controla bomba/solenóide de água |
| LED Irrigação | 2 | GPIO/output | Indicador visual de estado |

### Observação sobre INPUT_PULLUP
```cpp
pinMode(BTN_N, INPUT_PULLUP);  // Lê HIGH quando não pressionado
                               // Lê LOW quando pressionado
```

---

## 🍅 Parâmetros da Cultura - Tomate Débora

### Umidade do Solo

```cpp
const float UMIDADE_BAIXA_TOMATE = 45.0;  // Limite para irrigar sempre
const float UMIDADE_ALTA_TOMATE  = 80.0;  // Limite para não irrigar
```

**Lógica:**
- Umidade < 45% → Irrigação ativada (solo muito seco)
- 45% ≤ Umidade ≤ 80% → Decisão depende de pH e NPK
- Umidade > 80% → Irrigação desativada (solo muito úmido)

### pH do Solo

```cpp
const float PH_MIN_TOMATE = 6.0;   // Limite inferior ideal
const float PH_MAX_TOMATE = 6.8;   // Limite superior ideal
```

**Faixa ideal:** 6.0 a 6.8

### Ajustes de pH por Nutrientes Faltantes

```cpp
const float AJUSTE_FALTA_N = 0.3;  // Se N ausente, pH diminui 0.3
const float AJUSTE_FALTA_P = 0.2;  // Se P ausente, pH diminui 0.2
const float AJUSTE_FALTA_K = 0.2;  // Se K ausente, pH diminui 0.2
```

**Exemplo:**
- pH lido: 6.5
- Faltam N, P e K
- pH corrigido: 6.5 - 0.3 - 0.2 - 0.2 = 5.8 (abaixo do ideal!)
- Resultado na faixa de umidade de 45% a 80%: irrigação ativada. Acima de 80%, a regra de umidade desliga a irrigação.

---

## 🧊 Sensor DHT22

### Características

```cpp
DHTesp dhtSensor;
dhtSensor.setup(DHT_PIN, DHTesp::DHT22);
```

**Estados de leitura:**
```cpp
TempAndHumidity data = dhtSensor.getTempAndHumidity();

// O loop atual mantém os valores anteriores se houver NaN na leitura.
if (isnan(data.humidity) || isnan(data.temperature)) {
    Serial.println("Erro na leitura do DHT22");
}

// Dados válidos
float temperatura = data.temperature;    // Em °C
float umidade = data.humidity;           // Em % (0-100)
```

**Intervalo implementado de leitura:** 2000 ms. Não foi realizada aferição de precisão de um sensor físico na auditoria de 01/11/2026.

### Calibração

A simulação não inclui calibração para solo. Uso físico exigiria sensor apropriado, calibração e validação agronômica. O firmware mantém a última leitura quando o DHT22 retorna NaN, e a variável de umidade começa em zero antes da primeira leitura; esses limites devem ser revistos antes de uso real, conforme a [auditoria de segurança](../document/AUDITORIA_SEGURANCA_F2.md).

---

## 💡 Sensor LDR (pH Simulado)

### Como funciona

O LDR mapeia a leitura analógica para escala de pH:

```cpp
// Leitura do ADC (0-4095)
int valorLDR = analogRead(LDR_PIN);

// Mapeamento para pH (0-14)
float pH = 14.0 - ((valorLDR / 4095.0) * 14.0);

// Exemplo:
// LDR = 0     → pH = 14 (extremo básico simulado)
// LDR = 2048  → pH = 7 (neutro)
// LDR = 4095  → pH = 0 (extremo ácido simulado)
```

**Nota:** O LDR não é um sensor real de pH. É apenas para simulação didática em ambiente Wokwi.

---

## 🔘 Botões N, P, K (Toggle com Debounce)

### Como funciona

Cada botão opera em modo **toggle**, com detecção de borda de descida e intervalo maior que **180 ms** desde a última alternância aceita:

```cpp
// Pseudocódigo
if (borda_de_descida && tempo_desde_ultimo_ms > 180) {
    nutriente = !nutriente;  // Alterna entre true/false
    debounce_timestamp = agora;
}
```

**Estados:**
- `true` = Nutriente presente ✓
- `false` = Nutriente ausente ✗

**Por que toggle?**
- Facilita simulação com mouse no Wokwi
- Um clique = alterna estado
- Não precisa ficar pressionado

---

## 🔄 Lógica de Decisão de Irrigação

### Fluxograma

```
INÍCIO
  ↓
Ler sensores (DHT, LDR, botões)
  ↓
Calcular pH corrigido (com ajustes de NPK)
  ↓
┌─────────────────────────────────┐
│ Se umidade < 45% ?              │
│ SIM → Ativar bomba (SEMPRE)     │
│ NÃO → Próximo                   │
└─────────────────────────────────┘
  ↓
┌─────────────────────────────────┐
│ Se 45% ≤ umidade ≤ 80% ?        │
│ SIM → Verificar pH e NPK        │
│ NÃO → Próximo                   │
└─────────────────────────────────┘
  ↓
  ├─ pH fora do ideal [6.0-6.8] ? → Ativar bomba
  ├─ Faltando N, P ou K ?         → Ativar bomba
  ├─ (Nenhum problema)            → Desativar bomba
  ↓
┌─────────────────────────────────┐
│ Se umidade > 80% ?              │
│ SIM → Desativar bomba (NUNCA)   │
│ NÃO → Manter estado             │
└─────────────────────────────────┘
  ↓
Enviar status via UART
Atualizar LED e relé
  ↓
FIM
```

---

## 📡 Saída Serial (UART)

### Formato de Comunicação

**Velocidade:** 115200 baud  
**Protocolo:** Serial ASCII

### Tipos de Mensagens

#### 1. CSV_HDR (Cabeçalho)
Enviado uma única vez ao iniciar:
```
CSV_HDR,t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw
```

#### 2. CSV_ROW (Dados)
Enviado quando há mudança significativa ou a cada 30 segundos:
```
CSV_ROW,45000,68.50,25.20,2048,6.998,6.798,1,0,1,1
```

O registro acima é um exemplo didático de formato, não evidência de teste. O ESP32 não envia `ts_iso`: o capturador Python ou o filtro PlatformIO acrescenta a data/hora de recepção no PC ao persistir o CSV. O campo não é uma medição de horário feita pelo ESP32.

**Campos enviados pelo firmware:**
- `t_rel_ms` - Tempo em ms desde reset
- `umidade` - % (0-100)
- `temp_c` - °C
- `ldr` - Valor bruto ADC (0-4095)
- `ph_base` - Valor simulado a partir do LDR (0-14)
- `ph_corr` - pH com ajustes didáticos de NPK
- `N, P, K` - 1=presente, 0=ausente
- `bomba_fw` - 1=ligada, 0=desligada

#### 3. MENSAGENS DE DEBUG

```
Inicializando sistema de irrigacao inteligente para TOMATE...
Erro ao ler o DHT22.
```

---

## 🛠️ Como Compilar e Fazer Upload

### Via PlatformIO CLI

```bash
# Compilar
pio run -e esp32

# Compilar e fazer upload na placa
pio run -e esp32 --target upload

# Compilar e monitorar serial
pio run -e esp32 --target upload --target monitor
```

### Via VS Code + PlatformIO Extension

1. Clique no ícone PlatformIO (🤖 alienígena)
2. Vá para "Project Tasks"
3. Escolha:
   - `Build` → Compilar
   - `Upload` → Fazer upload
   - `Monitor` → Monitorar serial

### Com Wokwi (Simulação)

Siga o [procedimento de inicialização no README](../README.md#iniciar-o-wokwi-no-vs-code), usando o ambiente `esp32` e o comando **Wokwi: Start Simulator** na paleta do VS Code. O firmware precisa estar compilado previamente nos caminhos de [wokwi.toml](../wokwi.toml). O comando pode iniciar a simulação sem abrir uma nova aba `diagram.json`; o menu Python não faz a compilação nem inicia automaticamente o simulador.

Para persistir o CSV pelo menu principal, execute `python app.py` na raiz e escolha a opção 1. O capturador Python usa `rfc2217://127.0.0.1:4000` a 115200 baud; Enter ou Ctrl+C encerram a captura e retornam ao menu.

Como alternativa independente e interativa, use `pio device monitor -e esp32 -p rfc2217://127.0.0.1:4000 -b 115200`. Esse fluxo usa [monitor/filter_irrigation_csv.py](../monitor/filter_irrigation_csv.py), configurado no `platformio.ini`. O painel serial do Wokwi sozinho não grava o arquivo local. Use apenas um capturador por vez. Para placa física, o script Python também aceita `--port COM6` (substitua pela porta real); PySerial é a dependência de captura.

---

## 🐛 Troubleshooting de Firmware

### ❌ Erro: "Erro ao ler o DHT22."

**Causas:**
- Pino DHT não conectado corretamente
- Sensor danificado
- Leitura inválida reportada pela biblioteca DHTesp

**Verificação:** Confira a conexão ao GPIO 15 e a alimentação no diagrama ou na placa. O firmware já espaça as leituras em 2000 ms; o DHT22 não usa I2C. Não altere o firmware apenas para contornar a mensagem sem identificar a causa.

### ❌ Botões não funcionar

**Verificar:** Os botões usam INPUT_PULLUP: soltos leem HIGH e pressionados leem LOW. O estado do nutriente alterna por clique aceito, começando como ausente.

**Causas comuns:**
- INPUT_PULLUP não ativado
- Pino errado
- Botão com contato ruim

### ❌ Relé não ativa bomba

**Verificar:** Compare a regra de umidade/pH/NPK, a saída de status e a conexão do GPIO 14. O código atual usa `RELAY_ON = LOW` e `RELAY_OFF = HIGH`; o LED no GPIO 2 acompanha a decisão. Em hardware real, confirme a polaridade e a alimentação com o circuito desenergizado antes de qualquer ensaio.

**Causas:**
- N/OS do relé invertido
- Alimentação do relé insuficiente
- Pino voltou para HIGH mas relé não desligou

---

## 📊 Estrutura de Código

Esquema conceitual; os nomes abaixo resumem etapas, não substituem as funções reais de `prog1.ino`:

```cpp
#include <bibliotecas>          // Includes
#define constantes              // Pinos e parâmetros
DHTesp dhtSensor;               // Objetos globais
float umidadeSolo;              // Variáveis globais

void setup() {                  // Inicialização
    Serial.begin(115200);
    dhtSensor.setup(DHT_PIN, DHTesp::DHT22);
    pinMode(RELAY_PIN, OUTPUT);
    // ...
}

void loop() {                   // Loop principal
    lerSensores();
    processarDados();
    decidirIrrigacao();
    enviarSerial();
}

void lerSensores() { }          // Funções auxiliares
void processarDados() { }
void decidirIrrigacao() { }
void enviarSerial() { }
```

---

## 🔗 Documentação Relacionada

- [README.md](../README.md) - Visão geral do projeto
- [platformio.ini](../platformio.ini) - Configuração de build
- [wokwi.toml](../wokwi.toml) - Simulador
- [diagram.json](../diagram.json) - Circuito Wokwi

---

## 💾 Versão do Firmware

- **Identificação histórica deste guia:** 0.1.4 (13/04/2026). O README principal declarava 0.1.4 em 12/04/2026; as datas documentais divergem. Não há constante de versão no firmware nem tag no histórico consultado em 01/11/2026 que confirme um lançamento. Consulte o [histórico de versões documentadas](../README.md#-histórico-de-versões-documentadas) e o [CHANGELOG](../CHANGELOG.md).
- **Placa configurada no PlatformIO:** `esp32dev`
- **Framework:** Arduino (via PlatformIO)
- **Linguagem:** C++
