"""Worker de consulta da Fase 3. Nenhum serviço histórico é importado."""

from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from farmtech_integracao.contracts import Result

SERVICE_ROOT = PROJECT_ROOT / "servicos" / "fase3-dashboard"
CSV_PATH = SERVICE_ROOT / "src" / "dados" / "historico_irrigacao.csv"
NORMALIZER_PATH = SERVICE_ROOT / "src" / "utils" / "sensores.py"
MAX_RECORDS = 1000
MAX_CSV_BYTES = 20 * 1024 * 1024
MAX_REQUEST_BYTES = 4096
MAX_RESPONSE_BYTES = 512 * 1024
ORACLE_SQL = (
    "SELECT INSTANTE, TS_ISO, UMIDADE, TEMP_C, PH_CORR, N, P, K, BOMBA_FW "
    "FROM SENSORES_FARMTECH ORDER BY ID DESC FETCH FIRST :limit ROWS ONLY"
)
UNITS = {"instante": "ISO 8601, fuso conforme origem", "umidade": "%",
         "temp_c": "°C", "ph_corr": "pH", "n": "0/1", "p": "0/1",
         "k": "0/1", "bomba_fw": "0/1"}


def _normalizer():
    spec = importlib.util.spec_from_file_location("farmtech_fase3_sensores", NORMALIZER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("Normalizador indisponível")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._padronizar_df


def _read_csv(limit: int):
    import pandas as pd

    if CSV_PATH.stat().st_size > MAX_CSV_BYTES:
        raise ValueError("CSV excede o limite")
    return pd.read_csv(CSV_PATH, encoding="utf-8", nrows=limit)


def _read_oracle(limit: int):
    import oracledb
    import pandas as pd

    # Não carregar .env: a configuração deve ser fornecida ao processo pelo ambiente.
    with oracledb.connect(user=os.environ["ORACLE_USER"],
                          password=os.environ["ORACLE_PASS"],
                          dsn=os.environ["ORACLE_DSN"]) as connection:
        connection.call_timeout = 10000
        with connection.cursor() as cursor:
            cursor.arraysize = min(limit, 100)
            cursor.execute(ORACLE_SQL, {"limit": limit})
            columns = [description[0].lower() for description in cursor.description]
            return pd.DataFrame(cursor.fetchmany(limit), columns=columns)


def _records(frame, limit: int) -> list[dict]:
    # A normalização é a mesma da página histórica, extraída para um helper puro.
    frame = _normalizer()(frame)
    records = []
    for _, row in frame.head(limit).iterrows():
        values = {key: float(row[key]) for key in ("umidade", "temp_c", "ph_corr")}
        if not all(math.isfinite(value) for value in values.values()):
            continue
        values.update({key: int(row[key]) for key in ("n", "p", "k", "bomba_fw")})
        records.append({"instante": row["instante"].isoformat(), **values,
                        "irrigacao": str(row["irrigacao"])})
    return records


def handle(payload: dict) -> Result:
    if not isinstance(payload, dict) or payload.get("operation") != "query_sensors":
        return Result("invalid", "Operação de consulta inválida.")
    if set(payload) - {"operation", "source", "limit"}:
        return Result("invalid", "A consulta não aceita SQL, caminhos ou opções adicionais.")
    origin = payload.get("source")
    limit = payload.get("limit", 500)
    if origin not in ("csv", "oracle"):
        return Result("invalid", "Origem de dados inválida.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RECORDS:
        return Result("invalid", "Limite de registros inválido.")
    source = {"phase": "fase3", "kind": origin,
              "resource": "SENSORES_FARMTECH" if origin == "oracle" else "historico_irrigacao.csv"}
    if origin == "oracle" and not all(os.environ.get(name) for name in
                                      ("ORACLE_USER", "ORACLE_PASS", "ORACLE_DSN")):
        return Result("unavailable", "Oracle não configurado. Defina ORACLE_USER, ORACLE_PASS e ORACLE_DSN no ambiente.", source=source)
    try:
        frame = _read_oracle(limit) if origin == "oracle" else _read_csv(limit)
        rows = _records(frame, limit)
    except ImportError:
        message = ("Driver Oracle (oracledb) indisponível no ambiente Python selecionado. O CSV preservado continua disponível."
                   if origin == "oracle" else "Dependências de consulta CSV indisponíveis no ambiente Python selecionado.")
        return Result("unavailable", message, source=source)
    except Exception:
        message = ("Oracle indisponível. Verifique a rede, as permissões de leitura e a configuração do ambiente."
                   if origin == "oracle" else "CSV preservado indisponível ou inválido. Verifique o arquivo original da Fase 3.")
        return Result("unavailable", message, source=source)
    ordering = "últimos registros por ID" if origin == "oracle" else "primeiras linhas do CSV preservado"
    data = {"rows": rows, "count": len(rows), "requested_limit": limit, "units": UNITS,
            "selection": ordering, "timestamp_timezone": "conforme origem; não inferido"}
    message = f"Consulta concluída: {len(rows)} registros válidos." if rows else "Consulta concluída sem registros válidos."
    return Result("ok", message, data=data, source=source)


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            result = Result("invalid", "Solicitação excede o tamanho permitido.")
        else:
            result = handle(json.loads(raw.decode("utf-8")))
        encoded = json.dumps(result.as_dict(), ensure_ascii=False, allow_nan=False)
        if len(encoded.encode("utf-8")) > MAX_RESPONSE_BYTES:
            encoded = json.dumps(Result("error", "Resposta excede o tamanho permitido.").as_dict())
    except Exception:
        encoded = json.dumps(Result("invalid", "Solicitação de consulta inválida.").as_dict())
    sys.stdout.buffer.write(encoded.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
