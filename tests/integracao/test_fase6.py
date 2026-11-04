"""Contratos Fase 6 sem frameworks, inferência, rede ou alteração dos modelos."""

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from farmtech_integracao import fase6
from farmtech_integracao.contracts import Result
from farmtech_integracao.workers import fase6_worker


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def report():
    return {
        "abordagem": "customizada", "revisao": fase6.REVISAO_YOLO,
        "checkpoint_sha256": fase6.CHECKPOINT_SHA256, "total_imagens": 8,
        "metricas": {
            "banana": {"tp": 2, "fp": 1, "fn": 7, "precision": 2/3, "recall": 2/9, "f1": 1/3},
            "milho": {"tp": 4, "fp": 4, "fn": 3, "precision": .5, "recall": 4/7, "f1": 8/15},
        },
        "tempo_medio_ms": 250.0,
    }


class Fase6ContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.service = root / "fase6"
        self.python = root / "python.exe"
        self.python.touch()
        for name in ("entrega_2/avaliar_yolo.py", fase6.MODELO_RELATIVO):
            target = self.service / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
        for name in ("banana", "milho"):
            for number in range(4):
                for kind, extension in (("images", "jpg"), ("labels", "txt")):
                    target = self.service / "dataset" / "test" / kind / name / f"{name}_{number}.{extension}"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.touch()
        self.checkout = root / "checkout"
        self.checkout.mkdir()
        (self.checkout / ".git").mkdir()
        (self.checkout / "hubconf.py").touch()
        service_patch = patch.dict(fase6.SERVICE_DIRS, {"fase6": self.service})
        service_patch.start()
        self.addCleanup(service_patch.stop)

    def test_availability_only_checks_metadata(self):
        with patch.object(fase6, "run_json_worker", side_effect=AssertionError("Não executar")), \
                patch.object(Path, "open", side_effect=AssertionError("Não abrir conteúdo")):
            result = fase6.availability(self.checkout, python=self.python)
        self.assertTrue(result.ok)
        self.assertFalse(result.data["runtime_validado"])
        self.assertTrue(all(result.data["checks"].values()))

    def test_hub_cache_without_git_is_unavailable(self):
        (self.checkout / ".git").rmdir()
        with patch.object(fase6, "run_json_worker") as runner:
            result = fase6.evaluate_customizada(self.checkout, python=self.python)
        self.assertEqual(result.status, "unavailable")
        runner.assert_not_called()

    def test_action_uses_separate_python_fixed_revision_and_no_custom_weights(self):
        expected = Result("ok", "Concluído", data=report())
        with patch.object(fase6, "run_json_worker", return_value=expected) as runner:
            result = fase6.evaluate_customizada(self.checkout, python=self.python, timeout=90)
        self.assertIs(result, expected)
        runner.assert_called_once_with(
            "fase6", {"action": "evaluate_customizada", "yolo_repo": str(self.checkout.resolve()),
                      "revision": fase6.REVISAO_YOLO},
            timeout=90, python=str(self.python.resolve()),
        )

    def test_wrong_python_is_rejected_before_evaluator_import(self):
        with patch.object(fase6_worker.sys, "version_info", (3, 11, 9)), \
                patch.object(fase6_worker, "_load_evaluator") as loader:
            result = fase6_worker.handle({"action": "evaluate_customizada"})
        self.assertEqual(result.status, "unavailable")
        loader.assert_not_called()

    def test_worker_rejects_user_supplied_model_or_script(self):
        payload = {"action": "evaluate_customizada", "yolo_repo": str(self.checkout),
                   "revision": fase6.REVISAO_YOLO, "pesos": "outro.pt"}
        with patch.object(fase6_worker.sys, "version_info", (3, 13, 13)), \
                patch.object(fase6_worker, "_load_evaluator") as loader:
            result = fase6_worker.handle(payload)
        self.assertEqual(result.status, "error")
        loader.assert_not_called()

    def test_worker_calls_preserved_evaluator_and_suppresses_logs(self):
        def evaluate(argv):
            self.assertIn("--json", argv)
            self.assertEqual(argv[argv.index("--revisao") + 1], fase6.REVISAO_YOLO)
            print("log privado não retornado")
            output = report()
            output["log"] = "conteúdo privado"
            return output

        output = io.StringIO()
        payload = {"action": "evaluate_customizada", "yolo_repo": str(self.checkout), "revision": fase6.REVISAO_YOLO}
        with patch.object(fase6_worker.sys, "version_info", (3, 13, 13)), \
                patch.object(fase6_worker, "_load_evaluator", return_value=SimpleNamespace(main=evaluate)), \
                redirect_stdout(output):
            result = fase6_worker.handle(payload)
        self.assertTrue(result.ok)
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn("log", result.data)

    def test_worker_sanitizes_dependency_errors(self):
        payload = {"action": "evaluate_customizada", "yolo_repo": str(self.checkout), "revision": fase6.REVISAO_YOLO}
        with patch.object(fase6_worker.sys, "version_info", (3, 13, 13)), \
                patch.object(fase6_worker, "_load_evaluator", side_effect=ImportError("valor privado")):
            result = fase6_worker.handle(payload)
        self.assertEqual(result.status, "unavailable")
        self.assertNotIn("valor privado", json.dumps(result.as_dict()))

    def test_report_rejects_nonfinite_or_wrong_checkpoint(self):
        for change in ({"tempo_medio_ms": float("nan")}, {"checkpoint_sha256": "outro"}):
            invalid = report()
            invalid.update(change)
            with self.assertRaises(ValueError):
                fase6_worker._safe_report(invalid)


class PreservedEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = PROJECT_ROOT / "servicos/fase6-visao/entrega_2/avaliar_yolo.py"
        spec = importlib.util.spec_from_file_location("fase6_evaluator_unit_test", path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_json_mode_is_structured_and_preserves_legacy_mode(self):
        args = ["--abordagem", "customizada", "--yolo-repo", str(PROJECT_ROOT)]
        expected = report()
        with patch.object(self.module, "_executar", return_value=expected) as run:
            output = io.StringIO()
            with redirect_stdout(output):
                returned = self.module.main(args + ["--json"])
            self.assertEqual(json.loads(output.getvalue()), expected)
            self.assertEqual(returned, expected)
            self.assertTrue(run.call_args.args[0].json)
            self.module.main(args)
            self.assertFalse(run.call_args.args[0].json)

    def test_models_keep_preserved_hashes_without_deserializing(self):
        expected = {
            "yolov5s_custom_exp60_best.pt": fase6.CHECKPOINT_SHA256,
            "cnn_do_zero_fase6.keras": "f9e69a7c882f2a7e625897f73e6313637011288682a7d8a58145b6f64e44cc86",
        }
        directory = PROJECT_ROOT / "servicos/fase6-visao/entrega_2/modelos"
        for name, digest in expected.items():
            with (directory / name).open("rb") as handle:
                actual = hashlib.file_digest(handle, "sha256").hexdigest()
            self.assertEqual(actual, digest, name)


if __name__ == "__main__":
    unittest.main()
