"""Integração da avaliação preservada YOLO, sem carregar modelos neste processo."""

from __future__ import annotations

import os
from pathlib import Path
import uuid

from .contracts import Result
from .runtime import PROJECT_ROOT, SERVICE_DIRS, run_json_worker

REVISAO_YOLO = "4add2aff6e3d926586a3eab4659f3b498dd444a1"
CHECKPOINT_SHA256 = "93c086ad8e369cc295dced96b9d48db1524226207e82ab514148f02decad2f61"
MODELO_RELATIVO = "entrega_2/modelos/yolov5s_custom_exp60_best.pt"
PYTHON_VALIDADO = "3.13.13"


def _configuracao(yolo_repo=None, python=None):
    service = Path(SERVICE_DIRS["fase6"])
    executable = python or os.environ.get("FARMTECH_FASE6_PYTHON")
    executable = executable or service / ".venv-fase6" / "Scripts" / "python.exe"
    repo = yolo_repo if yolo_repo is not None else os.environ.get("FARMTECH_YOLO_REPO", "")
    if not repo:
        # Descoberta apenas de cópias locais preexistentes; nunca baixar automaticamente.
        candidates = (
            service / "vendor" / "yolov5",
            PROJECT_ROOT / "vendor" / "yolov5",
            Path.home() / "yolov5-validacao-fase6",
        )
        repo = next((str(candidate) for candidate in candidates
                     if (candidate / ".git").exists() and (candidate / "hubconf.py").is_file()), "")
    if not isinstance(repo, (str, Path)) or not str(repo).strip():
        return service, Path(executable).expanduser().resolve(), None
    if len(str(repo)) > 4096 or "\x00" in str(repo):
        raise ValueError("Caminho do checkout inválido.")
    return service, Path(executable).expanduser().resolve(), Path(repo).expanduser().resolve()


def _fonte():
    return {"fase": "fase6", "modelo": MODELO_RELATIVO, "revisao": REVISAO_YOLO,
            "python_validado": PYTHON_VALIDADO, "dataset": "dataset/test"}


def availability(yolo_repo=None, *, python=None) -> Result:
    """Consulta somente metadados; não executa Python/Git nem abre os pesos."""
    try:
        service, executable, repo = _configuracao(yolo_repo, python)
        checks = {
            "python_existe": executable.is_file(),
            "avaliador_existe": (service / "entrega_2" / "avaliar_yolo.py").is_file(),
            "checkpoint_existe": (service / MODELO_RELATIVO).is_file(),
            "checkout_configurado": repo is not None,
            "checkout_git": repo is not None and (repo / ".git").exists(),
            "hubconf_existe": repo is not None and (repo / "hubconf.py").is_file(),
        }
        dataset = service / "dataset" / "test"
        for classe in ("banana", "milho"):
            images = sorted((dataset / "images" / classe).glob("*.jpg"))
            checks[f"teste_{classe}"] = len(images) == 4 and all(
                (dataset / "labels" / classe / f"{photo.stem}.txt").is_file()
                for photo in images
            )
        ready = all(checks.values())
        return Result(
            "ok" if ready else "unavailable",
            ("Pré-requisitos locais presentes. Python, revisão e integridade serão verificados na avaliação."
             if ready else "Configure Python 3.13.13 e um checkout Git local da revisão exigida; confira modelo e teste preservados."),
            data={"checks": checks, "runtime_validado": False}, source=_fonte(),
        )
    except (OSError, TypeError, ValueError):
        return Result("unavailable", "Configuração local da visão computacional inválida.", source=_fonte())


def evaluate_customizada(yolo_repo=None, *, python=None, timeout=120) -> Result:
    """Avalia oito imagens fixas em processo 3.13.13, apenas quando solicitada."""
    preflight = availability(yolo_repo, python=python)
    if not preflight.ok:
        return preflight
    _, executable, repo = _configuracao(yolo_repo, python)
    return run_json_worker(
        "fase6", {"action": "evaluate_customizada", "yolo_repo": str(repo), "revision": REVISAO_YOLO},
        timeout=timeout, python=str(executable),
    )


MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def infer_availability() -> Result:
    """Consulta os componentes da inferência sem depender das oito imagens de teste."""
    try:
        service, executable, repo = _configuracao()
        checks = {
            "python_existe": executable.is_file(),
            "checkpoint_existe": (service / MODELO_RELATIVO).is_file(),
            "checkout_local": repo is not None and (repo / ".git").exists()
            and (repo / "hubconf.py").is_file(),
        }
        return Result("ok" if all(checks.values()) else "unavailable",
                      "Inferência disponível." if all(checks.values()) else
                      "Inferência indisponível: o responsável precisa preparar o ambiente YOLO local.",
                      data={"checks": checks}, source=_fonte())
    except (OSError, TypeError, ValueError):
        return Result("unavailable", "Ambiente de inferência inválido.", source=_fonte())


def inferir_imagem(content: bytes, filename: str) -> Result:
    """Recebe upload pequeno, guarda temporariamente e chama processo isolado."""
    if not isinstance(content, bytes) or not 0 < len(content) <= MAX_UPLOAD_BYTES:
        return Result("invalid", "Imagem vazia ou maior que 5 MB.", source=_fonte())
    if not isinstance(filename, str):
        return Result("invalid", "Nome do arquivo inválido.", source=_fonte())
    suffix = Path(filename).suffix.lower()
    is_png = suffix == ".png" and content.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpg = suffix in (".jpg", ".jpeg") and content.startswith(b"\xff\xd8\xff")
    if not (is_png or is_jpg):
        return Result("invalid", "Envie uma imagem JPG ou PNG válida.", source=_fonte())
    preflight = infer_availability()
    if not preflight.ok:
        return preflight
    _, executable, repo = _configuracao()
    upload_dir = PROJECT_ROOT / ".runtime" / "fase6" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex + suffix
    path = upload_dir / name
    try:
        with path.open("xb") as handle:
            handle.write(content)
        return run_json_worker("fase6", {"action": "infer_image", "filename": name,
                           "yolo_repo": str(repo), "revision": REVISAO_YOLO},
                           timeout=180, python=str(executable))
    finally:
        path.unlink(missing_ok=True)
