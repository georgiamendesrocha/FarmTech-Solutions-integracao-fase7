"""Pipeline experimental para estimar pH usando apenas variáveis de entrada."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.validation import numero_finito, validar_entrada_ph
from src.ml.artifact_security import (
    ModeloValidado, carregar_joblib_verificado, carregar_json, hash_confiavel_ph,
    registrar_artefato_gerado, validar_runtime,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "src" / "dados" / "Atividade_Cap10_produtos_agricolas.csv"
MODELS_DIR = ROOT / "src" / "ml" / "models"
MODEL_PATH = MODELS_DIR / "modelo_ph.joblib"
METADATA_PATH = MODELS_DIR / "modelo_ph_metadata.json"
METRICS_PATH = MODELS_DIR / "metricas_ph.json"
RESIDUALS_PATH = MODELS_DIR / "residuos_ph.csv"

FEATURES_NUM = ["N", "P", "K", "temperature", "humidity", "rainfall"]
FEATURE_CAT = "label"
FEATURES = FEATURES_NUM + [FEATURE_CAT]
TARGET = "ph"
RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_pipeline(estimator: Any) -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            ("num", StandardScaler(), FEATURES_NUM),
            ("cat", OneHotEncoder(handle_unknown="ignore"), [FEATURE_CAT]),
        ]
    )
    return Pipeline([("pre", preprocessor), ("model", estimator)])


def _load_dataset(dataset_path: Path) -> pd.DataFrame:
    if not dataset_path.is_file():
        raise FileNotFoundError("Dataset agronômico não encontrado.")

    frame = pd.read_csv(dataset_path)
    required = set(FEATURES + [TARGET])
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes no dataset: {sorted(missing)}")
    if TARGET in FEATURES:
        raise ValueError("Vazamento: pH não pode ser usado como variável de entrada.")

    frame = frame[FEATURES + [TARGET]].copy()
    if frame.isna().any().any():
        raise ValueError("Dataset contém valores ausentes nas variáveis do modelo.")
    for row in frame.to_dict("records"):
        numero_finito(row.pop(TARGET), "pH observado", 0, 14)
        validar_entrada_ph(row)
    return frame


def treinar_modelo_ph(
    dataset_path: Path = DATASET_PATH,
    models_dir: Path = MODELS_DIR,
    verbose: bool = True,
) -> dict[str, Any]:
    """Compara modelos por validação no treino e avalia o teste reservado uma vez."""
    models_dir = Path(models_dir)
    if models_dir.resolve() == (ROOT / "src" / "ml" / "models").resolve():
        raise RuntimeError(
            "Modelo experimental de pH preservado. Recupere os artefatos do backup "
            "verificado; treinos de diagnóstico exigem diretório isolado explícito."
        )
    dataset_path = Path(dataset_path)
    frame = _load_dataset(dataset_path)
    X = frame[FEATURES]
    y = frame[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=X[FEATURE_CAT],
    )

    splitter = StratifiedKFold(
        n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE
    )
    folds = list(splitter.split(X_train, X_train[FEATURE_CAT]))
    candidates: list[tuple[str, Any, float, dict[str, Any]]] = []

    baseline = _build_pipeline(DummyRegressor(strategy="mean"))
    baseline_scores = np.asarray(
        [
            r2_score(y_train.iloc[validation], clone(baseline).fit(
                X_train.iloc[training], y_train.iloc[training]
            ).predict(X_train.iloc[validation]))
            for training, validation in folds
        ]
    )
    baseline.fit(X_train, y_train)
    baseline_prediction = baseline.predict(X_test)
    baseline_metrics = _regression_metrics(y_test, baseline_prediction)
    candidates.append(
        ("Baseline (média)", baseline, float(baseline_scores.mean()), baseline_metrics)
    )

    ridge = GridSearchCV(
        _build_pipeline(Ridge()),
        param_grid={"model__alpha": [0.1, 1.0, 10.0, 100.0]},
        cv=folds,
        scoring="r2",
        n_jobs=1,
        refit=True,
    )
    estimators: list[tuple[str, Any]] = [
        ("LinearRegression", _build_pipeline(LinearRegression())),
        ("Ridge", ridge),
        (
            "RandomForest",
            _build_pipeline(
                RandomForestRegressor(
                    n_estimators=100, random_state=RANDOM_STATE, n_jobs=1
                )
            ),
        ),
    ]

    for name, estimator in estimators:
        if isinstance(estimator, GridSearchCV):
            estimator.fit(X_train, y_train)
            fitted = estimator.best_estimator_
            cv_mean = float(estimator.best_score_)
            best_params = estimator.best_params_
        else:
            scores = np.asarray(
                [
                    r2_score(
                        y_train.iloc[validation],
                        clone(estimator)
                        .fit(X_train.iloc[training], y_train.iloc[training])
                        .predict(X_train.iloc[validation]),
                    )
                    for training, validation in folds
                ]
            )
            estimator.fit(X_train, y_train)
            fitted = estimator
            cv_mean = float(scores.mean())
            best_params = {}

        test_metrics = _regression_metrics(y_test, fitted.predict(X_test))
        candidates.append((name, fitted, cv_mean, {**test_metrics, "params": best_params}))

    model_candidates = [item for item in candidates if item[0] != "Baseline (média)"]
    selected_name, selected_pipeline, selected_cv, _ = max(
        model_candidates, key=lambda item: item[2]
    )
    selected_metrics = _regression_metrics(y_test, selected_pipeline.predict(X_test))

    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / MODEL_PATH.name
    metadata_path = models_dir / METADATA_PATH.name
    metrics_path = models_dir / METRICS_PATH.name
    residuals_path = models_dir / RESIDUALS_PATH.name
    joblib.dump(selected_pipeline, model_path)

    residuals = pd.DataFrame(
        {
            "observado": y_test.to_numpy(),
            "previsto": selected_pipeline.predict(X_test),
            "residuo": y_test.to_numpy() - selected_pipeline.predict(X_test),
        },
        index=y_test.index,
    )
    residuals.to_csv(residuals_path, index_label="indice_dataset")

    metrics = {
        "target": TARGET,
        "status": "experimental",
        "n_amostras": int(len(frame)),
        "n_treino": int(len(X_train)),
        "n_teste": int(len(X_test)),
        "features": FEATURES,
        "alvo_excluido_das_features": TARGET not in FEATURES,
        "modelo_selecionado": selected_name,
        "selecao": "maior R² médio na validação cruzada estratificada do conjunto de treino",
        "cv_r2_medio_selecionado": selected_cv,
        "teste_reservado": selected_metrics,
        "modelos": [
            {
                "modelo": name,
                "cv_r2_medio": cv_mean,
                "teste": test_metrics,
            }
            for name, _, cv_mean, test_metrics in candidates
        ],
    }
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    metadata = {
        **metrics,
        "arquivo_dataset": dataset_path.name,
        "sha256_dataset": _sha256(dataset_path),
        "sha256_modelo": _sha256(model_path),
        "scikit_learn": sklearn.__version__,
        "pandas": pd.__version__,
        "python": sys.version.split()[0],
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "cv_folds": CV_FOLDS,
        "treinado_em_utc": datetime.now(timezone.utc).isoformat(),
        "limitacoes": [
            "Dataset acadêmico de condições agronômicas; não representa validação local de campo.",
            "Associação estatística não demonstra causalidade nem efeito de manejo.",
            "Cultura é informada previamente pelo usuário; pH não participa das entradas.",
            "Uso experimental até validação independente por agrônomos e medições locais.",
        ],
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    registrar_artefato_gerado(model_path)

    if verbose:
        print(
            f"pH: {selected_name}; CV R²={selected_cv:.4f}; "
            f"teste R²={selected_metrics['r2']:.4f}; "
            f"MAE={selected_metrics['mae']:.4f}; RMSE={selected_metrics['rmse']:.4f}"
        )
    return metrics


def _regression_metrics(observed: Any, predicted: Any) -> dict[str, float]:
    mse = float(mean_squared_error(observed, predicted))
    return {
        "mae": float(mean_absolute_error(observed, predicted)),
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(observed, predicted)),
    }


def carregar_modelo_ph(models_dir: Path = MODELS_DIR) -> ModeloValidado | None:
    """Carrega somente artefato acompanhado de metadados e hash íntegro."""
    models_dir = Path(models_dir)
    model_path = models_dir / MODEL_PATH.name
    metadata_path = models_dir / METADATA_PATH.name
    if not model_path.is_file() or not metadata_path.is_file():
        return None

    validar_runtime()
    metadata = carregar_json(metadata_path)
    if metadata.get("sha256_modelo") != _sha256(model_path):
        raise RuntimeError("Hash do modelo pH diverge dos metadados; carga recusada.")
    if metadata.get("target") != TARGET or metadata.get("features") != FEATURES:
        raise RuntimeError("Metadados do modelo pH incompatíveis; carga recusada.")
    if metadata.get("scikit_learn") != "1.6.1":
        raise RuntimeError("Versão de serialização do modelo pH não validada; carga recusada.")

    expected_hash = hash_confiavel_ph(model_path, MODEL_PATH)
    model, version_warnings = carregar_joblib_verificado(model_path, expected_hash)
    if version_warnings:
        raise RuntimeError("Modelo pH com avisos de compatibilidade; carga recusada.")
    if list(model.feature_names_in_) != FEATURES:
        raise RuntimeError("Schema do pipeline pH diverge das features registradas.")
    return ModeloValidado(model, "ph", {
        "sha256_modelo": expected_hash, "scikit_learn_runtime": "1.6.1",
        "status": "experimental", "avisos_versao": version_warnings,
    })


def carregar_metricas_ph(models_dir: Path = MODELS_DIR) -> dict[str, Any] | None:
    metrics_path = Path(models_dir) / METRICS_PATH.name
    if not metrics_path.is_file():
        return None
    result = carregar_json(metrics_path)
    try:
        if result["target"] != TARGET or result["features"] != FEATURES or result["status"] != "experimental":
            raise ValueError
        if not isinstance(result["modelo_selecionado"], str) or not result["modelos"]:
            raise ValueError
        numero_finito(result["cv_r2_medio_selecionado"], "R² da validação")
        selected = False
        for row in result["modelos"]:
            selected |= row["modelo"] == result["modelo_selecionado"]
            numero_finito(row["cv_r2_medio"], "R² da validação")
            for key in ("mae", "mse", "rmse", "r2"):
                numero_finito(row["teste"][key], key, 0 if key != "r2" else None)
        for key in ("mae", "mse", "rmse", "r2"):
            numero_finito(result["teste_reservado"][key], key, 0 if key != "r2" else None)
        if not selected:
            raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Schema das métricas de pH inválido.") from error
    return result


def preparar_entrada_ph(
    n: float,
    p: float,
    k: float,
    temperature: float,
    humidity: float,
    rainfall: float,
    culture: str,
) -> pd.DataFrame:
    """Cria entrada tipada sem permitir que pH seja informado como feature."""
    values = {
        "N": n,
        "P": p,
        "K": k,
        "temperature": temperature,
        "humidity": humidity,
        "rainfall": rainfall,
        "label": culture,
    }
    return pd.DataFrame([validar_entrada_ph(values)], columns=FEATURES)


if __name__ == "__main__":
    try:
        treinar_modelo_ph()
    except (OSError, ValueError, RuntimeError):
        print(
            "[ERRO] Treinamento de pH não concluído. Os artefatos empacotados "
            "estão preservados; recupere o backup verificado ou use um diretório "
            "isolado explícito para diagnóstico.",
            file=sys.stderr,
        )
        raise SystemExit(1)
