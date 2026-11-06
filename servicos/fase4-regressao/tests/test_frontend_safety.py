"""Regressões de interface em subprocessos e cópias isoladas do módulo.

Nenhum AppTest aponta para a árvore original. Os modelos carregados são cópias
dos bytes históricos/pH verificados pela auditoria, nunca pickles de fixtures.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]
TRUSTED_MODELS = {
    "modelo_rainfall.joblib": "6fe9f2afc508254b85f184b6345da5b0aa8301b0423b2dc927671d6d2e01a75c",
    "modelo_humidity.joblib": "ffffce2e370fa7d19061337f364dd97235f3a10c477e1add1016735aa213c9f9",
    "modelo_ph.joblib": "0ab712d8a4765a4fddcac4315e9803b9df2e4f8a1e5f1efc789f2e5974166625",
}


def _copy_module(destination):
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", "*.db-*", ".env", "secrets.toml")
    for name in ("src", "scripts", "assets", ".streamlit"):
        shutil.copytree(SOURCE / name, destination / name, ignore=ignore)
    shutil.copy2(SOURCE / "main.py", destination / "main.py")
    # A F7 acrescenta uma dependência local de código, copiada para a fixture.
    # Serviços/dados das outras fases não são copiados nem executados por ela.
    integration = SOURCE.parents[1] / "farmtech_integracao"
    if integration.is_dir():
        shutil.copytree(integration, destination / "farmtech_integracao", ignore=ignore)


def _worker(scenario, root):
    os.chdir(root)
    sys.path.insert(0, str(root))
    os.environ["DB_PATH"] = str(root / "fixture.db")
    os.environ["FARMTECH_SIMULACAO"] = "0"
    for name, expected in TRUSTED_MODELS.items():
        if hashlib.sha256((root / "src/ml/models" / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("A cópia do artefato não corresponde à referência da auditoria.")
    from scripts.init_db import inicializar_banco
    inicializar_banco(root / "fixture.db")
    from src.db import database as db
    from streamlit.testing.v1 import AppTest

    def run(name):
        return AppTest.from_file(str(root / "src/frontend" / name), default_timeout=45).run()

    def snapshot(at):
        return {
            "exceptions": [item.message for item in at.exception],
            "errors": [item.value for item in at.error],
            "warnings": [item.value for item in at.warning],
            "success": [item.value for item in at.success],
            "captions": [item.value for item in at.caption],
            "metrics": {item.label: item.value for item in at.metric},
            "rows": db.get_previsoes(),
        }

    def button(at, label):
        return next(item for item in at.button if item.label == label)

    page = "pages/4_Previsao.py"
    if scenario == "smoke_eight_screens":
        # História existente em fixture: não representa o SQLite histórico ausente.
        with db.get_connection() as connection:
            connection.execute("INSERT INTO previsoes(ts,modelo,target,valor_previsto,parametros_entrada) VALUES ('2026-11-01 12:00:00','Ridge','ph',6.2,'{\"label\":\"apple\"}')")
        pages = ["app.py", *[str(path.relative_to(root / "src/frontend")) for path in sorted((root / "src/frontend/pages").glob("*.py"))]]
        # Os links entre páginas exigem o registro de st.navigation da entrada.
        at = run("app.py")
        result = {"app.py": snapshot(at)}
        for name in pages[1:]:
            at.switch_page(name).run()
            result[name] = snapshot(at)
    elif scenario == "recommend_zero_n":
        at = run("pages/5_Recomendacoes.py")
        for field in at.slider:
            if field.label == "N (kg/ha)":
                field.set_value(0)
            elif field.label == "P (kg/ha)":
                field.set_value(134)
            elif field.label == "K (kg/ha)":
                field.set_value(200)
        button(at, "Gerar Recomendacoes").click().run()
        result = snapshot(at)
    elif scenario == "corrupt_metrics":
        (root / "src/ml/models/metricas.json").write_text("{", encoding="utf-8")
        result = snapshot(run("pages/3_Pipeline_ML.py"))
    elif scenario == "altered_joblib":
        model = root / "src/ml/models/modelo_rainfall.joblib"
        model.write_bytes(b"\x00")  # não desserializável; o hash deve recusar antes da carga
        result = snapshot(run(page))
        result["altered_preserved"] = model.read_bytes() == b"\x00"
    elif scenario == "missing_ph_plot_dataset":
        from src.ml import ph_model
        # O diagnóstico histórico usa a cópia íntegra do dataset. O recurso de
        # visualização pH é direcionado a arquivo ausente, isolando essa falha.
        ph_model.DATASET_PATH = root / "private-missing-ph-plot.csv"
        at = run(page)
        button(at, "Estimar pH").click().run()
        result = snapshot(at)
    elif scenario in {"ph_nan", "ph_above_max", "original_above_max"}:
        at = run(page)
        if scenario == "ph_nan":
            at.number_input(key="ph_n").set_value(float("nan"))
            action = "Estimar pH"
        elif scenario == "ph_above_max":
            at.number_input(key="ph_humidity").set_value(101.0)
            action = "Estimar pH"
        else:
            at.slider[0].set_value(141)
            action = "Prever"
        button(at, action).click().run()
        result = snapshot(at)
    elif scenario == "pair_rollback":
        with db.get_connection() as connection:
            connection.execute("CREATE TRIGGER reject_humidity BEFORE INSERT ON previsoes WHEN NEW.target='humidity' BEGIN SELECT RAISE(ABORT,'private-fixture-trigger'); END")
        at = run(page)
        button(at, "Prever").click().run()
        result = snapshot(at)
    elif scenario == "ph_persistence_failure":
        with db.get_connection() as connection:
            connection.execute("CREATE TRIGGER reject_ph BEFORE INSERT ON previsoes WHEN NEW.target='ph' BEGIN SELECT RAISE(ABORT,'private-fixture-trigger'); END")
        at = run(page)
        button(at, "Estimar pH").click().run()
        result = snapshot(at)
    elif scenario == "golden_predictions":
        at = run(page)
        button(at, "Prever").click().run()
        original = snapshot(at)
        at = run(page)
        button(at, "Estimar pH").click().run()
        result = {"original": original, "ph": snapshot(at)}
    elif scenario == "history_compatibility":
        with db.get_connection() as connection:
            for parameters in ('{"label":"apple"}', '{"cultura":"rice"}', '{"label":"banana","cultura":"banana"}'):
                connection.execute("INSERT INTO previsoes(ts,modelo,target,valor_previsto,parametros_entrada) VALUES ('2026-11-01T12:00:00Z','Ridge','ph',6.2,?)", (parameters,))
        at = run("pages/6_Historico_Previsoes.py")
        result = snapshot(at)
        result["table"] = at.dataframe[0].value.to_dict("records")
        result["downloads"] = len(at.get("download_button"))
    else:
        raise ValueError("Cenário desconhecido.")
    from src.frontend.scheduler import encerrar_scheduler
    import threading
    encerrar_scheduler()
    print("F402_RESULT " + json.dumps({"result": result, "threads": [thread.name for thread in threading.enumerate() if thread.name == "APScheduler"]}, ensure_ascii=False, default=str))


class FrontendSafetyTests(unittest.TestCase):
    def run_scenario(self, scenario):
        with tempfile.TemporaryDirectory(prefix="farmtech-ui-tests-") as temporary:
            root = Path(temporary) / "module"
            root.mkdir()
            _copy_module(root)
            env = dict(os.environ, FARMTECH_SIMULACAO="0", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
            command = [sys.executable, "-X", "utf8", "-B", str(Path(__file__).resolve()), "--worker", scenario, str(root)]
            result = subprocess.run(command, cwd=temporary, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-4000:])
            payload = next(line.removeprefix("F402_RESULT ") for line in reversed(result.stdout.splitlines()) if line.startswith("F402_RESULT "))
            response = json.loads(payload)
            self.assertEqual(response["threads"], [])
            return response["result"]

    def assert_safe_failure(self, result, *, warning=False):
        self.assertEqual(result["exceptions"], [])
        messages = result["warnings"] if warning else result["errors"]
        self.assertTrue(messages, result)
        public = " ".join(result["errors"] + result["warnings"] + result["captions"])
        for internal in (str(SOURCE), "farmtech-ui-tests-", "Traceback", "private-fixture-trigger", "private-missing-ph-plot"):
            self.assertNotIn(internal, public)
        self.assertEqual(result["rows"], [])
        self.assertFalse(any("registrada" in caption for caption in result["captions"]))

    def test_original_and_integration_screens_render_without_unhandled_errors(self):
        results = self.run_scenario("smoke_eight_screens")
        # Home + sete páginas F4 preservadas + cinco páginas adicionais da F7.
        self.assertEqual(len(results), 13)
        for page, result in results.items():
            with self.subTest(page=page):
                self.assertEqual(result["exceptions"], [])
                self.assertEqual(result["errors"], [])

    def test_recommendations_consider_n_zero_independently(self):
        result = self.run_scenario("recommend_zero_n")
        self.assertEqual(result["exceptions"], [])
        self.assertTrue(any("N: 0 kg/ha" in message for message in result["warnings"]))
        self.assertFalse(any("N, P e K estao dentro" in message for message in result["success"]))

    def test_corrupt_metric_json_has_actionable_public_error(self):
        self.assert_safe_failure(self.run_scenario("corrupt_metrics"))

    def test_altered_joblib_is_refused_without_replacement(self):
        result = self.run_scenario("altered_joblib")
        self.assert_safe_failure(result)
        self.assertTrue(result["altered_preserved"])

    def test_missing_ph_plot_dataset_has_controlled_failure(self):
        self.assert_safe_failure(self.run_scenario("missing_ph_plot_dataset"))

    def test_nan_input_is_rejected_without_exception_or_record(self):
        self.assert_safe_failure(self.run_scenario("ph_nan"))

    def test_ph_above_allowed_humidity_cannot_be_persisted(self):
        result = self.run_scenario("ph_above_max")
        if result["errors"]:
            self.assert_safe_failure(result)
        else:
            # Streamlit 1.54 restaura o valor válido do widget antes da execução
            # do formulário. O teste direto de backend cobre a rejeição de 101;
            # aqui verificamos o valor efetivamente submetido e persistido.
            self.assertEqual(result["exceptions"], [])
            self.assertEqual(len(result["rows"]), 1)
            parameters = json.loads(result["rows"][0]["parametros_entrada"])
            self.assertGreaterEqual(parameters["humidity"], 0)
            self.assertLessEqual(parameters["humidity"], 100)

    def test_original_above_allowed_n_is_rejected(self):
        self.assert_safe_failure(self.run_scenario("original_above_max"))

    def test_pair_persistence_failure_rolls_back_both_forecasts(self):
        self.assert_safe_failure(self.run_scenario("pair_rollback"))

    def test_ph_persistence_failure_reports_estimate_not_recorded(self):
        result = self.run_scenario("ph_persistence_failure")
        self.assert_safe_failure(result, warning=True)
        self.assertTrue(any("não registrada" in message for message in result["warnings"]))

    def test_verified_models_match_golden_predictions_and_persist_valid_records(self):
        result = self.run_scenario("golden_predictions")
        self.assertEqual(result["original"]["exceptions"], [])
        self.assertEqual(result["original"]["errors"], [])
        rows = {row["target"]: row for row in result["ph"]["rows"]}
        self.assertEqual(set(rows), {"rainfall", "humidity", "ph"})
        self.assertAlmostEqual(rows["rainfall"]["valor_previsto"], 151.85176765282134, places=9)
        self.assertAlmostEqual(rows["humidity"]["valor_previsto"], 92.2544727194549, places=9)
        self.assertAlmostEqual(rows["ph"]["valor_previsto"], 6.201944848017306, places=10)
        params = json.loads(rows["ph"]["parametros_entrada"])
        self.assertEqual(params["cultura"], "apple")
        self.assertEqual(params["label"], "apple")
        self.assertTrue(any("experimental" in message for message in result["ph"]["warnings"]))
        self.assertTrue(any("média simples" in caption for caption in result["ph"]["captions"]))
        self.assertEqual(result["ph"]["metrics"]["pH estimado"], "6.202")

    def test_history_displays_old_and_new_ph_culture_keys(self):
        result = self.run_scenario("history_compatibility")
        self.assertEqual(result["exceptions"], [])
        self.assertEqual({row["Cultura"] for row in result["table"]}, {"apple", "rice", "banana"})
        self.assertEqual(result["downloads"], 1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        _worker(sys.argv[2], Path(sys.argv[3]))
    else:
        unittest.main()
