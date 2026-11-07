"""Base reconstruída de demonstração: publicação exclusiva, nunca substituição."""

import os
from contextlib import closing
from pathlib import Path
import sqlite3

from farmtech_integracao.contracts import Result
from farmtech_integracao.runtime import PROJECT_ROOT, SERVICE_DIRS, run_json_worker


# Colunas consultadas pela dashboard F4. A inspeção continua independente das
# dependências do serviço, para também funcionar no Python usado pelo launcher.
_DASHBOARD_COLUMNS = {
    "culturas": ("id", "nome"),
    "sensores": ("id", "tipo", "unidade", "origem"),
    "leituras_sensores": ("id", "sensor_id", "ts", "umidade", "temp_c", "ldr", "ph", "n", "p", "k", "bomba_fw"),
    "amostras_agronomicas": ("id", "cultura_id", "n", "p", "k", "temperatura", "umidade", "ph", "chuva"),
    "previsoes": ("id", "ts", "modelo", "target", "valor_previsto", "parametros_entrada"),
}


def demo_path() -> Path:
    return PROJECT_ROOT / ".runtime" / "demo" / "farmtech-demo.db"


def inspect_database(path: str | Path) -> Result:
    """Inspeciona sem criar banco; caminhos relativos seguem a semântica da F4."""
    source = {"phase": "fase4", "kind": "sqlite", "reconstructed": False}
    try:
        if isinstance(path, str) and not path.strip():
            raise ValueError("DB_PATH vazia")
        path = Path(path).expanduser()
        path = (path if path.is_absolute() else SERVICE_DIRS["fase4"] / path).resolve()
        source.update(path=str(path), reconstructed=path == demo_path().resolve())
        if not path.is_file():
            return Result("unavailable", "Base ausente. Prepare explicitamente a base reconstruída com python iniciar.py --preparar-demo. Se DB_PATH estiver configurada, confira o caminho ou remova a variável para usar a base padrão.", source=source)
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                return Result("error", "Banco com falha de integridade. Preserve o arquivo para diagnóstico.", source=source)
            counts = {}
            for table, columns in _DASHBOARD_COLUMNS.items():
                connection.execute(f"SELECT {', '.join(columns)} FROM {table} LIMIT 0")
                counts[table] = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            marker = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ("integracao_proveniencia",)).fetchone()
            if marker:
                source["reconstructed"] = True
        return Result("ok", "Base reconstruída disponível; não representa histórico real recuperado." if source["reconstructed"] else "Banco existente disponível para consulta.", {"counts": counts}, source)
    except sqlite3.Error:
        return Result("error", "Banco indisponível ou schema incompatível. Confira DB_PATH e use um banco da Fase 4 compatível. Nenhuma reconstrução automática foi executada.", source=source)
    except (OSError, ValueError, TypeError):
        return Result("invalid", "DB_PATH inválida. Configure um caminho de banco válido ou remova a variável para usar a base padrão.", source=source)


def prepare_demo() -> Result:
    if demo_path().exists():
        return Result("unavailable", "O destino da demonstração já existe e foi preservado. Use --status para inspecioná-lo.", source={"phase": "fase4", "reconstructed": True})
    return run_json_worker("fase4", {"action": "prepare_demo"}, timeout=60)


def configure_dashboard() -> None:
    """Configuração antes dos imports F4; não cria banco nem carrega modelos."""
    if os.getenv("FARMTECH_INTEGRACAO") == "1":
        os.environ["FARMTECH_SIMULACAO"] = "0"
        os.environ.setdefault("DB_PATH", str(demo_path()))
    else:
        os.environ.setdefault("FARMTECH_SIMULACAO", "0")
