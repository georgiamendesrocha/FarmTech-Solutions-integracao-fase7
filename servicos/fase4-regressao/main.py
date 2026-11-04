"""
FarmTech Solutions — ponto de entrada integrado com menu de pipeline.

Ordem do pipeline:
    1. Ingestao CSV -> SQLite
    2. Treinamento ML (Scikit-Learn)
    3. Dashboard Streamlit

Uso:
    python main.py              # menu interativo
    python main.py --pipeline     # executa etapas pendentes + dashboard
    python main.py --ingestao     # apenas etapa 1
    python main.py --treinar      # apenas etapa 2
    python main.py --dashboard    # apenas etapa 3
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sqlite3
import warnings
import sys
from pathlib import Path

from dotenv import load_dotenv
from src.db.database import resolve_db_path, validar_banco

load_dotenv()

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "src" / "ml" / "models"
REQUIRED_MODELS = ("modelo_rainfall.joblib", "modelo_humidity.joblib")

MENU_WIDTH = 52


def db_path() -> str:
    return str(resolve_db_path())


def status_banco() -> bool:
    try:
        validar_banco()
        return True
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        return False


def status_modelos() -> tuple[bool, list[str]]:
    from src.ml.train import carregar_modelo, carregar_metricas
    invalid = []
    for target in ("rainfall", "humidity"):
        try:
            with warnings.catch_warnings(record=True) as notices:
                warnings.simplefilter("always")
                model = carregar_modelo(target)
            if notices:
                print("[AVISO] Artefatos históricos entre versões: uso limitado ao ambiente e às previsões de referência verificados; consulte as ressalvas no README.", file=sys.stderr)
            if model is None:
                invalid.append(f"modelo_{target}.joblib")
        except (OSError, ValueError, RuntimeError):
            invalid.append(f"modelo_{target}.joblib")
    try:
        if not carregar_metricas():
            invalid.append("metricas.json")
    except (OSError, ValueError, RuntimeError):
        invalid.append("metricas.json")
    return not invalid, invalid


def _run_script(relative_path: str, label: str) -> None:
    script = ROOT / relative_path
    print(f"\n[{label}] Executando {relative_path} ...", flush=True)
    subprocess.run([sys.executable, str(script)], check=True, cwd=ROOT)
    print(f"[{label}] Concluido.", flush=True)


def etapa_ingestao(*, force: bool = False) -> None:
    """Etapa 1 — CSVs -> SQLite."""
    if status_banco() and not force:
        resp = input("Banco ja existe. Recriar e recarregar CSVs? [s/N]: ").strip().lower()
        if resp not in ("s", "sim"):
            print("[1/3] Ingestao cancelada.")
            return
    _run_script("scripts/init_db.py", "1/3 Ingestao")


def etapa_treinamento(*, force: bool = False) -> None:
    """Etapa 2 — treino e persistencia dos modelos."""
    if not status_banco():
        raise RuntimeError("Banco ausente ou inválido. Execute a ingestão após verificar os CSVs.")
    if any((MODELS_DIR / name).exists() for name in REQUIRED_MODELS):
        raise RuntimeError("Modelos históricos preservados. Retreinamento requer proposta e autorização específica; use o backup para recuperar artefatos inválidos.")
    ok, _ = status_modelos()
    if ok and not force:
        resp = input("Modelos ja existem. Retreinar? [s/N]: ").strip().lower()
        if resp not in ("s", "sim"):
            print("[2/3] Treinamento cancelado.")
            return
    _run_script("src/ml/train.py", "2/3 ML")


def ensure_database() -> None:
    """Cria banco apenas se ausente (modo pipeline automatico)."""
    if status_banco():
        return
    if Path(db_path()).exists():
        raise RuntimeError("Banco existente inválido. Preserve uma cópia e execute a ingestão explicitamente.")
    _run_script("scripts/init_db.py", "1/3 Ingestao")


def ensure_models() -> None:
    """Treina modelos apenas se ausentes (modo pipeline automatico)."""
    ok, invalid = status_modelos()
    if ok:
        return
    raise RuntimeError("Artefatos ausentes, alterados ou incompatíveis. Recupere os modelos históricos e métricas do backup verificado.")


def etapa_dashboard(*, permitir_rede: bool = False) -> None:
    """Etapa 3 — dashboard Streamlit."""
    if not status_banco():
        raise RuntimeError("Banco ausente ou inválido. Execute a etapa de ingestão antes de abrir o dashboard.")
    ok, missing = status_modelos()
    if not ok:
        raise RuntimeError("Modelos ausentes, alterados ou incompatíveis. Recupere os artefatos do backup verificado.")
    run_streamlit(permitir_rede=permitir_rede)


def comando_streamlit(*, permitir_rede: bool = False) -> list[str]:
    """PORT define somente a porta; exposição de rede exige opção explícita."""
    port = os.environ.get("PORT", "8501")
    if not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("PORT deve ser um inteiro entre 1 e 65535.")
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "src/frontend/app.py",
        "--server.port",
        port,
        "--server.address",
        "0.0.0.0" if permitir_rede else "127.0.0.1",
        "--server.headless",
        "true",
        "--server.enableCORS",
        "true",
        "--server.enableXsrfProtection",
        "true",
    ]

def run_streamlit(*, permitir_rede: bool = False) -> None:
    """Mantém o processo filho sob controle, inclusive no encerramento."""
    from importlib.metadata import version, PackageNotFoundError
    try:
        runtime_version = version("streamlit")
    except PackageNotFoundError as error:
        raise RuntimeError("Streamlit não instalado. Instale as dependências declaradas.") from error
    if tuple(int(x) for x in runtime_version.split(".")[:2]) < (1, 54):
        raise RuntimeError("Streamlit incompatível com os requisitos de segurança. Instale as dependências declaradas no ambiente isolado.")
    cmd = comando_streamlit(permitir_rede=permitir_rede)
    print(f"\n[3/3 Dashboard] http://localhost:{os.environ.get('PORT', '8501')}", flush=True)
    print("[3/3 Dashboard] Pressione Ctrl+C para encerrar.\n", flush=True)
    proc = subprocess.Popen(cmd, cwd=ROOT)
    
    try:
        result = proc.wait()
        if result:
            raise RuntimeError("O dashboard encerrou com erro; consulte o diagnóstico local.")
    except KeyboardInterrupt:
        print("\n[3/3 Dashboard] Encerrando Streamlit...", flush=True)
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def pipeline_completo(*, permitir_rede: bool = False) -> None:
    """Executa 1 -> 2 -> 3 (somente o que estiver pendente, depois abre o dashboard)."""
    ensure_database()
    ensure_models()
    etapa_dashboard(permitir_rede=permitir_rede)


def _status_label(ok: bool) -> str:
    return "OK" if ok else "PENDENTE"


def exibir_menu() -> None:
    banco_ok = status_banco()
    modelos_ok, _ = status_modelos()

    print()
    print("=" * MENU_WIDTH)
    print("  FarmTech Solutions — Menu do Pipeline")
    print("=" * MENU_WIDTH)
    print()
    print("  Status atual:")
    print(f"    [1] Banco SQLite ........ {_status_label(banco_ok)}")
    print(f"    [2] Modelos ML .......... {_status_label(modelos_ok)}")
    print()
    print("  Pipeline (ordem do projeto):")
    print("    1 - Ingestao de dados (CSV -> SQLite)")
    print("    2 - Treinamento ML (Scikit-Learn)")
    print("    3 - Dashboard Streamlit")
    print("    4 - Pipeline completo (1 -> 2 -> 3)")
    print("    0 - Sair")
    print()


def _executar_opcao_menu(opcao: str) -> None:
    if opcao == "1":
        etapa_ingestao()
    elif opcao == "2":
        etapa_treinamento()
    elif opcao == "3":
        etapa_dashboard()
    elif opcao == "4":
        pipeline_completo()


def _pausar_menu() -> None:
    if sys.stdin.isatty():
        input("\nPressione Enter para voltar ao menu...")


def menu_interativo() -> None:
    """Loop do menu ate o usuario sair ou encerrar o dashboard."""
    os.chdir(ROOT)

    while True:
        exibir_menu()
        try:
            opcao = input("Escolha uma opcao: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            return

        if opcao == "0":
            print("Ate logo.")
            return
        if opcao not in ("1", "2", "3", "4"):
            print("Opcao invalida. Escolha 0, 1, 2, 3 ou 4.")
            _pausar_menu()
            continue

        try:
            _executar_opcao_menu(opcao)
        except subprocess.CalledProcessError as e:
            print(
                f"\n[ERRO] A etapa falhou com codigo de retorno {e.returncode}."
            )
            print("Verifique a mensagem acima e tente novamente pelo menu.")
            _pausar_menu()
        except Exception as e:
            print("\n[ERRO] Operação não concluída. Verifique o banco, os arquivos de entrada e o ambiente declarado.")
            print("O menu sera exibido novamente.")
            _pausar_menu()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FarmTech Solutions — launcher do pipeline agricola"
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="executa etapas pendentes e abre o dashboard (sem menu)",
    )
    parser.add_argument(
        "--ingestao",
        action="store_true",
        help="apenas etapa 1: CSV -> SQLite",
    )
    parser.add_argument(
        "--treinar",
        action="store_true",
        help="apenas etapa 2: treinamento ML",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="apenas etapa 3: dashboard Streamlit",
    )
    parser.add_argument("--permitir-rede", action="store_true", help="permite escuta em rede explicitamente; requer proteção de acesso externa")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    os.chdir(ROOT)
    args = parse_args(argv)

    if args.permitir_rede and not (args.pipeline or args.dashboard):
        print("[ERRO] --permitir-rede exige --dashboard ou --pipeline.")
        return 2
    try:
        if args.pipeline:
            pipeline_completo(permitir_rede=args.permitir_rede)
        elif args.ingestao:
            etapa_ingestao(force=True)
        elif args.treinar:
            etapa_treinamento(force=True)
        elif args.dashboard:
            etapa_dashboard(permitir_rede=args.permitir_rede)
        else:
            menu_interativo()
        return 0
    except (RuntimeError, ValueError, OSError, sqlite3.Error, subprocess.CalledProcessError):
        print("[ERRO] Operação não concluída. Confira banco, CSVs, integridade dos modelos e ambiente conforme o README.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
