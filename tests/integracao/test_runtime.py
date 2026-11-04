"""Limites de processos reais pequenos e validação do protocolo; sem serviços."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from farmtech_integracao.contracts import Result
from farmtech_integracao import runtime


class RuntimeTests(unittest.TestCase):
    def test_invalid_requests_do_not_spawn(self):
        with patch.object(runtime, "_execute") as execute:
            for phase, payload, timeout in (([], {}, 1), ("fase5", {}, 1), ("fase1", {}, 0),
                                            ("fase1", {}, float("nan")), ("fase1", {}, True),
                                            ("fase1", {"value": float("nan")}, 1)):
                self.assertFalse(runtime.run_json_worker(phase, payload, timeout=timeout).ok)
            self.assertFalse(runtime.run_json_worker("fase1", {}, python=123).ok)
            execute.assert_not_called()

    def test_environment_forwards_only_oracle_configuration_to_phase3(self):
        with patch.dict(os.environ, {"ORACLE_PASS": "private-test-password", "UNRELATED_TOKEN": "private-token", "PYTHONPATH": "not-allowed"}):
            self.assertIn("ORACLE_PASS", runtime._environment("fase3"))
            self.assertNotIn("ORACLE_PASS", runtime._environment("fase1"))
            self.assertNotIn("UNRELATED_TOKEN", runtime._environment("fase3"))
            self.assertNotIn("PYTHONPATH", runtime._environment("fase3"))

    def test_worker_command_is_fixed_and_utf8(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runtime, "PROJECT_ROOT", Path(directory)), patch.object(runtime, "_execute", return_value=(0, json.dumps(Result("ok", "ação").as_dict(), ensure_ascii=False).encode(), None)) as execute:
            result = runtime.run_json_worker("fase1", {"value": "$(untrusted)"})
        self.assertTrue(result.ok)
        command = execute.call_args.args[0]
        self.assertEqual(command[1:5], ["-X", "utf8", "-I", "-B"])
        self.assertNotIn("$(untrusted)", command)
        self.assertNotIn("shell", execute.call_args.kwargs)

    def test_bounded_output_and_real_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, reason = runtime._execute([sys.executable, "-X", "utf8", "-c", "import time; time.sleep(10)"], b"", cwd=Path(directory), env=runtime._environment("fase1"), timeout=.15)
            self.assertEqual(reason, "timeout")
            with patch.object(runtime, "MAX_OUTPUT_BYTES", 1024):
                _, output, reason = runtime._execute([sys.executable, "-c", "print('x'*10000)"], b"", cwd=Path(directory), env=runtime._environment("fase1"), timeout=5)
            self.assertEqual(reason, "output_limit")
            self.assertLessEqual(len(output), 1024)

    def test_large_input_to_nonreading_child_still_times_out(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, reason = runtime._execute([sys.executable, "-c", "import time; time.sleep(10)"], b"x"*32768, cwd=Path(directory), env=runtime._environment("fase1"), timeout=.15)
        self.assertEqual(reason, "timeout")

    def test_same_phase_is_locked_across_handles(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runtime, "PROJECT_ROOT", Path(directory)):
            with runtime._phase_lock("fase1"):
                with self.assertRaises(OSError):
                    with runtime._phase_lock("fase1"):
                        self.fail("A trava deveria recusar uma segunda ação concorrente")

    def test_invalid_worker_result_is_sanitized(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runtime, "PROJECT_ROOT", Path(directory)), patch.object(runtime, "_execute", return_value=(0, b"private-secret-not-json", None)):
            result = runtime.run_json_worker("fase1", {})
        self.assertEqual(result.status, "error")
        self.assertNotIn("private-secret", json.dumps(result.as_dict()))


if __name__ == "__main__":
    unittest.main()
