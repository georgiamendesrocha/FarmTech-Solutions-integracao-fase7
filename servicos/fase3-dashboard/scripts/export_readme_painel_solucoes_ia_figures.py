"""
Exporta figuras do Painel IA · soluções para `assets/readme/`.

Gera (quando dados existem):

Aba Irrigação (bomba_fw):
  painel_ia_01_bomba_fw_comparacao_modelos.png
  painel_ia_02_bomba_fw_matriz_confusao.png
  painel_ia_03_bomba_fw_prob_ultima_leitura.png

Aba Culturas (Atividade_Cap10_produtos_agricolas) — redesenhada:
  painel_ia_04_culturas_comparacao_modelos.png
  painel_ia_05_culturas_matriz_confusao.png
  painel_ia_06_culturas_feature_importance.png
  painel_ia_07_culturas_metricas_por_classe.png
  painel_ia_08_culturas_recomendador_top5.png
  painel_ia_09_culturas_radar_perfil.png

Sugestão de irrigação (5 dias × clima × IA):
  painel_ia_10_irrigacao_sugestao_5_dias.png  (requer Oracle WTH_DAILY_FORECAST)

Baseado na lógica de `src/frontend/pages/painel_solucoes_ia.py`.

Uso (raiz do repositório, venv activo):
  python scripts/export_readme_painel_solucoes_ia_figures.py
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy connectable.*", category=UserWarning)

import numpy as np
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.db import execute_query

OUT_DIR = ROOT / "assets" / "readme"
CSV_IOT = ROOT / "src" / "dados" / "historico_irrigacao.csv"
AGRI = ROOT / "src" / "dados" / "Atividade_Cap10_produtos_agricolas.csv"

load_dotenv(ROOT / ".env", override=True)

# --- Rótulos (alinhados ao painel) ---
_LBL_ON = "Ligada"
_LBL_OFF = "Desligada"
_LBL_REV = "Rever"


def _num_row(row: dict, key: str, default: float = 0.0) -> float:
    v = row.get(key)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _classificar_irrigacao_dia(
    prob_chuva_max: float,
    mm_chuva_dia: float,
    temp_max: float,
    p_media_modelos: float | None,
    umidade_solo_ult: float,
) -> tuple[str, str]:
    chuva_forte = prob_chuva_max >= 55.0 or mm_chuva_dia >= 4.0
    chuva_moderada = prob_chuva_max >= 40.0 or mm_chuva_dia >= 1.5
    tempo_seco = prob_chuva_max < 35.0 and mm_chuva_dia < 0.8
    calor = temp_max >= 29.0
    solo_seco = bool(np.isfinite(umidade_solo_ult) and umidade_solo_ult < 42.0)

    if chuva_forte:
        return _LBL_OFF, "Chuva prevista neste dia. Mantenha a bomba desligada."

    ia_quer_ligar = p_media_modelos is not None and p_media_modelos >= 0.5
    ia_quer_cortar = p_media_modelos is not None and p_media_modelos < 0.42

    if chuva_moderada and not ia_quer_ligar:
        return _LBL_OFF, "Alguma chuva prevista. Evite regar salvo indicação contrária no campo."

    if tempo_seco and (calor or solo_seco):
        if p_media_modelos is None:
            return _LBL_ON, "Tempo seco. Considere ligar a irrigação se o solo estiver abaixo do ideal."
        if ia_quer_ligar:
            return _LBL_ON, "Tempo seco e os modelos sugerem necessidade de rega (última leitura)."
        return _LBL_REV, "Tempo seco, mas os modelos não reforçam rega. Confirme a umidade do solo."

    if p_media_modelos is not None:
        if ia_quer_ligar and solo_seco and not chuva_moderada:
            return _LBL_ON, "Solo abaixo do conforto e modelos apontam para rega."
        if ia_quer_cortar and not tempo_seco:
            return _LBL_OFF, "Modelos indicam pouca necessidade de rega neste contexto."

    return _LBL_REV, "Sinais mistos. Veja sensores no campo antes de decidir."


def _carregar_iot_oracle() -> pd.DataFrame:
    user = os.getenv("ORACLE_USER")
    pwd = os.getenv("ORACLE_PASS")
    dsn = os.getenv("ORACLE_DSN")
    if not (user and pwd and dsn):
        raise ValueError("ORACLE_* ausentes.")
    with oracledb.connect(user=user, password=pwd, dsn=dsn) as conn:
        df = pd.read_sql(
            "SELECT UMIDADE, TEMP_C, PH_CORR, N, P, K, BOMBA_FW, TS_ISO FROM SENSORES_FARMTECH",
            conn,
        )
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _carregar_iot_csv() -> pd.DataFrame:
    if not CSV_IOT.is_file():
        raise FileNotFoundError(str(CSV_IOT))
    df = pd.read_csv(CSV_IOT, encoding="utf-8")
    df.columns = [str(c).strip().lower() for c in df.columns]
    for old, new in (("temperatura", "temp_c"), ("ph", "ph_corr")):
        if new not in df.columns and old in df.columns:
            df[new] = df[old]
    for col in ("n", "p", "k"):
        if col not in df.columns:
            df[col] = 0
    if "bomba_fw" not in df.columns:
        df["bomba_fw"] = df.get("irrigation", 0)
    return df


def _prepare_bomba_df(df: pd.DataFrame) -> pd.DataFrame | None:
    need = {"umidade", "temp_c", "ph_corr", "n", "p", "k", "bomba_fw"}
    if not need.issubset(set(df.columns)):
        return None
    d = df.copy()
    for c in ("umidade", "temp_c", "ph_corr", "bomba_fw"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    for c in ("n", "p", "k"):
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).clip(0, 1)
    d = d.dropna(subset=["umidade", "temp_c", "ph_corr", "bomba_fw"])
    if len(d) < 15:
        return None
    return d


def _compare_models_bomba(d: pd.DataFrame):
    FEATURES = ["umidade", "temp_c", "ph_corr", "n", "p", "k"]
    TARGET = "bomba_fw"
    X = d[FEATURES].values.astype(float)
    y = d[TARGET].values.astype(int).clip(0, 1)
    X_scaled = StandardScaler().fit_transform(X)
    split_kwargs: dict = {"test_size": 0.25, "random_state": 42}
    if pd.Series(y).value_counts().min() >= 2:
        split_kwargs["stratify"] = y
    try:
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, **split_kwargs)
    except ValueError:
        split_kwargs.pop("stratify", None)
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, **split_kwargs)

    modelos = {
        "Regressao Logistica": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=120, random_state=42, max_depth=8),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42, max_depth=3, n_estimators=80),
        "k-NN": KNeighborsClassifier(n_neighbors=max(1, min(5, len(X_train) // 4))),
        "Naive Bayes": GaussianNB(),
    }
    min_cls = int(pd.Series(y).value_counts().min())
    n_splits = min(5, min_cls) if min_cls >= 2 else 0
    usar_cv = n_splits >= 2 and len(y) >= 10

    linhas = []
    probs_ultimo: dict[str, float] = {}
    fitted: dict[str, object] = {}
    x_last = X_scaled[-1:, :]

    for nome, modelo in modelos.items():
        modelo.fit(X_train, y_train)
        fitted[nome] = modelo
        pred = modelo.predict(X_test)
        acc = float(accuracy_score(y_test, pred))
        f1 = float(f1_score(y_test, pred, average="binary", zero_division=0))
        cv_acc = float("nan")
        if usar_cv:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            cv_acc = float(cross_val_score(modelo, X_scaled, y, cv=cv, scoring="accuracy").mean())
        linhas.append({"Modelo": nome, "Acuracia_teste": acc, "F1_teste": f1, "Acuracia_CV": cv_acc})
        if hasattr(modelo, "predict_proba"):
            probs_ultimo[nome] = float(modelo.predict_proba(x_last)[0][1])
        else:
            probs_ultimo[nome] = float(modelo.predict(x_last)[0])

    resultado = pd.DataFrame(linhas).sort_values("Acuracia_teste", ascending=False)
    melhor = resultado.iloc[0]["Modelo"]
    pred_b = fitted[melhor].predict(X_test)
    cm = confusion_matrix(y_test, pred_b, labels=[0, 1])
    return resultado, melhor, cm, probs_ultimo


PRODUTOS_FEATURES = ["N", "P", "K", "temp_c", "umidade", "ph_corr", "chuva"]


def _compare_models_produtos() -> dict | None:
    """Devolve um pacote completo (modelos, scaler, métricas, perfis) — espelha
    `_produtos_pkg` em `painel_solucoes_ia.py`.
    """
    if not AGRI.is_file():
        return None
    df = pd.read_csv(AGRI, encoding="utf-8")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    m = {
        "temperature": "temp_c",
        "humidity": "umidade",
        "ph": "ph_corr",
        "rainfall": "chuva",
        "n": "N",
        "p": "P",
        "k": "K",
        "nitrogen": "N",
        "phosphorous": "P",
        "phosphorus": "P",
        "potassium": "K",
        "crop": "label",
        "crop_type": "label",
    }
    df = df.rename(columns={k: v for k, v in m.items() if k in df.columns and v not in df.columns})
    req = PRODUTOS_FEATURES + ["label"]
    for c in req[:-1]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["label"] = df["label"].astype(str).str.strip()
    df = df.dropna(subset=req).reset_index(drop=True)
    if len(df) < 20:
        return None

    X = df[PRODUTOS_FEATURES].to_numpy(dtype=float, copy=True)
    y = df["label"].astype(str).to_numpy(copy=True)
    scaler = StandardScaler().fit(X)
    X_scaled = scaler.transform(X)
    sk: dict = {"test_size": 0.25, "random_state": 42}
    if pd.Series(y).value_counts().min() >= 2:
        sk["stratify"] = y
    try:
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, **sk)
    except ValueError:
        sk.pop("stratify", None)
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, **sk)

    modelos = {
        "Regressao Logistica": LogisticRegression(max_iter=1200, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42, max_depth=10),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42),
        "k-NN": KNeighborsClassifier(n_neighbors=max(3, min(7, len(X_train) // 6))),
        "Naive Bayes": GaussianNB(),
    }
    min_cls = int(pd.Series(y).value_counts().min())
    n_splits = min(5, min_cls) if min_cls >= 2 else 0
    usar_cv = n_splits >= 2 and len(y) >= 10

    linhas = []
    fitted: dict = {}
    for nome, modelo in modelos.items():
        modelo.fit(X_train, y_train)
        fitted[nome] = modelo
        pred = modelo.predict(X_test)
        acc = float(accuracy_score(y_test, pred))
        f1w = float(f1_score(y_test, pred, average="weighted", zero_division=0))
        cv_acc = float("nan")
        if usar_cv:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            cv_acc = float(cross_val_score(modelo, X_scaled, y, cv=cv, scoring="accuracy").mean())
        linhas.append({"Modelo": nome, "Acuracia_teste": acc, "F1_ponderado": f1w, "Acuracia_CV": cv_acc})

    resultado = pd.DataFrame(linhas).sort_values("Acuracia_teste", ascending=False).reset_index(drop=True)
    melhor = resultado.iloc[0]["Modelo"]
    clf_best = fitted[melhor]
    classes = list(clf_best.classes_)

    pred_best = clf_best.predict(X_test)
    cm = confusion_matrix(y_test, pred_best, labels=classes)
    prec, rec, f1c, sup = precision_recall_fscore_support(
        y_test, pred_best, labels=classes, zero_division=0
    )
    per_class = pd.DataFrame(
        {
            "Cultura": classes,
            "Precisao": prec,
            "Recall": rec,
            "F1": f1c,
            "Suporte": sup.astype(int),
        }
    ).sort_values("F1", ascending=False).reset_index(drop=True)

    perfil_culturas = (
        df.groupby("label", as_index=False)[PRODUTOS_FEATURES]
        .mean()
        .round(2)
        .rename(columns={"label": "Cultura"})
    )

    return {
        "df": df,
        "features": PRODUTOS_FEATURES,
        "scaler": scaler,
        "fitted": fitted,
        "melhor": melhor,
        "resultado": resultado,
        "classes": classes,
        "cm": cm,
        "per_class": per_class,
        "perfil_culturas": perfil_culturas,
        "medianas": df[PRODUTOS_FEATURES].median().to_dict(),
    }


def _feature_importance_pkg(pkg: dict) -> tuple[pd.DataFrame, str]:
    nome = pkg["melhor"]
    clf = pkg["fitted"][nome]
    feats = pkg["features"]
    if hasattr(clf, "feature_importances_"):
        imp = clf.feature_importances_
        modo = "Importancia Gini"
    elif hasattr(clf, "coef_"):
        imp = np.mean(np.abs(clf.coef_), axis=0)
        if imp.sum() > 0:
            imp = imp / imp.sum()
        modo = "|w| normalizado"
    else:
        return pd.DataFrame(columns=["Feature", "Importancia"]), "indisponivel"
    return (
        pd.DataFrame({"Feature": feats, "Importancia": imp})
        .sort_values("Importancia", ascending=False)
        .reset_index(drop=True),
        modo,
    )


def _write(fig: go.Figure, name: str, height: int = 900) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(OUT_DIR / name), width=1600, height=height, scale=2)
    print(f"[OK] {name}")


def _daily_5(id_loc: int) -> pd.DataFrame:
    return pd.DataFrame(
        execute_query(
            """
            SELECT DT_FORECAST, NR_TEMP_MAX,
                   NVL(NR_PRECIP_SUM, 0) AS NR_PRECIP_SUM,
                   NVL(NR_RAIN_SUM, 0) AS NR_RAIN_SUM,
                   NVL(NR_PRECIP_PROB_MAX, 0) AS NR_PRECIP_PROB_MAX
            FROM WTH_DAILY_FORECAST
            WHERE ID_LOCATION = :l
              AND DT_FORECAST >= TRUNC(SYSDATE)
              AND DT_FORECAST < TRUNC(SYSDATE) + 5
            ORDER BY DT_FORECAST
            """,
            {"l": id_loc},
        )
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        df_iot = _carregar_iot_oracle()
        print("[INFO] IoT: Oracle")
    except Exception as e:
        print(f"[INFO] IoT: CSV ({e})")
        df_iot = _carregar_iot_csv()

    d_prep = _prepare_bomba_df(df_iot)
    probs_bomba: dict[str, float] = {}
    ultima_umid = (
        float(pd.to_numeric(df_iot.iloc[-1]["umidade"], errors="coerce"))
        if len(df_iot) and "umidade" in df_iot.columns
        else float("nan")
    )
    p_media = None

    if d_prep is not None:
        resultado_b, melhor_b, cm_b, probs_bomba = _compare_models_bomba(d_prep)
        p_media = float(np.mean(list(probs_bomba.values()))) if probs_bomba else None

        fig1 = go.Figure()
        fig1.add_trace(
            go.Bar(name="Acurácia (teste)", x=resultado_b["Modelo"], y=resultado_b["Acuracia_teste"], offsetgroup=0)
        )
        fig1.add_trace(go.Bar(name="F1 (teste)", x=resultado_b["Modelo"], y=resultado_b["F1_teste"], offsetgroup=1))
        fig1.update_layout(
            title="Painel IA — Comparação dos cinco modelos (bomba_fw)",
            barmode="group",
            yaxis=dict(range=[0, 1.05]),
            xaxis_tickangle=-20,
            height=420,
            margin=dict(t=56, b=120, l=64, r=48),
            legend=dict(orientation="h", yanchor="top", y=-0.15, x=0),
        )
        _write(fig1, "painel_ia_01_bomba_fw_comparacao_modelos.png", height=860)

        fig_cm = go.Figure(
            data=go.Heatmap(
                z=cm_b,
                x=["Pred. OFF", "Pred. ON"],
                y=["Real OFF", "Real ON"],
                colorscale="Blues",
                text=cm_b,
                texttemplate="%{text}",
            )
        )
        fig_cm.update_layout(
            title=f"Painel IA — Matriz de confusão (melhor: {melhor_b})",
            height=440,
            margin=dict(t=56, l=96, r=48, b=72),
        )
        _write(fig_cm, "painel_ia_02_bomba_fw_matriz_confusao.png", height=640)

        modelos_ord = list(probs_bomba.keys())
        vals = [probs_bomba[m] for m in modelos_ord]
        fig_p = go.Figure(go.Bar(x=vals, y=modelos_ord, orientation="h", marker_color="#1a5f3a"))
        fig_p.update_layout(
            title="Painel IA — P(bomba ligada | última leitura) por modelo",
            xaxis=dict(range=[0, 1], title="Probabilidade"),
            height=400,
            margin=dict(t=56, l=200, r=48, b=72),
        )
        _write(fig_p, "painel_ia_03_bomba_fw_prob_ultima_leitura.png", height=680)
    else:
        print("[SKIP] Bomba FW: menos de 15 linhas válidas ou colunas em falta — figuras 01–03 não geradas.")

    pkg = _compare_models_produtos()
    if pkg:
        resultado_p = pkg["resultado"]
        melhor_p = pkg["melhor"]
        classes_p = pkg["classes"]
        cm_p = pkg["cm"]

        # 04 — Comparação dos 5 modelos (Culturas)
        fig2 = go.Figure()
        fig2.add_trace(
            go.Bar(name="Acurácia (teste)", x=resultado_p["Modelo"], y=resultado_p["Acuracia_teste"], offsetgroup=0)
        )
        fig2.add_trace(
            go.Bar(name="F1 ponderado", x=resultado_p["Modelo"], y=resultado_p["F1_ponderado"], offsetgroup=1)
        )
        fig2.update_layout(
            title=f"Painel IA — Comparação dos cinco modelos (culturas) · melhor: {melhor_p}",
            barmode="group",
            yaxis=dict(range=[0, 1.05]),
            xaxis_tickangle=-20,
            height=420,
            margin=dict(t=56, b=120, l=64, r=48),
            legend=dict(orientation="h", yanchor="top", y=-0.15, x=0),
        )
        _write(fig2, "painel_ia_04_culturas_comparacao_modelos.png", height=860)

        # 05 — Matriz de confusão multiclasse do melhor modelo
        fig_cm_p = px.imshow(
            cm_p,
            x=classes_p,
            y=classes_p,
            color_continuous_scale="Blues",
            aspect="auto",
            labels=dict(x="Previsto", y="Real", color="Contagem"),
            text_auto=True,
            title=f"Painel IA — Matriz de confusão multiclasse (culturas · {melhor_p})",
        )
        fig_cm_p.update_layout(
            height=max(420, 22 * len(classes_p) + 220),
            margin=dict(t=64, l=120, r=48, b=140),
            xaxis_tickangle=-30,
        )
        _write(
            fig_cm_p,
            "painel_ia_05_culturas_matriz_confusao.png",
            height=max(720, 30 * len(classes_p) + 320),
        )

        # 06 — Importância das features para o melhor modelo
        imp_df, modo_imp = _feature_importance_pkg(pkg)
        if not imp_df.empty:
            fig_imp = px.bar(
                imp_df,
                x="Importancia",
                y="Feature",
                orientation="h",
                text=imp_df["Importancia"].map(lambda v: f"{v:.2f}"),
                color="Importancia",
                color_continuous_scale="Greens",
                title=f"Painel IA — Importância das variáveis ({modo_imp}) · {melhor_p}",
            )
            fig_imp.update_layout(
                yaxis=dict(autorange="reversed"),
                coloraxis_showscale=False,
                height=420,
                margin=dict(t=56, l=180, r=72, b=72),
            )
            _write(fig_imp, "painel_ia_06_culturas_feature_importance.png", height=620)
        else:
            print(f"[SKIP] Importância indisponível para o modelo `{melhor_p}` — figura 06 não gerada.")

        # 07 — Métricas por classe (precisão · recall · F1)
        per_class = pkg["per_class"]
        per_long = per_class.melt(
            id_vars=["Cultura"],
            value_vars=["Precisao", "Recall", "F1"],
            var_name="Métrica",
            value_name="Valor",
        )
        fig_pc = px.bar(
            per_long,
            x="Cultura",
            y="Valor",
            color="Métrica",
            barmode="group",
            range_y=[0, 1.05],
            title=f"Painel IA — Métricas por cultura (precisão · recall · F1) · {melhor_p}",
        )
        fig_pc.update_layout(
            xaxis_tickangle=-30,
            height=460,
            margin=dict(t=56, b=140, l=64, r=48),
            legend=dict(orientation="h", yanchor="top", y=-0.18, x=0),
        )
        _write(fig_pc, "painel_ia_07_culturas_metricas_por_classe.png", height=860)

        # 08 — Recomendador (top 5) sobre um perfil exemplo: medianas do dataset
        medianas = pkg["medianas"]
        x_exemplo = np.array([[medianas[f] for f in pkg["features"]]], dtype=float)
        x_scaled = pkg["scaler"].transform(x_exemplo)
        clf_best = pkg["fitted"][melhor_p]
        if hasattr(clf_best, "predict_proba"):
            probs_exemplo = clf_best.predict_proba(x_scaled)[0]
        else:
            probs_exemplo = np.zeros(len(classes_p))
            probs_exemplo[list(classes_p).index(clf_best.predict(x_scaled)[0])] = 1.0

        rank = (
            pd.DataFrame({"Cultura": classes_p, "Probabilidade": probs_exemplo})
            .sort_values("Probabilidade", ascending=False)
            .reset_index(drop=True)
        )
        top_n = min(5, len(rank))
        top = rank.head(top_n)
        fig_top = px.bar(
            top,
            x="Probabilidade",
            y="Cultura",
            orientation="h",
            text=top["Probabilidade"].map(lambda v: f"{v:.1%}"),
            color="Probabilidade",
            color_continuous_scale="Greens",
        )
        fig_top.update_layout(
            yaxis=dict(autorange="reversed"),
            xaxis=dict(range=[0, 1], tickformat=".0%"),
            coloraxis_showscale=False,
            title=f"Painel IA — Recomendador: top {top_n} culturas (perfil mediano · {melhor_p})",
            height=380,
            margin=dict(t=56, b=64, l=160, r=72),
        )
        _write(fig_top, "painel_ia_08_culturas_recomendador_top5.png", height=620)

        # 09 — Radar perfil ideal (TOP1) vs perfil exemplo (mediano)
        cult_top = top.iloc[0]["Cultura"]
        perfil_ideal_row = pkg["perfil_culturas"][pkg["perfil_culturas"]["Cultura"] == cult_top]
        if not perfil_ideal_row.empty:
            perfil_ideal = perfil_ideal_row.iloc[0][pkg["features"]].astype(float)
            perfil_atual = pd.Series([medianas[f] for f in pkg["features"]], index=pkg["features"])
            norm = perfil_ideal.abs().clip(lower=1e-6) + perfil_atual.abs().clip(lower=1e-6)
            ideal_norm = (perfil_ideal / norm).fillna(0).tolist()
            atual_norm = (perfil_atual / norm).fillna(0).tolist()
            radar_categorias = pkg["features"] + [pkg["features"][0]]
            fig_radar = go.Figure()
            fig_radar.add_trace(
                go.Scatterpolar(
                    r=ideal_norm + [ideal_norm[0]],
                    theta=radar_categorias,
                    fill="toself",
                    name=f"Ideal · {cult_top}",
                    line=dict(color="#2d7a4f"),
                )
            )
            fig_radar.add_trace(
                go.Scatterpolar(
                    r=atual_norm + [atual_norm[0]],
                    theta=radar_categorias,
                    fill="toself",
                    name="Perfil mediano (exemplo)",
                    line=dict(color="#e76f51"),
                    opacity=0.7,
                )
            )
            fig_radar.update_layout(
                title=f"Painel IA — Perfil ideal vs perfil mediano · cultura {cult_top}",
                polar=dict(radialaxis=dict(visible=False)),
                height=460,
                margin=dict(t=64, b=64, l=48, r=48),
                legend=dict(orientation="h", yanchor="top", y=-0.05, x=0),
            )
            _write(fig_radar, "painel_ia_09_culturas_radar_perfil.png", height=760)
        else:
            print(f"[SKIP] Perfil da cultura `{cult_top}` indisponível — figura 09 não gerada.")
    else:
        print("[SKIP] Culturas: ficheiro em falta ou poucos registos — figuras 04–09 não geradas.")

    try:
        locs = execute_query("SELECT ID_LOCATION, NM_CITY FROM WTH_LOCATIONS ORDER BY NM_CITY")
        if not locs:
            raise RuntimeError("WTH_LOCATIONS vazio.")
        id_loc = int(locs[0]["id_location"])
        df5 = _daily_5(id_loc)
        if df5.empty:
            raise RuntimeError("WTH_DAILY_FORECAST sem linhas nos próximos 5 dias.")
        rows_out = []
        for _, row in df5.iterrows():
            rd = row.to_dict()
            prob = _num_row(rd, "nr_precip_prob_max")
            mm_day = _num_row(rd, "nr_precip_sum") + _num_row(rd, "nr_rain_sum")
            tmax = _num_row(rd, "nr_temp_max")
            dt = rd.get("dt_forecast")
            data_label = pd.to_datetime(dt).strftime("%d/%m/%Y") if dt is not None else "—"
            bomba, motive = _classificar_irrigacao_dia(prob, mm_day, tmax, p_media, ultima_umid)
            rows_out.append(
                [
                    data_label,
                    bomba,
                    motive[:80] + ("…" if len(motive) > 80 else ""),
                    str(int(round(prob))),
                    str(round(mm_day, 1)),
                    str(round(tmax, 1)),
                ]
            )
        headers = ["Dia", "Bomba", "Resumo", "Prob. máx.%", "Chuva mm", "T máx."]
        fig_t = go.Figure(
            data=[
                go.Table(
                    header=dict(values=headers, fill_color="#37474f", font=dict(color="white", size=14), height=40),
                    cells=dict(values=list(zip(*rows_out)), align="left", font=dict(size=13), height=36),
                )
            ]
        )
        fig_t.update_layout(
            title="Painel IA — Sugestão de irrigação (próximos 5 dias · clima × média IA)",
            height=200 + len(rows_out) * 40,
            margin=dict(t=56, l=24, r=24, b=48),
        )
        _write(fig_t, "painel_ia_10_irrigacao_sugestao_5_dias.png", height=min(980, 200 + len(rows_out) * 80))
    except Exception as e:
        print(f"[SKIP] Figura 5 dias: {e}")


if __name__ == "__main__":
    main()
