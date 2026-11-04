"""Entrada integrada: seleciona o ambiente validado da F4 sem instalar pacotes."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main() -> int:
    configured = os.getenv("FARMTECH_FASE4_PYTHON")
    executable = Path(configured).expanduser() if configured else ROOT / "servicos" / "fase4-regressao" / ".venv-f402" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_absolute() or not executable.is_file():
        print("Python da Fase 4 não encontrado. Configure FARMTECH_FASE4_PYTHON com um caminho absoluto para Python 3.11.9.", file=sys.stderr)
        return 2
    arguments = sys.argv[1:]
    env = dict(os.environ, FARMTECH_INTEGRACAO="1", FARMTECH_SIMULACAO="0",
               PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    try:
        from farmtech_integracao.runtime import _stop_tree
        options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
                   if os.name == "nt" else {"start_new_session": True})
        process = subprocess.Popen([str(executable), "-X", "utf8", "-I", "-B", str(ROOT / "farmtech_integracao" / "cli.py"), *arguments], cwd=ROOT, env=env,
                                   stdout=sys.stdout, stderr=sys.stderr, **options)
        try:
            return process.wait()
        except KeyboardInterrupt:
            _stop_tree(process)
            return 130
    except KeyboardInterrupt:
        return 130
    except OSError:
        print("Não foi possível iniciar o Python configurado da Fase 4.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
