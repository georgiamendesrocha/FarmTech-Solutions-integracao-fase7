"""Erros públicos de prévia não devem repetir células, tokens ou paths privados."""

from contextlib import redirect_stderr, redirect_stdout
import csv
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
_before = list(sys.path)
_spec = importlib.util.spec_from_file_location("_fase7_worker_errors", ROOT / "farmtech_integracao/workers/fase7_worker.py")
worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(worker)
sys.path[:] = _before
SENTINEL = "SENTINELA_PRIVADA_DO_TESTE"


class ErrosSegurancaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.history = self.folder / "history.csv"
        for name, value in (("HISTORY_CSV", self.history), ("UPLOAD_DIR", self.folder / "runtime")):
            guard = patch.object(worker, name, value)
            guard.start()
            self.addCleanup(guard.stop)
        self.paths = list(sys.path)
        names = ("sensores", "regras", "mensagem", "gerar_exemplo", "gerar_exemplo_iot")
        self.modules = {name: sys.modules.get(name) for name in names}
        self.addCleanup(self._restore)
        worker._modules.cache_clear()
        self._csv((datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat())

    def _restore(self):
        sys.path[:] = self.paths
        for name, previous in self.modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        worker._modules.cache_clear()

    def _csv(self, stamp, **changes):
        row = dict(ts_iso=stamp, t_rel_ms=30000, umidade=40, temp_c=25, ldr=2223,
                   ph_base=6.4, ph_corr=6.4, N=1, P=1, K=1, bomba_fw=1)
        row.update(changes)
        with self.history.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row), lineterminator="\n")
            writer.writeheader()
            writer.writerow(row)

    def _safe(self, result, captured=""):
        serialized = json.dumps(result.as_dict(), ensure_ascii=False) + captured
        self.assertNotIn(SENTINEL, serialized)
        self.assertNotIn("C:\\privado", serialized)
        self.assertIs(result.data["preview_only"], True)
        self.assertIs(result.data["sns_enabled"], False)

    def test_timestamp_invalido_nao_reflete_celula_em_resposta_ou_streams(self):
        self._csv("2026-T_" + SENTINEL)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = worker.handle({"operation": "evaluate_iot_csv", "fuso": "UTC"})
        self.assertEqual(result.status, "invalid")
        self._safe(result, stdout.getvalue() + stderr.getvalue())
        self.assertIn("timestamp", result.message.casefold())

    def test_excecoes_do_parser_nao_expoem_texto_interno(self):
        sensors = worker._modules()[0]
        for kind in (ValueError, TypeError, OverflowError):
            with self.subTest(kind=kind.__name__), patch.object(
                    sensors, "ler_leitura_csv", side_effect=kind("C:\\privado\\" + SENTINEL)):
                result = worker.handle({"operation": "evaluate_iot_csv"})
                self.assertEqual(result.status, "invalid")
                self._safe(result)

    def test_excecao_da_regra_nao_expoe_texto_interno(self):
        sensors = worker._modules()[0]
        with patch.object(sensors, "avaliar_sensor", side_effect=ValueError(SENTINEL)):
            result = worker.handle({"operation": "evaluate_iot_csv"})
        self.assertEqual(result.status, "invalid")
        self._safe(result)

    def test_conteudo_csv_invalido_e_recusado_sem_refletir_celulas(self):
        stamp = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        for changes in ({"umidade": "NaN"}, {"umidade": -1}, {"umidade": 101},
                        {"temp_c": "Infinity"}, {"ph_base": 15}, {"ph_corr": -1},
                        {"ldr": 4096}, {"t_rel_ms": 4294967296},
                        {"N": 2}, {"P": "1.0"}, {"K": "=IMPORT(" + SENTINEL + ")"},
                        {"bomba_fw": SENTINEL}):
            with self.subTest(fields=list(changes)):
                self._csv(stamp, **changes)
                result = worker.handle({"operation": "evaluate_iot_csv"})
                self.assertEqual(result.status, "invalid")
                self._safe(result)

    def test_erro_meteorologico_nao_reflete_message_ou_metadados(self):
        forecast = {"status": "error", "message": SENTINEL,
                    "data": {}, "source": {"retrieved_at": SENTINEL}}
        result = worker.handle({"operation": "evaluate_weather", "previsao": forecast})
        self.assertEqual(result.status, "error")
        self._safe(result)

    def test_orientacoes_de_fuso_idade_e_futuro_permanecem_publicas(self):
        now = datetime.now(timezone.utc)
        for stamp, hint in ((now.replace(tzinfo=None).isoformat(), "fuso"),
                            ((now - timedelta(days=1)).isoformat(), "historico"),
                            ((now + timedelta(hours=1)).isoformat(), "futuro")):
            with self.subTest(hint=hint):
                self._csv(stamp)
                result = worker.handle({"operation": "evaluate_iot_csv"})
                self.assertEqual(result.status, "invalid")
                self.assertIn(hint, result.message.casefold())
                self._safe(result)

    def test_falha_inesperada_no_protocolo_json_nao_emite_traceback(self):
        class Input(io.BytesIO):
            @property
            def buffer(self):
                return self

        output, error = io.StringIO(), io.StringIO()
        with patch.object(worker, "handle", side_effect=RuntimeError(SENTINEL)), \
                patch.object(sys, "stdin", Input(b'{"operation":"demo_iot","tipo":"normal"}')), \
                patch.object(sys, "stdout", output), patch.object(sys, "stderr", error):
            worker.main()
        response = json.loads(output.getvalue())
        self.assertEqual(response["status"], "error")
        self.assertNotIn(SENTINEL, output.getvalue() + error.getvalue())
        self.assertNotIn("Traceback", output.getvalue() + error.getvalue())


if __name__ == "__main__":
    unittest.main()
