"""Pré-condição da dashboard sem criar, substituir ou modificar bancos."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from farmtech_integracao import demo
from farmtech_integracao.workers.fase4_worker import prepare


class DatabasePreflightTests(unittest.TestCase):
    def test_missing_database_does_not_create_file_or_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-created" / "missing.db"
            result = demo.inspect_database(path)
            self.assertEqual(result.status, "unavailable")
            self.assertIn("python iniciar.py --preparar-demo", result.message)
            self.assertEqual(result.source["path"], str(path.resolve()))
            self.assertFalse(path.parent.exists())

    def test_empty_or_malformed_database_setting_has_clear_error(self):
        for path in ("", "   ", "\0invalid.db", None):
            with self.subTest(path=repr(path)):
                result = demo.inspect_database(path)
                self.assertEqual(result.status, "invalid")
                self.assertIn("DB_PATH", result.message)

    def test_relative_database_path_is_relative_to_fase4(self):
        with tempfile.TemporaryDirectory() as directory:
            service = Path(directory) / "fase4"
            destination = service / "relative.db"
            self.assertTrue(prepare(destination).ok)
            with patch.object(demo, "SERVICE_DIRS", {"fase4": service}):
                result = demo.inspect_database("relative.db")
            self.assertTrue(result.ok, result.message)
            self.assertEqual(result.source["path"], str(destination.resolve()))
            self.assertEqual(result.data["counts"]["leituras_sensores"], 153)

    def test_missing_dashboard_columns_are_rejected_without_modifying_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "incompatible.db"
            with closing(sqlite3.connect(path)) as connection, connection:
                for table in ("culturas", "sensores", "leituras_sensores", "amostras_agronomicas", "previsoes"):
                    connection.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
            before = path.read_bytes()
            result = demo.inspect_database(path)
            self.assertEqual(result.status, "error")
            self.assertIn("schema incompatível", result.message)
            self.assertEqual(path.read_bytes(), before)

    def test_valid_inspection_is_read_only_and_does_not_require_demo_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.db"
            self.assertTrue(prepare(path).ok)
            # Um banco operacional pode ter outra quantidade de leituras.
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute("""INSERT INTO leituras_sensores
                    (sensor_id, ts, umidade, temp_c, ldr, ph, n, p, k, bomba_fw)
                    SELECT sensor_id, ts, umidade, temp_c, ldr, ph, n, p, k, bomba_fw
                    FROM leituras_sensores WHERE id = 1""")
            before = path.read_bytes()
            result = demo.inspect_database(path)
            self.assertTrue(result.ok, result.message)
            self.assertEqual(result.data["counts"]["leituras_sensores"], 154)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual([item.name for item in Path(directory).iterdir()], ["existing.db"])


if __name__ == "__main__":
    unittest.main()
