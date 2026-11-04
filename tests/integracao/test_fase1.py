"""Exercita reutilização da Fase 1 e preservação de seus CSVs."""

import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from farmtech_integracao import fase1
from farmtech_integracao.contracts import Result
from farmtech_integracao.workers import fase1_worker

ROOT = Path(__file__).resolve().parents[2]


class Fase1Tests(unittest.TestCase):
    def test_real_calculation_preserves_historical_csvs(self):
        files = [ROOT / "servicos" / "fase1-gestao" / "config" / name
                 for name in ("dados_fazenda.csv", "insumos_por_talhao.csv")]
        before = {file: hashlib.sha256(file.read_bytes()).hexdigest() for file in files}
        result = fase1.calculate_plot("rectangle", [10, 20], crop="Soja", spacing=0.5)
        self.assertTrue(result.ok, result.message)
        self.assertAlmostEqual(result.data["area_m2"], 200)
        self.assertAlmostEqual(result.data["hectares"], 0.02)
        self.assertEqual(result.data["estimated_line_count"], 20)
        curbix = next(row for row in result.data["products"] if row["product"] == "Curbix")
        self.assertAlmostEqual(curbix["quantity"], 0.015)
        self.assertAlmostEqual(curbix["total_cost"], 4.80)
        self.assertAlmostEqual(curbix["dose_per_m"], 0.0375)
        self.assertFalse(result.source["persistence"])
        self.assertEqual(before, {file: hashlib.sha256(file.read_bytes()).hexdigest() for file in files})

    def test_worker_rejects_unsafe_or_inconsistent_inputs(self):
        base = {"operation": "calculate", "shape": "rectangle", "measurements": [10, 20],
                "crop": "Soja", "spacing": 0.5}
        mutations = [{"measurements": [float("nan"), 20]}, {"measurements": [-1, 20]},
                     {"measurements": [10]}, {"measurements": [True, 20]},
                     {"spacing": 0}, {"spacing": float("inf")}, {"crop": "desconhecida"},
                     {"shape": "../../../farm"}, {"operation": "write_csv"}]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                fase1_worker.calculate({**base, **mutation})

    def test_invalid_triangle_cannot_produce_a_result(self):
        result = fase1.calculate_plot("triangle", [1, 2, 10])
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "invalid")

    def test_regular_polygon_validation_and_original_area(self):
        with self.assertRaises(ValueError):
            fase1_worker.calculate({"operation": "calculate", "shape": "pentagon", "measurements": [10, 10, 10, 10, 9]})
        result = fase1.calculate_plot("pentagon", [10] * 5)
        self.assertTrue(result.ok, result.message)
        self.assertAlmostEqual(result.data["area_m2"], 172.0477400589)

    def test_worker_protocol_preserves_portuguese_unicode(self):
        result = fase1.calculate_plot("retângulo", [10, 20], crop="Café")
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.data["crop"], "Café")
        self.assertEqual(result.data["geometry"], "Retângulo")

    def test_adapter_uses_fixed_phase_and_explicit_operation(self):
        expected = Result("ok", "fixture")
        with patch.object(fase1, "run_json_worker", return_value=expected) as run:
            self.assertIs(fase1.calculate_plot("circle", [10], crop="Milho", spacing=1), expected)
        self.assertEqual(run.call_args.args[0], "fase1")
        self.assertEqual(run.call_args.args[1]["operation"], "calculate")


if __name__ == "__main__":
    unittest.main()
