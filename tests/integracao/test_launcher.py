"""Startup and environment regressions without real subprocesses or services."""

from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import iniciar
from farmtech_integracao.contracts import Result


class LauncherEnvironmentTests(unittest.TestCase):
    def test_explicit_database_is_preserved_and_simulation_is_disabled(self):
        configured = {"DB_PATH": "configured/database.db", "FARMTECH_SIMULACAO": "1"}
        with patch.dict(os.environ, configured, clear=True):
            environment = iniciar._environment()
            self.assertEqual(os.environ["FARMTECH_SIMULACAO"], "1")
        self.assertEqual(environment["DB_PATH"], configured["DB_PATH"])
        self.assertEqual(environment["FARMTECH_SIMULACAO"], "0")
        self.assertEqual(environment["FARMTECH_INTEGRACAO"], "1")

    def test_demo_database_is_the_default(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "farmtech_integracao.demo.demo_path", return_value=Path("demo.db")
        ):
            self.assertEqual(iniciar._environment()["DB_PATH"], str(Path("demo.db")))


class LauncherPythonTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.local = (self.root / "servicos" / "fase4-regressao" / ".venv-f402" /
                      ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        self.local.parent.mkdir(parents=True)
        self.local.write_bytes(b"local-interpreter-fixture")
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(iniciar, "ROOT", self.root))
        stack.enter_context(patch.dict(os.environ, {}, clear=True))

    def test_project_virtualenv_is_found_without_activation_or_editor_configuration(self):
        self.assertEqual(iniciar._python_fase4(), self.local)

    def test_explicit_interpreter_in_another_worktree_takes_priority(self):
        other = self.root / "another-worktree-python.exe"
        other.write_bytes(b"other-interpreter-fixture")
        with patch.dict(os.environ, {"FARMTECH_FASE4_PYTHON": str(other)}):
            self.assertEqual(iniciar._python_fase4(), other)

    def test_invalid_explicit_interpreter_does_not_silently_use_the_local_one(self):
        with patch.dict(os.environ, {"FARMTECH_FASE4_PYTHON": "missing/python.exe"}):
            with self.assertRaisesRegex(FileNotFoundError, "FARMTECH_FASE4_PYTHON"):
                iniciar._python_fase4()

    def test_missing_local_interpreter_has_manual_setup_instructions(self):
        with patch.object(iniciar, "ROOT", self.root / "new-checkout"):
            with self.assertRaises(FileNotFoundError) as caught:
                iniciar._python_fase4()
        message = str(caught.exception)
        self.assertIn("-m venv servicos/fase4-regressao/.venv-f402", message)
        self.assertIn("-m pip install -r requirements.txt", message)
        self.assertIn("somente se a pasta", message)
        self.assertFalse((self.root / "new-checkout").exists())

    def test_wrong_python_version_is_rejected_before_dashboard_or_installation(self):
        response = subprocess.CompletedProcess([], 0, json.dumps({"version": [3, 14, 4], "missing": []}))
        with patch.object(iniciar.subprocess, "run", return_value=response) as run:
            with self.assertRaisesRegex(ValueError, "esperado 3.11.9"):
                iniciar._validar_python(self.local)
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("pip", run.call_args.args[0])

    def test_missing_dependencies_have_commands_for_the_selected_interpreter(self):
        response = subprocess.CompletedProcess([], 0, json.dumps({"version": [3, 11, 9], "missing": ["streamlit"]}))
        with patch.object(iniciar.subprocess, "run", return_value=response) as run:
            with self.assertRaises(ValueError) as caught:
                iniciar._validar_python(self.local)
        self.assertIn(str(self.local), str(caught.exception))
        self.assertIn("-m pip install -r requirements.txt", str(caught.exception))
        self.assertEqual(run.call_count, 1)

    def test_compatible_environment_passes_without_installing_anything(self):
        response = subprocess.CompletedProcess([], 0, json.dumps({"version": [3, 11, 9], "missing": []}))
        with patch.object(iniciar.subprocess, "run", return_value=response) as run:
            iniciar._validar_python(self.local)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][0], str(self.local))

    def test_interpreter_probe_failure_produces_configuration_instructions(self):
        with patch.object(iniciar.subprocess, "run", side_effect=subprocess.TimeoutExpired("python", 15)):
            with self.assertRaisesRegex(ValueError, "Não foi possível validar o Python"):
                iniciar._validar_python(self.local)


class LauncherDatabaseTests(unittest.TestCase):
    def test_absent_database_is_not_created_and_reports_preparation_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.db"
            with self.assertRaisesRegex(ValueError, "python iniciar.py --preparar-demo"):
                iniciar._verificar_banco({"DB_PATH": str(path)})
            self.assertFalse(path.exists())

    def test_valid_explicit_database_is_inspected_without_preparation(self):
        with patch("farmtech_integracao.demo.inspect_database", return_value=Result("ok", "available")) as inspect:
            iniciar._verificar_banco({"DB_PATH": "custom/database.db"})
        inspect.assert_called_once_with("custom/database.db")


class LauncherStartupTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(iniciar, "_python_fase4", return_value=Path("python.exe")))
        self.validate_python = stack.enter_context(patch.object(iniciar, "_validar_python"))
        self.database_check = stack.enter_context(patch.object(iniciar, "_verificar_banco"))
        self.choose_port = stack.enter_context(patch.object(iniciar, "_escolher_porta", return_value=8501))
        stack.enter_context(patch.object(iniciar, "_environment", return_value={}))
        stack.enter_context(patch.object(iniciar, "LOG", MagicMock()))
        stack.enter_context(patch.object(iniciar.time, "sleep"))
        stack.enter_context(patch("builtins.print"))
        self.process = MagicMock()
        self.process.poll.return_value = None
        self.spawn = stack.enter_context(patch.object(iniciar.subprocess, "Popen", return_value=self.process))
        self.stop = stack.enter_context(patch.object(iniciar, "_parar"))
        self.health = stack.enter_context(patch.object(iniciar, "urlopen"))
        self.health.return_value.__enter__.return_value.status = 200
        self.browser = stack.enter_context(patch.object(iniciar.webbrowser, "open_new_tab", return_value=True))

    def test_missing_database_blocks_server_port_selection_and_browser(self):
        self.database_check.side_effect = ValueError("Base ausente; python iniciar.py --preparar-demo")
        with self.assertRaisesRegex(ValueError, "Base ausente"):
            iniciar._iniciar()
        self.choose_port.assert_not_called()
        self.spawn.assert_not_called()
        self.browser.assert_not_called()

    def test_invalid_python_blocks_database_check_and_server(self):
        self.validate_python.side_effect = ValueError("Python incompatível")
        with self.assertRaisesRegex(ValueError, "Python incompatível"):
            iniciar._iniciar()
        self.database_check.assert_not_called()
        self.spawn.assert_not_called()

    def test_keyboard_interrupt_during_health_wait_stops_the_spawned_process(self):
        self.health.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            iniciar._iniciar()
        self.stop.assert_called_once_with(self.process)
        self.browser.assert_not_called()

    def test_unexpected_browser_failure_stops_the_spawned_process(self):
        self.browser.side_effect = RuntimeError("browser failure")
        with self.assertRaisesRegex(RuntimeError, "browser failure"):
            iniciar._iniciar()
        self.stop.assert_called_once_with(self.process)

    def test_browser_unavailable_keeps_the_healthy_process_under_control(self):
        self.browser.side_effect = iniciar.webbrowser.Error("no browser")
        process, address = iniciar._iniciar()
        self.assertIs(process, self.process)
        self.assertEqual(address, "http://127.0.0.1:8501")
        self.stop.assert_not_called()

    def test_failed_health_checks_stop_the_process_after_the_startup_limit(self):
        self.health.side_effect = OSError("not ready")
        self.assertEqual(iniciar._iniciar(abrir_navegador=False), (None, None))
        self.assertEqual(self.health.call_count, 160)
        self.stop.assert_called_once_with(self.process)
        self.browser.assert_not_called()

    def test_healthy_process_is_returned_without_opening_a_browser_when_disabled(self):
        process, address = iniciar._iniciar(abrir_navegador=False)
        self.assertIs(process, self.process)
        self.assertEqual(address, "http://127.0.0.1:8501")
        self.stop.assert_not_called()
        self.browser.assert_not_called()


class LauncherMenuTests(unittest.TestCase):
    def test_configuration_error_keeps_the_menu_available_for_the_next_action(self):
        process = MagicMock()
        process.poll.return_value = None
        with patch("builtins.input", side_effect=["1", "1", "0", "s"]), patch("builtins.print"), \
                patch.object(iniciar, "_iniciar", side_effect=[ValueError("Prepare a base"), (process, "http://127.0.0.1:8501")]) as start, \
                patch.object(iniciar, "_parar") as stop:
            self.assertEqual(iniciar._menu(), 0)
        self.assertEqual(start.call_count, 2)
        stop.assert_called_once_with(process)


if __name__ == "__main__":
    unittest.main()
