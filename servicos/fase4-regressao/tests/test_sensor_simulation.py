"""Primeira execução e simulação real em cópias temporárias, sem banco do projeto."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from test_frontend_safety import _copy_module


def _worker(scenario, root):
    os.chdir(root)
    sys.path.insert(0, str(root))
    database = root / ".runtime/demo/farmtech-demo.db"
    if scenario == "other_database":
        database = root / "existing.db"
    os.environ.update(
        DB_PATH=str(database), FARMTECH_INTEGRACAO="1", FARMTECH_SIMULACAO="0",
        SCHEDULER_INTERVALO="3600",
    )
    from src.db import database as db
    from src.frontend import scheduler
    from streamlit.testing.v1 import AppTest

    def button(app, label):
        return next(item for item in app.button if item.label == label)

    def snapshot(app):
        return {
            "exceptions": [item.message for item in app.exception],
            "errors": [item.value for item in app.error],
            "warnings": [item.value for item in app.warning],
            "success": [item.value for item in app.success],
            "captions": [item.value for item in app.caption],
        }

    if scenario != "missing_database":
        from scripts.init_db import inicializar_banco
        inicializar_banco(database)

    try:
        app = AppTest.from_file(str(root / "src/frontend/app.py"), default_timeout=60).run()
        app.switch_page("pages/1_Sensores_IoT.py").run()
        result = {"initial": snapshot(app)}
        if scenario == "missing_database":
            result.update(
                start_disabled=button(app, "Iniciar simulação").disabled,
                database_created=database.exists(), producer_created=scheduler._SCHEDULER is not None,
            )
            # A página inicial registrou a falha no holder da sessão. Preparar
            # explicitamente o banco e atualizar permite recuperar essa sessão.
            from scripts.init_db import inicializar_banco
            inicializar_banco(database)
            app.run()
            result["start_enabled_after_prepare"] = not button(app, "Iniciar simulação").disabled
            button(app, "Iniciar simulação").click().run()
            result["recovered"] = snapshot(app)
            result["stale_error_cleared"] = "erro" not in app.session_state["scheduler_holder"]
            button(app, "Parar simulação").click().run()
        elif scenario == "other_database":
            result.update(
                start_disabled=button(app, "Iniciar simulação").disabled,
                producer_created=scheduler._SCHEDULER is not None,
                readings=len(db.get_leituras(limite=100000)),
            )
        elif scenario == "start_write_stop":
            result["initial_readings"] = len(db.get_leituras(limite=100000))
            result["charts"] = len(app.get("plotly_chart"))
            button(app, "Iniciar simulação").click().run()
            result["started"] = snapshot(app)
            holder = app.session_state["scheduler_holder"]
            producer = holder["scheduler"]
            result["running"] = producer.running
            # O executor do APScheduler roda o callback real, em outra thread,
            # sem esperar o intervalo de uma hora nem simular a escrita SQLite.
            from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
            completed = threading.Event()
            events = []

            def on_job(event):
                events.append(event.exception is None)
                completed.set()

            producer.add_listener(on_job, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
            producer.modify_job("simulacao_iot", next_run_time=datetime.now(timezone.utc))
            result["job_completed"] = completed.wait(timeout=15)
            button(app, "Parar simulação").click().run()
            result["stopped"] = snapshot(app)
            result["job_success"] = events
            result["running_after_stop"] = producer.running
            result["final_readings"] = len(db.get_leituras(limite=100000))
            result["latest"] = db.get_ultima_leitura()
        else:
            raise ValueError("Cenário desconhecido.")
    finally:
        scheduler.encerrar_scheduler()
    print("F402_SIMULATION_RESULT " + json.dumps({
        "result": result,
        "threads": [item.name for item in threading.enumerate() if item.name == "APScheduler"],
    }, ensure_ascii=False))


class SensorSimulationTests(unittest.TestCase):
    def run_scenario(self, scenario):
        with tempfile.TemporaryDirectory(prefix="farmtech-simulation-tests-") as temporary:
            root = Path(temporary) / "module"
            root.mkdir()
            _copy_module(root)
            result = subprocess.run(
                [sys.executable, "-X", "utf8", "-B", str(Path(__file__).resolve()), "--worker", scenario, str(root)],
                cwd=temporary, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1"),
                capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-4000:])
            payload = next(line.removeprefix("F402_SIMULATION_RESULT ")
                           for line in reversed(result.stdout.splitlines())
                           if line.startswith("F402_SIMULATION_RESULT "))
            response = json.loads(payload)
            self.assertEqual(response["threads"], [])
            return response["result"]

    def assert_screen_ok(self, screen):
        self.assertEqual(screen["exceptions"], [])
        self.assertEqual(screen["errors"], [])

    def test_missing_demo_has_executable_preparation_guidance_and_cannot_start(self):
        result = self.run_scenario("missing_database")
        self.assert_screen_ok(result["initial"])
        self.assertTrue(result["start_disabled"])
        self.assertTrue(any("python iniciar.py --preparar-demo" in text
                            for text in result["initial"]["warnings"]))
        self.assertFalse(result["database_created"])
        self.assertFalse(result["producer_created"])
        self.assertTrue(result["start_enabled_after_prepare"])
        self.assert_screen_ok(result["recovered"])
        self.assertTrue(any("Simulação ativa" in text for text in result["recovered"]["success"]))
        self.assertTrue(result["stale_error_cleared"])

    def test_prepared_demo_renders_153_readings_and_scheduler_really_writes_then_stops(self):
        result = self.run_scenario("start_write_stop")
        for state in ("initial", "started", "stopped"):
            self.assert_screen_ok(result[state])
        self.assertEqual(result["initial_readings"], 153)
        self.assertEqual(result["charts"], 4)
        self.assertTrue(result["running"])
        self.assertTrue(any("Simulação ativa" in text for text in result["started"]["success"]))
        self.assertTrue(result["job_completed"])
        self.assertEqual(result["job_success"], [True])
        self.assertEqual(result["final_readings"], 154)
        self.assertTrue(result["latest"]["ts"].endswith("Z"))
        self.assertFalse(result["running_after_stop"])

    def test_other_existing_database_is_readable_but_manual_simulation_is_blocked(self):
        result = self.run_scenario("other_database")
        self.assert_screen_ok(result["initial"])
        self.assertTrue(result["start_disabled"])
        self.assertFalse(result["producer_created"])
        self.assertEqual(result["readings"], 153)
        self.assertTrue(any("DB_PATH" in text for text in result["initial"]["captions"]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker(sys.argv[2], Path(sys.argv[3]))
    else:
        unittest.main()
