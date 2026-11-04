"""Histórico acima do limite de tela, sempre com SQLite e interface isolados."""

import csv
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_frontend_safety import _copy_module


def _history_fixture(path, count=650):
    with sqlite3.connect(path) as connection:
        connection.execute("""
            CREATE TABLE previsoes (
                id INTEGER PRIMARY KEY, ts TEXT NOT NULL, modelo TEXT NOT NULL,
                target TEXT NOT NULL, valor_previsto REAL NOT NULL,
                parametros_entrada TEXT NOT NULL
            )
        """)
        for identity in range(1, count + 1):
            instant = datetime(2026, 11, 1, tzinfo=timezone.utc) + timedelta(seconds=identity // 2)
            # Pares têm o mesmo instante, com formatos históricos diferentes.
            timestamp = (instant.isoformat() if identity % 2 else
                         instant.replace(tzinfo=None).isoformat(sep=" "))
            parameters = ({"label": "apple"}, {"cultura": "rice"},
                          {"label": "banana", "cultura": "banana"})[identity % 3]
            connection.execute(
                "INSERT INTO previsoes VALUES (?, ?, 'Ridge', ?, 6.2, ?)",
                (identity, timestamp, "ph" if identity % 2 else "rainfall", json.dumps(parameters)),
            )


def _worker(root):
    os.chdir(root)
    sys.path.insert(0, str(root))
    os.environ["DB_PATH"] = str(root / "fixture.db")
    os.environ["FARMTECH_SIMULACAO"] = "0"
    _history_fixture(root / "fixture.db")

    import streamlit as st
    from streamlit.testing.v1 import AppTest

    def snapshot(at):
        return {
            "exceptions": [item.message for item in at.exception],
            "errors": [item.value for item in at.error],
            "captions": [item.value for item in at.caption],
            "metrics": {item.label: item.value for item in at.metric},
            "table": at.dataframe[0].value.to_dict("records"),
            "downloads": len(at.get("download_button")),
        }

    with patch("streamlit.download_button", wraps=st.download_button) as download:
        at = AppTest.from_file(str(root / "src/frontend/pages/6_Historico_Previsoes.py"),
                               default_timeout=45).run()
        initial = snapshot(at)
        initial["csv"] = download.call_args.kwargs["data"].decode("utf-8")
        at.multiselect[0].set_value(["ph"])
        at.slider[0].set_value(500).run()
        filtered = snapshot(at)
        filtered["csv"] = download.call_args.kwargs["data"].decode("utf-8")

    print("F402_HISTORY " + json.dumps({"initial": initial, "filtered": filtered}, ensure_ascii=False))


class HistoryAuditTests(unittest.TestCase):
    def test_sqlite_count_includes_predictions_beyond_loaded_limit(self):
        from src.db import database as db

        with tempfile.TemporaryDirectory(prefix="farmtech-history-db-") as temporary:
            path = Path(temporary) / "fixture.db"
            _history_fixture(path)
            with patch.object(db, "DB_PATH", str(path)):
                self.assertEqual(db.get_total_previsoes(), 650)
                rows = db.get_previsoes(limite=500)
                self.assertEqual(len(rows), 500)
                self.assertEqual([row["id"] for row in rows], list(range(650, 150, -1)))
                self.assertEqual(db.get_previsoes(limite=0), [])
                self.assertEqual(db.get_total_previsoes(), 650)

    def test_count_does_not_create_missing_database(self):
        from src.db import database as db

        with tempfile.TemporaryDirectory(prefix="farmtech-history-missing-") as temporary:
            path = Path(temporary) / "missing.db"
            with patch.object(db, "DB_PATH", str(path)), self.assertRaises(sqlite3.OperationalError):
                db.get_total_previsoes()
            self.assertFalse(path.exists())

    def test_interface_distinguishes_total_and_loaded_and_preserves_filtered_csv(self):
        with tempfile.TemporaryDirectory(prefix="farmtech-history-ui-") as temporary:
            root = Path(temporary) / "module"
            root.mkdir()
            _copy_module(root)
            result = subprocess.run(
                [sys.executable, "-X", "utf8", "-B", str(Path(__file__).resolve()), "--worker", str(root)],
                cwd=temporary,
                env=dict(os.environ, FARMTECH_SIMULACAO="0", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1"),
                capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-4000:])
            payload = next(line.removeprefix("F402_HISTORY ") for line in result.stdout.splitlines()
                           if line.startswith("F402_HISTORY "))
            snapshots = json.loads(payload)

        for name, snapshot in snapshots.items():
            with self.subTest(view=name):
                self.assertEqual(snapshot["exceptions"], [])
                self.assertEqual(snapshot["errors"], [])
                self.assertEqual(snapshot["metrics"]["Total de previsoes"], "650")
                self.assertTrue(any("500 previsoes mais recentes carregadas de 650" in caption
                                    for caption in snapshot["captions"]))
                self.assertEqual(snapshot["downloads"], 1)
                exported = list(csv.DictReader(io.StringIO(snapshot["csv"])))
                expected = list(range(650, 550, -1)) if name == "initial" else list(range(649, 150, -2))
                self.assertEqual([row["ID"] for row in snapshot["table"]], expected)
                self.assertEqual([int(row["id"]) for row in exported], expected)
                self.assertEqual({row["Cultura"] for row in snapshot["table"]}, {"apple", "rice", "banana"})
                self.assertEqual([row["cultura"] for row in exported],
                                 [row["Cultura"] for row in snapshot["table"]])
                if name == "filtered":
                    self.assertEqual({row["target"] for row in exported}, {"ph"})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker(Path(sys.argv[2]))
    else:
        unittest.main()
