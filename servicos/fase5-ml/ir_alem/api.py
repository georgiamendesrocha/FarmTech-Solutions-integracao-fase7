# API da integração com ESP32 simulado no Wokwi.
# A validação da integração não utilizou hardware físico.
from datetime import datetime
import math
import os
from pathlib import Path
import sqlite3

from flask import Flask, jsonify, request


BASE_DIR = Path(__file__).resolve().parent
PROJECT_NAME = "FarmTech Solutions - Ir Além"


# FARMTECH_DB define o arquivo SQLite; o padrão é sensores.db ao lado desta API.
def get_db_path() -> Path:
    configured = os.environ.get("FARMTECH_DB")
    if configured:
        return Path(configured).expanduser()
    return BASE_DIR / "sensores.db"


# Prepara o diretório e cria a tabela apenas se ela ainda não existir.
def init_db() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Cada leitura tem chave sequencial, data/hora e as três medições obrigatórias.
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leituras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                light INTEGER NOT NULL
            )
            """
        )

        # Preserva bancos existentes e adiciona a identificação do dispositivo se faltar.
        columns = {row[1] for row in conn.execute("PRAGMA table_info(leituras)")}
        if "device_id" not in columns:
            conn.execute("ALTER TABLE leituras ADD COLUMN device_id TEXT")


# Padroniza a mensagem de erro em JSON e o código HTTP da resposta.
def _json_error(message: str, status_code: int = 400):
    return jsonify({"status": "erro", "erro": message}), status_code


# Exige texto não vazio e remove espaços nas extremidades do identificador.
def _required_text(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"campo obrigatório inválido: {field}")
    return value.strip()


# Aceita int/float; rejeita bool explicitamente, pois bool é uma subclasse de int.
def _required_number(payload: dict, field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"campo obrigatório inválido: {field}")
    value = float(value)
    # Rejeita NaN e infinitos antes de conferir as faixas dos sensores.
    if not math.isfinite(value):
        raise ValueError(f"campo numérico não finito: {field}")
    return value


# Exige um objeto JSON com device_id e os três valores numéricos dos sensores.
def validate_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload JSON inválido")

    device_id = _required_text(payload, "device_id")
    temperature = _required_number(payload, "temperature")
    humidity = _required_number(payload, "humidity")
    light = _required_number(payload, "light")

    # Limites inclusivos: temperatura do DHT22 de -40 a 80 °C e percentuais de 0 a 100.
    if not -40 <= temperature <= 80:
        raise ValueError("temperature fora do intervalo esperado do DHT22 (-40 a 80 °C)")
    if not 0 <= humidity <= 100:
        raise ValueError("humidity deve estar entre 0 e 100")
    if not 0 <= light <= 100:
        raise ValueError("light deve estar entre 0 e 100")

    # A luminosidade validada é arredondada para um inteiro antes da persistência.
    return {
        "device_id": device_id,
        "temperature": temperature,
        "humidity": humidity,
        "light": int(round(light)),
    }


app = Flask(__name__)


# GET /health informa que a API está online e identifica o projeto.
# Esta sonda verifica o processo da API, sem consultar o SQLite ou os sensores.
@app.get("/health")
def health():
    return jsonify({"status": "online", "projeto": PROJECT_NAME})


# POST /telemetria valida e registra uma leitura dos sensores no SQLite.
@app.post("/telemetria")
def telemetria():
    # Corpo ausente ou JSON malformado resulta em None e é rejeitado na validação.
    payload = request.get_json(silent=True)
    try:
        leitura = validate_payload(payload)
    # Erros de validação retornam JSON com o motivo e HTTP 400 antes de acessar o banco.
    except ValueError as exc:
        return _json_error(str(exc), 400)

    # Garante a estrutura e usa a data/hora local do servidor, em texto sem fuso horário.
    init_db()
    timestamp = datetime.now().isoformat(timespec="seconds")

    # O INSERT parametrizado mantém os valores recebidos separados da instrução SQL.
    # O contexto confirma a transação ao sair com sucesso ou a reverte em caso de erro.
    # Erros do SQLite seguem o tratamento padrão de exceções do Flask.
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO leituras (timestamp, device_id, temperature, humidity, light)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                leitura["device_id"],
                leitura["temperature"],
                leitura["humidity"],
                leitura["light"],
            ),
        )
        leitura_id = cursor.lastrowid

    # HTTP 201 confirma a criação e devolve a chave gerada para a leitura.
    return jsonify({"status": "registrado", "leitura_id": leitura_id}), 201


# A execução direta prepara o banco antes de iniciar o servidor Flask.
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
