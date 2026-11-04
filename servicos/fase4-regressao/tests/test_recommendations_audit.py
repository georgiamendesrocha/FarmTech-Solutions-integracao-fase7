"""Regressões pós-auditoria em cópias isoladas, sem leituras atuais de fazenda."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_frontend_safety import _copy_module


def _worker(scenario, root):
    os.chdir(root)
    sys.path.insert(0, str(root))
    os.environ.update(DB_PATH=str(root / "fixture.db"), FARMTECH_SIMULACAO="0", UMIDADE_LIMIAR="72.5")
    from scripts.init_db import inicializar_banco
    inicializar_banco(root / "fixture.db")
    from src.db import database as db
    from streamlit.testing.v1 import AppTest

    def run(*, bits=0, humidity=65.0, ph=6.5):
        with db.get_connection() as connection:
            connection.execute(
                "UPDATE leituras_sensores SET n=?, p=?, k=?, umidade=?, ph=?",
                (bits, bits, bits, humidity, ph),
            )
        return AppTest.from_file(str(root / "src/frontend/pages/5_Recomendacoes.py"), default_timeout=45).run()

    def submit(at, values=None, culture="rice"):
        at.selectbox[0].set_value(culture)
        if values is not None:
            for field, value in zip(at.slider, values):
                field.set_value(value)
        next(button for button in at.button if button.label == "Gerar Recomendacoes").click().run()
        return snapshot(at)

    def snapshot(at):
        return {
            "exceptions": [item.message for item in at.exception],
            "errors": [item.value for item in at.error],
            "warnings": [item.value for item in at.warning],
            "success": [item.value for item in at.success],
            "captions": [item.value for item in at.caption],
            "metrics": {item.label: item.value for item in at.metric},
            "sliders": {item.label: [item.value, item.proto.min, item.proto.max] for item in at.slider},
            "rows": db.get_previsoes(),
        }

    if scenario == "defaults":
        result = [snapshot(run(bits=bits)) for bits in (0, 1)]
    elif scenario == "comparisons":
        result = [submit(run(), values=values) for values in ((0, 5, 5), (140, 145, 205))]
    elif scenario == "near_means":
        means = db.media_cultura("rice")
        result = submit(run(), values=[round(means[key]) for key in ("n_med", "p_med", "k_med")])
    elif scenario == "humidity":
        result = [submit(run(humidity=value)) for value in (65.0, 72.5, 80.0)]
    elif scenario == "ph":
        result = [submit(run(ph=value)) for value in (4.5, 6.5, 9.0)]
    else:
        raise ValueError("Cenário desconhecido")
    print("AUDIT_RESULT " + json.dumps(result, ensure_ascii=True))


class RecommendationAuditTests(unittest.TestCase):
    def run_scenario(self, scenario):
        with tempfile.TemporaryDirectory(prefix="farmtech-recommendations-audit-") as directory:
            root = Path(directory) / "module"
            root.mkdir()
            _copy_module(root)
            environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", FARMTECH_SIMULACAO="0")
            result = subprocess.run(
                [sys.executable, "-X", "utf8", "-B", str(Path(__file__).resolve()), "--worker", scenario, str(root)],
                cwd=directory, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-4000:])
            return json.loads(next(line.removeprefix("AUDIT_RESULT ") for line in result.stdout.splitlines() if line.startswith("AUDIT_RESULT ")))

    def assert_valid(self, result):
        self.assertEqual(result["exceptions"], [])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["rows"], [])

    def test_npk_scenario_defaults_are_independent_of_binary_readings(self):
        for result in self.run_scenario("defaults"):
            self.assert_valid(result)
            for label, expected in {"N (kg/ha)": [40, 0, 140], "P (kg/ha)": [30, 5, 145], "K (kg/ha)": [20, 5, 205]}.items():
                self.assertEqual(result["sliders"][label], expected)
            captions = " ".join(result["captions"])
            self.assertIn("parametros de cenario editaveis", captions)
            self.assertIn("nao sao medicoes quantitativas", captions)
            self.assertIn("nao sao medicoes atuais de uma fazenda real", captions)

    def test_npk_at_input_bounds_describe_differences_without_prescribing_fertilizer(self):
        results = self.run_scenario("comparisons")
        for result, direction in zip(results, ("abaixo", "acima")):
            self.assert_valid(result)
            comparison = next(message for message in result["warnings"] if "Comparacao Descritiva de NPK" in message)
            self.assertIn(direction + " da media do dataset academico", comparison)
            self.assertNotIn("aumentar", comparison)
            self.assertNotIn("reduzir", comparison)
            self.assertNotIn("aplicacao", comparison)
            self.assertIn("Nao constituem recomendacao de adubacao", " ".join(result["captions"]))

    def test_npk_near_dataset_mean_does_not_claim_agronomic_adequacy(self):
        result = self.run_scenario("near_means")
        self.assert_valid(result)
        comparison = next(message for message in result["success"] if "Comparacao Descritiva de NPK" in message)
        self.assertIn("nao comprova adequacao agronomica", comparison)
        self.assertNotIn("faixa esperada", comparison)

    def test_humidity_uses_configured_threshold_without_operational_time(self):
        below, equal, above = self.run_scenario("humidity")
        for result in (below, equal, above):
            self.assert_valid(result)
            public = " ".join(result["warnings"] + result["success"] + result["captions"])
            self.assertIn("72.5%", public)
            self.assertNotIn("60.0%", public)
            self.assertNotIn("minutos", public)
            self.assertIn("rainfall e um proxy academico", public)
            self.assertIn("nao representa volume direto de irrigacao", public)
            self.assertIn("Proxy de necessidade hidrica", result["metrics"])
        self.assertTrue(any("Umidade Abaixo do Limiar" in message for message in below["warnings"]))
        for result in (equal, above):
            self.assertTrue(any("Umidade no Limiar ou Acima" in message for message in result["success"]))

    def test_ph_ranges_remain_indicative_without_input_doses(self):
        for result, expected in zip(self.run_scenario("ph"), ("pH Abaixo", "pH Dentro", "pH Acima")):
            self.assert_valid(result)
            public = " ".join(result["warnings"] + result["success"] + result["captions"])
            self.assertIn(expected, public)
            self.assertIn("6.0–7.0", public)
            self.assertIn("faixas de pH sao referencias indicativas", public)
            self.assertIn("prescricao validada de correcao do solo", public)
            self.assertNotIn("calagem", public)
            self.assertNotIn("enxofre", public)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker(sys.argv[2], Path(sys.argv[3]))
    else:
        unittest.main()
