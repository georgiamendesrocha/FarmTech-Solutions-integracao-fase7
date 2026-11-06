"""Controle local da FarmTech: menu 1 (iniciar) e 0 (parar).

Mantém compatibilidade com ``--dashboard`` e com as opções da CLI existente.
Nunca encerra processos de outras aplicações nem usa uma porta ocupada.
"""

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent
LOG = ROOT / ".runtime" / "logs" / "dashboard.log"


def _python_fase4() -> Path:
    configured = os.getenv("FARMTECH_FASE4_PYTHON")
    executable = (Path(configured).expanduser() if configured else
                  ROOT / "servicos" / "fase4-regressao" / ".venv-f402" /
                  ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    if not executable.is_absolute() or not executable.is_file():
        raise FileNotFoundError(
            "Python da Fase 4 não encontrado. Configure FARMTECH_FASE4_PYTHON "
            "com o caminho absoluto para o Python 3.11.9 validado."
        )
    return executable


def _environment() -> dict:
    from farmtech_integracao.demo import demo_path
    environment = dict(os.environ, FARMTECH_INTEGRACAO="1", FARMTECH_SIMULACAO="0",
                       PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    environment.setdefault("DB_PATH", str(demo_path()))
    return environment


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
                                       env=_environment(), stdout=arquivo_log,
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
                    processo, _ = _iniciar()
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
        comando = [str(executable), "-X", "utf8", "-I", "-B",
                   str(ROOT / "farmtech_integracao" / "cli.py"), *sys.argv[1:]]
        return subprocess.call(comando, cwd=ROOT, env=_environment())
    except (OSError, ValueError) as exc:
        print(f"Não foi possível executar a FarmTech: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
