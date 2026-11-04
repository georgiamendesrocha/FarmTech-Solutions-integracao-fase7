import json
import hashlib
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.ml.ph_model import (
    DATASET_PATH,
    FEATURES,
    TARGET,
    carregar_modelo_ph,
    preparar_entrada_ph,
    treinar_modelo_ph,
)


class PhModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.models_dir = Path(cls.temp_dir.name)
        cls.metrics = treinar_modelo_ph(
            dataset_path=DATASET_PATH,
            models_dir=cls.models_dir,
            verbose=False,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_training_persists_test_metrics_and_reloads_pipeline(self) -> None:
        model = carregar_modelo_ph(self.models_dir)
        self.assertIsNotNone(model)
        self.assertEqual(self.metrics["n_amostras"], 2200)
        self.assertEqual(self.metrics["n_teste"], 440)
        self.assertIn("mae", self.metrics["teste_reservado"])
        self.assertIn("mse", self.metrics["teste_reservado"])
        self.assertIn("rmse", self.metrics["teste_reservado"])
        self.assertIn("r2", self.metrics["teste_reservado"])
        expected = {
            "mae": 0.4279210985937805, "mse": 0.362534461587942,
            "rmse": 0.602108347050547, "r2": 0.32910794902476237,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(self.metrics["teste_reservado"][key], value, places=12)
        # A serialização pode variar sem alterar as métricas; o pacote preservado
        # tem hash fixo no loader, e cada novo treino precisa corresponder ao seu.
        metadata = json.loads((self.models_dir / "modelo_ph_metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256((self.models_dir / "modelo_ph.joblib").read_bytes()).hexdigest(),
            metadata["sha256_modelo"],
        )

        entry = preparar_entrada_ph(90, 42, 43, 21, 82, 203, "rice")
        prediction = float(model.predict(entry)[0])
        self.assertTrue(pd.notna(prediction))
        self.assertEqual(list(entry.columns), FEATURES)

        saved_metrics = json.loads(
            (self.models_dir / "metricas_ph.json").read_text(encoding="utf-8")
        )
        self.assertEqual(saved_metrics["modelo_selecionado"], self.metrics["modelo_selecionado"])

    def test_target_is_never_an_input(self) -> None:
        self.assertNotIn(TARGET, FEATURES)
        entry = preparar_entrada_ph(90, 42, 43, 21, 82, 203, "rice")
        self.assertNotIn(TARGET, entry.columns)

    def test_model_hash_mismatch_is_rejected(self) -> None:
        model_path = self.models_dir / "modelo_ph.joblib"
        original_model = model_path.read_bytes()
        try:
            model_path.write_bytes(original_model + b"tampered")
            with self.assertRaisesRegex(RuntimeError, "Hash do modelo pH"):
                carregar_modelo_ph(self.models_dir)
        finally:
            model_path.write_bytes(original_model)

    def test_dataset_schema_errors_are_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_dataset = Path(temp_dir) / "missing_ph.csv"
            pd.DataFrame({"N": [1], "label": ["rice"]}).to_csv(bad_dataset, index=False)
            with self.assertRaisesRegex(ValueError, "Colunas obrigatórias ausentes"):
                treinar_modelo_ph(bad_dataset, Path(temp_dir) / "models", verbose=False)


if __name__ == "__main__":
    unittest.main()
