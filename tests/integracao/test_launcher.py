"""Startup and environment regressions without real subprocesses or services."""

from contextlib import ExitStack
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import iniciar


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


class LauncherStartupTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(iniciar, "_python_fase4", return_value=Path("python.exe")))
        stack.enter_context(patch.object(iniciar, "_escolher_porta", return_value=8501))
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


if __name__ == "__main__":
    unittest.main()
