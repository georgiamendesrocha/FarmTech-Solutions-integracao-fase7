"""SQLite: conexões fechadas, validação e transações explícitas.

DB_PATH absoluto é respeitado; caminhos relativos são relativos à raiz do módulo.
Nenhum helper de consulta cria silenciosamente um banco ausente.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
DB_PATH = os.getenv("DB_PATH", "src/db/farmtech.db")
SCHEMA_COLUMNS = {
    "culturas": ("id", "nome"),
    "sensores": ("id", "tipo", "unidade", "origem"),
    "leituras_sensores": ("id", "sensor_id", "ts", "umidade", "temp_c", "ldr", "ph", "n", "p", "k", "bomba_fw"),
    "amostras_agronomicas": ("id", "cultura_id", "n", "p", "k", "temperatura", "umidade", "ph", "chuva"),
    "previsoes": ("id", "ts", "modelo", "target", "valor_previsto", "parametros_entrada"),
}


def resolve_db_path(path=None) -> Path:
    value = Path(DB_PATH if path is None else path).expanduser()
    return (value if value.is_absolute() else ROOT / value).resolve()


def normalizar_timestamp(value: str) -> str:
    """Interpreta históricos sem offset como UTC; novos registros usam ISO UTC."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Timestamp inválido.")
    if "T" not in value and " " not in value:
        raise ValueError("Timestamp deve conter data e hora.")
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Timestamp inválido.") from exc
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    try:
        return date.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    except OverflowError as exc:
        raise ValueError("Timestamp fora do intervalo suportado.") from exc


def _utc_micros(value):
    try:
        date = datetime.fromisoformat(normalizar_timestamp(value).replace("Z", "+00:00"))
        delta = date - datetime(1970, 1, 1, tzinfo=timezone.utc)
        return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
    except (ValueError, TypeError, OverflowError):
        return None


def configurar_conexao(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.create_function("utc_micros", 1, _utc_micros, deterministic=True)


@contextmanager
def get_connection():
    """Abre banco existente; confirma ou reverte e sempre fecha a conexão."""
    conn = sqlite3.connect(resolve_db_path().as_uri() + "?mode=rw", uri=True, timeout=5)
    try:
        configurar_conexao(conn)
        with conn:
            yield conn
    finally:
        conn.close()


def validar_conexao(conn: sqlite3.Connection) -> dict:
    """Valida schema mínimo, constraints, integridade e referências sem gravar."""
    configurar_conexao(conn)
    if [r[0] for r in conn.execute("PRAGMA integrity_check")] != ["ok"]:
        raise sqlite3.DatabaseError("Banco com falha de integridade.")
    counts = {}
    for table, columns in SCHEMA_COLUMNS.items():
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if tuple(row[1] for row in info) != columns or not info[0][5]:
            raise sqlite3.DatabaseError("Schema do banco incompatível.")
        if any(not row[3] for row in info[1:]):
            raise sqlite3.DatabaseError("Schema do banco sem campos obrigatórios.")
        integer_columns = {"id", "sensor_id", "cultura_id", "bomba_fw"}
        if table == "leituras_sensores":
            integer_columns.update(("n", "p", "k"))
        text_columns = {"nome", "tipo", "unidade", "origem", "ts", "modelo", "target", "parametros_entrada"}
        for row in info:
            expected_type = "INTEGER" if row[1] in integer_columns else "TEXT" if row[1] in text_columns else "REAL"
            if row[2].upper() != expected_type:
                raise sqlite3.DatabaseError("Tipos do schema incompatíveis.")
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    unique_names = [r[1] for r in conn.execute("PRAGMA index_list(culturas)") if r[2]]
    if not any([r[2] for r in conn.execute('PRAGMA index_info("' + name.replace('"', '""') + '")')] == ["nome"] for name in unique_names):
        raise sqlite3.DatabaseError("Schema sem unicidade de cultura.")
    for table, column, parent in (
        ("leituras_sensores", "sensor_id", "sensores"),
        ("amostras_agronomicas", "cultura_id", "culturas"),
    ):
        foreign_keys = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
        if not any(row[2] == parent and row[3] == column and row[4] == "id" for row in foreign_keys):
            raise sqlite3.DatabaseError("Schema do banco sem relação obrigatória.")
    sensor_schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='leituras_sensores'").fetchone()[0]
    if "check(bomba_fwin(0,1))" not in "".join(sensor_schema.lower().split()):
        raise sqlite3.DatabaseError("Schema do banco sem restrição de bomba.")
    if conn.execute("PRAGMA foreign_key_check").fetchone():
        raise sqlite3.DatabaseError("Banco com referências inválidas.")
    for table in ("leituras_sensores", "previsoes"):
        if conn.execute(f"SELECT 1 FROM {table} WHERE utc_micros(ts) IS NULL LIMIT 1").fetchone():
            raise sqlite3.DatabaseError("Histórico contém timestamp inválido.")
    return counts


def validar_banco(path=None) -> dict:
    """Inspeção somente leitura, inclusive para pré-condição de execução da CLI."""
    conn = sqlite3.connect(resolve_db_path(path).as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        return validar_conexao(conn)
    finally:
        conn.close()


def status_banco() -> dict:
    return validar_banco()


def _limite(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 100000:
        raise ValueError("Limite deve ser inteiro entre 0 e 100000.")
    return value


def get_leituras(limite: int = 200) -> list[dict]:
    sql = """
        SELECT ls.id, ls.ts, ls.umidade, ls.temp_c, ls.ldr,
               ls.ph, ls.n, ls.p, ls.k, ls.bomba_fw, s.tipo as sensor_tipo
        FROM leituras_sensores ls JOIN sensores s ON s.id = ls.sensor_id
        ORDER BY utc_micros(ls.ts) DESC, ls.id DESC LIMIT ?
    """
    with get_connection() as conn:
        rows = conn.execute(sql, (_limite(limite),)).fetchall()
    return [dict(r) for r in rows]


def get_ultima_leitura() -> dict | None:
    rows = get_leituras(1)
    return rows[0] if rows else None


def get_amostras_agronomicas() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT aa.id, c.nome as cultura, aa.n, aa.p, aa.k,
                   aa.temperatura, aa.umidade, aa.ph, aa.chuva
            FROM amostras_agronomicas aa JOIN culturas c ON c.id = aa.cultura_id
            ORDER BY aa.id
        """).fetchall()
    return [dict(r) for r in rows]


def get_culturas() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT nome FROM culturas ORDER BY nome").fetchall()
    return [r["nome"] for r in rows]


def _validar_previsao(modelo, target, valor, parametros):
    from src.validation import validar_entrada_original, validar_entrada_ph, validar_valor_previsto

    if not isinstance(modelo, str) or not modelo.strip() or len(modelo) > 200:
        raise ValueError("Identificação de modelo inválida.")
    if not isinstance(parametros, str) or len(parametros) > 20000:
        raise ValueError("Parâmetros de previsão inválidos.")
    try:
        params = json.loads(parametros, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Valor JSON não finito.")))
    except (ValueError, TypeError) as exc:
        raise ValueError("Parâmetros de previsão inválidos.") from exc
    if not isinstance(params, dict):
        raise ValueError("Parâmetros de previsão devem ser um objeto.")
    if target == "ph" and "cultura" in params and "label" in params:
        if params["cultura"] != params["label"]:
            raise ValueError("Identificação de cultura inconsistente.")
        params.pop("cultura")
    valid = validar_entrada_ph(params) if target == "ph" else validar_entrada_original(params)
    value = validar_valor_previsto(target, valor)
    if target == "ph":
        valid["cultura"] = valid["label"]
    return modelo.strip(), target, value, json.dumps(valid, ensure_ascii=False, allow_nan=False)


def inserir_previsoes(registros) -> None:
    """Persiste UMA transação; registros são (modelo, target, valor, parametros_json)."""
    records = [_validar_previsao(*record) for record in registros]
    if not records:
        raise ValueError("Nenhuma previsão informada.")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO previsoes (ts, modelo, target, valor_previsto, parametros_entrada)
            VALUES (?, ?, ?, ?, ?)
        """, [(timestamp, *record) for record in records])


def inserir_previsao(modelo: str, target: str, valor: float, parametros: str) -> None:
    inserir_previsoes([(modelo, target, valor, parametros)])


def get_previsoes(limite: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, ts, modelo, target, valor_previsto, parametros_entrada FROM previsoes
            ORDER BY utc_micros(ts) DESC, id DESC LIMIT ?
        """, (_limite(limite),)).fetchall()
    return [dict(r) for r in rows]


def get_total_previsoes() -> int:
    """Conta todo o histórico, independentemente do limite de exibição."""
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM previsoes").fetchone()[0]


def validar_leitura(umidade, temp_c, ldr, ph, n, p, k, bomba_fw, sensor_id=1):
    from src.validation import numero_finito

    values = [numero_finito(value, name, low, high) for value, name, low, high in (
        (umidade, "umidade", 0, 100), (temp_c, "temperatura", -50, 80),
        (ldr, "ldr", 0, 4095), (ph, "ph", 0, 14),
    )]
    for name, value in (("n", n), ("p", p), ("k", k), ("bomba_fw", bomba_fw)):
        if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
            raise ValueError(f"{name} deve ser inteiro 0 ou 1 na leitura simulada.")
        values.append(value)
    if isinstance(sensor_id, bool) or not isinstance(sensor_id, int) or sensor_id <= 0:
        raise ValueError("Sensor inválido.")
    return (sensor_id, *values)


def inserir_leitura_simulada(umidade: float, temp_c: float, ldr: float, ph: float,
                           n: int, p: int, k: int, bomba_fw: int, sensor_id: int = 1) -> None:
    values = validar_leitura(umidade, temp_c, ldr, ph, n, p, k, bomba_fw, sensor_id)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO leituras_sensores
                (sensor_id, ts, umidade, temp_c, ldr, ph, n, p, k, bomba_fw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (values[0], timestamp, *values[1:]))


def media_cultura(cultura: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT AVG(aa.n) as n_med, AVG(aa.p) as p_med,
                   AVG(aa.k) as k_med, AVG(aa.ph) as ph_med
            FROM amostras_agronomicas aa JOIN culturas c ON c.id = aa.cultura_id
            WHERE c.nome = ?
        """, (cultura,)).fetchone()
    return dict(row) if row else None
