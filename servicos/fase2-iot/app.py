import os
import socket
import threading
import time
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Criar diretórios necessários
def ensure_directories():
    """Garante que os diretórios necessários existem"""
    directories = [
        ROOT / "dados",
        ROOT / "dados" / "plots",
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Garantir que os diretórios existem quando o app inicia
ensure_directories()

SERIAL_CAPTURE_CMD = [
    sys.executable,
    "-u",
    str(ROOT / "scripts" / "serial_grava_csv.py"),
    "--port",
    "rfc2217://127.0.0.1:4000",
    "--baud",
    "115200",
]

RSCRIPT_CMD = ["Rscript", str(ROOT / "app.r")]


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_rfc2217(host: str, port: int) -> bool:
    print(f"Verificando porta {host}:{port}...")
    for tentativa in range(1, 13):
        if is_port_open(host, port):
            print("Porta RFC2217 disponível.")
            return True
        print("Porta ainda não disponível. Aguardando 1 segundo...")
        time.sleep(1)
    return False


def is_enter_pressed() -> bool:
    if sys.platform.startswith("win"):
        try:
            import msvcrt
        except ImportError:
            return False
        pressed = False
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                pressed = True
            # consume all pending keys so they don't leak into next input prompt
        return pressed

    try:
        import select
    except ImportError:
        return False

    if select.select([sys.stdin], [], [], 0)[0]:
        try:
            line = sys.stdin.readline()
        except Exception:
            return False
        return True if line is not None else False
    return False


def run_serial_capture() -> None:
    proc = subprocess.Popen(
        SERIAL_CAPTURE_CMD,
        cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    stop_event = threading.Event()

    def watch_output() -> None:
        assert proc.stdout is not None
        try:
            for raw_line in proc.stdout:
                print(raw_line.rstrip())
        finally:
            stop_event.set()

    output_thread = threading.Thread(target=watch_output, daemon=True)
    output_thread.start()

    interrupted = False
    try:
        while proc.poll() is None and not stop_event.is_set():
            if is_enter_pressed():
                print("\nENTER detectado. Encerrando a captura serial e retornando ao menu...\n")
                interrupted = True
                stop_event.set()
                break
            # O leitor PySerial detecta a desconexão. Sondagens TCP paralelas
            # podem disputar a conexão RFC2217 usada pela captura.
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nUsuário interrompeu a captura serial. Encerrando processo...\n")
        interrupted = True
        stop_event.set()
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        else:
            proc.wait()
        output_thread.join(timeout=1)
        if proc.stdout is not None:
            proc.stdout.close()
    if proc.returncode and not interrupted:
        print(f"Captura serial encerrada com código {proc.returncode}.")


def run_weather_forecast() -> None:
    script_file = ROOT / "scripts" / "weather_forecast.py"
    if not script_file.exists():
        print("Erro: scripts/weather_forecast.py não encontrado.")
        return

    city = input("Digite a cidade para previsão (ex: São Paulo,BR) [padrão: São Paulo,BR]: ").strip()
    if not city:
        city = "São Paulo,BR"

    cmd = [sys.executable, str(script_file), "--city", city]
    try:
        result = subprocess.run(cmd, cwd=ROOT, check=False)
        if result.returncode:
            print(f"Consulta de previsão encerrada com código {result.returncode}.")
    except KeyboardInterrupt:
        print("\nConsulta de previsão interrompida pelo usuário.")
    except Exception as exc:
        print(f"Erro ao executar o script de previsão do tempo: {exc}")


def run_wokwi_simulation() -> None:
    serial_script = ROOT / "scripts" / "serial_grava_csv.py"
    if not serial_script.is_file():
        print(f"Erro: script de captura serial não encontrado: {serial_script}")
        return

    diagram_file = ROOT / "diagram.json"
    if not diagram_file.exists():
        print("Erro: arquivo diagram.json não encontrado na raiz do projeto.")
        return

    print("\n=== Simulação Wokwi + captura serial ===")
    print("Tentando abrir diagram.json para facilitar a inicialização do Wokwi...")
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(diagram_file))
        elif shutil.which("xdg-open") is not None:
            subprocess.run(["xdg-open", str(diagram_file)], check=False)
        elif shutil.which("open") is not None:
            subprocess.run(["open", str(diagram_file)], check=False)
        elif shutil.which("code") is not None:
            subprocess.run(["code", str(diagram_file)], check=False)
        else:
            print("Não foi possível abrir diagram.json automaticamente. Abra-o manualmente no Wokwi ou no VS Code.")
    except Exception as exc:
        print(f"Aviso: não foi possível abrir diagram.json automaticamente: {exc}")

    print("\nAguardando o Wokwi iniciar e a porta RFC2217 abrir...")

    if not wait_for_rfc2217("127.0.0.1", 4000):
        print("\nA porta RFC2217 não ficou disponível no tempo esperado.")
        print("Verifique se o Wokwi está rodando, se a simulação foi iniciada e se o arquivo wokwi.toml está configurado com rfc2217ServerPort = 4000.")
        print("Depois disso, tente novamente a opção 1 do menu.")
        return

    print("\nPorta RFC2217 aberta. Iniciando a captura serial Python em dados/historico_irrigacao.csv...")
    print("Para encerrar a captura serial e voltar ao menu, pressione ENTER.\n")

    try:
        run_serial_capture()
    except Exception as exc:
        print(f"Erro ao iniciar a captura serial: {exc}")


def run_r_menu() -> None:
    if shutil.which("Rscript") is None:
        print("Erro: não foi possível encontrar o comando 'Rscript' no PATH.")
        print("Instale o R ou verifique sua instalação.")
        return

    if not (ROOT / "app.r").exists():
        print("Erro: arquivo app.r não encontrado na raiz do projeto.")
        return

    print("\n=== Executando menu R ===")
    print("O menu R será aberto no console. Use as opções disponíveis.")

    try:
        result = subprocess.run(RSCRIPT_CMD, cwd=ROOT, check=False)
        if result.returncode:
            print(f"Menu R encerrado com código {result.returncode}.")
    except KeyboardInterrupt:
        print("\nExecução do R interrompida pelo usuário. Retornando ao menu...")
    except Exception as exc:
        print(f"Erro ao iniciar o Rscript: {exc}")


def show_menu() -> None:
    print("\n===== APP Principal =====")
    print("1 - Simulação Wokwi + captura serial")
    print("2 - Análises em R (menu R)")
    print("3 - Consulta de previsão do tempo")
    print("4 - Sair")


def main() -> None:
    while True:
        show_menu()
        try:
            escolha = input("Escolha uma opção: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaindo...")
            break
        try:
            if escolha == "1":
                run_wokwi_simulation()
            elif escolha == "2":
                run_r_menu()
            elif escolha == "3":
                run_weather_forecast()
            elif escolha == "4":
                print("Saindo...")
                break
            else:
                print("Opção inválida. Digite 1, 2, 3 ou 4.")
        except KeyboardInterrupt:
            print("\nOperação interrompida. Retornando ao menu...")


if __name__ == "__main__":
    main()
