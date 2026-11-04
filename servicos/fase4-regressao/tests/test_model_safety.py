"""Regressões F4-02: contratos, procedência e compatibilidade dos modelos."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from src.ml import artifact_security as security, ph_model, productivity, train
from src.validation import validar_entrada_original, validar_entrada_ph, validar_valor_previsto


ORIGINAL = dict(n=60, p=55, k=44, temperatura=25, ph=6.5, cultura="apple")
PH = dict(N=60, P=55, K=44, temperature=25, humidity=70, rainfall=100, label="apple")


class InputContractTests(unittest.TestCase):
    def test_boundaries_and_zero_are_valid(self):
        for n in (0, 140):
            self.assertEqual(validar_entrada_original({**ORIGINAL, "n": n})["n"], n)
        for value in (0, 100):
            self.assertEqual(validar_entrada_ph({**PH, "humidity": value})["humidity"], value)
        for values in (
            dict(n=0, p=5, k=5, temperatura=5, ph=3.5, cultura="rice"),
            dict(n=140, p=145, k=205, temperatura=50, ph=10, cultura="rice"),
        ):
            validar_entrada_original(values)
        for values in (
            dict(N=0, P=0, K=0, temperature=5, humidity=0, rainfall=0, label="rice"),
            dict(N=140, P=145, K=205, temperature=50, humidity=100, rainfall=300, label="rice"),
        ):
            validar_entrada_ph(values)

    def test_invalid_numeric_values_are_rejected(self):
        for validator, base, key in ((validar_entrada_original, ORIGINAL, "n"), (validar_entrada_ph, PH, "N")):
            for value in (-1, 141, np.nan, np.inf, -np.inf, None, True, "60", [], {}):
                with self.subTest(validator=validator.__name__, value=value):
                    with self.assertRaises(ValueError):
                        validator({**base, key: value})

    def test_missing_unknown_and_target_fields_are_rejected(self):
        for values in ({**PH, "label": "unknown"}, {**PH, "label": None}, {**PH, "label": 2},
                       {key: value for key, value in PH.items() if key != "N"}, {**PH, "ph": 6.5}):
            with self.assertRaises(ValueError):
                validar_entrada_ph(values)

    def test_historical_ph_key_alias_is_consistent(self):
        self.assertEqual(validar_entrada_ph({**PH, "cultura": "apple"}), validar_entrada_ph(PH))
        with self.assertRaises(ValueError):
            validar_entrada_ph({**PH, "cultura": "rice"})

    def test_prediction_targets_are_finite_and_bounded(self):
        for target, value in (("ph", 15), ("rainfall", -1), ("humidity", 101), ("other", 1), ([], 1), ("ph", np.nan), ("rainfall", np.inf)):
            with self.assertRaises(ValueError):
                validar_valor_previsto(target, value)


class ModelProvenanceTests(unittest.TestCase):
    def test_invalid_target_cannot_become_path(self):
        for target in ("../../arbitrary", [], None):
            with self.assertRaises(ValueError):
                train.carregar_modelo(target)

    def test_corrupt_original_is_refused_before_deserialization(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for file in ("modelo_rainfall.joblib", "residuos_rainfall.csv"):
                shutil.copy2(train.MODELS_DIR / file, directory / file)
            (directory / "modelo_rainfall.joblib").write_bytes(b"not a pickle")
            with patch.object(train, "MODELS_DIR", directory), patch.object(security.joblib, "load") as load:
                with self.assertRaisesRegex(RuntimeError, "Integridade do modelo"):
                    train.carregar_modelo("rainfall")
                load.assert_not_called()

    def test_wrong_runtime_is_refused_before_deserialization(self):
        with patch.object(security.sklearn, "__version__", "0.0.0"), patch.object(security.joblib, "load") as load:
            with self.assertRaisesRegex(RuntimeError, "Runtime"):
                train.carregar_modelo("rainfall")
            load.assert_not_called()

    def test_reference_corruption_is_refused_before_deserialization(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            shutil.copy2(train.MODELS_DIR / "modelo_rainfall.joblib", directory / "modelo_rainfall.joblib")
            (directory / "residuos_rainfall.csv").write_bytes(b"bad reference")
            with patch.object(train, "MODELS_DIR", directory), patch.object(security.joblib, "load") as load:
                with self.assertRaisesRegex(RuntimeError, "Resíduos"):
                    train.carregar_modelo("rainfall")
                load.assert_not_called()

    def test_numerically_incompatible_model_is_refused(self):
        class Wrong:
            feature_names_in_ = train.FEATURES_NUM + [train.FEATURE_CAT]
            def predict(self, frame):
                return np.zeros(len(frame))
        with patch.object(train, "carregar_joblib_verificado", return_value=(Wrong(), [])):
            with self.assertRaisesRegex(RuntimeError, "440 previsões"):
                train.carregar_modelo("rainfall")

    def test_same_directory_hash_does_not_authorize_external_ph_pickle(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            metadata = json.loads(ph_model.METADATA_PATH.read_text(encoding="utf-8"))
            payload = b"untrusted pickle"
            metadata["sha256_modelo"] = hashlib.sha256(payload).hexdigest()
            (directory / ph_model.MODEL_PATH.name).write_bytes(payload)
            (directory / ph_model.METADATA_PATH.name).write_text(json.dumps(metadata), encoding="utf-8")
            with patch.object(security.joblib, "load") as load:
                with self.assertRaisesRegex(RuntimeError, "procedência"):
                    ph_model.carregar_modelo_ph(directory)
                load.assert_not_called()

    def test_exact_copy_of_reviewed_ph_can_be_loaded(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for source in (ph_model.MODEL_PATH, ph_model.METADATA_PATH):
                shutil.copy2(source, directory / source.name)
            model = ph_model.carregar_modelo_ph(directory)
            self.assertAlmostEqual(model.predict(pd.DataFrame([PH]))[0], 6.201944848017306)

    def test_loaded_predict_rejects_backend_invalid_input(self):
        model = ph_model.carregar_modelo_ph()
        for entry in ({**PH, "N": 141}, {**PH, "humidity": np.nan}, {**PH, "label": "unknown"}):
            with self.assertRaises(ValueError):
                model.predict(pd.DataFrame([entry]))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            historical = train.carregar_modelo("rainfall")
        self.assertTrue(any(issubclass(item.category, security.HistoricalCompatibilityWarning) for item in caught))
        self.assertEqual(len(historical.diagnostico["avisos_versao"]), 11)
        with self.assertRaises(ValueError):
            historical.predict(pd.DataFrame([{**ORIGINAL, "n": 141}]))

    def test_invalid_model_output_is_rejected(self):
        class Bad:
            def predict(self, frame):
                return [np.inf] * len(frame)
        with self.assertRaises(RuntimeError):
            security.ModeloValidado(Bad(), "ph", {}).predict(pd.DataFrame([PH]))

    def test_metric_json_corruption_and_nonfinite_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "metricas.json"
            for payload in ("{bad", '{"rainfall":NaN}', '{"rainfall":{"melhor_modelo":"Ridge"}}'):
                file.write_text(payload, encoding="utf-8")
                with patch.object(train, "METRICS_PATH", file):
                    with self.assertRaises(ValueError):
                        train.carregar_metricas()

    def test_json_overflow_and_duplicate_keys_are_rejected_without_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "diagnostico.json"
            for payload in ('{"a":[{"b":1e999}]}', '{"a":{"x":1,"x":2}}'):
                with self.subTest(payload=payload):
                    file.write_text(payload, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        security.carregar_json(file)

    def test_training_does_not_overwrite_historical_artifacts(self):
        with patch.object(train, "get_amostras_agronomicas") as db, patch.object(train.joblib, "dump") as dump:
            with self.assertRaisesRegex(RuntimeError, "preservados"):
                train.treinar(verbose=False)
            db.assert_not_called()
            dump.assert_not_called()

    def test_ph_training_refuses_packaged_directory_before_loading_or_writing(self):
        with patch.object(ph_model, "_load_dataset") as load, patch.object(ph_model.joblib, "dump") as dump:
            for arguments in ({}, {"models_dir": ph_model.MODELS_DIR, "dataset_path": Path("missing.csv")}):
                with self.subTest(arguments=arguments), self.assertRaisesRegex(RuntimeError, "preservado"):
                    ph_model.treinar_modelo_ph(**arguments, verbose=False)
            load.assert_not_called()
            dump.assert_not_called()

    def test_ph_cli_refuses_default_training_without_traceback(self):
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-B", "-m", "src.ml.ph_model"],
            cwd=ph_model.ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preservados", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn(str(ph_model.MODEL_PATH), result.stderr)


class ProductivityArtifactTests(unittest.TestCase):
    def test_nonfinite_unknown_schema_and_inconsistent_forecasts_are_rejected(self):
        base = dict(codigo_cultura="2692", cultura="Arroz (em casca)", ano_previsao=2026,
                    rendimento_previsto_kg_ha=3000, metodo_selecionado="Regressão linear temporal",
                    ultimo_ano_observado=2025, ultimo_rendimento_observado_kg_ha=2900, validacao_ate_ano=2025)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            crop = {"previsao_disponivel": True, "metodo_selecionado": "Regressão linear temporal", "teste_temporal": {
                "metodo_selecionado": {"mae": 1, "rmse": 2, "r2": .8},
                "persistencia_ultimo_ano": {"mae": 10, "rmse": 11, "r2": .1},
            }}
            metrics = {"previsao_disponivel": True, "culturas": {"2692": crop}}
            (directory / productivity.METRICS_FILENAME).write_text(json.dumps(metrics), encoding="utf-8")
            (directory / productivity.METADATA_FILENAME).write_text(json.dumps({"previsao_disponivel": True, "previsao_para": [2026]}), encoding="utf-8")
            pd.DataFrame([base]).to_csv(directory / productivity.FORECAST_FILENAME, index=False)
            self.assertEqual(len(productivity.carregar_previsoes_produtividade(directory)), 1)
            for value in (np.nan, np.inf, -np.inf, -1):
                pd.DataFrame([{**base, "rendimento_previsto_kg_ha": value}]).to_csv(directory / productivity.FORECAST_FILENAME, index=False)
                with self.subTest(value=value), self.assertRaises(ValueError):
                    productivity.carregar_previsoes_produtividade(directory)
            for row in ({**base, "ano_previsao": 2026.5}, {**base, "cultura": "Other"}, {**base, "validacao_ate_ano": 2024},
                        {key: value for key, value in base.items() if key != "ultimo_ano_observado"}, {**base, "extra": 1}):
                pd.DataFrame([row]).to_csv(directory / productivity.FORECAST_FILENAME, index=False)
                with self.assertRaises(ValueError):
                    productivity.carregar_previsoes_produtividade(directory)
            crop["teste_temporal"]["metodo_selecionado"]["r2"] = -.2
            (directory / productivity.METRICS_FILENAME).write_text(json.dumps(metrics), encoding="utf-8")
            pd.DataFrame([base]).to_csv(directory / productivity.FORECAST_FILENAME, index=False)
            with self.assertRaises(ValueError):
                productivity.carregar_previsoes_produtividade(directory)


class ScientificReproductionTests(unittest.TestCase):
    def test_originals_reproduce_440_predictions_and_metrics_without_retraining(self):
        frame = pd.read_csv(ph_model.DATASET_PATH).rename(columns={
            "N": "n", "P": "p", "K": "k", "temperature": "temperatura", "label": "cultura",
        })
        metrics = train.carregar_metricas()
        for target in ("rainfall", "humidity"):
            with warnings.catch_warnings(record=True):
                model = train.carregar_modelo(target)
            _, test, _, observed = train_test_split(frame[train.FEATURES_NUM + [train.FEATURE_CAT]], frame[target], test_size=.2, random_state=42)
            predicted = model.predict(test)
            expected = next(row for row in metrics[target]["metricas"] if row["modelo"] == metrics[target]["melhor_modelo"])
            self.assertEqual(model.diagnostico["n_previsoes_verificadas"], 440)
            self.assertAlmostEqual(mean_absolute_error(observed, predicted), expected["mae"], places=10)
            self.assertAlmostEqual(r2_score(observed, predicted), expected["r2"], places=10)

    def test_ph_metrics_and_crop_mean_baseline_are_preserved(self):
        frame = pd.read_csv(ph_model.DATASET_PATH)
        train_x, test, train_y, observed = train_test_split(frame[ph_model.FEATURES], frame.ph, test_size=.2, random_state=42, stratify=frame.label)
        model = ph_model.carregar_modelo_ph()
        predicted = model.predict(test)
        metrics = ph_model.carregar_metricas_ph()["teste_reservado"]
        self.assertAlmostEqual(mean_absolute_error(observed, predicted), metrics["mae"], places=12)
        self.assertAlmostEqual(mean_squared_error(observed, predicted), metrics["mse"], places=12)
        self.assertAlmostEqual(r2_score(observed, predicted), metrics["r2"], places=12)
        baseline = test.label.map(train_y.groupby(train_x.label).mean())
        self.assertAlmostEqual(mean_absolute_error(observed, baseline), .4278357605674432, places=12)
        self.assertAlmostEqual(r2_score(observed, baseline), .3288132455783588, places=12)

    def test_productivity_temporal_metrics_and_block_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            reproduced = productivity.avaliar_produtividade(models_dir=directory)
            recorded = json.loads((productivity.MODELS_DIR / productivity.METRICS_FILENAME).read_text(encoding="utf-8"))
            self.assertEqual(reproduced, recorded)
            self.assertFalse(reproduced["previsao_disponivel"])
            self.assertTrue(all(item["teste_temporal"]["metodo_selecionado"]["r2"] < 0 for item in reproduced["culturas"].values()))
            self.assertIsNone(productivity.carregar_previsoes_produtividade(directory))


if __name__ == "__main__":
    unittest.main()
