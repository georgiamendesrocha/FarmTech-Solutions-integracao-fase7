"""Worker descartável da Fase 6; stdin JSON, stdout Result JSON, sem logs públicos."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import json
import math
import hashlib
import subprocess
from pathlib import Path
import sys
import time
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from farmtech_integracao.contracts import Result
from farmtech_integracao.fase6 import CHECKPOINT_SHA256, REVISAO_YOLO, MODELO_RELATIVO, _fonte
from farmtech_integracao.runtime import PROJECT_ROOT, SERVICE_DIRS


class _DiscardLogs:
    def write(self, value):
        return len(value)

    def flush(self):
        pass


def _load_evaluator():
    path = Path(SERVICE_DIRS["fase6"]) / "entrega_2" / "avaliar_yolo.py"
    spec = importlib.util.spec_from_file_location("farmtech_yolo_avaliador_local", path)
    if spec is None or spec.loader is None:
        raise ValueError("Avaliador indisponível.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_report(report):
    if (not isinstance(report, dict) or report.get("abordagem") != "customizada"
            or report.get("revisao") != REVISAO_YOLO
            or report.get("checkpoint_sha256") != CHECKPOINT_SHA256
            or report.get("total_imagens") != 8):
        raise ValueError("Relatório incompatível.")
    metrics = report.get("metricas")
    if not isinstance(metrics, dict) or set(metrics) != {"banana", "milho"}:
        raise ValueError("Classes incompatíveis.")
    safe_metrics = {}
    for name, values in metrics.items():
        safe_metrics[name] = {}
        for key in ("tp", "fp", "fn"):
            value = values[key]
            if type(value) is not int or not 0 <= value <= 100_000:
                raise ValueError("Contagem inválida.")
            safe_metrics[name][key] = value
        for key in ("precision", "recall", "f1"):
            value = values[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Métrica inválida.")
            safe_metrics[name][key] = value
    time_ms = report.get("tempo_medio_ms")
    if type(time_ms) not in (int, float) or not math.isfinite(time_ms) or time_ms < 0:
        raise ValueError("Tempo inválido.")
    # Seleção explícita: mensagens/caminhos de bibliotecas não atravessam o contrato.
    return {"experimento": "nova_avaliacao_independente_yolo", "abordagem": "customizada",
            "total_imagens": 8, "metricas": safe_metrics, "tempo_medio_ms": time_ms,
            "configuracao": {"confianca": 0.25, "iou_associacao": 0.5, "tamanho": 640},
            "ambiente": {"python": "3.13.13", "dispositivo": "CPU"},
            "revisao": REVISAO_YOLO, "checkpoint_sha256": CHECKPOINT_SHA256}


def _infer_one(payload) -> Result:
    """Inferência isolada: arquivo temporário allowlisted e checkpoint verificado."""
    if (set(payload) != {"action", "filename", "yolo_repo", "revision"}
            or payload.get("revision") != REVISAO_YOLO):
        return Result("invalid", "Parâmetros da inferência inválidos.", source=_fonte())
    name, repo = payload.get("filename"), payload.get("yolo_repo")
    import re
    if not isinstance(name, str) or not re.fullmatch(r"[0-9a-f]{32}\.(png|jpg|jpeg)", name):
        return Result("invalid", "Imagem temporária inválida.", source=_fonte())
    if not isinstance(repo, str) or not repo.strip() or len(repo) > 4096 or "\x00" in repo:
        return Result("invalid", "Ambiente YOLO inválido.", source=_fonte())
    path = (PROJECT_ROOT / ".runtime" / "fase6" / "uploads" / name).resolve()
    base = (PROJECT_ROOT / ".runtime" / "fase6" / "uploads").resolve()
    if path.parent != base or not path.is_file() or not 0 < path.stat().st_size <= 5 * 1024 * 1024:
        return Result("invalid", "Upload ausente ou excede o limite.", source=_fonte())
    checkout = Path(repo).resolve()
    weights = Path(SERVICE_DIRS["fase6"]) / MODELO_RELATIVO
    if not (checkout / ".git").exists() or not (checkout / "hubconf.py").is_file() or not weights.is_file():
        return Result("unavailable", "YOLO local ou checkpoint não disponível.", source=_fonte())
    try:
        evaluator = _load_evaluator()
        evaluator.verificar_fonte(SimpleNamespace(
            yolo_repo=checkout, revisao=REVISAO_YOLO, abordagem="customizada",
        ))
        digest = hashlib.sha256()
        with weights.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != CHECKPOINT_SHA256:
            return Result("invalid", "Checkpoint divergente do hash preservado.", source=_fonte())
        from PIL import Image, ImageOps
        Image.MAX_IMAGE_PIXELS = 16_000_000
        with Image.open(path) as uploaded:
            if uploaded.format not in ("JPEG", "PNG"):
                return Result("invalid", "Formato real da imagem inválido.", source=_fonte())
            uploaded.verify()
        with Image.open(path) as uploaded:
            uploaded = ImageOps.exif_transpose(uploaded)
            if uploaded.width > 4096 or uploaded.height > 4096:
                return Result("invalid", "Dimensões acima de 4096 pixels.", source=_fonte())
            picture = uploaded.convert("RGB")
        with redirect_stdout(_DiscardLogs()), redirect_stderr(_DiscardLogs()):
            evaluator.impedir_mistura_modulos()
            # A proteção permanece somente neste worker descartável, antes do framework.
            sys.addaudithook(lambda evento, dados: evaluator.bloquear_rede_e_processos(
                evento, dados, checkout,
            ))
            import torch
            # Mesma compatibilidade de carregamento utilizada pelo avaliador preservado.
            load_started = time.perf_counter()
            with evaluator.compatibilidade_posix_windows():
                model = torch.hub.load(str(checkout), "custom", path=str(weights),
                                       source="local", device="cpu")
            model.conf = 0.25
            model.eval()
            raw_names = enumerate(model.names) if isinstance(model.names, (tuple, list)) else model.names.items()
            names = {int(i): str(v).lower() for i, v in raw_names}
            if names != {0: "banana", 1: "milho"}:
                return Result("invalid", "Classes do checkpoint incompatíveis.", source=_fonte())
            load_ms = (time.perf_counter() - load_started) * 1000
            inference_started = time.perf_counter()
            with torch.inference_mode():
                pred = model(picture, size=640)
            rows = pred.xyxy[0].detach().cpu().tolist()
            inference_ms = (time.perf_counter() - inference_started) * 1000
        detections = []
        for row in rows[:100]:
            x1, y1, x2, y2, conf, class_id = row[:6]
            class_id = int(class_id)
            if class_id not in names or not all(math.isfinite(float(v)) for v in (x1, y1, x2, y2, conf)):
                raise ValueError("Detecção inválida.")
            detections.append({"classe": names[class_id], "confianca": round(float(conf), 4),
                               "caixa": [round(max(0.0, float(v)), 1) for v in (x1, y1, x2, y2)]})
        return Result("ok", "Inferência concluída; modelo experimental.",
                      data={"deteccoes": detections, "largura": picture.width,
                            "altura": picture.height, "total": len(detections),
                            "modelo_carregado": True, "classes_modelo": list(names.values()),
                            "tempo_carregamento_ms": load_ms, "tempo_inferencia_ms": inference_ms,
                            "limite": "Resultados experimentais; não substituem avaliação agronômica."},
                      source=_fonte())
    except (ImportError, ModuleNotFoundError, AttributeError):
        return Result("unavailable", "Dependências ou funções YOLO não disponíveis no ambiente validado.", source=_fonte())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        return Result("error", "Não foi possível executar a inferência. Verifique o ambiente e o checkpoint.", source=_fonte())
    except Exception:
        return Result("error", "Falha na inferência isolada da imagem.", source=_fonte())


def handle(payload) -> Result:
    if tuple(sys.version_info[:3]) != (3, 13, 13):
        return Result("unavailable", "A Fase 6 exige o Python 3.13.13 validado, em processo separado.", source=_fonte())
    if isinstance(payload, dict) and payload.get("action") == "infer_image":
        return _infer_one(payload)
    if (not isinstance(payload, dict) or set(payload) != {"action", "yolo_repo", "revision"}
            or payload.get("action") != "evaluate_customizada"
            or payload.get("revision") != REVISAO_YOLO):
        return Result("error", "Solicitação de avaliação inválida.", source=_fonte())
    repo = payload.get("yolo_repo")
    if not isinstance(repo, str) or not repo.strip() or len(repo) > 4096 or "\x00" in repo:
        return Result("error", "Informe um checkout Git local válido.", source=_fonte())
    try:
        checkout = Path(repo).expanduser().resolve()
        if not (checkout / ".git").exists() or not (checkout / "hubconf.py").is_file():
            return Result("unavailable", "O caminho informado deve ser um checkout Git; cache do Hub não atende este requisito.", source=_fonte())
        # O avaliador verifica Git, revisão, hash, dataset e classes antes da inferência.
        with redirect_stdout(_DiscardLogs()), redirect_stderr(_DiscardLogs()):
            evaluator = _load_evaluator()
            report = evaluator.main([
                "--abordagem", "customizada", "--yolo-repo", str(checkout),
                "--revisao", REVISAO_YOLO, "--json",
            ])
        data = _safe_report(report)
        return Result("ok", "Avaliação das oito imagens de teste concluída; resultados desta execução.", data=data, source=_fonte())
    except ImportError:
        return Result("unavailable", "Dependências da Fase 6 ausentes ou incompatíveis no ambiente selecionado.", source=_fonte())
    except (OSError, ValueError, RuntimeError):
        return Result("error", "A avaliação foi recusada ou falhou. Confira revisão, integridade, dataset e ambiente local.", source=_fonte())
    except Exception:
        return Result("error", "Não foi possível concluir a avaliação no processo isolado.", source=_fonte())


def main():
    try:
        raw = sys.stdin.read(16_385)
        if len(raw) > 16_384:
            raise ValueError("Solicitação excede o limite.")
        result = handle(json.loads(raw))
    except (ValueError, TypeError, UnicodeError):
        result = Result("error", "Solicitação JSON inválida.", source=_fonte())
    print(json.dumps(result.as_dict(), ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
