"""Integridade de históricos e publicação que recusa substituição."""

import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from farmtech_integracao import demo
from farmtech_integracao.runtime import PROJECT_ROOT
from farmtech_integracao.workers.fase4_worker import publish_new, prepare


class DemoIntegrityTests(unittest.TestCase):
    def test_reconstructed_database_is_created_in_isolated_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)/"demo.db"
            result = prepare(destination)
            self.assertTrue(result.ok, result.message)
            self.assertEqual(result.data["counts"]["leituras_sensores"], 153)
            self.assertTrue(demo.inspect_database(destination).source["reconstructed"])
            before = destination.read_bytes()
            self.assertFalse(prepare(destination).ok)
            self.assertEqual(destination.read_bytes(), before)
            self.assertEqual([item.name for item in Path(directory).iterdir()], ["demo.db"])

    def test_all_preserved_payloads_match_baseline(self):
        files = json.loads((PROJECT_ROOT / "docs" / "integridade-int02.json").read_text(encoding="utf-8"))["files"]
        ui = json.loads((PROJECT_ROOT / "docs" / "integridade-ui-lote1.json").read_text(encoding="utf-8"))
        self.assertEqual(ui["baseline"], "integridade-int02.json")
        self.assertEqual(set(ui["files"]), {
            "servicos/fase4-regressao/src/frontend/pages/1_Sensores_IoT.py",
            "servicos/fase4-regressao/src/frontend/pages/2_Analise_Exploratoria.py",
            "servicos/fase4-regressao/src/frontend/pages/3_Pipeline_ML.py",
            "servicos/fase4-regressao/src/frontend/pages/4_Previsao.py",
            "servicos/fase4-regressao/src/frontend/pages/5_Recomendacoes.py",
            "servicos/fase4-regressao/src/frontend/pages/6_Historico_Previsoes.py",
            "servicos/fase4-regressao/src/frontend/pages/7_Dados_Oficiais.py",
        })
        self.assertTrue(set(ui["files"]).issubset(files))
        self.assertGreater(len(files), 100)
        for relative, expected in files.items():
            with self.subTest(path=relative):
                expected = ui["files"].get(relative, expected)
                self.assertEqual(hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest(), expected)

    def test_publication_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            stage, destination = Path(directory)/"stage.db", Path(directory)/"existing.db"
            stage.write_bytes(b"new")
            destination.write_bytes(b"preserved")
            with self.assertRaises(FileExistsError):
                publish_new(stage, destination)
            self.assertEqual(destination.read_bytes(), b"preserved")

    def test_missing_and_invalid_database_are_not_recreated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"missing.db"
            self.assertEqual(demo.inspect_database(path).status, "unavailable")
            self.assertFalse(path.exists())
            path.write_bytes(b"not a database")
            self.assertEqual(demo.inspect_database(path).status, "error")
            self.assertEqual(path.read_bytes(), b"not a database")

    def test_demo_command_refuses_existing_destination_before_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"demo.db"
            path.write_bytes(b"preserved")
            with patch.object(demo, "demo_path", return_value=path), patch.object(demo, "run_json_worker") as worker:
                self.assertEqual(demo.prepare_demo().status, "unavailable")
                worker.assert_not_called()

    def test_integrated_configuration_disables_simulation_without_creating_database(self):
        import os
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"FARMTECH_INTEGRACAO":"1", "FARMTECH_SIMULACAO":"1"}, clear=True):
            path=Path(directory)/"missing.db"
            with patch.object(demo,"demo_path",return_value=path):
                demo.configure_dashboard()
            self.assertEqual(os.environ["FARMTECH_SIMULACAO"], "0")
            self.assertEqual(os.environ["DB_PATH"], str(path))
            self.assertFalse(path.exists())

    def test_integrated_configuration_preserves_explicit_database_without_creating_it(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "explicit.db"
            with patch.dict(os.environ, {"FARMTECH_INTEGRACAO": "1", "DB_PATH": str(path)}, clear=True):
                demo.configure_dashboard()
                self.assertEqual(os.environ["DB_PATH"], str(path))
                self.assertEqual(os.environ["FARMTECH_SIMULACAO"], "0")
                self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
