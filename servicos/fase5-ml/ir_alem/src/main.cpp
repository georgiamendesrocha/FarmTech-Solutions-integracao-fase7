// Firmware validado com ESP32 simulado no Wokwi.
// A validação da integração não utilizou hardware físico.
#include <Arduino.h>
#include <DHT.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <math.h>

// Carrega as credenciais Wi-Fi e a URL da API; sem secrets.h, a compilação falha.
#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Copie src/secrets.example.h para src/secrets.h e configure WIFI_SSID, WIFI_PASSWORD e API_URL."
#endif

// DHT22 no GPIO 15: leitura digital de temperatura (°C) e umidade relativa (%).
#define DHTPIN 15
#define DHTTYPE DHT22

// LDR no GPIO 34: entrada analógica com resolução de 12 bits definida no setup.
const int LDR_PIN = 34;
const char *DEVICE_ID = "esp32-farmtech-01";
// Pausa ao fim de cada ciclo; o tempo de coleta e transmissão é adicional.
const unsigned long SEND_INTERVAL_MS = 10000;
// Limita a espera de cada tentativa de conexão Wi-Fi a 15 segundos.
const unsigned long WIFI_TIMEOUT_MS = 15000;

DHT dht(DHTPIN, DHTTYPE);

// Mapeia o ADC de 0..4095 para um percentual inteiro e limita a saída a 0..100.
// A escala é relativa: não representa uma medição calibrada em lux.
int normalizarLuminosidade(int leituraAnalogica) {
  int luminosidade = map(leituraAnalogica, 0, 4095, 0, 100);
  return constrain(luminosidade, 0, 100);
}

// Reutiliza a conexão ativa ou inicia uma tentativa no modo estação (WIFI_STA).
bool conectarWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  Serial.print("Conectando ao Wi-Fi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // Aguarda a conexão com pausas de 500 ms, até o limite desta tentativa.
  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < WIFI_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("Wi-Fi conectado. IP local: ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.println();
  Serial.println("Falha ao conectar ao Wi-Fi. Nova tentativa no próximo ciclo.");
  return false;
}

// Verifica o Wi-Fi novamente antes do POST; sem conexão, retorna falha de envio.
bool enviarTelemetria(float temperatura, float umidade, int luminosidade) {
  if (!conectarWiFi()) {
    return false;
  }

  // Configura o destino e informa à API que o corpo da requisição contém JSON.
  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");

  // Monta o JSON com o identificador e os três campos esperados pela API.
  // Temperatura e umidade têm uma casa decimal; luminosidade é um inteiro.
  String payload = String("{\"device_id\":\"") + DEVICE_ID +
                   "\",\"temperature\":" + String(temperatura, 1) +
                   ",\"humidity\":" + String(umidade, 1) +
                   ",\"light\":" + String(luminosidade) + "}";

  // Envia a leitura, obtém a resposta e libera os recursos do cliente HTTP.
  int statusHttp = http.POST(payload);
  String resposta = http.getString();
  http.end();

  Serial.print("POST /telemetria -> HTTP ");
  Serial.println(statusHttp);
  if (resposta.length() > 0) {
    Serial.println(resposta);
  }

  // Apenas respostas HTTP 2xx são consideradas sucesso.
  return statusHttp >= 200 && statusHttp < 300;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Inicializa o DHT22, a entrada do LDR e o ADC de 12 bits (valores de 0 a 4095).
  dht.begin();
  pinMode(LDR_PIN, INPUT);
  analogReadResolution(12);

  conectarWiFi();
}

// Cada ciclo tenta restabelecer o Wi-Fi antes de coletar e transmitir os sensores.
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    conectarWiFi();
  }

  float umidade = dht.readHumidity();
  float temperatura = dht.readTemperature();

  // Se o DHT22 retornar NaN, descarta o envio e espera o próximo ciclo de coleta.
  if (isnan(umidade) || isnan(temperatura)) {
    Serial.println("Leitura inválida do DHT22. Envio ignorado neste ciclo.");
    delay(SEND_INTERVAL_MS);
    return;
  }

  // Lê e normaliza o LDR somente após obter leituras do DHT22 sem NaN.
  int leituraLdr = analogRead(LDR_PIN);
  int luminosidadePercent = normalizarLuminosidade(leituraLdr);

  Serial.println("=========================================");
  Serial.print("Device ID: ");
  Serial.println(DEVICE_ID);
  Serial.print("Temperatura do ar: ");
  Serial.print(temperatura, 1);
  Serial.println(" C");
  Serial.print("Umidade do ar: ");
  Serial.print(umidade, 1);
  Serial.println(" %");
  Serial.print("Luminosidade normalizada: ");
  Serial.print(luminosidadePercent);
  Serial.println(" %");
  Serial.println("=========================================");

  // Envia a leitura atual; falhas não geram fila local nem reenvio desta amostra.
  enviarTelemetria(temperatura, umidade, luminosidadePercent);
  // A pausa soma-se ao tempo gasto na coleta, nas tentativas Wi-Fi e no POST.
  delay(SEND_INTERVAL_MS);
}
