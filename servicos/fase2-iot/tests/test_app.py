"""Valida encerramento de subprocessos e retorno do menu sem simulador/R/rede."""

import contextlib
import io
import subprocess
import unittest
from unittest.mock import Mock, patch

import app


class AppTests(unittest.TestCase):
    def test_enter_terminates_and_waits_without_tcp_probes(self):
        proc = Mock(stdout=io.StringIO(), returncode=-15)
        proc.poll.return_value = None
        thread = Mock()
        with patch.object(app.subprocess, "Popen", return_value=proc) as popen:
            with patch.object(app.threading, "Thread", return_value=thread):
                with patch.object(app, "is_enter_pressed", return_value=True), patch.object(app, "is_port_open") as probe:
                    with contextlib.redirect_stdout(io.StringIO()):
                        app.run_serial_capture()
        proc.terminate.assert_called_once()
        proc.wait.assert_called_once_with(timeout=3)
        probe.assert_not_called()
        self.assertEqual(popen.call_args.kwargs["cwd"], app.ROOT)
        self.assertEqual(popen.call_args.args[0], app.SERIAL_CAPTURE_CMD)
        self.assertTrue(proc.stdout.closed)

    def test_ctrl_c_forces_kill_after_timeout_and_reaps(self):
        proc = Mock(stdout=io.StringIO(), returncode=-9)
        proc.poll.return_value = None
        proc.wait.side_effect = [subprocess.TimeoutExpired("capture", 3), 0]
        with patch.object(app.subprocess, "Popen", return_value=proc), patch.object(app.threading, "Thread"):
            with patch.object(app, "is_enter_pressed", side_effect=KeyboardInterrupt()):
                with contextlib.redirect_stdout(io.StringIO()):
                    app.run_serial_capture()
        proc.terminate.assert_called_once()
        proc.kill.assert_called_once()
        self.assertEqual(proc.wait.call_count, 2)

    def test_child_error_is_reported(self):
        proc = Mock(stdout=io.StringIO("capture error\n"), returncode=3)
        proc.poll.return_value = 3
        output = io.StringIO()
        with patch.object(app.subprocess, "Popen", return_value=proc), contextlib.redirect_stdout(output):
            app.run_serial_capture()
        self.assertIn("código 3", output.getvalue())
        proc.terminate.assert_not_called()
        proc.wait.assert_called_once()

    def test_r_and_weather_run_at_repository_root(self):
        with patch.object(app.shutil, "which", return_value="Rscript"), patch.object(app.subprocess, "run", return_value=Mock(returncode=0)) as run:
            with patch("builtins.input", return_value="Irecê"), contextlib.redirect_stdout(io.StringIO()):
                app.run_r_menu()
                app.run_weather_forecast()
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertEqual(call.kwargs["cwd"], app.ROOT)

    def test_missing_r_returns_without_subprocess(self):
        with patch.object(app.shutil, "which", return_value=None), patch.object(app.subprocess, "run") as run:
            with contextlib.redirect_stdout(io.StringIO()):
                app.run_r_menu()
        run.assert_not_called()

    def test_menu_invalid_selection_eof_and_ctrl_c(self):
        for choices in (["invalid", "4"], [EOFError()], [KeyboardInterrupt()]):
            with patch("builtins.input", side_effect=choices), contextlib.redirect_stdout(io.StringIO()):
                app.main()


if __name__ == "__main__":
    unittest.main()
