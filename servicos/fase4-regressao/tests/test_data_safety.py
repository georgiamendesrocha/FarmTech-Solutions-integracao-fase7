"""Regressões A04/A05/A06: dados e publicações apenas em diretórios temporários."""

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import pandas as pd

from src import atomic_files as atomic
from src import data_sources as ds
from tests.test_data_sources import _inmet_csv, _noaa_line, _sidra_complete_payload, _sidra_payload


def _noaa_content() -> bytes:
    return "\n".join(_noaa_line().replace("20250101", "20250102").replace("0100", f"{hour:02d}00", 1) for hour in range(24)).encode()


class DataSafetyTests(unittest.TestCase):
    def test_noaa_official_sentinels_are_missing_per_field(self):
        fields = _noaa_line().split()
        for field in ["T_HR_AVG", "P_CALC", "RH_HR_AVG", "SOIL_TEMP_5"]:
            fields[ds.NOAA_COLUMNS.index(field)] = "-9999.0"
        fields[ds.NOAA_COLUMNS.index("SOIL_MOISTURE_5")] = "-99.000"
        frame = ds.parse_noaa_text(" ".join(fields))
        columns = ["air_temperature_c", "precipitation_mm", "relative_humidity_pct", "soil_temperature_5cm_c", "soil_moisture_5cm_m3_m3"]
        self.assertTrue(frame[columns].isna().all(axis=None))
        self.assertEqual(frame["soil_moisture_10cm_m3_m3"].iloc[0], 0.168)

    def test_noaa_rejects_identity_period_and_nonfinite(self):
        for field, value in [("WBANNO", "99999"), ("LATITUDE", "0"), ("LONGITUDE", "0"),
                             ("UTC_DATE", "20240101"), ("UTC_TIME", "0130"),
                             ("T_HR_AVG", "inf"), ("SOIL_MOISTURE_5", "nan"),
                             ("P_CALC", "-1"), ("SOIL_TEMP_5", "100")]:
            with self.subTest(field=field):
                fields = _noaa_line().split()
                fields[ds.NOAA_COLUMNS.index(field)] = value
                with self.assertRaises(ValueError):
                    ds.parse_noaa_text(" ".join(fields))

    def test_noaa_identity_validation_applies_to_discarded_rows(self):
        fields = _noaa_line().split()
        fields[0] = "99999"
        fields[ds.NOAA_COLUMNS.index("UTC_TIME")] = "0200"
        for column in ds.NOAA_COLUMNS:
            if column.startswith("SOIL_MOISTURE_"):
                fields[ds.NOAA_COLUMNS.index(column)] = "-99.000"
        with self.assertRaisesRegex(ValueError, "WBAN"):
            ds.parse_noaa_text(_noaa_line() + "\n" + " ".join(fields))

    def test_noaa_all_missing_soil_cannot_be_published(self):
        fields = _noaa_line().split()
        for column in ds.NOAA_COLUMNS:
            if column.startswith("SOIL_MOISTURE_"):
                fields[ds.NOAA_COLUMNS.index(column)] = "-99.000"
        with self.assertRaisesRegex(ValueError, "Menos de 1"):
            ds.parse_noaa_text(" ".join(fields))

    def test_inmet_rejects_bad_identity_coordinates_dates_units_and_values(self):
        for before, after in [
            (b"LATITUDE:;-23,4962888", b"LATITUDE:;999"),
            (b"LONGITUDE:;-46,6200666", b"LONGITUDE:;nan"),
            (b"UF:;SP", b"UF:;MG"),
            (b"ESTACAO:;SAO PAULO - MIRANTE", b"ESTACAO:;OUTRA"),
            (b"2025/01/01", b"2024/01/01"),
            (b"(mm)", b"(cm)"),
            (b";0,1;21,2;76", b";0,1;inf;76"),
            (b";0,1;21,2;76", b";0,1;21,2;101"),
        ]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                ds.parse_inmet_csv(_inmet_csv().replace(before, after))

    def test_sidra_rejects_invalid_rows_including_after_first(self):
        for change in [{"D2C": "8331"}, {"MN": "Hectares"}, {"D4C": "0"},
                       {"D4N": "outro produto"}, {"D3C": "2023.5"},
                       {"D1C": "999"}, {"D1N": "Cidade - ZZ"},
                       {"V": "nan"}, {"V": "inf"}, {"V": "-1"}]:
            with self.subTest(change=change):
                payload = json.loads(_sidra_payload())
                extra = {**payload[1], "D1C": "3550308", "D1N": "São Paulo - SP", **change}
                payload.append(extra)
                with self.assertRaises(ValueError):
                    ds.parse_sidra_json(json.dumps(payload).encode(), "municipio")

    def test_sidra_rejects_corrupted_json_missing_keys_and_wrong_level(self):
        for content in [b"broken", b"[{}, {}]", b"[{}, null]", b"{}"]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                ds.parse_sidra_json(content, "municipio")
        with self.assertRaises(ValueError):
            ds.parse_sidra_json(_sidra_payload(), "invalid")

    def test_sidra_import_rejects_wrong_requested_period_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "Período"):
                ds.importar_sidra(root, 2025, _sidra_complete_payload("brasil"), _sidra_complete_payload("municipio", 2023))
            self.assertEqual(list(root.iterdir()), [])
            with self.assertRaisesRegex(ValueError, "Cobertura"):
                payload = json.loads(_sidra_payload())
                payload[1].update(D1C="1", D1N="Brasil")
                ds.importar_sidra(root, 2023, json.dumps(payload).encode(), _sidra_complete_payload("municipio", 2023))
            self.assertEqual(list(root.iterdir()), [])

    def test_local_readers_reject_invalid_single_timestamp_infinite_and_ranges(self):
        frames = [(ds.parse_noaa_text(_noaa_content().decode()), ds.carregar_noaa),
                  (ds.parse_inmet_csv(_inmet_csv())[0], ds.carregar_inmet)]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.csv"
            for frame, loader in frames:
                for column, invalid in [("timestamp_utc", "invalid"), ("precipitation_mm", np.inf),
                                        ("latitude", 0), ("relative_humidity_pct", 101),
                                        ("air_temperature_c", -9999)]:
                    with self.subTest(loader=loader.__name__, column=column):
                        changed = frame.copy()
                        changed[column] = changed[column].astype(object)
                        changed.loc[0, column] = invalid
                        changed.to_csv(path, index=False)
                        with self.assertRaises(ValueError):
                            loader(path)

    def test_local_sidra_rejects_nonfinite_fractional_year_units_and_keys(self):
        frame = ds.parse_sidra_json(_sidra_payload(), "municipio")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.csv"
            for column, value in [("rendimento_kg_ha", np.inf), ("rendimento_kg_ha", "wrong"),
                                  ("ano", 2023.5), ("unidade", "ton/ha"), ("codigo_cultura", "0")]:
                changed = frame.copy()
                changed[column] = value
                changed.to_csv(path, index=False)
                with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                    ds.carregar_sidra(path)

    def test_import_failure_before_publication_preserves_noaa_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output, metadata = root / "observations.csv", root / "metadata.json"
            output.write_bytes(b"prior csv")
            metadata.mkdir()
            with self.assertRaises(ValueError):
                ds.importar_noaa(_noaa_content(), output, metadata)
            self.assertEqual(output.read_bytes(), b"prior csv")
            self.assertFalse((root / ".farmtech-publication").exists())

    def test_publication_failure_rolls_back_existing_and_new_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b, c = root / "a.csv", root / "b.json", root / "new.json"
            a.write_bytes(b"old csv")
            b.write_bytes(b"old metadata")
            original = atomic.os.replace
            def fail_metadata(source, target):
                if Path(source).name == "1.new":
                    raise OSError("simulated failure")
                return original(source, target)
            with patch.object(atomic.os, "replace", side_effect=fail_metadata), self.assertRaises(OSError):
                atomic.publish_files({a: b"changed", b: b"changed metadata", c: b"new"})
            self.assertEqual(a.read_bytes(), b"old csv")
            self.assertEqual(b.read_bytes(), b"old metadata")
            self.assertFalse(c.exists())
            self.assertFalse((root / ".farmtech-publication").exists())

    def test_commit_marker_fsync_failure_restores_previous_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = root / "a.csv", root / "b.json"
            a.write_bytes(b"old csv")
            b.write_bytes(b"old metadata")
            original = atomic._write_bytes
            def fail_marker(path, content):
                if path.name == "committed.tmp":
                    with patch.object(atomic.os, "fsync", side_effect=OSError("marker fsync failed")):
                        return original(path, content)
                return original(path, content)
            with patch.object(atomic, "_write_bytes", side_effect=fail_marker), self.assertRaises(OSError):
                atomic.publish_files({a: b"new csv", b: b"new metadata"})
            self.assertEqual(a.read_bytes(), b"old csv")
            self.assertEqual(b.read_bytes(), b"old metadata")
            self.assertFalse((root / ".farmtech-publication").exists())

    def test_post_commit_cleanup_failure_does_not_report_failed_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = root / "a.csv", root / "b.json"
            a.write_bytes(b"old csv")
            b.write_bytes(b"old metadata")
            with patch.object(atomic.shutil, "rmtree", side_effect=OSError("cleanup temporarily denied")):
                atomic.publish_files({a: b"new csv", b: b"new metadata"})
            self.assertEqual(a.read_bytes(), b"new csv")
            self.assertEqual(b.read_bytes(), b"new metadata")
            self.assertTrue((root / ".farmtech-publication" / "committed").exists())
            with atomic.data_directory(root):
                self.assertEqual(a.read_bytes(), b"new csv")
                self.assertEqual(b.read_bytes(), b"new metadata")
            self.assertFalse((root / ".farmtech-publication").exists())

    def test_recovery_rejects_symlink_directory_before_recursive_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            pending = root / ".farmtech-publication"
            pending.mkdir()
            original = Path.is_symlink
            def simulated_symlink(path):
                return True if path == pending else original(path)
            with patch.object(Path, "is_symlink", simulated_symlink), patch.object(atomic.shutil, "rmtree") as cleanup:
                with self.assertRaisesRegex(ValueError, "fora do destino"):
                    with atomic.data_directory(root):
                        pass
                cleanup.assert_not_called()

    def test_noaa_import_rolls_back_when_metadata_publication_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            csv_path, meta_path = root / "observations.csv", root / "metadata.json"
            ds.importar_noaa(_noaa_content(), csv_path, meta_path)
            prior = (csv_path.read_bytes(), meta_path.read_bytes())
            original = atomic.os.replace
            def fail_metadata(source, target):
                if Path(source).name == "1.new":
                    raise OSError("simulated metadata failure")
                return original(source, target)
            with patch.object(atomic.os, "replace", side_effect=fail_metadata), self.assertRaises(OSError):
                ds.importar_noaa(_noaa_content().replace(b"19.9", b"20.0"), csv_path, meta_path)
            self.assertEqual((csv_path.read_bytes(), meta_path.read_bytes()), prior)

    def test_local_reader_verifies_metadata_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            csv_path, meta_path = root / "observations.csv", root / "metadata.json"
            ds.importar_noaa(_noaa_content(), csv_path, meta_path)
            self.assertEqual(len(ds.carregar_noaa(csv_path, meta_path)), 24)
            csv_path.write_bytes(csv_path.read_bytes().replace(b"19.9", b"20.0"))
            with self.assertRaisesRegex(ValueError, "Integridade"):
                ds.carregar_noaa(csv_path, meta_path)

    def test_group_reader_rejects_missing_keys_types_count_period_and_unit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            csv_path, meta_path = root / "observations.csv", root / "metadata.json"
            _, metadata = ds.importar_noaa(_noaa_content(), csv_path, meta_path)
            valid = json.loads(json.dumps(metadata))
            invalid_metadata = [{}, [], {**valid, "observacoes": 999},
                                {**valid, "latitude": "31.19"},
                                {**valid, "fim_utc": "invalid"},
                                {**valid, "unidades": {"temperatura_ar": "F"}}]
            for changed in invalid_metadata:
                meta_path.write_text(json.dumps(changed), encoding="utf-8")
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    ds.carregar_conjunto_meteorologico("NOAA", csv_path, meta_path)
            meta_path.write_text(json.dumps(valid), encoding="utf-8")
            frame, observed = ds.carregar_conjunto_meteorologico("NOAA", csv_path, meta_path)
            self.assertEqual(observed["observacoes"], len(frame))

    def test_group_sidra_reader_validates_shared_snapshot_and_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ds.importar_sidra(root, 2025, _sidra_complete_payload("brasil"), _sidra_complete_payload("municipio", 2025))
            national, municipal, metadata = ds.carregar_conjunto_sidra(root)
            self.assertEqual((len(national), len(municipal)), (180, 5))
            metadata_path = root / "sidra1612_metadata_municipios_2025.json"
            metadata["observacoes_municipais"] += 1
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "divergem"):
                ds.carregar_conjunto_sidra(root)

    def test_inmet_import_rolls_back_when_metadata_publication_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, csv_path, metadata_path = root / "source.zip", root / "inmet.csv", root / "metadata.json"
            with ZipFile(archive, "w") as output:
                output.writestr("INMET_SE_SP_A701_2025.CSV", _inmet_csv())
            ds.importar_inmet(archive, csv_path, metadata_path)
            previous = csv_path.read_bytes(), metadata_path.read_bytes()
            original = atomic.os.replace
            def fail_metadata(source, target):
                if Path(source).name == "1.new":
                    raise OSError("simulated metadata failure")
                return original(source, target)
            with patch.object(atomic.os, "replace", side_effect=fail_metadata), self.assertRaises(OSError):
                ds.importar_inmet(archive, csv_path, metadata_path)
            self.assertEqual((csv_path.read_bytes(), metadata_path.read_bytes()), previous)

    def test_different_directories_or_same_file_cannot_form_a_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "old.csv"
            original.write_bytes(b"old")
            for metadata_path in [original, root / "nested" / "metadata.json"]:
                with self.subTest(path=metadata_path), self.assertRaises(ValueError):
                    ds.importar_noaa(_noaa_content(), original, metadata_path)
                self.assertEqual(original.read_bytes(), b"old")

    def test_sidra_shared_national_updates_all_snapshot_metadata_consistently(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            national = _sidra_complete_payload("brasil")
            ds.importar_sidra(root, 2023, national, _sidra_complete_payload("municipio", 2023))
            changed = national.replace(b'"4000"', b'"4001"')
            ds.importar_sidra(root, 2025, changed, _sidra_complete_payload("municipio", 2025))
            actual_hash = hashlib.sha256((root / ds.SIDRA_NATIONAL_CSV.name).read_bytes()).hexdigest()
            for metadata in root.glob("sidra1612_metadata*.json"):
                self.assertEqual(json.loads(metadata.read_text(encoding="utf-8"))["arquivo_nacional_sha256"], actual_hash)
            self.assertEqual(len(ds.carregar_sidra(root / ds.SIDRA_NATIONAL_CSV.name)), 180)
            self.assertEqual(len(ds.carregar_sidra(root / "sidra1612_rendimento_municipios_2023.csv")), 5)

    def test_sidra_failed_publication_restores_all_snapshots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            national = _sidra_complete_payload("brasil")
            ds.importar_sidra(root, 2023, national, _sidra_complete_payload("municipio", 2023))
            ds.importar_sidra(root, 2025, national, _sidra_complete_payload("municipio", 2025))
            prior = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
            original = atomic.os.replace
            def fail_metadata(source, target):
                if Path(source).name == "3.new":
                    raise OSError("simulated failure")
                return original(source, target)
            with patch.object(atomic.os, "replace", side_effect=fail_metadata), self.assertRaises(OSError):
                ds.importar_sidra(root, 2025, national.replace(b'"4000"', b'"4001"'), _sidra_complete_payload("municipio", 2025))
            self.assertEqual({p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}, prior)

    def test_publication_recovery_after_process_termination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.csv").write_bytes(b"old csv")
            (root / "b.json").write_bytes(b"old metadata")
            code = """import os,sys
from pathlib import Path
from src import atomic_files as a
p=Path(sys.argv[1]); original=a.os.replace
def stop(source,target):
    original(source,target)
    if Path(source).name=='0.new': os._exit(19)
a.os.replace=stop
a.publish_files({p/'a.csv':b'new',p/'b.json':b'new metadata'})
"""
            result = subprocess.run([sys.executable, "-B", "-c", code, str(root)], cwd=ds.ROOT, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 19, result.stderr)
            self.assertTrue((root / ".farmtech-publication" / "journal.json").exists())
            with atomic.data_directory(root):
                self.assertEqual((root / "a.csv").read_bytes(), b"old csv")
                self.assertEqual((root / "b.json").read_bytes(), b"old metadata")
            self.assertFalse((root / ".farmtech-publication").exists())

    def test_concurrent_publishers_and_reader_never_observe_mixed_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = root / "a.csv", root / "b.json"
            atomic.publish_files({a: b"0", b: b"0"})
            def writer(offset):
                for index in range(10):
                    content = str(offset + index).encode()
                    atomic.publish_files({a: content, b: content})
            def reader():
                for _ in range(30):
                    with atomic.data_directory(root):
                        self.assertEqual(a.read_bytes(), b.read_bytes())
            with ThreadPoolExecutor(max_workers=3) as pool:
                tasks = [pool.submit(writer, 10), pool.submit(writer, 100), pool.submit(reader)]
                for task in tasks:
                    task.result(timeout=20)

    def test_data_directory_lock_excludes_another_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            code = """import sys,time
from pathlib import Path
from src.atomic_files import data_directory
with data_directory(Path(sys.argv[1])):
    print('locked',flush=True)
    time.sleep(0.5)
"""
            process = subprocess.Popen([sys.executable, "-B", "-c", code, temporary], cwd=ds.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(), "locked")
                with self.assertRaises(TimeoutError):
                    with atomic.data_directory(Path(temporary), timeout=0.05):
                        self.fail("Process lock was not respected")
                process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)

    def test_network_failure_has_no_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(ds, "_download", side_effect=RuntimeError("connection failure")), self.assertRaises(RuntimeError):
                ds.importar_noaa(output_path=root / "a.csv", metadata_path=root / "b.json")
            self.assertEqual(list(root.iterdir()), [])

    def test_import_cli_failure_returns_nonzero_and_hides_internal_details(self):
        spec = importlib.util.spec_from_file_location("official_cli", ds.ROOT / "scripts" / "importar_dados_oficiais.py")
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["importar_dados_oficiais.py", "--noaa"]), patch.object(cli, "importar_noaa", side_effect=RuntimeError("secret internal path")), redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(cli.main(), 1)
        self.assertNotIn("[OK]", stdout.getvalue())
        self.assertNotIn("secret internal path", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

