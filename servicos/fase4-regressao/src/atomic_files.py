"""Publicação recuperável de conjuntos locais, com exclusão mútua entre processos.

Os consumidores deste módulo devem ler sob ``data_directory``. Outros programas
que leiam os CSVs diretamente precisam respeitar a mesma trava/validar os hashes.
O journal mantém os bytes anteriores até concluir todo o conjunto; uma próxima
leitura ou escrita recupera uma interrupção antes de servir os arquivos.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Mapping


def _write_bytes(path: Path, content: bytes) -> None:
    with path.open("wb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())


def _pending_path(directory: Path) -> Path:
    pending = directory / ".farmtech-publication"
    if pending.is_symlink() or pending.resolve().parent != directory.resolve():
        raise ValueError("Diretório de recuperação fora do destino previsto.")
    return pending


def _cleanup(directory: Path) -> None:
    pending = _pending_path(directory)
    # Uma limpeza interrompida depois de remover o marcador não pode fazer uma
    # publicação já concluída parecer pendente de rollback na próxima leitura.
    journal = pending / "journal.json"
    if journal.exists():
        journal.unlink()
    shutil.rmtree(pending)


def _recover(directory: Path) -> None:
    pending = _pending_path(directory)
    if not pending.exists():
        return
    journal = pending / "journal.json"
    if journal.exists() and not (pending / "committed").exists():
        entries = json.loads(journal.read_text(encoding="utf-8"))
        for entry in entries:
            name = entry["name"]
            backup = entry["backup"]
            if (Path(name).name != name or name in {"", ".", ".."}
                    or Path(backup).name != backup or not backup.endswith(".old")):
                raise ValueError("Journal de publicação inválido; recuperação manual necessária.")
            target = directory / name
            if entry["existed"]:
                restored = pending / "restore.tmp"
                _write_bytes(restored, (pending / entry["backup"]).read_bytes())
                os.replace(restored, target)
            elif target.is_file():
                target.unlink()
        _cleanup(directory)
    else:
        # Sem journal, nenhum alvo chegou a ser trocado; com marcador, todos
        # já foram confirmados. Falha de limpeza não invalida dados coerentes.
        try:
            _cleanup(directory)
        except OSError:
            pass


@contextmanager
def data_directory(directory: Path, timeout: float = 15) -> Iterator[None]:
    """Trava cooperativa por diretório, liberada pelo SO se o processo terminar."""
    directory = Path(directory).resolve()
    locks = Path(tempfile.gettempdir()) / "farmtech-data-locks"
    locks.mkdir(exist_ok=True)
    key = hashlib.sha256(os.path.normcase(str(directory)).encode()).hexdigest()
    with (locks / (key + ".lock")).open("a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                lock.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (OSError, BlockingIOError) as error:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Dados oficiais em atualização; tente novamente.") from error
                time.sleep(0.02)
        try:
            _recover(directory)
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def publish_files(files: Mapping[Path, bytes], *, locked: bool = False) -> None:
    """Publica um conjunto no mesmo diretório, restaurando-o em caso de falha.

    ``locked=True`` destina-se ao importador que precisa ler e publicar sob a
    mesma trava (SIDRA compartilha a série nacional entre vários recortes).
    """
    targets = {Path(path).resolve(): content for path, content in files.items()}
    if len(targets) != len(files):
        raise ValueError("Destinos de publicação duplicados.")
    parents = {path.parent for path in targets}
    if len(parents) != 1:
        raise ValueError("CSV e metadados devem compartilhar o diretório de publicação.")
    directory = next(iter(parents))
    directory.mkdir(parents=True, exist_ok=True)
    if not locked:
        with data_directory(directory):
            publish_files(targets, locked=True)
        return
    for target in targets:
        if target.exists() and not target.is_file():
            raise ValueError("Destino de publicação não é um arquivo regular.")
        if target.name == ".farmtech-publication":
            raise ValueError("Nome reservado para recuperação de publicação.")
    pending = _pending_path(directory)
    pending.mkdir()
    entries = []
    try:
        for index, (target, content) in enumerate(targets.items()):
            backup = f"{index}.old"
            existed = target.is_file()
            if existed:
                _write_bytes(pending / backup, target.read_bytes())
            _write_bytes(pending / f"{index}.new", content)
            entries.append({"name": target.name, "existed": existed, "backup": backup})
        _write_bytes(pending / "journal.tmp", json.dumps(entries).encode("utf-8"))
        os.replace(pending / "journal.tmp", pending / "journal.json")
        for index, target in enumerate(targets):
            os.replace(pending / f"{index}.new", target)
        _write_bytes(pending / "committed.tmp", b"complete")
        os.replace(pending / "committed.tmp", pending / "committed")
    except BaseException:
        # Se o rollback falhar, o journal e os backups ficam disponíveis para
        # recuperação na próxima operação; nunca anunciar conclusão parcial.
        _recover(directory)
        raise
    try:
        _cleanup(directory)
    except OSError:
        # A publicação está concluída; uma nova leitura tentará a limpeza.
        # Não devolver falha de importação para um conjunto já confirmado.
        pass
