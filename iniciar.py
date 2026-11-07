"""Controle local da FarmTech: menu 1 (iniciar) e 0 (parar).

Mantém compatibilidade com ``--dashboard`` e com as opções da CLI existente.
Nunca encerra processos de outras aplicações nem usa uma porta ocupada.
"""

import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent
LOG = ROOT / ".runtime" / "logs" / "dashboard.log"


def _instrucoes_ambiente() -> str:
    relative = "servicos/fase4-regressao/.venv-f402"
    if os.name == "nt":
        create = f"py -3.11 -m venv {relative}"
        python = f"& ./{relative}/Scripts/python.exe"
        version = "py -3.11 --version"
    else:
        create = f"python3.11 -m venv {relative}"
        python = f"./{relative}/bin/python"
        version = "python3.11 --version"
    return (
        "Na raiz do projeto, confira Python 3.11.9 e crie o ambiente local "
        "somente se a pasta .venv-f402 ainda não existir:\n"
        f"{version}\n{create}\n"
        "Instale as dependências explicitamente, sem substituir um ambiente existente:\n"
        f"{python} -m pip install -r requirements.txt\n{python} -m pip check\n"
        "O ambiente local será localizado automaticamente. Para outro ambiente, "
        "configure FARMTECH_FASE4_PYTHON com seu caminho absoluto."
    )


def _comando_python(executable: Path) -> str:
    if os.name == "nt":
        return "& '" + str(executable).replace("'", "''") + "'"
    return shlex.quote(str(executable))


def _python_fase4() -> Path:
    configured = os.getenv("FARMTECH_FASE4_PYTHON")
    executable = (Path(configured).expanduser() if configured else
                  ROOT / "servicos" / "fase4-regressao" / ".venv-f402" /
                  ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    if not executable.is_absolute() or not executable.is_file():
        reset = ("Remove-Item Env:FARMTECH_FASE4_PYTHON -ErrorAction SilentlyContinue"
                 if os.name == "nt" else "unset FARMTECH_FASE4_PYTHON")
        detail = (f"FARMTECH_FASE4_PYTHON aponta para um executável inválido: {executable}. "
                  "Corrija essa variável ou volte ao padrão local nesta sessão:\n"
                  f"{reset}\n" if configured else
                  f"Python da Fase 4 não encontrado no ambiente local: {executable}.\n")
        raise FileNotFoundError(
            detail + _instrucoes_ambiente()
        )
    return executable


def _validar_python(executable: Path) -> None:
    """Confere versão e presença das dependências, sem instalar ou carregar modelos."""
    probe = (
        "import importlib.util,json,sys; "
        "modules=('streamlit','plotly','pandas','numpy','sklearn','joblib',"
        "'apscheduler','dotenv','PIL'); "
        "print(json.dumps({'version':list(sys.version_info[:3]),"
        "'missing':[m for m in modules if importlib.util.find_spec(m) is None]}))"
    )
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        result = subprocess.run([str(executable), "-X", "utf8", "-I", "-B", "-c", probe],
                                capture_output=True, text=True, encoding="utf-8", timeout=15,
                                check=True, **options)
        info = json.loads(result.stdout)
        version = tuple(info["version"])
        missing = info["missing"]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(
            f"Não foi possível validar o Python da Fase 4: {executable}.\n"
            "Confira o executável e seu ambiente.\n" + _instrucoes_ambiente()
        ) from exc
    if version != (3, 11, 9):
        raise ValueError(
            f"Python da Fase 4 incompatível: {'.'.join(map(str, version))}; esperado 3.11.9.\n"
            "Confira FARMTECH_FASE4_PYTHON e preserve os ambientes existentes.\n" +
            _instrucoes_ambiente()
        )
    if missing:
        command = _comando_python(executable)
        raise ValueError(
            "Dependências ausentes no Python da Fase 4: " + ", ".join(missing) + ".\n"
            "Na raiz do projeto, execute explicitamente:\n"
            f"{command} -m pip install -r requirements.txt\n{command} -m pip check\n"
            "Nenhuma dependência foi instalada automaticamente."
        )


def _environment() -> dict:
    from farmtech_integracao.demo import demo_path
    environment = dict(os.environ, FARMTECH_INTEGRACAO="1", FARMTECH_SIMULACAO="0",
                       PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    environment.setdefault("DB_PATH", str(demo_path()))
    return environment


def _verificar_banco(environment: dict) -> None:
    from farmtech_integracao.demo import inspect_database
    result = inspect_database(environment["DB_PATH"])
    if not result.ok:
        reset = ("Remove-Item Env:DB_PATH -ErrorAction SilentlyContinue"
                 if os.name == "nt" else "unset DB_PATH")
        raise ValueError(
            f"Banco da dashboard indisponível: {result.message}\n"
            f"Destino: {result.source.get('path', environment['DB_PATH'])}\n"
            "Confira a configuração com: python iniciar.py --status\n"
            "Se a base demonstrativa ainda não existe, prepare-a explicitamente:\n"
            "python iniciar.py --preparar-demo\n"
            "Esse comando cria somente .runtime/demo/farmtech-demo.db e nunca sobrescreve. "
            "Preserve bancos existentes para diagnóstico. Se DB_PATH estiver configurada, "
            "corrija seu destino ou remova a variável para usar a demonstração:\n"
            f"{reset}"
        )


def _porta_livre(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", porta))
            return True
        except OSError:
            return False


def _escolher_porta(solicitada=None) -> int:
    portas = [solicitada] if solicitada is not None else range(8501, 8511)
    for porta in portas:
        if not 1 <= porta <= 65535:
            raise ValueError("Porta inválida.")
        if _porta_livre(porta):
            return porta
    if solicitada is not None:
        raise OSError(f"A porta {solicitada} está ocupada. O servidor anterior não será reutilizado.")
    raise OSError("As portas 8501 a 8510 estão ocupadas. Encerre servidores antigos primeiro.")


def _linhas_log():
    try:
        return "\n".join(LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-24:])
    except OSError:
        return "Log indisponível."


def _iniciar(porta=None, *, abrir_navegador=True):
    executable = _python_fase4()
    _validar_python(executable)
    environment = _environment()
    _verificar_banco(environment)
    porta = _escolher_porta(porta)
    endereco = f"http://127.0.0.1:{porta}"
    alvo = ROOT / "servicos" / "fase4-regressao" / "src" / "frontend" / "app.py"
    comando = [str(executable), "-B", "-m", "streamlit", "run", str(alvo),
               "--server.address", "127.0.0.1", "--server.port", str(porta),
               "--server.headless", "true", "--server.enableCORS", "true",
               "--server.enableXsrfProtection", "true", "--browser.gatherUsageStats", "false"]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    opcoes = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
              if os.name == "nt" else {"start_new_session": True})
    processo = None
    try:
        with LOG.open("w", encoding="utf-8") as arquivo_log:
            processo = subprocess.Popen(comando, cwd=ROOT / "servicos" / "fase4-regressao",
                                       env=environment, stdout=arquivo_log,
                                       stderr=subprocess.STDOUT, **opcoes)
        # Confirma a saúde da instância recém-criada, não apenas a existência de uma aba antiga.
        for _ in range(160):
            if processo.poll() is not None:
                print("O Streamlit encerrou antes de iniciar. Últimas mensagens:")
                print(_linhas_log())
                return None, None
            pronto = False
            try:
                with urlopen(endereco + "/_stcore/health", timeout=0.25) as resposta:
                    pronto = resposta.status == 200
            except (OSError, URLError, TimeoutError):
                pass
            if pronto:
                print(f"Dashboard ativo: {endereco} (PID {processo.pid})")
                print("Para encerrar, escolha 0 no menu ou use Ctrl+C.")
                if abrir_navegador:
                    try:
                        if not webbrowser.open_new_tab(endereco):
                            print("Não foi possível abrir o navegador. Acesse o endereço acima.")
                    except webbrowser.Error:
                        print("Não foi possível abrir o navegador. Acesse o endereço acima.")
                return processo, endereco
            time.sleep(0.125)
        _parar(processo)
        print("O servidor não ficou pronto. Últimas mensagens:")
        print(_linhas_log())
        return None, None
    except BaseException:
        if processo is not None:
            _parar(processo)
        raise


def _parar(processo):
    if processo is None:
        print("Nenhum servidor iniciado por este controlador.")
        return
    if processo.poll() is None:
        from farmtech_integracao.runtime import _stop_tree
        _stop_tree(processo)
    print("Dashboard encerrado. O endereço desta instância não está mais disponível.")


def _menu() -> int:
    processo = None
    try:
        while True:
            if processo is not None and processo.poll() is not None:
                print("O dashboard foi encerrado inesperadamente. Consulte " + str(LOG))
                processo = None
            print("\nFarmTech Solutions | 1 - Iniciar | 0 - Parar | S - Sair")
            opcao = input("Escolha: ").strip().lower()
            if opcao == "1":
                if processo is not None:
                    print("Dashboard já iniciado por este menu.")
                else:
                    try:
                        processo, _ = _iniciar()
                    except (OSError, ValueError) as exc:
                        print(f"Não foi possível iniciar a dashboard: {exc}", file=sys.stderr)
            elif opcao == "0":
                _parar(processo)
                processo = None
            elif opcao in ("s", "sair"):
                break
            else:
                print("Opção inválida: escolha 1, 0 ou S.")
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrando o controlador...")
    finally:
        if processo is not None:
            _parar(processo)
    return 0


def _dashboard_direto(argv) -> int:
    parser = argparse.ArgumentParser(description="Inicia o dashboard e aguarda Ctrl+C.")
    parser.add_argument("--dashboard", action="store_true", required=True)
    parser.add_argument("--port", type=int)
    opcoes = parser.parse_args(argv)
    processo, _ = _iniciar(opcoes.port)
    if processo is None:
        return 1
    try:
        return processo.wait()
    except KeyboardInterrupt:
        _parar(processo)
        return 0
    finally:
        if processo.poll() is None:
            _parar(processo)


def main() -> int:
    try:
        if len(sys.argv) == 1:
            return _menu()
        if "--dashboard" in sys.argv[1:]:
            return _dashboard_direto(sys.argv[1:])
        # As ações acadêmicas não relacionadas ao servidor continuam na CLI validada.
        executable = _python_fase4()
        _validar_python(executable)
        comando = [str(executable), "-X", "utf8", "-I", "-B",
                   str(ROOT / "farmtech_integracao" / "cli.py"), *sys.argv[1:]]
        return subprocess.call(comando, cwd=ROOT, env=_environment())
    except (OSError, ValueError) as exc:
        print(f"Não foi possível executar a FarmTech: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
