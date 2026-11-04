# -*- coding: utf-8 -*-
"""
Arranque do projeto: API FastAPI (uvicorn) e/ou dashboard Streamlit.

Na raiz do repositorio, com .env e ambiente virtual ativos:
    python run.py              # API + dashboard (recomendado)
    python run.py --api-only   # apenas FastAPI
    python run.py --dashboard-only   # apenas Streamlit

Opcoes: ``python run.py --help``.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    root_str = str(ROOT)
    existing = env.get("PYTHONPATH", "")
    if root_str not in existing.split(os.pathsep):
        env["PYTHONPATH"] = root_str if not existing else root_str + os.pathsep + existing
    return env


def _terminate_all(procs: list[subprocess.Popen], *, label: str) -> None:
    for p in procs:
        if p.poll() is None:
            p.terminate()
    for p in procs:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=5)
    if label:
        print(label, file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inicia API FastAPI e/ou dashboard Streamlit.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--api-only",
        action="store_true",
        help="Inicia apenas a API (uvicorn).",
    )
    mode.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Inicia apenas o dashboard Streamlit.",
    )
    parser.add_argument("--api-host", default="127.0.0.1", help="Host uvicorn (padrao 127.0.0.1)")
    parser.add_argument("--api-port", type=int, default=8000, help="Porta API (padrao 8000)")
    parser.add_argument("--streamlit-port", type=int, default=8501, help="Porta Streamlit (padrao 8501)")
    parser.add_argument(
        "--api-reload",
        action="store_true",
        help="API com --reload (apenas desenvolvimento).",
    )
    args = parser.parse_args()

    env = _child_env()
    popen_kw: dict = {"cwd": str(ROOT), "env": env}

    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api.main:app",
        "--host",
        args.api_host,
        "--port",
        str(args.api_port),
    ]
    if args.api_reload:
        api_cmd.append("--reload")

    st_app = ROOT / "src" / "frontend" / "app.py"
    if not st_app.is_file():
        print(f"Ficheiro em falta: {st_app}", file=sys.stderr)
        return 1

    st_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(st_app),
        "--server.port",
        str(args.streamlit_port),
        "--server.address",
        "127.0.0.1",
    ]

    procs: list[subprocess.Popen] = []

    def _shutdown_from_signal(_sig=None, _frame=None) -> None:
        _terminate_all(procs, label="Servicos encerrados.")
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _shutdown_from_signal)
        signal.signal(signal.SIGTERM, _shutdown_from_signal)
    except ValueError:
        pass

    start_api = not args.dashboard_only
    start_dashboard = not args.api_only

    if start_api and start_dashboard:
        print("A iniciar API (FastAPI) e painel Streamlit...")
        print(f"  - API Swagger: http://{args.api_host}:{args.api_port}/docs")
        print(f"  - Dashboard:   http://127.0.0.1:{args.streamlit_port}")
        print("  - Ctrl+C encerra ambos.\n")
    elif start_api:
        print("A iniciar apenas a API (FastAPI)...")
        print(f"  - API Swagger: http://{args.api_host}:{args.api_port}/docs")
        print("  - Ctrl+C encerra o servico.\n")
    else:
        print("A iniciar apenas o painel Streamlit...")
        print(f"  - Dashboard: http://127.0.0.1:{args.streamlit_port}")
        print("  - Ctrl+C encerra o servico.\n")

    try:
        if start_api:
            api_p = subprocess.Popen(api_cmd, **popen_kw)
            procs.append(api_p)
            if start_dashboard:
                time.sleep(1.25)
                if api_p.poll() is not None:
                    rc = api_p.returncode if api_p.returncode is not None else 1
                    print(
                        f"A API terminou antes do Streamlit (codigo {rc}). "
                        "Verifique portas, .env e dependencias.",
                        file=sys.stderr,
                    )
                    procs.pop()
                    return int(rc)

        if start_dashboard:
            procs.append(subprocess.Popen(st_cmd, **popen_kw))

        while True:
            for p in procs:
                code = p.poll()
                if code is not None:
                    _terminate_all(
                        procs,
                        label=f"Um processo terminou (codigo {code}). Outros encerrados.",
                    )
                    return int(code != 0)
            time.sleep(0.35)
    except KeyboardInterrupt:
        _terminate_all(procs, label="Interrompido (Ctrl+C). Servicos encerrados.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
