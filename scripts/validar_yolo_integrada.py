"""Validação real por botão, com checkout existente, revisão e pesos preservados.

--inferencias usa os bytes originais de banana_01.jpg e milho_02.jpg. Como
AppTest não oferece upload nativo, somente o transporte file_uploader é
controlado; página, botão, adaptador, subprocesso e modelo permanecem reais.
Sem essa opção, executa a avaliação histórica das oito imagens.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from farmtech_integracao.fase6 import CHECKPOINT_SHA256, REVISAO_YOLO
from farmtech_integracao.runtime import SERVICE_DIRS

DEFAULT_OUTPUT = ROOT / ".runtime/validation/complementar-20261106/yolo-integrada.json"
PAGE = SERVICE_DIRS["fase4"] / "src/frontend/pages/12_Visao_Computacional.py"


def _new_page():
    from streamlit.testing.v1 import AppTest

    page = AppTest.from_file(str(PAGE), default_timeout=180).run()
    if page.exception:
        raise RuntimeError("Erro ao abrir a página integrada de visão.")
    return page


def _click(page, label):
    button = next(item for item in page.button if item.label == label)
    if button.disabled:
        raise RuntimeError("Pré-condições do botão YOLO não atendidas.")
    started = time.perf_counter()
    button.click().run()
    elapsed_ms = (time.perf_counter() - started) * 1000
    if page.exception:
        raise RuntimeError("Erro de interface ao executar a YOLO.")
    return elapsed_ms


def _inferencias():
    import streamlit as st

    images = SERVICE_DIRS["fase6"] / "dataset/test/images"
    results = []
    for culture, name in (("banana", "banana_01.jpg"), ("milho", "milho_02.jpg")):
        image = images / culture / name
        content = image.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        upload = SimpleNamespace(name=name, getvalue=lambda: content)
        # A substituição só entrega os bytes ao widget sem suporte no AppTest.
        # Não substitui inferir_imagem, run_json_worker, torch ou o modelo.
        with patch.object(st, "file_uploader", return_value=upload):
            page = _new_page()
            elapsed_ms = _click(page, "Identificar banana ou milho")
        result = page.session_state["fase6_inferencia"]["resultado"]
        results.append({
            "imagem": str(image.relative_to(ROOT)).replace("\\", "/"),
            "classe_do_conjunto": culture,
            "imagem_sha256": digest,
            "imagem_preservada": hashlib.sha256(image.read_bytes()).hexdigest() == digest,
            "tempo_botao_ms": elapsed_ms,
            "ui_exceptions": len(page.exception),
            "ui_errors": len(page.error),
            "ui_dataframes": len(page.dataframe),
            "result": result,
        })
        print(f"Inferência real de {name}: {result['status']}.", flush=True)
    return {
        "validation": "real Streamlit page/button -> adapter -> worker Python3.13.13 -> local YOLOv5",
        "upload_transport": "controlled file_uploader bytes; AppTest has no native upload support",
        "models_or_workers_mocked": False,
        "inferences": results,
    }


def _avaliacao():
    page = _new_page()
    elapsed_ms = _click(page, "Avaliar YOLO customizada")
    return {
        "validation": "real Streamlit button -> adapter -> worker Python3.13.13 -> avaliar_yolo.py",
        "ui_exceptions": len(page.exception),
        "plotly_charts": len(page.get("plotly_chart")),
        "tempo_botao_ms": elapsed_ms,
        "result": page.session_state["fase6_avaliacao"]["resultado"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yolo-repo", type=Path, required=True)
    parser.add_argument("--inferencias", action="store_true", help="Validar somente os dois uploads reais.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    repo = args.yolo_repo.expanduser().resolve()
    if not repo.is_dir() or not (repo / ".git").exists():
        raise RuntimeError("Checkout Git local ausente.")
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")

    def git(*arguments):
        return subprocess.run(
            ["git", "-C", str(repo), *arguments], capture_output=True,
            text=True, encoding="utf-8", check=True, timeout=15, env=env,
        ).stdout.strip()

    head = git("rev-parse", "--verify", "HEAD^{commit}")
    if head != REVISAO_YOLO:
        raise RuntimeError("Revisão Git diferente da revisão exigida.")
    file_filters = ("*.py", "*.yaml", "*.yml", "*.txt", "*.toml", "*.cfg", "*.ini", "*.json", "*.pyd", "*.so", "*.pth")
    status_args = ("status", "--porcelain", "--untracked-files=all", "--ignored=matching", "--", *file_filters)
    before_status = git(*status_args)
    if before_status:
        raise RuntimeError("Checkout com fontes/configuração alterados; avaliação recusada.")
    print("Checkout existente, revisão completa correta e fontes limpas; iniciando validação integrada.", flush=True)
    models = SERVICE_DIRS["fase6"] / "entrega_2/modelos"

    def model_hashes():
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in models.iterdir() if p.suffix in (".pt", ".keras")}

    before = model_hashes()
    if before.get("yolov5s_custom_exp60_best.pt") != CHECKPOINT_SHA256:
        raise RuntimeError("Checkpoint divergente do hash preservado.")
    # A página obtém o checkout da configuração; o antigo text_input foi removido.
    with patch.dict(os.environ, {"FARMTECH_YOLO_REPO": str(repo)}):
        evidence = _inferencias() if args.inferencias else _avaliacao()
    preserved = before == model_hashes()
    checkout_unchanged = git(*status_args) == before_status and git("rev-parse", "HEAD") == head
    evidence.update({"revision": head, "checkpoint_sha256": CHECKPOINT_SHA256,
                     "models_preserved": preserved, "checkout_unchanged": checkout_unchanged})
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False))
    if args.inferencias:
        successful = all(item["result"]["status"] == "ok" and item["imagem_preservada"]
                         and item["ui_errors"] == 0 for item in evidence["inferences"])
    else:
        successful = evidence["result"]["status"] == "ok"
    return 0 if successful and preserved and checkout_unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
