"""CLI e limites de exposição: subprocessos locais, sem iniciar servidor real."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]


def _copy_module(destination):
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", "*.db-*", ".env", "secrets.toml")
    for name in ("src", "scripts", "assets", ".streamlit"):
        shutil.copytree(SOURCE / name, destination / name, ignore=ignore)
    shutil.copy2(SOURCE / "main.py", destination / "main.py")


def _command_worker(root, scenario):
    os.chdir(root)
    sys.path.insert(0, str(root))
    os.environ["DB_PATH"] = str(root / "fixture.db")
    os.environ["FARMTECH_SIMULACAO"] = "0"
    from unittest.mock import patch, MagicMock
    import main
    fake = MagicMock()
    fake.wait.return_value = 0
    with patch("subprocess.Popen", return_value=fake) as start:
        if scenario == "old_streamlit":
            with patch("importlib.metadata.version", return_value="1.45.1"):
                try:
                    main.run_streamlit()
                except RuntimeError:
                    result = {"blocked": True, "spawned": start.called}
                else:
                    result = {"blocked": False, "spawned": start.called}
        else:
            with patch("importlib.metadata.version", return_value="1.54.0"):
                try:
                    main.run_streamlit(permitir_rede=scenario == "network")
                except ValueError:
                    result = {"invalid_port": True, "spawned": start.called}
                else:
                    result = {"command": start.call_args.args[0], "cwd": str(start.call_args.kwargs["cwd"]), "spawned": start.called}
    print("F402_RESULT " + json.dumps(result))


class LauncherSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="farmtech-cli-tests-")
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "module"
        self.root.mkdir()
        _copy_module(self.root)
        self.consumer = self.directory / "consumer"
        self.consumer.mkdir()
        self.database = self.root / "fixture.db"
        self.env = dict(os.environ, DB_PATH=str(self.database), FARMTECH_SIMULACAO="0", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *arguments, env=None):
        return subprocess.run([sys.executable, "-X", "utf8", "-B", str(self.root / "main.py"), *arguments],
                              cwd=self.consumer, env=self.env if env is None else env, capture_output=True,
                              text=True, encoding="utf-8", timeout=45)

    def create_database(self):
        result = self.cli("--ingestao")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def command_scenario(self, scenario, port="8765"):
        result = subprocess.run([sys.executable, "-X", "utf8", "-B", str(Path(__file__).resolve()), "--worker", str(self.root), scenario],
                                cwd=self.consumer, env=dict(self.env, PORT=port), capture_output=True, text=True,
                                encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        line = next(line for line in reversed(result.stdout.splitlines()) if line.startswith("F402_RESULT "))
        return json.loads(line.removeprefix("F402_RESULT "))

    def assert_cli_failure(self, result):
        self.assertNotEqual(result.returncode, 0)
        public = result.stdout + result.stderr
        self.assertIn("[ERRO]", public)
        self.assertNotIn("Traceback", public)
        self.assertNotIn(str(self.root), public)
        self.assertNotIn("Concluido", public)

    def test_port_does_not_expose_service_and_protections_are_enabled(self):
        result = self.command_scenario("local")
        command = result["command"]
        for option, expected in (("--server.address", "127.0.0.1"), ("--server.port", "8765"),
                                 ("--server.enableCORS", "true"), ("--server.enableXsrfProtection", "true")):
            self.assertEqual(command[command.index(option) + 1], expected)
        self.assertTrue(result["spawned"])
        self.assertEqual(Path(result["cwd"]), self.root)

    def test_network_binding_requires_explicit_option(self):
        command = self.command_scenario("network")["command"]
        self.assertEqual(command[command.index("--server.address") + 1], "0.0.0.0")
        for option in ("--server.enableCORS", "--server.enableXsrfProtection"):
            self.assertEqual(command[command.index(option) + 1], "true")
        result = self.cli("--permitir-rede")
        self.assertEqual(result.returncode, 2)

    def test_invalid_ports_fail_before_any_process_is_spawned(self):
        for port in ("0", "65536", "not-a-port", "-1"):
            with self.subTest(port=port):
                result = self.command_scenario("invalid_port", port)
                self.assertTrue(result["invalid_port"])
                self.assertFalse(result["spawned"])

    def test_old_streamlit_is_refused_before_start(self):
        result = self.command_scenario("old_streamlit")
        self.assertTrue(result["blocked"])
        self.assertFalse(result["spawned"])

    def test_missing_database_dashboard_and_training_return_nonzero(self):
        for flag in ("--dashboard", "--treinar"):
            with self.subTest(flag=flag):
                self.assert_cli_failure(self.cli(flag))
                self.assertFalse(self.database.exists())

    def test_empty_and_corrupted_databases_are_not_considered_ready(self):
        for content in (b"", b"not sqlite"):
            with self.subTest(content=content):
                self.database.write_bytes(content)
                self.assert_cli_failure(self.cli("--dashboard"))
                self.assertEqual(self.database.read_bytes(), content)

    def test_pipeline_does_not_reinitialize_existing_invalid_database(self):
        self.database.write_bytes(b"private-invalid-db")
        self.assert_cli_failure(self.cli("--pipeline"))
        self.assertEqual(self.database.read_bytes(), b"private-invalid-db")

    def test_pipeline_does_not_retrain_altered_historical_model(self):
        self.create_database()
        model = self.root / "src/ml/models/modelo_rainfall.joblib"
        other = self.root / "src/ml/models/modelo_humidity.joblib"
        before = hashlib.sha256(other.read_bytes()).hexdigest()
        model.write_bytes(b"\x00")
        self.assert_cli_failure(self.cli("--pipeline"))
        self.assertEqual(model.read_bytes(), b"\x00")
        self.assertEqual(hashlib.sha256(other.read_bytes()).hexdigest(), before)

    def test_training_does_not_overwrite_preserved_historical_models(self):
        self.create_database()
        models = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (self.root / "src/ml/models").glob("*.joblib")}
        self.assert_cli_failure(self.cli("--treinar"))
        for path, digest in models.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_missing_models_fail_without_automatic_training(self):
        self.create_database()
        models = list((self.root / "src/ml/models").glob("modelo_*.joblib"))
        for model in models:
            model.unlink()  # somente a cópia temporária deste teste
        self.assert_cli_failure(self.cli("--pipeline"))
        self.assertTrue(all(not model.exists() for model in models))

    def test_ingestion_from_different_cwd_resolves_default_db_inside_module(self):
        environment = dict(self.env)
        environment.pop("DB_PATH", None)
        result = self.cli("--ingestao", env=environment)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        expected = self.root / "src/db/farmtech.db"
        self.assertTrue(expected.is_file())
        self.assertFalse((self.consumer / "src").exists())
        connection = sqlite3.connect(expected)
        try:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM amostras_agronomicas").fetchone()[0], 2200)
        finally:
            connection.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _command_worker(Path(sys.argv[2]), sys.argv[3])
    else:
        unittest.main()
