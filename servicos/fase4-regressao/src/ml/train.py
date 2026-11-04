"""
Pipeline de Machine Learning — FarmTech Solutions.
Treina modelos de regressão para rainfall e humidity a partir das amostras agronômicas.

Uso independente:
    python src/ml/train.py
"""

import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.db.database import get_amostras_agronomicas
from src.validation import validar_entrada_original
from src.ml.artifact_security import (
    DATASET_SHA256, HISTORICAL_COMPATIBILITY, ORIGINAL_COMMIT, ORIGINAL_HASHES,
    RESIDUAL_HASHES, HistoricalCompatibilityWarning, ModeloValidado,
    bytes_verificados, carregar_joblib_verificado, carregar_json, validar_runtime,
)

MODELS_DIR = ROOT / "src" / "ml" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_PATH = MODELS_DIR / "metricas.json"

TARGETS = ["chuva", "umidade"]
TARGET_LABELS = {"chuva": "rainfall", "umidade": "humidity"}
FEATURES_NUM = ["n", "p", "k", "temperatura", "ph"]
FEATURE_CAT = "cultura"
RANDOM_STATE = 42
K_FOLDS = 5


def _build_preprocessor() -> ColumnTransformer:
    """Cria o preprocessador com one-hot para cultura e passthrough para numéricas."""
    return ColumnTransformer(
        transformers=[
            ("num", "passthrough", FEATURES_NUM),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), [FEATURE_CAT]),
        ]
    )


def _build_models() -> dict:
    """Retorna dicionário de pipelines candidatos."""
    ridge_cv = GridSearchCV(
        Pipeline([("pre", _build_preprocessor()), ("ridge", Ridge())]),
        param_grid={"ridge__alpha": [0.1, 1.0, 10.0, 100.0]},
        cv=3,
        scoring="r2",
        n_jobs=-1,
    )
    models = {
        "LinearRegression": Pipeline(
            [("pre", _build_preprocessor()), ("lr", LinearRegression())]
        ),
        "Ridge": ridge_cv,
        "RandomForest": Pipeline(
            [
                ("pre", _build_preprocessor()),
                ("rf", RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE, n_jobs=-1)),
            ]
        ),
    }
    return models


def _avaliar(pipeline, X_train, X_test, y_train, y_test, nome: str) -> dict:
    """Treina o pipeline e calcula métricas de avaliação."""
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    mae = float(mean_absolute_error(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_test, y_pred))

    kf = KFold(n_splits=K_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(pipeline, pd.concat([X_train, X_test]), pd.concat([y_train, y_test]), cv=kf, scoring="r2", n_jobs=-1)

    return {
        "modelo": nome,
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2": r2,
        "cv_r2_media": float(cv_scores.mean()),
        "cv_r2_desvio": float(cv_scores.std()),
    }


def treinar(verbose: bool = True) -> dict:
    """
    Treina os modelos para todos os targets, persiste os melhores e salva métricas.

    Returns:
        dict com métricas por target.
    """
    if MODELS_DIR.resolve() == (ROOT / "src" / "ml" / "models").resolve():
        raise RuntimeError(
            "Treinamento histórico não altera os artefatos preservados. "
            "Uma substituição exige proposta e autorização específica."
        )
    amostras = get_amostras_agronomicas()
    if not amostras:
        raise RuntimeError("Nenhuma amostra agronômica encontrada. Execute scripts/init_db.py primeiro.")

    df = pd.DataFrame(amostras)

    resultados = {}

    for target in TARGETS:
        if verbose:
            print(f"\n=== Target: {target} ===")

        X = df[FEATURES_NUM + [FEATURE_CAT]]
        y = df[target]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=RANDOM_STATE
        )

        modelos = _build_models()
        metricas_target = []
        melhor_r2 = -np.inf
        melhor_nome = None
        melhor_pipeline = None

        for nome, pipeline in modelos.items():
            met = _avaliar(pipeline, X_train, X_test, y_train, y_test, nome)
            metricas_target.append(met)
            if verbose:
                print(
                    f"  {nome:20s} | R²={met['r2']:.4f} | MAE={met['mae']:.4f} "
                    f"| RMSE={met['rmse']:.4f} | CV R²={met['cv_r2_media']:.4f}±{met['cv_r2_desvio']:.4f}"
                )
            if met["r2"] > melhor_r2:
                melhor_r2 = met["r2"]
                melhor_nome = nome
                melhor_pipeline = pipeline

        if verbose:
            print(f"  Melhor modelo: {melhor_nome} (R²={melhor_r2:.4f})")

        # Persiste o melhor pipeline — usa label externo (rainfall/humidity) no nome do arquivo
        label = TARGET_LABELS.get(target, target)
        model_path = MODELS_DIR / f"modelo_{label}.joblib"
        joblib.dump(melhor_pipeline, model_path)
        if verbose:
            print(f"  Salvo em {model_path}")

        # Salva dados de resíduo e importância para o dashboard
        _salvar_artefatos_diagnostico(melhor_pipeline, melhor_nome, X_test, y_test, label)

        resultados[label] = {
            "melhor_modelo": melhor_nome,
            "metricas": metricas_target,
        }

    METRICS_PATH.write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    if verbose:
        print(f"\n[OK] Métricas salvas em {METRICS_PATH}")

    return resultados


def _salvar_artefatos_diagnostico(pipeline, nome_modelo: str, X_test, y_test, target: str) -> None:
    """Salva CSV com resíduos e importâncias para uso no dashboard."""
    y_pred = pipeline.predict(X_test)
    residuos = pd.DataFrame({
        "y_real": y_test.values,
        "y_previsto": y_pred,
        "residuo": y_test.values - y_pred,
    })
    residuos_path = MODELS_DIR / f"residuos_{target}.csv"
    residuos.to_csv(residuos_path, index=False)

    # Feature importance — apenas para RandomForest
    if nome_modelo == "RandomForest":
        try:
            rf_step = pipeline.named_steps["rf"]
            pre_step = pipeline.named_steps["pre"]
            num_names = FEATURES_NUM
            cat_names = list(
                pre_step.named_transformers_["cat"].get_feature_names_out([FEATURE_CAT])
            )
            feature_names = num_names + cat_names
            importances = rf_step.feature_importances_
            imp_df = pd.DataFrame({"feature": feature_names, "importance": importances})
            imp_df = imp_df.sort_values("importance", ascending=False)
            imp_path = MODELS_DIR / f"importancias_{target}.csv"
            imp_df.to_csv(imp_path, index=False)
        except Exception:
            pass


def preparar_entrada_historica(n, p, k, temperatura, ph, cultura) -> pd.DataFrame:
    """Contrato de inferência dos modelos históricos, também fora da interface."""
    return pd.DataFrame([validar_entrada_original({
        "n": n, "p": p, "k": k, "temperatura": temperatura,
        "ph": ph, "cultura": cultura,
    })])


def carregar_modelo(target: str):
    """Carga restrita aos bytes históricos revisados; não aceita joblib externo."""
    if not isinstance(target, str) or target not in ORIGINAL_HASHES:
        raise ValueError("Alvo de modelo histórico não reconhecido.")
    model_path = MODELS_DIR / f"modelo_{target}.joblib"
    if not model_path.is_file():
        return None
    validar_runtime()
    dataset_bytes = bytes_verificados(
        ROOT / "src" / "dados" / "Atividade_Cap10_produtos_agricolas.csv",
        DATASET_SHA256, "Dataset de referência alterado; diagnóstico do modelo recusado.",
    )
    residual_bytes = bytes_verificados(
        MODELS_DIR / f"residuos_{target}.csv", RESIDUAL_HASHES[target],
        "Resíduos de referência alterados; diagnóstico do modelo recusado.",
    )
    model, version_warnings = carregar_joblib_verificado(model_path, ORIGINAL_HASHES[target])
    from io import BytesIO
    frame = pd.read_csv(BytesIO(dataset_bytes)).rename(columns={
        "N": "n", "P": "p", "K": "k", "temperature": "temperatura",
        "label": "cultura", "humidity": "umidade", "rainfall": "chuva",
    })
    feature_names = FEATURES_NUM + [FEATURE_CAT]
    if list(getattr(model, "feature_names_in_", [])) != feature_names:
        raise RuntimeError("Schema do modelo histórico incompatível; carga recusada.")
    _, X_test, _, y_test = train_test_split(
        frame[feature_names], frame[{"rainfall": "chuva", "humidity": "umidade"}[target]],
        test_size=0.2, random_state=RANDOM_STATE,
    )
    reference = pd.read_csv(BytesIO(residual_bytes))
    try:
        predicted = np.asarray(model.predict(X_test), dtype=float)
        valid = (
            predicted.shape == (440,) and np.isfinite(predicted).all()
            and np.allclose(reference["y_real"], y_test, rtol=0, atol=1e-10)
            and np.allclose(reference["y_previsto"], predicted, rtol=0, atol=1e-8)
        )
    except (ValueError, TypeError, AttributeError) as error:
        raise RuntimeError("Diagnóstico de compatibilidade do modelo falhou.") from error
    if not valid:
        raise RuntimeError("Modelo não reproduz as 440 previsões de referência; carga recusada.")
    diagnostic = {
        "commit_origem": ORIGINAL_COMMIT, "sha256_modelo": ORIGINAL_HASHES[target],
        "scikit_learn_runtime": "1.6.1", "scikit_learn_serializacao": "1.9.0",
        "n_previsoes_verificadas": 440, "avisos_versao": version_warnings,
        "ressalva": HISTORICAL_COMPATIBILITY,
    }
    warnings.warn(HISTORICAL_COMPATIBILITY, HistoricalCompatibilityWarning, stacklevel=2)
    return ModeloValidado(model, target, diagnostic)


def carregar_metricas() -> dict | None:
    """Carrega o JSON de métricas salvo após o treinamento."""
    if not METRICS_PATH.exists():
        return None
    result = carregar_json(METRICS_PATH)
    try:
        if set(result) != set(ORIGINAL_HASHES):
            raise ValueError
        for target in ORIGINAL_HASHES:
            group = result[target]
            if not isinstance(group["melhor_modelo"], str) or not group["metricas"]:
                raise ValueError
            selected = False
            for row in group["metricas"]:
                selected |= row["modelo"] == group["melhor_modelo"]
                for key in ("mae", "mse", "rmse", "r2", "cv_r2_media", "cv_r2_desvio"):
                    from src.validation import numero_finito
                    numero_finito(row[key], key, 0 if key in {"mae", "mse", "rmse", "cv_r2_desvio"} else None)
            if not selected:
                raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Schema das métricas históricas inválido.") from error
    return result


if __name__ == "__main__":
    treinar(verbose=True)
