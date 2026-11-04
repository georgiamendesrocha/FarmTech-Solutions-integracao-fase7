"""Configuração compartilhada e estados públicos, sempre com UI e banco isolados."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_frontend_safety import _copy_module


def _worker(scenario, root):
    os.chdir(root)
    sys.path.insert(0, str(root))
    os.environ.update(
        DB_PATH=str(root / "fixture.db"),
        FARMTECH_SIMULACAO="0",
        UMIDADE_LIMIAR="72.5",
        SCHEDULER_INTERVALO="3600",
    )
    from scripts.init_db import inicializar_banco
    inicializar_banco(root / "fixture.db")
    from src.db import database as db
    from src.frontend import scheduler
    from streamlit.testing.v1 import AppTest

    def run(page, holder=None):
        app = AppTest.from_file(str(root / "src/frontend" / page), default_timeout=45)
        if holder is not None:
            app.session_state["scheduler_holder"] = holder
        return app.run()

    def snapshot(app):
        return {
            "exceptions": [item.message for item in app.exception],
            "errors": [item.value for item in app.error],
            "warnings": [item.value for item in app.warning],
            "success": [item.value for item in app.success],
            "info": [item.value for item in app.info],
        }

    initial_readings = len(db.get_leituras(limite=100000))
    try:
        if scenario == "home_states":
            with patch.dict(os.environ, {"FARMTECH_SIMULACAO": "1"}):
                active = run("app.py")
                holder = active.session_state["scheduler_holder"]
                result = {"active": snapshot(active), "running": holder["scheduler"].running}
                scheduler.encerrar_scheduler()
                with patch.object(scheduler, "iniciar_scheduler", return_value=None):
                    result["stopped"] = snapshot(run("app.py", holder))
                with patch.object(db, "validar_banco", side_effect=ValueError("private-scheduler-failure")):
                    result["error"] = snapshot(run("app.py"))
            with patch.object(db, "validar_banco", side_effect=ValueError("private-disabled-db")):
                result["disabled"] = snapshot(run("app.py", {"erro": "private-stale-error"}))
        elif scenario == "sensor_threshold":
            app = run("pages/1_Sensores_IoT.py")
            result = snapshot(app)
            result["configured_threshold"] = scheduler.UMIDADE_LIMIAR
            result["chart"] = json.loads(app.get("plotly_chart")[0].proto.spec)
        elif scenario == "paused_scheduler":
            from apscheduler.schedulers.base import STATE_PAUSED
            with patch.dict(os.environ, {"FARMTECH_SIMULACAO": "1"}):
                holder = {}
                scheduler.iniciar_scheduler(holder)
                producer = holder["scheduler"]
                producer.pause()
                result = {
                    "running_while_paused": producer.running,
                    "paused_before": producer.state == STATE_PAUSED,
                    "reported_state": scheduler.estado_simulacao(holder),
                    "home": snapshot(run("app.py", holder)),
                    "sensors": snapshot(run("pages/1_Sensores_IoT.py", holder)),
                    "paused_after": producer.state == STATE_PAUSED,
                    "same_producer": scheduler._SCHEDULER is producer,
                }
        else:
            raise ValueError("Cenário desconhecido.")
        result["unchanged_readings"] = len(db.get_leituras(limite=100000)) == initial_readings
    finally:
        scheduler.encerrar_scheduler()
    print("F402_SCHEDULER_RESULT " + json.dumps({
        "result": result,
        "threads": [thread.name for thread in threading.enumerate() if thread.name == "APScheduler"],
    }, ensure_ascii=False))


class SchedulerAuditTests(unittest.TestCase):
    def run_scenario(self, scenario):
        with tempfile.TemporaryDirectory(prefix="farmtech-scheduler-tests-") as temporary:
            root = Path(temporary) / "module"
            root.mkdir()
            _copy_module(root)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
            result = subprocess.run(
                [sys.executable, "-X", "utf8", "-B", str(Path(__file__).resolve()), "--worker", scenario, str(root)],
                cwd=temporary, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-4000:])
            payload = next(line.removeprefix("F402_SCHEDULER_RESULT ") for line in reversed(result.stdout.splitlines()) if line.startswith("F402_SCHEDULER_RESULT "))
            response = json.loads(payload)
            self.assertEqual(response["threads"], [])
            self.assertTrue(response["result"]["unchanged_readings"])
            return response["result"]

    def test_home_distinguishes_running_disabled_error_and_stopped(self):
        result = self.run_scenario("home_states")
        self.assertTrue(result["running"])
        expected = {
            "active": ("success", "Simulação ativa"),
            "disabled": ("info", "Simulação desativada por configuração"),
            "error": ("warnings", "Simulação indisponível"),
            "stopped": ("info", "Simulação parada"),
        }
        for state, (level, message) in expected.items():
            with self.subTest(state=state):
                screen = result[state]
                self.assertEqual(screen["exceptions"], [])
                self.assertEqual(screen["errors"], [])
                self.assertTrue(any(message in text for text in screen[level]), screen)
                public = " ".join(text for messages in screen.values() for text in messages)
                self.assertNotIn("private-", public)
                if state != "active":
                    self.assertNotIn("Simulação ativa", public)
                    self.assertNotIn("scheduler ativo", public)

    def test_sensor_chart_uses_threshold_from_environment(self):
        result = self.run_scenario("sensor_threshold")
        self.assertEqual(result["exceptions"], [])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["configured_threshold"], 72.5)
        layout = result["chart"]["layout"]
        self.assertEqual(layout["shapes"][0]["y0"], 72.5)
        self.assertEqual(layout["shapes"][0]["y1"], 72.5)
        self.assertIn("72.5%", layout["annotations"][0]["text"])
        self.assertTrue(any("desativada por configuração" in message for message in result["info"]))

    def test_simulated_pump_uses_shared_threshold_including_boundary(self):
        from src.frontend import scheduler
        for humidity, expected_pump in ((70.0, 1), (72.5, 0), (75.0, 0)):
            with self.subTest(humidity=humidity):
                with patch.object(scheduler, "UMIDADE_LIMIAR", 72.5), patch.object(
                    scheduler.np.random, "normal", side_effect=[humidity, 25.0, 1800.0, 7.0]
                ):
                    reading = scheduler._gerar_leitura()
                self.assertEqual(reading["umidade"], humidity)
                self.assertEqual(reading["bomba_fw"], expected_pump)

    def test_real_paused_scheduler_remains_paused_and_ui_never_reports_active(self):
        result = self.run_scenario("paused_scheduler")
        self.assertTrue(result["running_while_paused"])
        self.assertTrue(result["paused_before"])
        self.assertTrue(result["paused_after"])
        self.assertTrue(result["same_producer"])
        self.assertEqual(result["reported_state"], "pausada")
        for page in ("home", "sensors"):
            with self.subTest(page=page):
                screen = result[page]
                self.assertEqual(screen["exceptions"], [])
                self.assertEqual(screen["errors"], [])
                self.assertTrue(any("Simulação pausada" in message for message in screen["info"]))
                public = " ".join(text for messages in screen.values() for text in messages)
                self.assertNotIn("Simulação ativa", public)
                self.assertNotIn("Scheduler ativo", public)

    def test_public_status_requires_running_and_honors_disabled_and_errors(self):
        from src.frontend import scheduler
        with patch.dict(os.environ, {"FARMTECH_SIMULACAO": "1"}):
            self.assertEqual(scheduler.estado_simulacao({}), "parada")
            self.assertEqual(scheduler.estado_simulacao({"scheduler": SimpleNamespace(running=False)}), "parada")
            self.assertEqual(scheduler.estado_simulacao({"scheduler": SimpleNamespace(running=True)}), "ativa")
            self.assertEqual(scheduler.estado_simulacao({"scheduler": SimpleNamespace(running=True), "erro": "failure"}), "indisponivel")
        with patch.dict(os.environ, {"FARMTECH_SIMULACAO": "0"}):
            self.assertEqual(scheduler.estado_simulacao({"erro": "old failure"}), "desativada")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker(sys.argv[2], Path(sys.argv[3]))
    else:
        unittest.main()
