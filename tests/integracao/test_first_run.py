"""Preparação temporária e menu com servidor real; não instala dependências."""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import urlopen

import iniciar
from farmtech_integracao import demo
from farmtech_integracao.workers.fase4_worker import prepare


@unittest.skipUnless(sys.version_info[:3] == (3, 11, 9), "Requer o perfil F4 Python 3.11.9 instalado.")
class FirstRunTests(unittest.TestCase):
    def test_explicit_preparation_then_real_menu_start_health_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.db"
            log = Path(directory) / "dashboard.log"
            launched = []
            output = StringIO()
            errors = StringIO()
            real_start = iniciar._iniciar

            def start():
                process, address = real_start(abrir_navegador=False)
                self.assertIsNotNone(process, output.getvalue())
                launched.append((process, address))
                return process, address

            actions = iter(("1", "0", "s"))

            def choose(_prompt):
                action = next(actions)
                if action == "0":
                    process, address = launched[0]
                    self.assertIsNone(process.poll())
                    with urlopen(address + "/_stcore/health", timeout=3) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.read(), b"ok")
                return action

            environment = {"FARMTECH_FASE4_PYTHON": sys.executable, "DB_PATH": str(path)}
            with patch.dict(os.environ, environment), patch.object(demo, "demo_path", return_value=path), \
                    patch.object(iniciar, "LOG", log), redirect_stdout(output), redirect_stderr(errors):
                # O preflight não cria a base ausente nem inicia um servidor.
                with self.assertRaisesRegex(ValueError, "python iniciar.py --preparar-demo"):
                    real_start(abrir_navegador=False)
                self.assertFalse(path.exists())
                self.assertFalse(log.exists())

                result = prepare(path)
                self.assertTrue(result.ok, result.message)
                self.assertEqual(result.data["counts"]["leituras_sensores"], 153)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                try:
                    with patch.object(iniciar, "_iniciar", side_effect=start), patch("builtins.input", side_effect=choose):
                        self.assertEqual(iniciar._menu(), 0)
                finally:
                    for process, _ in launched:
                        if process.poll() is None:
                            iniciar._parar(process)

                self.assertEqual(len(launched), 1)
                self.assertIsNotNone(launched[0][0].poll())
                self.assertIn("Dashboard ativo:", output.getvalue())
                self.assertEqual(errors.getvalue(), "")
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
                self.assertEqual(demo.inspect_database(path).data["counts"]["leituras_sensores"], 153)


if __name__ == "__main__":
    unittest.main()
