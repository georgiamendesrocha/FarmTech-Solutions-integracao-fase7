"""Integração da avaliação preservada YOLO, sem carregar modelos neste processo."""

from __future__ import annotations

import os
from pathlib import Path

from .contracts import Result
from .runtime import SERVICE_DIRS, run_json_worker

REVISAO_YOLO = "4add2aff6e3d926586a3eab4659f3b498dd444a1"
CHECKPOINT_SHA256 = "93c086ad8e369cc295dced96b9d48db1524226207e82ab514148f02decad2f61"
MODELO_RELATIVO = "entrega_2/modelos/yolov5s_custom_exp60_best.pt"
PYTHON_VALIDADO = "3.13.13"


def _configuracao(yolo_repo=None, python=None):
    service = Path(SERVICE_DIRS["fase6"])
    executable = python or os.environ.get("FARMTECH_FASE6_PYTHON")
    executable = executable or service / ".venv-fase6" / "Scripts" / "python.exe"
    repo = yolo_repo if yolo_repo is not None else os.environ.get("FARMTECH_YOLO_REPO", "")
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
