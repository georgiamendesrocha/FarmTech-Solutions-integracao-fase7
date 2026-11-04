"""Regressões F4-02: somente bancos/CSVs temporários, nunca o SQLite do módulo."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import init_db
from src.db import database as db


ORIGINAL = dict(n=60, p=55, k=44, temperatura=25, ph=6.5, cultura="apple")
PH = dict(N=60, P=55, K=44, temperature=25, humidity=70, rainfall=100, label="apple")
READING = dict(umidade=70, temp_c=25, ldr=1800, ph=6.5, n=0, p=1, k=0, bomba_fw=0)


class DatabaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="farmtech-db-tests-")
        self.root = Path(self.temporary.name)
        self.database = self.root / "isolado.db"
        self.irrigation = self.root / "irrigacao.csv"
        self.agriculture = self.root / "agricola.csv"
        self.irrigation.write_text(
            "ts_iso,umidade,temp_c,ldr,ph_corr,N,P,K,bomba_fw\n"
            "2026-05-03T20:03:40,70,25,1800,6.5,0,1,0,0\n", encoding="utf-8")
        self.agriculture.write_text(
            "N,P,K,temperature,humidity,ph,rainfall,label\n"
            "60,55,44,25,70,6.5,100,apple\n", encoding="utf-8")
        self.path_patch = patch.object(db, "DB_PATH", str(self.database))
        self.path_patch.start()
        self.reinitialize()

    def tearDown(self):
        self.path_patch.stop()
        self.temporary.cleanup()

    def reinitialize(self, **kwargs):
        return init_db.inicializar_banco(self.database, self.irrigation, self.agriculture, **kwargs)

    def predict(self):
        db.inserir_previsao("Ridge", "ph", 6.2, json.dumps(PH))

    def state(self):
        with db.get_connection() as conn:
            return tuple((table, tuple(tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY id")))
                         for table in db.SCHEMA_COLUMNS)

    def test_full_original_csv_ingestion_is_isolated_and_integral(self):
        other = self.root / "csvs-originais-copy.db"
        result = init_db.inicializar_banco(other)
        self.assertEqual(result["contagens"], dict(culturas=22, sensores=1, leituras_sensores=153,
                                                amostras_agronomicas=2200, previsoes=0))
        self.assertEqual(db.validar_banco(other), result["contagens"])

    def test_missing_csv_preserves_all_previous_records(self):
        self.predict()
        before = self.state()
        self.irrigation.unlink()
        with self.assertRaises(FileNotFoundError):
            self.reinitialize()
        self.assertEqual(self.state(), before)

    def test_invalid_second_csv_preserves_previous_records(self):
        self.predict()
        before = self.state()
        self.agriculture.write_text(self.agriculture.read_text() + "NaN,55,44,25,70,6.5,100,apple\n")
        with self.assertRaises(ValueError):
            self.reinitialize()
        self.assertEqual(self.state(), before)

    def test_duplicated_csv_columns_are_rejected_without_mutation(self):
        before = self.state()
        self.agriculture.write_text("N,P,K,temperature,humidity,ph,rainfall,label,label\n60,55,44,25,70,6.5,100,apple,rice\n")
        with self.assertRaises(ValueError):
            self.reinitialize()
        self.assertEqual(self.state(), before)

    def test_cli_import_error_is_nonzero_and_contains_no_internal_path_or_success(self):
        self.predict()
        before = self.state()
        private = self.root / "private-missing.csv"
        stderr, stdout = io.StringIO(), io.StringIO()
        with patch.object(init_db, "CSV_IRRIGACAO", private), patch.object(init_db, "DB_PATH", str(self.database)):
            with redirect_stderr(stderr), redirect_stdout(stdout):
                self.assertEqual(init_db.main(), 1)
        self.assertNotIn(str(private), stderr.getvalue())
        self.assertNotIn("[OK]", stdout.getvalue())
        self.assertEqual(self.state(), before)

    def test_invalid_sensor_row_is_rejected_instead_of_silently_skipped(self):
        before = self.state()
        self.irrigation.write_text(self.irrigation.read_text() + "2026-05-03T20:04:40,101,25,1800,6.5,0,1,0,0\n")
        with self.assertRaises(ValueError):
            self.reinitialize()
        self.assertEqual(self.state(), before)

    def test_snapshot_failure_preserves_all_records(self):
        self.predict()
        before = self.state()
        with patch.object(init_db, "_snapshot", side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                self.reinitialize()
        self.assertEqual(self.state(), before)

    def test_trigger_failure_rolls_back_deletes_and_inserts(self):
        self.predict()
        with db.get_connection() as conn:
            conn.execute("CREATE TRIGGER rejeitar BEFORE INSERT ON amostras_agronomicas BEGIN SELECT RAISE(ABORT,'fixture'); END")
        before = self.state()
        with self.assertRaises(sqlite3.IntegrityError):
            self.reinitialize()
        self.assertEqual(self.state(), before)
        with db.get_connection() as conn:
            self.assertIsNotNone(conn.execute("SELECT name FROM sqlite_master WHERE name='rejeitar'").fetchone())

    def test_existing_wal_and_open_connection_are_preserved_and_backup_is_readable(self):
        observer = sqlite3.connect(self.database)
        try:
            self.assertEqual(observer.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
            observer.execute("SELECT COUNT(*) FROM previsoes").fetchone()
            self.predict()
            before = self.state()
            self.assertTrue(Path(str(self.database) + "-wal").exists())
            identity = self.database.stat().st_ino
            result = self.reinitialize()
            self.assertEqual(self.database.stat().st_ino, identity)
            self.assertEqual(observer.execute("SELECT COUNT(*) FROM previsoes").fetchone()[0], 0)
            self.assertEqual(db.validar_banco(result["backup"])["previsoes"], 1)
            with patch.object(db, "DB_PATH", result["backup"]):
                self.assertEqual(self.state(), before)
        finally:
            observer.close()

    def test_write_lock_failure_preserves_records(self):
        self.predict()
        before = self.state()
        blocker = sqlite3.connect(self.database)
        try:
            blocker.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                self.reinitialize(timeout=0.05)
        finally:
            blocker.rollback()
            blocker.close()
        self.assertEqual(self.state(), before)

    def test_commit_lock_failure_rolls_back_and_preserves_records(self):
        self.predict()
        before = self.state()
        reader = sqlite3.connect(self.database)
        try:
            reader.execute("BEGIN")
            reader.execute("SELECT * FROM previsoes").fetchall()
            with self.assertRaises(sqlite3.OperationalError):
                self.reinitialize(timeout=0.05)
        finally:
            reader.rollback()
            reader.close()
        self.assertEqual(self.state(), before)

    def test_invalid_existing_database_is_not_overwritten(self):
        broken = self.root / "broken.db"
        broken.write_bytes(b"not sqlite")
        original = broken.read_bytes()
        with self.assertRaises(sqlite3.DatabaseError):
            init_db.inicializar_banco(broken, self.irrigation, self.agriculture)
        self.assertEqual(broken.read_bytes(), original)

    def test_pair_prediction_transaction_rolls_back_on_second_insert(self):
        with db.get_connection() as conn:
            conn.execute("CREATE TRIGGER rejeitar_umidade BEFORE INSERT ON previsoes WHEN NEW.target='humidity' BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            db.inserir_previsoes([("Ridge", "rainfall", 100, json.dumps(ORIGINAL)),
                                  ("Ridge", "humidity", 70, json.dumps(ORIGINAL))])
        self.assertEqual(db.get_previsoes(), [])

    def test_pair_prediction_is_committed_and_last_id_breaks_tie(self):
        db.inserir_previsoes([("Ridge", "rainfall", 100, json.dumps(ORIGINAL)),
                              ("Ridge", "humidity", 70, json.dumps(ORIGINAL))])
        rows = db.get_previsoes()
        self.assertEqual([r["target"] for r in rows], ["humidity", "rainfall"])
        self.assertEqual(rows[0]["ts"], rows[1]["ts"])

    def test_prediction_history_uses_utc_and_id_without_rewriting_historical_values(self):
        dates = ["2026-11-01T01:00:00", "2026-11-01 22:00:00", "2026-11-02T01:00:00+03:00"]
        with db.get_connection() as conn:
            for date in dates:
                conn.execute("INSERT INTO previsoes(ts,modelo,target,valor_previsto,parametros_entrada) VALUES (?,'Ridge','ph',6.2,'{}')", (date,))
        rows = db.get_previsoes()
        self.assertEqual([r["ts"] for r in rows], dates[::-1])

    def test_sensor_history_uses_utc_and_microseconds_and_id(self):
        dates = ["2026-11-01T01:00:00", "2026-11-01 22:00:00.000001", "2026-11-02T01:00:00.000001+03:00"]
        with db.get_connection() as conn:
            for date in dates:
                conn.execute("INSERT INTO leituras_sensores(sensor_id,ts,umidade,temp_c,ldr,ph,n,p,k,bomba_fw) VALUES (1,?,70,25,1800,6.5,0,1,0,0)", (date,))
        self.assertEqual(db.get_ultima_leitura()["ts"], dates[-1])
        self.assertEqual([r["ts"] for r in db.get_leituras(3)], dates[::-1])

    def test_connections_close_and_roll_back_after_exception(self):
        connection = None
        with self.assertRaises(RuntimeError):
            with db.get_connection() as conn:
                connection = conn
                conn.execute("DELETE FROM amostras_agronomicas")
                raise RuntimeError("fixture")
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
        self.assertEqual(db.status_banco()["amostras_agronomicas"], 1)

    def test_missing_and_empty_schema_rejected_without_creating_file(self):
        missing = self.root / "no-parent" / "missing.db"
        with self.assertRaises(sqlite3.Error):
            db.validar_banco(missing)
        self.assertFalse(missing.exists())
        with patch.object(db, "DB_PATH", str(missing)):
            with self.assertRaises(sqlite3.Error):
                db.get_culturas()
        self.assertFalse(missing.parent.exists())
        empty = self.root / "empty.db"
        sqlite3.connect(empty).close()
        with self.assertRaises(sqlite3.DatabaseError):
            db.validar_banco(empty)

    def test_schema_missing_constraints_is_rejected(self):
        broken = self.root / "no-check.db"
        conn = sqlite3.connect(broken)
        conn.executescript(init_db.DDL.replace("CHECK (bomba_fw IN (0, 1))", ""))
        conn.close()
        with self.assertRaises(sqlite3.DatabaseError):
            db.validar_banco(broken)

    def test_relative_path_does_not_depend_on_consumer_cwd(self):
        before = Path.cwd()
        try:
            os.chdir(self.root)
            self.assertEqual(db.resolve_db_path("src/db/farmtech.db"), db.ROOT / "src/db/farmtech.db")
            self.assertEqual(db.resolve_db_path(self.database), self.database)
        finally:
            os.chdir(before)
        self.assertFalse((self.root / "src").exists())

    def test_sensor_valid_zero_and_invalid_values_do_not_partially_write(self):
        before = db.status_banco()["leituras_sensores"]
        db.inserir_leitura_simulada(**READING)
        for field, value in (("umidade", -1), ("umidade", 101), ("temp_c", 999), ("ph", 20),
                             ("ldr", math.inf), ("umidade", math.nan), ("n", 2), ("p", None),
                             ("k", True), ("bomba_fw", "1"), ("sensor_id", 0)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    db.inserir_leitura_simulada(**dict(READING, **{field: value}))
        self.assertEqual(db.status_banco()["leituras_sensores"], before + 1)

    def test_prediction_invalid_json_domains_and_values_are_rejected_before_insert(self):
        for target, value, params in (
            ("ph", math.nan, json.dumps(PH)), ("ph", math.inf, json.dumps(PH)),
            ("ph", 15, json.dumps(PH)), ("humidity", 101, json.dumps(ORIGINAL)),
            ("rainfall", -1, json.dumps(ORIGINAL)), ("unknown", 2, json.dumps(ORIGINAL)),
            ("ph", 6.2, "{"), ("ph", 6.2, "[]"), ("ph", 6.2, '{"N":NaN}'),
            ("ph", 6.2, json.dumps(dict(PH, humidity=101))),
            ("ph", 6.2, json.dumps(dict(PH, label="unknown"))),
            ("ph", 6.2, json.dumps(dict(PH, cultura="rice"))),
            ("rainfall", 100, json.dumps(dict(ORIGINAL, n=141))),
        ):
            with self.subTest(target=target, value=value, params=params):
                with self.assertRaises(ValueError):
                    db.inserir_previsao("Ridge", target, value, params)
        self.assertEqual(db.get_previsoes(), [])

    def test_ph_persistence_accepts_alias_and_records_both_history_keys(self):
        old = dict(PH)
        old["cultura"] = old.pop("label")
        db.inserir_previsao("Ridge", "ph", 6.2, json.dumps(old))
        params = json.loads(db.get_previsoes()[0]["parametros_entrada"])
        self.assertEqual(params["label"], "apple")
        self.assertEqual(params["cultura"], "apple")

    def test_invalid_limits_and_timestamps(self):
        for limit in (-1, 1.5, "2", True, 100001):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    db.get_previsoes(limit)
        for value in ("", "today", "2026-11-01", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    db.normalizar_timestamp(value)


if __name__ == "__main__":
    unittest.main()
