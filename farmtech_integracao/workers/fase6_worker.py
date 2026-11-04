"""Worker descartável da Fase 6; stdin JSON, stdout Result JSON, sem logs públicos."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import json
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from farmtech_integracao.contracts import Result
from farmtech_integracao.fase6 import CHECKPOINT_SHA256, REVISAO_YOLO, _fonte
from farmtech_integracao.runtime import SERVICE_DIRS


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


def handle(payload) -> Result:
    if tuple(sys.version_info[:3]) != (3, 13, 13):
        return Result("unavailable", "A Fase 6 exige o Python 3.13.13 validado, em processo separado.", source=_fonte())
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
