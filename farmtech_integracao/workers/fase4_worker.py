"""Prepara apenas uma base nova em staging; não carrega modelos."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from farmtech_integracao.contracts import Result
from farmtech_integracao.demo import demo_path
from farmtech_integracao.runtime import SERVICE_DIRS


def publish_new(stage: Path, destination: Path) -> None:
    """Hard link no mesmo volume: falha se o destino existir, inclusive em corrida."""
    os.link(stage, destination)


def prepare(destination=None) -> Result:
    # O protocolo público nunca aceita destino; o argumento existe para fixtures isoladas.
    destination = demo_path() if destination is None else Path(destination)
    if destination.exists():
        return Result("unavailable", "A base de demonstração já existe e foi preservada.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    service = SERVICE_DIRS["fase4"]
    spec = importlib.util.spec_from_file_location("_farmtech_demo_init", service / "scripts" / "init_db.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="staging-demo-", dir=destination.parent) as directory:
        stage = Path(directory) / "reconstruida.db"
        result = module.inicializar_banco(db_path=stage)
        sources = {}
        for name in ("historico_irrigacao.csv", "Atividade_Cap10_produtos_agricolas.csv"):
            path = service / "src" / "dados" / name
            sources[str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
        with closing(sqlite3.connect(stage)) as connection, connection:
            connection.execute("CREATE TABLE integracao_proveniencia (id INTEGER PRIMARY KEY, descricao TEXT NOT NULL, criado_utc TEXT NOT NULL, fontes_json TEXT NOT NULL)")
            connection.execute("INSERT INTO integracao_proveniencia VALUES (?, ?, ?, ?)",
                               (1, "Base reconstruída de demonstração; dados acadêmicos e leituras registradas/simuladas. Não é histórico real recuperado.",
                                datetime.now(timezone.utc).isoformat(), json.dumps(sources, ensure_ascii=False)))
        publish_new(stage, destination)
    return Result("ok", "Base reconstruída criada sem substituir bancos existentes.",
                  {"counts": result["contagens"]}, {"phase": "fase4", "kind": "sqlite", "reconstructed": True, "sources_sha256": sources})


def main():
    try:
        payload = json.load(sys.stdin)
        result = prepare() if payload == {"action": "prepare_demo"} else Result("invalid", "Operação não permitida.")
    except FileExistsError:
        result = Result("unavailable", "O destino passou a existir durante a preparação e foi preservado.")
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        result = Result("error", "Preparação não concluída. Confira os CSVs e permissões; nenhum banco existente foi substituído.")
    print(json.dumps(result.as_dict(), ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
