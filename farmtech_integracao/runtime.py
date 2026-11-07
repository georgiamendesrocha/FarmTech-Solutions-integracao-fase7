"""Processos permitidos, sem shell, com limites e comunicação JSON por stdin.

Nenhum processo ou diretório é criado ao importar este módulo. As travas são
adquiridas somente em uma ação explícita e coordenam também outras instâncias.
"""

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from farmtech_integracao.contracts import Result

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICE_DIRS = {
    f"fase{number}": PROJECT_ROOT / "servicos" / directory
    for number, directory in enumerate((
        "fase1-gestao", "fase2-iot", "fase3-dashboard", "fase4-regressao",
        "fase5-ml", "fase6-visao", "fase7-alertas-aws",
    ), 1)
}
WORKERS = {key: Path(__file__).parent / "workers" / f"{key}_worker.py"
           for key in ("fase1", "fase2", "fase3", "fase4", "fase6", "fase7")}
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_INPUT_BYTES = 32768


def _environment(phase: str) -> dict[str, str]:
    names = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE",
             "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "NUMBER_OF_PROCESSORS",
             "PROCESSOR_ARCHITECTURE", "LANG", "LC_ALL"}
    if phase == "fase3":
        names.update({"ORACLE_USER", "ORACLE_PASS", "ORACLE_DSN"})
    env = {key: value for key, value in os.environ.items() if key.upper() in names}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               FARMTECH_SIMULACAO="0", YOLO_AUTOINSTALL="False",
               YOLO_OFFLINE="True", WANDB_MODE="disabled")
    if phase == "fase6":
        # Configurações/caches de bibliotecas ficam separados dos arquivos históricos.
        directory = PROJECT_ROOT / ".runtime" / "fase6"
        env.update(YOLO_CONFIG_DIR=str(directory / "yolo"),
                   MPLCONFIGDIR=str(directory / "matplotlib"),
                   TORCH_HOME=str(directory / "torch"))
    return env


@contextmanager
def _phase_lock(phase: str):
    directory = PROJECT_ROOT / ".runtime" / "locks"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f"{phase}.lock").open("a+b") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _stop_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        taskkill = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32" / "taskkill.exe"
        try:
            subprocess.run([str(taskkill), "/F", "/T", "/PID", str(process.pid)],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5,
                           creationflags=subprocess.CREATE_NO_WINDOW, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def _execute(command: list[str], payload: bytes, *, cwd: Path,
             env: dict, timeout: float) -> tuple[int, bytes, str | None]:
    options = ({"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == "nt" else {"start_new_session": True})
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options)
    buffers = [bytearray(), bytearray()]
    overflow = threading.Event()

    def read(pipe, output):
        try:
            while chunk := pipe.read(65536):
                available = MAX_OUTPUT_BYTES - len(output)
                output.extend(chunk[:available])
                if len(chunk) > available:
                    overflow.set()
        finally:
            pipe.close()

    readers = [threading.Thread(target=read, args=(pipe, output), daemon=True)
               for pipe, output in zip((process.stdout, process.stderr), buffers)]
    for thread in readers:
        thread.start()
    reason = None
    def write_input():
        try:
            process.stdin.write(payload)
            process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass
        finally:
            process.stdin.close()
    writer = threading.Thread(target=write_input, daemon=True)
    try:
        writer.start()
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if overflow.is_set() or time.monotonic() >= deadline:
                reason = "output_limit" if overflow.is_set() else "timeout"
                _stop_tree(process)
                break
            time.sleep(0.025)
        for thread in readers:
            thread.join(timeout=2)
        writer.join(timeout=2)
        if any(thread.is_alive() for thread in readers):
            _stop_tree(process)
            reason = reason or "process_error"
        if overflow.is_set():
            reason = "output_limit"
        return process.returncode, bytes(buffers[0]), reason
    except BaseException:
        _stop_tree(process)
        raise
    finally:
        if not process.stdin.closed and not writer.is_alive():
            process.stdin.close()


def run_json_worker(phase: str, payload: dict, *, timeout=30, python=None) -> Result:
    if not isinstance(phase, str) or phase not in WORKERS or not isinstance(payload, dict):
        return Result("invalid", "Operação não permitida.")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 300:
        return Result("invalid", "Tempo limite inválido; permitido até 300 segundos.")
    try:
        executable = Path(python or sys.executable).expanduser()
        if not executable.is_absolute() or not executable.is_file():
            raise ValueError
    except (OSError, ValueError, TypeError):
        return Result("unavailable", "Interpretador Python configurado não encontrado.", source={"phase": phase})
    if not WORKERS[phase].is_file():
        return Result("unavailable", "Adaptador do serviço não encontrado.", source={"phase": phase})
    try:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_INPUT_BYTES:
            raise ValueError
    except (ValueError, TypeError):
        return Result("invalid", "Entrada inválida ou acima do limite.")
    try:
        with _phase_lock(phase):
            code, output, reason = _execute(
                [str(executable), "-X", "utf8", "-I", "-B", str(WORKERS[phase])], encoded,
                cwd=SERVICE_DIRS[phase], env=_environment(phase), timeout=float(timeout),
            )
        if reason:
            messages = {"timeout": "Tempo limite atingido; o processo foi encerrado.",
                        "output_limit": "O serviço excedeu o limite de saída e foi encerrado.",
                        "process_error": "O serviço não encerrou todos os processos corretamente."}
            return Result("error", messages[reason], {"reason": reason}, {"phase": phase})
        if code != 0:
            return Result("error", "O serviço encerrou com erro. Confira suas pré-condições.", source={"phase": phase})
        return Result.from_dict(json.loads(output.decode("utf-8")))
    except (OSError, BlockingIOError):
        return Result("unavailable", "Serviço ocupado ou sem permissão para executar. Tente novamente após verificar o ambiente.", source={"phase": phase})
    except (ValueError, UnicodeError):
        return Result("error", "O serviço não retornou uma resposta estruturada válida.", source={"phase": phase})
