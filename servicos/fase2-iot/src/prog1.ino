#include <DHTesp.h>
#include <math.h>

// =========================
// Definição de pinos
// =========================
#define BTN_N      25
#define BTN_P      26
#define BTN_K      27

#define LDR_PIN    34
#define DHT_PIN    15

#define RELAY_PIN  14
#define LED_IRR    2

// Muitos módulos de relé acionam a carga com IN em LOW (ativo em baixo).
// Se a sua bomba ligar com HIGH no IN, troque RELAY_ON para HIGH e RELAY_OFF para LOW.
static const uint8_t RELAY_ON  = LOW;
static const uint8_t RELAY_OFF = HIGH;

// =========================
// Parâmetros da cultura: TOMATE
// =========================
const float PH_MIN_TOMATE = 6.0;
const float PH_MAX_TOMATE = 6.8;

const float UMIDADE_BAIXA_TOMATE = 45.0;
const float UMIDADE_ALTA_TOMATE  = 80.0;

// Ajustes de pH pela ausência de nutrientes
const float AJUSTE_FALTA_N = 0.3;
const float AJUSTE_FALTA_P = 0.2;
const float AJUSTE_FALTA_K = 0.2;

// =========================
// Objeto do DHT22
// =========================
DHTesp dhtSensor;

// =========================
// Variáveis globais
// =========================
float umidadeSolo = 0.0;
float temperatura = 0.0;
int valorLDR = 0;

bool nitrogenio = false;
bool fosforo = false;
bool potassio = false;

float phBaseLdr = 7.0;
float phCorrigido = 7.0;
bool irrigacaoLigada = false;

float ultimoUmidadeSolo = NAN;
float ultimaTemperatura = NAN;
int ultimoValorLDR = -1;
float ultimoPhBaseLdr = NAN;
float ultimoPhCorrigido = NAN;
bool ultimoNitrogenio = false;
bool ultimoFosforo = false;
bool ultimoPotassio = false;
bool ultimaIrrigacao = false;
bool primeiraImpressao = true;

// =========================
// Controle de clique/toggle
// =========================
bool ultimoEstadoBtnN = HIGH;
bool ultimoEstadoBtnP = HIGH;
bool ultimoEstadoBtnK = HIGH;

unsigned long ultimoCliqueN = 0;
unsigned long ultimoCliqueP = 0;
unsigned long ultimoCliqueK = 0;

const unsigned long debounceDelay = 180;

// =========================
// Controle de tempo
// =========================
unsigned long ultimaLeituraDHT = 0;

const unsigned long intervaloDHT = 2000;

// Amostra CSV_ROW a cada N ms para serie temporal (historico no PC via script serial)
const unsigned long INTERVALO_LOG_HISTORICO_MS = 30000UL;
unsigned long ultimoLogHistoricoMs = 0;

// =========================
// Função para converter LDR em pH simulado
// ADC ESP32: 0 a 4095
// pH: 0 a 14
// =========================
float calcularPhBase(int leituraLdr) {
  float ph = 14.0 - ((leituraLdr / 4095.0) * 14.0);

  if (ph < 0.0) ph = 0.0;
  if (ph > 14.0) ph = 14.0;

  return ph;
}

// =========================
// Corrige pH com base nos nutrientes
// =========================
float corrigirPhPorNutrientes(float phBase, bool n, bool p, bool k) {
  float phFinal = phBase;

  if (!n) phFinal -= AJUSTE_FALTA_N;
  if (!p) phFinal -= AJUSTE_FALTA_P;
  if (!k) phFinal -= AJUSTE_FALTA_K;

  if (phFinal < 0.0) phFinal = 0.0;
  if (phFinal > 14.0) phFinal = 14.0;

  return phFinal;
}

// =========================
// Classificações
// =========================
String classificarPhTomate(float ph) {
  if (ph <= 5.9) return "ACIDO";
  if (ph <= 6.8) return "NEUTRO/IDEAL";
  return "ALCALINO";
}

String classificarUmidadeTomate(float umidade) {
  if (umidade < UMIDADE_BAIXA_TOMATE) return "BAIXA";
  if (umidade <= UMIDADE_ALTA_TOMATE) return "ADEQUADA/ATENCAO";
  return "ALTA";
}

String classificarNutrientes(bool n, bool p, bool k) {
  if (n && p && k) return "ADEQUADOS";
  if (!n && !p && !k) return "TODOS AUSENTES";
  return "INADEQUADOS";
}

// =========================
// Toggle por clique para pushbutton
// =========================
void atualizarBotaoToggle(int pino, bool &estadoTravado, bool &ultimoEstado, unsigned long &ultimoClique) {
  bool estadoAtual = digitalRead(pino);

  // Detecta borda de descida: botão foi pressionado
  if (ultimoEstado == HIGH && estadoAtual == LOW) {
    if (millis() - ultimoClique > debounceDelay) {
      estadoTravado = !estadoTravado;
      ultimoClique = millis();
    }
  }

  ultimoEstado = estadoAtual;
}

// =========================
// Regra de irrigação para tomate
// =========================
bool decidirIrrigacaoTomate(float umidade, float ph, bool n, bool p, bool k) {
  // Evita comparações com NaN/Inf (resultado indefinido e podia cair no "return false" final).
  if (isnan(umidade) || isinf(umidade) || umidade < 0.0f || umidade > 100.0f) {
    return false;
  }

  const bool nutrientesAdequados = (n && p && k);
  const bool phOk = (!isnan(ph) && !isinf(ph) && ph >= PH_MIN_TOMATE && ph <= PH_MAX_TOMATE);

  if (umidade > UMIDADE_ALTA_TOMATE) {
    return false;
  }

  if (umidade < UMIDADE_BAIXA_TOMATE) {
    return true;
  }

  // Faixa intermediária [UMIDADE_BAIXA, UMIDADE_ALTA]: irrigar se NPK incompleto ou pH fora do ideal
  if (!nutrientesAdequados || !phOk) {
    return true;
  }

  return false;
}

// =========================
// Justificativa textual
// =========================
String gerarMotivoIrrigacao(float umidade, float ph, bool n, bool p, bool k, bool irrigando) {
  bool nutrientesAdequados = n && p && k;
  bool phIdeal = (!isnan(ph) && !isinf(ph) && ph >= PH_MIN_TOMATE && ph <= PH_MAX_TOMATE);

  if (irrigando) {
    if (umidade < UMIDADE_BAIXA_TOMATE) {
      return "Umidade baixa para tomate.";
    }

    if (!phIdeal && !nutrientesAdequados) {
      return "Umidade em atencao, pH inadequado e nutrientes inadequados.";
    }

    if (!phIdeal) {
      return "Umidade em atencao e pH inadequado para tomate.";
    }

    if (!nutrientesAdequados) {
      return "Umidade em atencao e combinacao NPK inadequada.";
    }
  }

  if (umidade > UMIDADE_ALTA_TOMATE) {
    return "Solo ja esta muito umido para tomate.";
  }

  return "Condicoes adequadas para tomate, sem necessidade de irrigacao.";
}

// =========================
// Exportacao CSV para analise em R (linhas prefixadas para filtro no PC)
// Formato: CSV_HDR = cabecalho; CSV_ROW = uma observacao por mudanca relevante
// =========================
static void imprimirCabecalhoCsvParaR() {
  Serial.println("CSV_HDR,t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw");
}

static void imprimirLinhaCsvParaR() {
  const int n = nitrogenio ? 1 : 0;
  const int p = fosforo ? 1 : 0;
  const int k = potassio ? 1 : 0;
  const int bomba = irrigacaoLigada ? 1 : 0;

  Serial.printf(
    "CSV_ROW,%lu,%.2f,%.2f,%d,%.3f,%.3f,%d,%d,%d,%d\n",
    static_cast<unsigned long>(millis()),
    static_cast<double>(umidadeSolo),
    static_cast<double>(temperatura),
    valorLDR,
    static_cast<double>(phBaseLdr),
    static_cast<double>(phCorrigido),
    n,
    p,
    k,
    bomba
  );
}

// =========================
// Mostra dados no Serial
// =========================
void imprimirStatus() {
  Serial.println("=========== LEITURA ATUAL ===========");
  Serial.println("CULTURA MONITORADA: TOMATE");

  Serial.print("Umidade do solo simulada (%): ");
  Serial.println(umidadeSolo, 1);

  Serial.print("Classificacao da umidade: ");
  Serial.println(classificarUmidadeTomate(umidadeSolo));

  Serial.print("Temperatura ambiente (C): ");
  Serial.println(temperatura, 1);

  Serial.print("Leitura LDR: ");
  Serial.println(valorLDR);

  Serial.print("pH base do LDR: ");
  Serial.println(phBaseLdr, 2);

  Serial.print("pH corrigido pelos nutrientes: ");
  Serial.println(phCorrigido, 2);

  Serial.print("Classificacao do pH: ");
  Serial.println(classificarPhTomate(phCorrigido));

  Serial.print("Nitrogenio (N): ");
  Serial.println(nitrogenio ? "PRESENTE" : "AUSENTE");

  Serial.print("Fosforo (P): ");
  Serial.println(fosforo ? "PRESENTE" : "AUSENTE");

  Serial.print("Potassio (K): ");
  Serial.println(potassio ? "PRESENTE" : "AUSENTE");

  Serial.print("Estado dos nutrientes: ");
  Serial.println(classificarNutrientes(nitrogenio, fosforo, potassio));

  Serial.print("Irrigacao: ");
  Serial.println(irrigacaoLigada ? "LIGADA" : "DESLIGADA");

  Serial.print("Justificativa: ");
  Serial.println(gerarMotivoIrrigacao(
    umidadeSolo,
    phCorrigido,
    nitrogenio,
    fosforo,
    potassio,
    irrigacaoLigada
  ));

  Serial.println("=====================================");
  Serial.println();
}

// =========================
// Setup
// =========================
void setup() {
  Serial.begin(115200);
  Serial.println("Inicializando sistema de irrigacao inteligente para TOMATE...");

  pinMode(BTN_N, INPUT_PULLUP);
  pinMode(BTN_P, INPUT_PULLUP);
  pinMode(BTN_K, INPUT_PULLUP);

  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_IRR, OUTPUT);

  digitalWrite(RELAY_PIN, RELAY_OFF);
  digitalWrite(LED_IRR, LOW);

  dhtSensor.setup(DHT_PIN, DHTesp::DHT22);

  ultimoEstadoBtnN = digitalRead(BTN_N);
  ultimoEstadoBtnP = digitalRead(BTN_P);
  ultimoEstadoBtnK = digitalRead(BTN_K);

  Serial.println("Sistema iniciado com sucesso.");
  Serial.println("Clique nos botoes N, P e K para alternar os nutrientes.");
  Serial.println("O LDR representa o pH do solo.");
  Serial.println("O DHT22 representa a umidade do solo.");
  Serial.println("--------------------------------------------");
  Serial.println("Log CSV para R: linhas CSV_HDR (uma vez) e CSV_ROW a cada atualizacao.");
  imprimirCabecalhoCsvParaR();
}

// =========================
// Loop principal
// =========================
void loop() {
  // Atualiza estados travados dos nutrientes por clique
  atualizarBotaoToggle(BTN_N, nitrogenio, ultimoEstadoBtnN, ultimoCliqueN);
  atualizarBotaoToggle(BTN_P, fosforo,    ultimoEstadoBtnP, ultimoCliqueP);
  atualizarBotaoToggle(BTN_K, potassio,   ultimoEstadoBtnK, ultimoCliqueK);

  // Leitura do LDR e cálculo do pH
  valorLDR = analogRead(LDR_PIN);
  phBaseLdr = calcularPhBase(valorLDR);
  phCorrigido = corrigirPhPorNutrientes(phBaseLdr, nitrogenio, fosforo, potassio);

  // Leitura periódica do DHT22
  if (millis() - ultimaLeituraDHT >= intervaloDHT) {
    ultimaLeituraDHT = millis();

    TempAndHumidity dados = dhtSensor.getTempAndHumidity();

    if (!isnan(dados.humidity) && !isnan(dados.temperature)) {
      umidadeSolo = dados.humidity;
      temperatura = dados.temperature;
    } else {
      Serial.println("Erro ao ler o DHT22.");
    }
  }

  // Decisão de irrigação para tomate
  irrigacaoLigada = decidirIrrigacaoTomate(
    umidadeSolo,
    phCorrigido,
    nitrogenio,
    fosforo,
    potassio
  );

  // Acionamento do relé e LED
  digitalWrite(RELAY_PIN, irrigacaoLigada ? RELAY_ON : RELAY_OFF);
  digitalWrite(LED_IRR, irrigacaoLigada ? HIGH : LOW);

  // Imprime apenas quando houver alteração nos dados ou botões
  bool houveAlteracao = primeiraImpressao;
  primeiraImpressao = false;

  if (fabsf(umidadeSolo - ultimoUmidadeSolo) > 0.2f) houveAlteracao = true;
  if (fabsf(temperatura - ultimaTemperatura) > 0.2f) houveAlteracao = true;
  if (valorLDR != ultimoValorLDR) houveAlteracao = true;
  if (fabsf(phBaseLdr - ultimoPhBaseLdr) > 0.01f) houveAlteracao = true;
  if (fabsf(phCorrigido - ultimoPhCorrigido) > 0.01f) houveAlteracao = true;
  if (nitrogenio != ultimoNitrogenio) houveAlteracao = true;
  if (fosforo != ultimoFosforo) houveAlteracao = true;
  if (potassio != ultimoPotassio) houveAlteracao = true;
  if (irrigacaoLigada != ultimaIrrigacao) houveAlteracao = true;

  if (houveAlteracao) {
    imprimirStatus();
    imprimirLinhaCsvParaR();

    ultimoUmidadeSolo = umidadeSolo;
    ultimaTemperatura = temperatura;
    ultimoValorLDR = valorLDR;
    ultimoPhBaseLdr = phBaseLdr;
    ultimoPhCorrigido = phCorrigido;
    ultimoNitrogenio = nitrogenio;
    ultimoFosforo = fosforo;
    ultimoPotassio = potassio;
    ultimaIrrigacao = irrigacaoLigada;
  }

  // Historico: linha CSV periodica mesmo sem mudanca (captura pelo PC grava em CSV local)
  if (millis() - ultimoLogHistoricoMs >= INTERVALO_LOG_HISTORICO_MS) {
    ultimoLogHistoricoMs = millis();
    imprimirLinhaCsvParaR();
  }
}