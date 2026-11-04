import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.data_sources import SIDRA_OUTPUT_COLUMNS
from src.ml import productivity


def _snapshot(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*")
        if path.is_file()
    }


def _fixture(path: Path, *, declining_test: bool = False) -> None:
    rows = []
    for year in range(1990, 2026):
        value = 3000 + (year - 1990) * 55
        if declining_test and year >= 2021:
            value = 4300 - (year - 2021) * 300
        rows.append({
            "codigo_geografico": "1", "geografia": "Brasil",
            "municipio": None, "uf": None, "nivel_geografico": "brasil",
            "codigo_cultura": "2692", "cultura": "Arroz (em casca)",
            "ano": year, "rendimento_kg_ha": value, "unidade": "kg/ha",
        })
    pd.DataFrame(rows, columns=SIDRA_OUTPUT_COLUMNS).to_csv(path, index=False)


class ProductivityAuditTests(unittest.TestCase):
    def _assert_refused(self, models_dir: Path | None = None) -> None:
        arguments = {"data_path": Path("missing-productivity-audit.csv")}
        if models_dir is not None:
            arguments["models_dir"] = models_dir
        with (
            patch.object(productivity, "carregar_sidra") as load,
            patch.object(productivity.joblib, "dump") as dump,
            patch.object(Path, "mkdir") as mkdir,
            patch.object(Path, "write_text") as write_text,
            patch.object(pd.DataFrame, "to_csv") as to_csv,
        ):
            with self.assertRaisesRegex(RuntimeError, "preservados"):
                productivity.avaliar_produtividade(**arguments)
            for operation in (load, dump, mkdir, write_text, to_csv):
                operation.assert_not_called()

    def test_packaged_directory_and_aliases_are_refused_without_changes(self):
        preserved = productivity.MODELS_DIR
        before = _snapshot(preserved)
        for destination in (
            None,
            preserved,
            Path(os.path.relpath(preserved)),
            preserved.parent / "models" / ".." / "models",
            preserved / "audit-output-must-not-be-created",
        ):
            with self.subTest(destination=destination):
                self._assert_refused(destination)
        self.assertEqual(_snapshot(preserved), before)

    def test_directory_link_to_preserved_fixture_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            preserved = root / "src" / "ml" / "models"
            preserved.mkdir(parents=True)
            (preserved / productivity.MODEL_FILENAME).write_bytes(b"preserved-model")
            before = _snapshot(preserved)
            alias = root / "external-alias"
            if os.name == "nt":
                import _winapi

                _winapi.CreateJunction(str(preserved), str(alias))
            else:
                alias.symlink_to(preserved, target_is_directory=True)
            with patch.object(productivity, "ROOT", root):
                self._assert_refused(alias)
                self._assert_refused(alias / "nested")
            self.assertEqual(_snapshot(preserved), before)

    def test_external_hardlink_to_any_preserved_artifact_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            preserved = root / "src" / "ml" / "models"
            preserved.mkdir(parents=True)
            artifact = preserved / "historical-model.joblib"
            artifact.write_bytes(b"preserved-model")
            before = _snapshot(preserved)
            output = root / "external-output"
            output.mkdir()
            os.link(artifact, output / productivity.MODEL_FILENAME)
            with patch.object(productivity, "ROOT", root):
                self._assert_refused(output)
            self.assertEqual(_snapshot(preserved), before)

    def test_external_temporary_directory_can_produce_validated_forecast(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_path = root / "fixture.csv"
            _fixture(data_path)
            output = root / "external-output"
            results = productivity.avaliar_produtividade(data_path, output)
            self.assertTrue(results["previsao_disponivel"])
            forecasts = productivity.carregar_previsoes_produtividade(output)
            self.assertIsNotNone(forecasts)
            self.assertEqual(forecasts["ano_previsao"].tolist(), [2026])

    def test_failed_temporal_performance_keeps_forecasts_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_path = root / "fixture.csv"
            _fixture(data_path, declining_test=True)
            output = root / "external-output"
            results = productivity.avaliar_produtividade(data_path, output)
            crop = results["culturas"]["2692"]
            self.assertEqual(crop["metodo_selecionado"], "Regressão linear temporal")
            self.assertLessEqual(crop["teste_temporal"]["metodo_selecionado"]["r2"], 0)
            self.assertFalse(results["previsao_disponivel"])
            self.assertFalse(crop["previsao_disponivel"])
            self.assertIsNone(productivity.carregar_previsoes_produtividade(output))
            metadata = json.loads(
                (output / productivity.METADATA_FILENAME).read_text(encoding="utf-8")
            )
            self.assertFalse(metadata["previsao_disponivel"])
            self.assertEqual(metadata["previsao_para"], [])


if __name__ == "__main__":
    unittest.main()
