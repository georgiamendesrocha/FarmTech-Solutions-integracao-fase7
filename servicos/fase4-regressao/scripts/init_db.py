"""
Script de inicialização do banco de dados FarmTech Solutions.
Cria o schema normalizado e carrega dois CSVs:
- historico_irrigacao.csv: leituras registradas/simuladas do protótipo ESP32/Wokwi.
- Atividade_Cap10_produtos_agricolas.csv: dataset agronômico fornecido pela FIAP,
  já utilizado na entrega da FarmTech na Fase 3.

Uso:
    python scripts/init_db.py
"""

import sqlite3
import csv
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Garante que a raiz do projeto está no path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db.database import (
    DB_PATH, SCHEMA_COLUMNS, configurar_conexao, normalizar_timestamp,
    resolve_db_path, validar_banco, validar_conexao, validar_leitura,
)
CSV_IRRIGACAO = ROOT / "src" / "dados" / "historico_irrigacao.csv"
CSV_AGRICOLA = ROOT / "src" / "dados" / "Atividade_Cap10_produtos_agricolas.csv"


DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS culturas (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS sensores (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo    TEXT NOT NULL,
    unidade TEXT NOT NULL,
    origem  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leituras_sensores (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id INTEGER NOT NULL REFERENCES sensores(id),
    ts        TEXT    NOT NULL,
    umidade   REAL    NOT NULL,
    temp_c    REAL    NOT NULL,
    ldr       REAL    NOT NULL,
    ph        REAL    NOT NULL,
    n         INTEGER NOT NULL,
    p         INTEGER NOT NULL,
    k         INTEGER NOT NULL,
    bomba_fw  INTEGER NOT NULL CHECK (bomba_fw IN (0, 1))
);

CREATE TABLE IF NOT EXISTS amostras_agronomicas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cultura_id  INTEGER NOT NULL REFERENCES culturas(id),
    n           REAL    NOT NULL,
    p           REAL    NOT NULL,
    k           REAL    NOT NULL,
    temperatura REAL    NOT NULL,
    umidade     REAL    NOT NULL,
    ph          REAL    NOT NULL,
    chuva       REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS previsoes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                 TEXT    NOT NULL,
    modelo             TEXT    NOT NULL,
    target             TEXT    NOT NULL,
    valor_previsto     REAL    NOT NULL,
    parametros_entrada TEXT    NOT NULL
);
"""


def criar_schema(conn: sqlite3.Connection) -> None:
    """Cria todas as tabelas se não existirem."""
    conn.executescript(DDL)
    conn.commit()


def seed_sensores(conn: sqlite3.Connection) -> int:
    """Garante que o sensor do protótipo ESP32/Wokwi está cadastrado e retorna seu id."""
    row = conn.execute("SELECT id FROM sensores WHERE origem = 'ESP32'").fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO sensores (tipo, unidade, origem) VALUES (?, ?, ?)",
        ("multiparâmetro", "misto", "ESP32"),
    )
    conn.commit()
    return cur.lastrowid


def _ler_irrigacao(path):
    values = []
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"ts_iso", "umidade", "temp_c", "ldr", "ph_corr", "N", "P", "K", "bomba_fw"}
        if (not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames)
                or not required.issubset(reader.fieldnames)
                or not set(reader.fieldnames).issubset(required | {"t_rel_ms", "ph_base"})):
            raise ValueError("CSV de irrigação sem colunas obrigatórias.")
        for row in reader:
            if row.get("ts_iso") == "=========== LEITURA ATUAL ===========":
                continue  # separador explícito do arquivo histórico do protótipo
            if None in row:
                raise ValueError("CSV de irrigação com schema inconsistente.")
            try:
                reading = validar_leitura(
                    float(row["umidade"]), float(row["temp_c"]), float(row["ldr"]),
                    float(row["ph_corr"]), int(row["N"]), int(row["P"]), int(row["K"]),
                    int(row["bomba_fw"]),
                )
                timestamp = normalizar_timestamp(row["ts_iso"])
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError("CSV de irrigação contém leitura inválida.") from exc
            values.append((timestamp, *reading[1:]))
    if not values:
        raise ValueError("CSV de irrigação não contém leituras válidas.")
    return values


def carregar_irrigacao(conn: sqlite3.Connection, sensor_id: int, registros=None) -> int:
    registros = _ler_irrigacao(CSV_IRRIGACAO) if registros is None else registros
    conn.executemany("""
        INSERT INTO leituras_sensores
            (sensor_id, ts, umidade, temp_c, ldr, ph, n, p, k, bomba_fw)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(sensor_id, *row) for row in registros])
    conn.commit()
    return len(registros)


def _ler_agricola(path):
    from src.validation import numero_finito, validar_entrada_ph

    values = []
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"N", "P", "K", "temperature", "humidity", "ph", "rainfall", "label"}
        if not reader.fieldnames or set(reader.fieldnames) != required or len(reader.fieldnames) != len(required):
            raise ValueError("CSV agronômico com schema inconsistente.")
        for row in reader:
            if None in row:
                raise ValueError("CSV agronômico com schema inconsistente.")
            try:
                features = {key: (row[key] if key == "label" else float(row[key])) for key in required - {"ph"}}
                entry = validar_entrada_ph(features)
                ph = numero_finito(float(row["ph"]), "ph", 0, 14)
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError("CSV agronômico contém amostra inválida.") from exc
            values.append((entry["label"], entry["N"], entry["P"], entry["K"],
                           entry["temperature"], entry["humidity"], ph, entry["rainfall"]))
    if not values:
        raise ValueError("CSV agronômico não contém amostras válidas.")
    return values


def carregar_agricola(conn: sqlite3.Connection, registros=None) -> int:
    registros = _ler_agricola(CSV_AGRICOLA) if registros is None else registros
    cultura_ids = {}
    for cultura, *values in registros:
        if cultura not in cultura_ids:
            conn.execute("INSERT OR IGNORE INTO culturas (nome) VALUES (?)", (cultura,))
            cultura_ids[cultura] = conn.execute("SELECT id FROM culturas WHERE nome = ?", (cultura,)).fetchone()[0]
        conn.execute("""
            INSERT INTO amostras_agronomicas
                (cultura_id, n, p, k, temperatura, umidade, ph, chuva)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (cultura_ids[cultura], *values))
    conn.commit()
    return len(registros)


def _snapshot(db_file: Path) -> Path:
    """Backup SQLite inclui commits em WAL; nunca copia apenas o arquivo principal."""
    directory = db_file.parent / "backups"
    directory.mkdir(exist_ok=True)
    prefix = db_file.stem + "-antes-importacao-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-"
    fd, filename = tempfile.mkstemp(prefix=prefix, suffix=".db", dir=directory)
    os.close(fd)
    backup_path = Path(filename)
    source = sqlite3.connect(db_file.as_uri() + "?mode=ro", uri=True)
    destination = None
    try:
        destination = sqlite3.connect(backup_path)
        source.backup(destination)
        validar_conexao(destination)
        destination.close()
        with backup_path.open("rb+") as file:
            os.fsync(file.fileno())
    finally:
        source.close()
        if destination is not None:
            destination.close()
    return backup_path


def _publicar(stage: Path, db_file: Path, timeout=5) -> Path | None:
    """Troca dados por transação no MESMO arquivo SQLite, preservando WAL e handles.

    Banco anterior deve ter schema válido. Conexão concorrente bloqueante faz a
    operação falhar/rollback; não há unlink/rename de banco ativo nem de sidecars.
    """
    existing = db_file.exists()
    backup = None
    conn = sqlite3.connect(db_file, timeout=timeout)
    try:
        configurar_conexao(conn)
        conn.execute("ATTACH DATABASE ? AS prepared", (str(stage),))
        conn.execute("BEGIN IMMEDIATE")
        if existing:
            validar_conexao(conn)
            backup = _snapshot(db_file)
            for table in ("previsoes", "leituras_sensores", "amostras_agronomicas", "sensores", "culturas"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('previsoes','leituras_sensores','amostras_agronomicas','sensores','culturas')")
        else:
            # executescript faz commit implícito: executar as DDL individualmente.
            for statement in DDL.split(";"):
                if statement.strip():
                    conn.execute(statement)
        for table in SCHEMA_COLUMNS:
            conn.execute(f"INSERT INTO main.{table} SELECT * FROM prepared.{table}")
        counts = validar_conexao(conn)
        expected = validar_banco(stage)
        if counts != expected:
            raise sqlite3.DatabaseError("Contagens divergentes na carga preparada.")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    return backup


def inicializar_banco(db_path=None, csv_irrigacao=None, csv_agricola=None, *, timeout=5):
    """Valida ambos CSVs, prepara base isolada e só então publica atomicamente."""
    irrigation = _ler_irrigacao(CSV_IRRIGACAO if csv_irrigacao is None else csv_irrigacao)
    agriculture = _ler_agricola(CSV_AGRICOLA if csv_agricola is None else csv_agricola)
    db_file = resolve_db_path(DB_PATH if db_path is None else db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".farmtech-import-", dir=db_file.parent) as temporary:
        stage = Path(temporary) / "prepared.db"
        conn = sqlite3.connect(stage)
        try:
            criar_schema(conn)
            sensor = seed_sensores(conn)
            carregar_irrigacao(conn, sensor, irrigation)
            carregar_agricola(conn, agriculture)
            counts = validar_conexao(conn)
        finally:
            conn.close()
        backup = _publicar(stage, db_file, timeout)
    return {"contagens": counts, "backup": str(backup) if backup else None}


def main() -> int:
    try:
        result = inicializar_banco()
    except (OSError, ValueError, sqlite3.Error):
        print("[ERRO] Inicialização não concluída. Confira os CSVs, o schema e as permissões; o banco anterior foi preservado.", file=sys.stderr)
        return 1
    print("[OK] Banco inicializado com integridade e referências conferidas.")
    if result["backup"]:
        print("[INFO] Cópia recuperável do estado anterior preservada na pasta backups do banco.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
