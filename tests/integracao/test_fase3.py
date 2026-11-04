"""Consultas Fase 3: somente CSV preservado e Oracle simulado."""

import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from farmtech_integracao.contracts import Result
from farmtech_integracao import fase3
from farmtech_integracao.workers import fase3_worker as worker


class Fase3Tests(unittest.TestCase):
    def test_public_query_rejects_arbitrary_paths_and_invalid_limits(self):
        with patch.object(fase3, "run_json_worker") as run:
            for source, limit in (("other.csv", 1), ("oracle", 0), ("csv", 1001),
                                  ("csv", True), ("csv", 2.5)):
                self.assertEqual("invalid", fase3.query_sensors(source, limit=limit).status)
            run.assert_not_called()

    def test_public_query_delegates_to_fixed_worker(self):
        expected = Result("ok", "consulta")
        with patch.object(fase3, "run_json_worker", return_value=expected) as run:
            self.assertIs(expected, fase3.query_sensors("csv", limit=12, timeout=10))
        run.assert_called_once_with("fase3", {"operation": "query_sensors", "source": "csv", "limit": 12}, timeout=10, python=None)

    def test_availability_checks_no_connection_or_worker(self):
        with patch.object(fase3, "run_json_worker") as run, patch.dict(os.environ, {}, clear=True):
            result = fase3.availability()
        self.assertTrue(result.data["csv_available"])
        self.assertFalse(result.data["oracle_configured"])
        run.assert_not_called()

    def test_csv_query_preserves_original_and_limits_result(self):
        before = worker.CSV_PATH.read_bytes()
        result = worker.handle({"operation": "query_sensors", "source": "csv", "limit": 7})
        self.assertEqual("ok", result.status, result.message)
        self.assertEqual(7, result.data["count"])
        self.assertEqual("csv", result.source["kind"])
        self.assertEqual(before, worker.CSV_PATH.read_bytes())
        self.assertEqual({"instante", "umidade", "temp_c", "ph_corr", "n", "p", "k", "bomba_fw", "irrigacao"}, set(result.data["rows"][0]))
        self.assertIn("T", result.data["rows"][0]["instante"])
        self.assertLess(len(json.dumps(result.as_dict()).encode()), worker.MAX_RESPONSE_BYTES)

    def test_csv_process_round_trip(self):
        before = worker.CSV_PATH.read_bytes()
        result = fase3.query_sensors("csv", limit=3, python=sys.executable)
        self.assertEqual("ok", result.status, result.message)
        self.assertEqual(3, result.data["count"])
        self.assertEqual("csv", result.source["kind"])
        self.assertEqual(before, worker.CSV_PATH.read_bytes())

    def test_page_opens_without_query_and_reports_process_timeout(self):
        from streamlit.testing.v1 import AppTest

        page = Path(__file__).resolve().parents[2] / "servicos" / "fase4-regressao" / "src" / "frontend" / "pages" / "11_Oracle_Consultas.py"
        with patch.object(fase3, "query_sensors", return_value=Result("error", "Tempo limite atingido.", source={"phase": "fase3"})) as query:
            app = AppTest.from_file(str(page)).run()
            self.assertFalse(app.exception)
            query.assert_not_called()
            app.button[0].click().run()
            query.assert_called_once_with("csv", limit=200)
            self.assertFalse(app.exception)
            self.assertEqual("Tempo limite atingido.", app.warning[0].value)

    def test_page_plots_csv_only_after_explicit_query(self):
        from streamlit.testing.v1 import AppTest

        result = worker.handle({"operation": "query_sensors", "source": "csv", "limit": 3})
        page = Path(__file__).resolve().parents[2] / "servicos" / "fase4-regressao" / "src" / "frontend" / "pages" / "11_Oracle_Consultas.py"
        with patch.object(fase3, "query_sensors", return_value=result):
            app = AppTest.from_file(str(page)).run()
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(4, len(app.get("plotly_chart")))
        self.assertEqual(3, len(app.dataframe[0].value))
        self.assertTrue(any("CSV preservado" in item.value for item in app.caption))

    def test_extra_payload_cannot_choose_file_or_sql(self):
        with patch.object(worker, "_read_csv") as read:
            for field in ("path", "sql", "dsn"):
                result = worker.handle({"operation": "query_sensors", "source": "csv", "limit": 2, field: "ignored"})
                self.assertEqual("invalid", result.status)
            read.assert_not_called()

    def test_missing_oracle_configuration_does_not_connect(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(worker, "_read_oracle") as read:
            result = worker.handle({"operation": "query_sensors", "source": "oracle", "limit": 2})
        self.assertEqual("unavailable", result.status)
        self.assertEqual("oracle", result.source["kind"])
        read.assert_not_called()

    def test_oracle_exception_and_credentials_are_not_returned(self):
        configured = {name: "sensitive-placeholder" for name in ("ORACLE_USER", "ORACLE_PASS", "ORACLE_DSN")}
        with patch.dict(os.environ, configured, clear=True), patch.object(worker, "_read_oracle", side_effect=RuntimeError("private-error-detail")):
            result = worker.handle({"operation": "query_sensors", "source": "oracle", "limit": 2})
        serialized = json.dumps(result.as_dict())
        self.assertEqual("unavailable", result.status)
        self.assertNotIn("sensitive-placeholder", serialized)
        self.assertNotIn("private-error-detail", serialized)

    def test_oracle_uses_only_fixed_parameterized_select_and_no_commit(self):
        driver = MagicMock()
        connection = driver.connect.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        columns = ("INSTANTE", "TS_ISO", "UMIDADE", "TEMP_C", "PH_CORR", "N", "P", "K", "BOMBA_FW")
        cursor.description = [(name,) for name in columns]
        cursor.fetchmany.return_value = [("2026-01-01T10:00:00", "2026-01-01T10:00:00", 42, 25, 6.4, 1, 0, 1, 0)]
        configured = {name: "mock-only" for name in ("ORACLE_USER", "ORACLE_PASS", "ORACLE_DSN")}
        with patch.dict(os.environ, configured, clear=True), patch.dict(sys.modules, {"oracledb": driver}):
            result = worker.handle({"operation": "query_sensors", "source": "oracle", "limit": 2})
        self.assertEqual("ok", result.status, result.message)
        self.assertEqual("oracle", result.source["kind"])
        cursor.execute.assert_called_once_with(worker.ORACLE_SQL, {"limit": 2})
        cursor.fetchmany.assert_called_once_with(2)
        self.assertTrue(worker.ORACLE_SQL.startswith("SELECT "))
        for forbidden in ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "MERGE"):
            self.assertNotIn(forbidden, worker.ORACLE_SQL)
        connection.commit.assert_not_called()

    def test_worker_import_does_not_load_historical_src_services(self):
        self.assertNotIn("src.api.main", sys.modules)
        self.assertNotIn("src.api.collector", sys.modules)
        self.assertNotIn("src.frontend.app", sys.modules)


if __name__ == "__main__":
    unittest.main()
