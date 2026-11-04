"""Base reconstruída de demonstração: publicação exclusiva, nunca substituição."""

import os
from contextlib import closing
from pathlib import Path
import sqlite3

from farmtech_integracao.contracts import Result
from farmtech_integracao.runtime import PROJECT_ROOT, run_json_worker


def demo_path() -> Path:
    return PROJECT_ROOT / ".runtime" / "demo" / "farmtech-demo.db"


def inspect_database(path: Path) -> Result:
    path = Path(path)
    source = {"phase": "fase4", "kind": "sqlite", "reconstructed": path.resolve() == demo_path().resolve()}
    if not path.is_file():
        return Result("unavailable", "Base ausente. Prepare explicitamente a base reconstruída com python iniciar.py --preparar-demo.", source=source)
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                return Result("error", "Banco com falha de integridade. Preserve o arquivo para diagnóstico.", source=source)
            counts = {}
            for table in ("culturas", "sensores", "leituras_sensores", "amostras_agronomicas", "previsoes"):
                counts[table] = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            marker = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ("integracao_proveniencia",)).fetchone()
            if marker:
                source["reconstructed"] = True
        return Result("ok", "Base reconstruída disponível; não representa histórico real recuperado." if source["reconstructed"] else "Banco existente disponível para consulta.", {"counts": counts}, source)
    except sqlite3.Error:
        return Result("error", "Banco indisponível ou schema incompatível. Nenhuma reconstrução automática foi executada.", source=source)


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
