"""Estimativa experimental de rendimento médio nacional com validação temporal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.data_sources import SIDRA_CROPS, SIDRA_NATIONAL_CSV, carregar_sidra
from src.ml.artifact_security import carregar_json
from src.validation import numero_finito

ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = ROOT / "src" / "ml" / "models"
MODEL_FILENAME = "modelo_produtividade.joblib"
METRICS_FILENAME = "metricas_produtividade.json"
FORECAST_FILENAME = "previsoes_produtividade.csv"
METADATA_FILENAME = "modelo_produtividade_metadata.json"
MIN_HISTORY_YEARS = 15
VALIDATION_YEARS = 5
TEST_YEARS = 5
FORECAST_COLUMNS = [
    "codigo_cultura", "cultura", "ano_previsao", "rendimento_previsto_kg_ha",
    "metodo_selecionado", "ultimo_ano_observado",
    "ultimo_rendimento_observado_kg_ha", "validacao_ate_ano",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metrics(observed: list[float], predicted: list[float]) -> dict[str, float]:
    mse = float(mean_squared_error(observed, predicted))
    return {
        "mae": float(mean_absolute_error(observed, predicted)),
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(observed, predicted)),
    }


def _walk_forward(
    series: pd.DataFrame, target_years: list[int]
) -> tuple[list[int], list[float], list[float], list[float]]:
    years: list[int] = []
    observed: list[float] = []
    trend: list[float] = []
    persistence: list[float] = []
    for year in target_years:
        train = series.loc[series["ano"] < year]
        actual = series.loc[series["ano"] == year, "rendimento_kg_ha"]
        previous_year = series.loc[series["ano"] == year - 1, "rendimento_kg_ha"]
        if (
            train["ano"].nunique() < MIN_HISTORY_YEARS
            or actual.empty
            or previous_year.empty
        ):
            continue
        model = LinearRegression()
        model.fit(train[["ano"]], train["rendimento_kg_ha"])
        years.append(int(year))
        observed.append(float(actual.iloc[0]))
        trend.append(float(model.predict(pd.DataFrame({"ano": [year]}))[0]))
        persistence.append(float(previous_year.iloc[-1]))
    return years, observed, trend, persistence


def avaliar_produtividade(
    data_path: Path = SIDRA_NATIONAL_CSV,
    models_dir: Path = MODELS_DIR,
) -> dict[str, Any]:
    """Avalia regressão temporal contra persistência e gera previsão anual agregada."""
    models_dir = Path(models_dir).resolve()
    preserved_dir = (ROOT / "src" / "ml" / "models").resolve()
    output_paths = [models_dir] + [
        (models_dir / filename).resolve()
        for filename in (
            MODEL_FILENAME, METRICS_FILENAME, FORECAST_FILENAME, METADATA_FILENAME
        )
    ]
    existing_outputs = [path for path in output_paths[1:] if path.is_file()]
    if any(path.is_relative_to(preserved_dir) for path in output_paths) or any(
        output.samefile(artifact)
        for artifact in preserved_dir.rglob("*")
        if artifact.is_file()
        for output in existing_outputs
    ):
        raise RuntimeError(
            "Artefatos de produtividade preservados; avaliações exigem "
            "diretório de saída isolado fora de src/ml/models."
        )
    data_path = Path(data_path)
    frame = carregar_sidra(data_path)
    frame = frame[
        (frame["nivel_geografico"] == "brasil")
        & frame["codigo_cultura"].isin(SIDRA_CROPS)
    ].dropna(subset=["rendimento_kg_ha"])

    by_crop: dict[str, dict[str, Any]] = {}
    forecasts: list[dict[str, Any]] = []
    fitted_models: dict[str, LinearRegression] = {}
    for crop_code, crop_name in SIDRA_CROPS.items():
        series = frame.loc[
            frame["codigo_cultura"] == crop_code, ["ano", "rendimento_kg_ha"]
        ].sort_values("ano")
        series = series.drop_duplicates("ano")
        if series["ano"].nunique() < MIN_HISTORY_YEARS:
            continue

        history_years = series["ano"].tolist()
        validation_years = history_years[-(VALIDATION_YEARS + TEST_YEARS):-TEST_YEARS]
        test_years = history_years[-TEST_YEARS:]
        validated_years, val_observed, val_trend, val_persistence = _walk_forward(
            series, validation_years
        )
        evaluated_years, test_observed, test_trend, test_persistence = _walk_forward(
            series, test_years
        )
        if len(val_observed) < 3 or len(test_observed) < 3:
            continue

        validation_trend_metrics = _metrics(val_observed, val_trend)
        validation_persistence_metrics = _metrics(val_observed, val_persistence)
        selected_method = (
            "Regressão linear temporal"
            if validation_trend_metrics["mae"] < validation_persistence_metrics["mae"]
            else "Persistência (último ano)"
        )
        test_trend_metrics = _metrics(test_observed, test_trend)
        test_persistence_metrics = _metrics(test_observed, test_persistence)
        selected_test_metrics = (
            test_trend_metrics
            if selected_method == "Regressão linear temporal"
            else test_persistence_metrics
        )

        full_model = LinearRegression()
        full_model.fit(series[["ano"]], series["rendimento_kg_ha"])
        fitted_models[crop_code] = full_model
        last_year = int(series["ano"].max())
        next_year = last_year + 1
        raw_trend = float(full_model.predict(pd.DataFrame({"ano": [next_year]}))[0])
        forecast_value = (
            raw_trend
            if selected_method == "Regressão linear temporal"
            else float(series.iloc[-1]["rendimento_kg_ha"])
        )
        prediction_available = (
            selected_method == "Regressão linear temporal"
            and selected_test_metrics["r2"] > 0
            and selected_test_metrics["mae"] < test_persistence_metrics["mae"]
        )
        if prediction_available:
            forecasts.append(
                {
                "codigo_cultura": crop_code,
                "cultura": crop_name,
                "ano_previsao": next_year,
                "rendimento_previsto_kg_ha": max(0.0, forecast_value),
                "metodo_selecionado": selected_method,
                "ultimo_ano_observado": last_year,
                "ultimo_rendimento_observado_kg_ha": float(
                    series.iloc[-1]["rendimento_kg_ha"]
                ),
                "validacao_ate_ano": max(evaluated_years),
                }
            )
        by_crop[crop_code] = {
            "cultura": crop_name,
            "anos_validacao_modelo": validated_years,
            "anos_teste_temporal": evaluated_years,
            "n_anos_historicos": int(series["ano"].nunique()),
            "validacao_selecao": {
                "regressao_linear_temporal": validation_trend_metrics,
                "persistencia_ultimo_ano": validation_persistence_metrics,
            },
            "teste_temporal": {
                "metodo_selecionado": selected_test_metrics,
                "persistencia_ultimo_ano": test_persistence_metrics,
            },
            "metodo_selecionado": selected_method,
            "previsao_disponivel": prediction_available,
        }

    if not by_crop:
        raise ValueError(
            "Nenhuma cultura tem histórico suficiente para validação temporal."
        )

    results = {
        "fonte": "IBGE/SIDRA tabela 1612 — rendimento médio agregado nacional",
        "unidade": "kg/ha",
        "variavel_de_entrada": "ano (conhecido antes da previsão)",
        "alvo": "rendimento médio oficial por cultura e ano",
        "validacao": (
            "selecao em cinco períodos walk-forward anteriores ao teste; teste "
            "temporal reservado nos cinco anos mais recentes; treino em cada "
            "período usa somente anos anteriores"
        ),
        "culturas": by_crop,
        "previsao_disponivel": bool(forecasts),
        "status": (
            "estimativa experimental; associação temporal não implica causalidade"
            if forecasts
            else (
                "somente histórico: o teste temporal reservado não demonstrou "
                "skill preditivo suficiente frente ao baseline"
            )
        ),
    }

    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / MODEL_FILENAME
    metrics_path = models_dir / METRICS_FILENAME
    forecast_path = models_dir / FORECAST_FILENAME
    metadata_path = models_dir / METADATA_FILENAME
    joblib.dump(fitted_models, model_path)
    pd.DataFrame(forecasts, columns=FORECAST_COLUMNS).to_csv(forecast_path, index=False)
    metrics_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metadata = {
        "sha256_dataset_sidra": _sha256(data_path),
        "sha256_modelo": _sha256(model_path),
        "periodo_treino": [
            int(frame["ano"].min()),
            int(frame["ano"].max()),
        ],
        "previsao_para": sorted(
            {int(forecast["ano_previsao"]) for forecast in forecasts}
        ),
        "minimo_anos_historicos": MIN_HISTORY_YEARS,
        "algoritmo": "LinearRegression por cultura",
        "criterio_selecao": "menor MAE walk-forward que baseline de persistência",
        "nao_utiliza_rendimento_como_feature": True,
        "previsao_disponivel": bool(forecasts),
        "motivo_sem_previsao": (
            None
            if forecasts
            else "R² temporal reservado não positivo para as culturas avaliadas."
        ),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return results


def carregar_previsoes_produtividade(
    models_dir: Path = MODELS_DIR,
) -> pd.DataFrame | None:
    path = Path(models_dir) / FORECAST_FILENAME
    if not path.is_file():
        return None
    try:
        frame = pd.read_csv(path, dtype={"codigo_cultura": str})
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise ValueError("Arquivo de previsões de produtividade inválido.") from error
    required = {
        "codigo_cultura",
        "cultura",
        "ano_previsao",
        "rendimento_previsto_kg_ha",
        "metodo_selecionado",
    }
    if not required.issubset(frame.columns):
        raise ValueError("Schema de previsões de produtividade inválido.")
    if frame.empty:
        return None
    if set(frame.columns) != set(FORECAST_COLUMNS) or frame.columns.duplicated().any():
        raise ValueError("Schema completo de previsões de produtividade inválido.")
    if frame.isna().any().any() or frame["codigo_cultura"].duplicated().any():
        raise ValueError("Previsões de produtividade incompletas ou duplicadas.")

    metrics = carregar_json(Path(models_dir) / METRICS_FILENAME)
    metadata = carregar_json(Path(models_dir) / METADATA_FILENAME)
    try:
        if metrics["previsao_disponivel"] is not True or metadata["previsao_disponivel"] is not True:
            raise ValueError
        for row in frame.to_dict("records"):
            code = row["codigo_cultura"]
            if code not in SIDRA_CROPS or row["cultura"] != SIDRA_CROPS[code]:
                raise ValueError
            for column in ("rendimento_previsto_kg_ha", "ultimo_rendimento_observado_kg_ha"):
                numero_finito(row[column], column, 0)
            for column in ("ano_previsao", "ultimo_ano_observado", "validacao_ate_ano"):
                year = numero_finito(row[column], column, 1900, 2200)
                if not year.is_integer():
                    raise ValueError
            if row["ano_previsao"] != row["ultimo_ano_observado"] + 1:
                raise ValueError
            if row["validacao_ate_ano"] != row["ultimo_ano_observado"]:
                raise ValueError
            if row["ano_previsao"] not in metadata["previsao_para"]:
                raise ValueError
            crop = metrics["culturas"][code]
            if crop["previsao_disponivel"] is not True:
                raise ValueError
            if row["metodo_selecionado"] != crop["metodo_selecionado"] or row["metodo_selecionado"] != "Regressão linear temporal":
                raise ValueError
            selected = crop["teste_temporal"]["metodo_selecionado"]
            baseline = crop["teste_temporal"]["persistencia_ultimo_ano"]
            for test in (selected, baseline):
                for name in ("mae", "rmse", "r2"):
                    numero_finito(test[name], name, 0 if name != "r2" else None)
            if selected["r2"] <= 0 or selected["mae"] >= baseline["mae"]:
                raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Previsão de produtividade inconsistente ou sem desempenho demonstrado.") from error
    return frame


if __name__ == "__main__":
    results = avaliar_produtividade()
    for code, result in results["culturas"].items():
        test = result["teste_temporal"]["metodo_selecionado"]
        print(
            f"{result['cultura']}: {result['metodo_selecionado']} | "
            f"MAE={test['mae']:.2f} kg/ha | RMSE={test['rmse']:.2f} kg/ha "
            f"| R²={test['r2']:.4f}"
        )
