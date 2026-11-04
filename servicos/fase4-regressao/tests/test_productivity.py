import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.data_sources import SIDRA_OUTPUT_COLUMNS
from src.ml.productivity import (
    avaliar_produtividade,
    carregar_previsoes_produtividade,
)


def _historical_data() -> pd.DataFrame:
    rows = []
    for year in range(1990, 2026):
        rows.append(
            {
                "codigo_geografico": "1",
                "geografia": "Brasil",
                "municipio": None,
                "uf": None,
                "nivel_geografico": "brasil",
                "codigo_cultura": "2692",
                "cultura": "Arroz (em casca)",
                "ano": year,
                "rendimento_kg_ha": 3000 + (year - 1990) * 55,
                "unidade": "kg/ha",
            }
        )
    return pd.DataFrame(rows, columns=SIDRA_OUTPUT_COLUMNS)


class ProductivityTests(unittest.TestCase):
    def test_empty_forecast_artifact_represents_no_public_predictions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_dir = root / "models"
            model_dir.mkdir()
            pd.DataFrame(
                columns=[
                    "codigo_cultura",
                    "cultura",
                    "ano_previsao",
                    "rendimento_previsto_kg_ha",
                    "metodo_selecionado",
                ]
            ).to_csv(model_dir / "previsoes_produtividade.csv", index=False)
            self.assertIsNone(carregar_previsoes_produtividade(model_dir))

    def test_temporal_validation_compares_trend_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_path = root / "sidra.csv"
            _historical_data().to_csv(data_path, index=False)
            results = avaliar_produtividade(data_path, root / "models")

            rice = results["culturas"]["2692"]
            self.assertEqual(rice["anos_teste_temporal"], [2021, 2022, 2023, 2024, 2025])
            self.assertIn("regressao_linear_temporal", rice["validacao_selecao"])
            self.assertIn("persistencia_ultimo_ano", rice["validacao_selecao"])
            self.assertIn("mae", rice["teste_temporal"]["metodo_selecionado"])
            self.assertIn("rmse", rice["teste_temporal"]["metodo_selecionado"])
            self.assertIn("r2", rice["teste_temporal"]["metodo_selecionado"])

            forecasts = carregar_previsoes_produtividade(root / "models")
            self.assertIsNotNone(forecasts)
            self.assertEqual(int(forecasts.iloc[0]["ano_previsao"]), 2026)
            self.assertTrue((forecasts["rendimento_previsto_kg_ha"] >= 0).all())


if __name__ == "__main__":
    unittest.main()
