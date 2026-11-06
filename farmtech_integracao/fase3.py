"""Consultas limitadas da Fase 3 em processo isolado, sem iniciar a API histórica."""

import importlib.util
import os

from .contracts import Result
from .runtime import SERVICE_DIRS, run_json_worker

MAX_RECORDS = 1000


def availability() -> Result:
    """Informa presença de arquivos/configuração, sem carregar segredos ou conectar."""
    csv_available = (SERVICE_DIRS["fase3"] / "src" / "dados" / "historico_irrigacao.csv").is_file()
    configured = all(os.environ.get(name) for name in ("ORACLE_USER", "ORACLE_PASS", "ORACLE_DSN"))
    driver_available = importlib.util.find_spec("oracledb") is not None
    return Result(
        "ok" if csv_available else "unavailable",
        "Consulta CSV disponível; Oracle depende de configuração e acesso ao banco."
        if csv_available else "CSV preservado indisponível; verifique os arquivos da Fase 3.",
        data={"csv_available": csv_available, "oracle_configured": configured,
              "oracle_dependency_available": driver_available},
        source={"phase": "fase3"},
    )


def query_sensors(source: str, *, limit: int = 500, python: str | None = None,
                  timeout: float = 30) -> Result:
    """Consulta Oracle ou o CSV preservado; não aceita SQL nem caminhos do usuário."""
    if source not in ("oracle", "csv"):
        return Result("invalid", "Selecione a origem Oracle ou CSV preservado.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RECORDS:
        return Result("invalid", f"O limite deve ser um inteiro entre 1 e {MAX_RECORDS}.")
    return run_json_worker(
        "fase3", {"operation": "query_sensors", "source": source, "limit": limit},
        timeout=timeout, python=python,
    )


def query_sensors_authenticated(rm: str, password: str, dsn: str, *,
                                limit: int = 200, timeout: float = 30) -> Result:
    """Consulta Oracle com credenciais transitórias da sessão; nunca salva os valores."""
    import re

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RECORDS:
        return Result("invalid", f"O limite deve ser um inteiro entre 1 e {MAX_RECORDS}.")
    if not isinstance(rm, str) or not re.fullmatch(r"RM[0-9]{4,12}", rm.strip().upper()):
        return Result("invalid", "Informe sua RM FIAP no formato RM seguido de números.")
    if (not isinstance(password, str) or not 1 <= len(password) <= 256
            or any(ord(c) < 32 or ord(c) == 127 for c in password)):
        return Result("invalid", "Informe uma senha Oracle válida.")
    if (not isinstance(dsn, str) or not 1 <= len(dsn.strip()) <= 1024
            or any(ord(c) < 32 or ord(c) == 127 for c in dsn)):
        return Result("invalid", "Informe um servidor/serviço Oracle válido.")
    return run_json_worker(
        "fase3",
        {"operation": "query_sensors", "source": "oracle", "limit": limit,
         "auth": {"user": rm.strip().upper(), "password": password, "dsn": dsn.strip()}},
        timeout=timeout,
    )
