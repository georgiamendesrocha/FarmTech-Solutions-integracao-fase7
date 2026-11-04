"""
Painel: comparação dos modelos ML + tabela simples de irrigação (5 dias × tempo × tendência IA).

Sem barema nem rubricas — foco só em resultado dos algoritmos e decisão apoiada.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
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

from src.api.db import execute_query

_SRC = Path(__file__).resolve().parents[2]
_REPO = _SRC.parent
_CSV_IOT = _SRC / "dados" / "historico_irrigacao.csv"
_AGRI = _SRC / "dados" / "Atividade_Cap10_produtos_agricolas.csv"
_TTL = 90

load_dotenv(_REPO / ".env", override=True)


def _num(cur: dict | None, key: str, default: float = 0.0) -> float:
    if cur is None:
        return default
    v = cur.get(key)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


@st.cache_data(ttl=_TTL)
def _loc_clima():
    return execute_query(
        "SELECT ID_LOCATION, NM_CITY||' - '||NM_COUNTRY AS LABEL FROM WTH_LOCATIONS ORDER BY NM_CITY"
    )


@st.cache_data(ttl=_TTL)
def _cur_clima(id_loc: int):
    rows = execute_query(
        """
        SELECT DT_FORECAST, NR_TEMPERATURE_2M, NR_APPARENT_TEMP, NR_HUMIDITY,
               NR_PRECIPITATION, NR_RAIN, NR_PRECIP_PROB, NR_UV_INDEX
        FROM WTH_HOURLY_FORECAST
        WHERE ID_LOCATION = :l
          AND DT_FORECAST = (
              SELECT MAX(DT_FORECAST) FROM WTH_HOURLY_FORECAST
              WHERE ID_LOCATION = :l AND DT_FORECAST <= SYSTIMESTAMP
          )
        """,
        {"l": id_loc},
    )
    return rows[0] if rows else None


@st.cache_data(ttl=_TTL)
def _previsao_diaria_5_dias(id_loc: int) -> pd.DataFrame:
    """Um registo por dia: hoje até +4 dias (5 dias no total)."""
    return pd.DataFrame(
        execute_query(
            """
            SELECT DT_FORECAST, NR_TEMP_MAX, NR_TEMP_MIN,
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


# Textos curtos (fáceis de traduzir para outro idioma)
_LBL_BOMBA_ON = "Ligada"
_LBL_BOMBA_OFF = "Desligada"
_LBL_BOMBA_REV = "Rever"


def _classificar_irrigacao_dia(
    prob_chuva_max: float,
    mm_chuva_dia: float,
    temp_max: float,
    p_media_modelos: float | None,
    umidade_solo_ult: float,
) -> tuple[str, str]:
    """
    Devolve (rótulo bomba, frase curta).
    p_media_modelos: None se ainda não há modelos treinados.
    """
    chuva_forte = prob_chuva_max >= 55.0 or mm_chuva_dia >= 4.0
    chuva_moderada = prob_chuva_max >= 40.0 or mm_chuva_dia >= 1.5
    tempo_seco = prob_chuva_max < 35.0 and mm_chuva_dia < 0.8
    calor = temp_max >= 29.0
    solo_seco = bool(np.isfinite(umidade_solo_ult) and umidade_solo_ult < 42.0)

    if chuva_forte:
        return _LBL_BOMBA_OFF, "Chuva prevista neste dia. Mantenha a bomba desligada."

    ia_quer_ligar = p_media_modelos is not None and p_media_modelos >= 0.5
    ia_quer_cortar = p_media_modelos is not None and p_media_modelos < 0.42

    if chuva_moderada and not ia_quer_ligar:
        return _LBL_BOMBA_OFF, "Alguma chuva prevista. Evite regar salvo indicação contrária no campo."

    if tempo_seco and (calor or solo_seco):
        if p_media_modelos is None:
            return _LBL_BOMBA_ON, "Tempo seco. Considere ligar a irrigação se o solo estiver abaixo do ideal."
        if ia_quer_ligar:
            return _LBL_BOMBA_ON, "Tempo seco e os modelos sugerem necessidade de rega (última leitura)."
        return _LBL_BOMBA_REV, "Tempo seco, mas os modelos não reforçam rega. Confirme a umidade do solo."

    if p_media_modelos is not None:
        if ia_quer_ligar and solo_seco and not chuva_moderada:
            return _LBL_BOMBA_ON, "Solo abaixo do conforto e modelos apontam para rega."
        if ia_quer_cortar and not tempo_seco:
            return _LBL_BOMBA_OFF, "Modelos indicam pouca necessidade de rega neste contexto."

    return _LBL_BOMBA_REV, "Sinais mistos. Veja sensores no campo antes de decidir."


def _carregar_iot_oracle() -> pd.DataFrame:
    user = os.getenv("ORACLE_USER")
    pwd = os.getenv("ORACLE_PASS")
    dsn = os.getenv("ORACLE_DSN")
    if not (user and pwd and dsn):
        raise ValueError("Variáveis ORACLE_USER/ORACLE_PASS/ORACLE_DSN ausentes.")
    with oracledb.connect(user=user, password=pwd, dsn=dsn) as conn:
        df = pd.read_sql(
            "SELECT UMIDADE, TEMP_C, PH_CORR, N, P, K, BOMBA_FW, TS_ISO FROM SENSORES_FARMTECH",
            conn,
        )
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _carregar_iot_csv() -> pd.DataFrame:
    if not _CSV_IOT.is_file():
        raise FileNotFoundError(f"CSV não encontrado: {_CSV_IOT}")
    df = pd.read_csv(_CSV_IOT, encoding="utf-8")
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
    """Mesmos algoritmos e hiperparâmetros que `notebook_ml.py` → `_secao_modelos`."""
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


_PRODUTOS_FEATURES = ["N", "P", "K", "temp_c", "umidade", "ph_corr", "chuva"]


@st.cache_resource(ttl=600, show_spinner="Treinando 5 modelos de cultura (cache 10 min)...")
def _produtos_pkg() -> dict | None:
    """Treina cinco classificadores multiclasse e devolve um pacote completo:
    modelos, scaler, classes, métricas, métricas por classe e dataset preparado.
    Cacheado com `st.cache_resource` para evitar retreinar a cada interação.
    """
    if not _AGRI.is_file():
        return None
    df = pd.read_csv(_AGRI, encoding="utf-8")
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
    req = _PRODUTOS_FEATURES + ["label"]
    for c in req[:-1]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["label"] = df["label"].astype(str).str.strip()
    df = df.dropna(subset=req).reset_index(drop=True)
    if len(df) < 20:
        return None

    X = df[_PRODUTOS_FEATURES].to_numpy(dtype=float, copy=True)
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
            "Suporte (teste)": sup.astype(int),
        }
    ).sort_values("F1", ascending=False).reset_index(drop=True)

    perfil_culturas = (
        df.groupby("label", as_index=False)[_PRODUTOS_FEATURES]
        .mean()
        .round(2)
        .rename(columns={"label": "Cultura"})
    )

    return {
        "df": df,
        "features": _PRODUTOS_FEATURES,
        "scaler": scaler,
        "fitted": fitted,
        "melhor": melhor,
        "resultado": resultado,
        "classes": classes,
        "X_test": X_test,
        "y_test": y_test,
        "cm": cm,
        "per_class": per_class,
        "perfil_culturas": perfil_culturas,
        "medianas": df[_PRODUTOS_FEATURES].median().to_dict(),
    }


def _feature_importance(pkg: dict) -> tuple[pd.DataFrame, str]:
    """Devolve uma tabela de importância de features para o melhor modelo.

    - Random Forest / Gradient Boosting: `feature_importances_`.
    - Regressão Logística: norma dos coeficientes (média absoluta entre classes).
    - k-NN / Naive Bayes: indisponível (devolve DataFrame vazio).
    """
    nome = pkg["melhor"]
    clf = pkg["fitted"][nome]
    feats = pkg["features"]
    if hasattr(clf, "feature_importances_"):
        imp = clf.feature_importances_
        modo = "Importância Gini"
    elif hasattr(clf, "coef_"):
        imp = np.mean(np.abs(clf.coef_), axis=0)
        if imp.sum() > 0:
            imp = imp / imp.sum()
        modo = "Coeficientes (|w| normalizado)"
    else:
        return pd.DataFrame(columns=["Feature", "Importancia"]), "indisponivel"
    out = (
        pd.DataFrame({"Feature": feats, "Importancia": imp})
        .sort_values("Importancia", ascending=False)
        .reset_index(drop=True)
    )
    return out, modo


def _media_prob_bomba(probs_bomba: dict[str, float]) -> float | None:
    if not probs_bomba:
        return None
    return float(np.mean(list(probs_bomba.values())))


st.title("Painel IA — soluções")
st.caption(
    "**1)** Comparação dos **cinco modelos** · **2)** Tabela simples: próximos **5 dias** — bomba **ligada / desligada / rever**, "
    "com previsão diária e tendência dos modelos na **última leitura**. Executar **`python run.py`** para popular o tempo no Oracle."
)

with st.sidebar:
    st.markdown("### Fonte IoT")
    fonte_iot = st.radio("Telemetria", ["Oracle (`SENSORES_FARMTECH`)", "CSV (`src/dados/historico_irrigacao.csv`)"], index=0)
    atualizar = st.button("🔄 Recalcular modelos")
if atualizar:
    st.cache_data.clear()
    st.rerun()

df_iot_err: str | None = None
df_iot: pd.DataFrame | None = None
if fonte_iot.startswith("Oracle"):
    try:
        df_iot = _carregar_iot_oracle()
    except Exception as e:
        df_iot_err = str(e)
else:
    try:
        df_iot = _carregar_iot_csv()
    except Exception as e:
        df_iot_err = str(e)

# --- Clima (localização) ---
loc_rows = _loc_clima()
cur: dict | None = None
id_loc: int | None = None
if loc_rows:
    labels = [r["label"] for r in loc_rows]
    choice = st.sidebar.selectbox("Local (previsão)", labels, index=0)
    id_loc = next(int(r["id_location"]) for r in loc_rows if r["label"] == choice)
    cur = _cur_clima(id_loc)
else:
    st.sidebar.caption("Sem `WTH_LOCATIONS` — API/deslocação meteorológico inativo.")

st.subheader("1) Avaliação comparativa dos modelos")

tab_p, tab_b = st.tabs(["Culturas (`produtos_agricolas`)", "Irrigação (`bomba_fw`)"])

probs_bomba: dict[str, float] = {}

with tab_b:
    if df_iot is None:
        st.error(df_iot_err or "Sem dados IoT.")
    else:
        d_prep = _prepare_bomba_df(df_iot)
        if d_prep is None:
            st.warning("Menos de 15 linhas válidas ou colunas em falta — impossível treinar os 5 modelos de irrigação.")
        else:
            resultado_b, melhor_b, cm_b, probs_bomba = _compare_models_bomba(d_prep)
            st.dataframe(resultado_b.round(4), width="stretch")
            fig = go.Figure()
            fig.add_trace(
                go.Bar(name="Acurácia (teste)", x=resultado_b["Modelo"], y=resultado_b["Acuracia_teste"], offsetgroup=0)
            )
            fig.add_trace(go.Bar(name="F1 (teste)", x=resultado_b["Modelo"], y=resultado_b["F1_teste"], offsetgroup=1))
            fig.update_layout(
                title="Comparação dos cinco modelos — bomba_fw",
                barmode="group",
                yaxis=dict(range=[0, 1.05]),
                xaxis_tickangle=-20,
                height=400,
            )
            st.plotly_chart(fig, width="stretch")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Melhor modelo neste corte:** `{melhor_b}`")
                st.markdown("**P(bomba ligada | última leitura)** por modelo:")
                st.dataframe(pd.DataFrame.from_dict(probs_bomba, orient="index", columns=["Prob. ligada"]))
            with c2:
                st.markdown("Matriz do melhor modelo (teste)")
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
                fig_cm.update_layout(height=280)
                st.plotly_chart(fig_cm, width="stretch")

with tab_p:
    pkg = _produtos_pkg()
    if pkg is None:
        st.warning(f"Não foi possível treinar sobre `{_AGRI.name}` — ficheiro em falta ou poucos registos.")
    else:
        df_p = pkg["df"]
        resultado_p = pkg["resultado"]
        melhor_p = pkg["melhor"]
        classes_p = pkg["classes"]
        cm_p = pkg["cm"]

        st.subheader("🌱 Recomendador inteligente — qual cultura combina com o solo agora?")
        st.caption(
            "Use a última leitura do **IoT** (umidade, temperatura, pH) e a **previsão de chuva** "
            "para estimar as culturas mais prováveis. N, P e K começam na mediana do dataset; "
            "ajuste se conhecer os valores do seu solo."
        )

        ult_iot = (
            df_iot.iloc[-1].to_dict()
            if df_iot is not None and len(df_iot) and {"umidade", "temp_c", "ph_corr"}.issubset(df_iot.columns)
            else None
        )
        chuva_estimada_mm = float("nan")
        if id_loc is not None:
            try:
                df5_chuva = _previsao_diaria_5_dias(int(id_loc))
                if not df5_chuva.empty:
                    chuva_estimada_mm = float(
                        pd.to_numeric(df5_chuva.get("nr_precip_sum", 0), errors="coerce").fillna(0).sum()
                        + pd.to_numeric(df5_chuva.get("nr_rain_sum", 0), errors="coerce").fillna(0).sum()
                    )
            except Exception:
                chuva_estimada_mm = float("nan")
        if not np.isfinite(chuva_estimada_mm) or chuva_estimada_mm <= 0:
            chuva_estimada_mm = float(pkg["medianas"]["chuva"])
            chuva_origem = "mediana do dataset"
        else:
            chuva_estimada_mm = round(chuva_estimada_mm, 1)
            chuva_origem = "soma 5 dias (previsão local)"

        with st.form("rec_cultura"):
            cA, cB, cC = st.columns(3)
            n_in = cA.number_input(
                "N (Nitrogênio)", 0.0, 200.0,
                value=float(pkg["medianas"]["N"]), step=1.0,
            )
            p_in = cB.number_input(
                "P (Fósforo)", 0.0, 200.0,
                value=float(pkg["medianas"]["P"]), step=1.0,
            )
            k_in = cC.number_input(
                "K (Potássio)", 0.0, 250.0,
                value=float(pkg["medianas"]["K"]), step=1.0,
            )
            cD, cE, cF, cG = st.columns(4)
            temp_in = cD.number_input(
                "Temperatura (°C)", -5.0, 50.0,
                value=float(ult_iot["temp_c"]) if ult_iot else float(pkg["medianas"]["temp_c"]),
                step=0.1,
            )
            umid_in = cE.number_input(
                "Umidade (%)", 0.0, 100.0,
                value=float(ult_iot["umidade"]) if ult_iot else float(pkg["medianas"]["umidade"]),
                step=0.1,
            )
            ph_in = cF.number_input(
                "pH", 3.0, 10.0,
                value=float(ult_iot["ph_corr"]) if ult_iot else float(pkg["medianas"]["ph_corr"]),
                step=0.1,
            )
            chuva_in = cG.number_input(
                "Chuva (mm)", 0.0, 1000.0,
                value=float(chuva_estimada_mm), step=1.0,
                help=f"Origem do valor inicial: {chuva_origem}.",
            )
            usar_melhor = st.toggle(
                f"Usar melhor modelo (**{melhor_p}**)",
                value=True,
                help="Desligue para escolher outro modelo manualmente.",
            )
            if not usar_melhor:
                modelo_escolhido = st.selectbox(
                    "Modelo para a recomendação",
                    options=list(pkg["fitted"].keys()),
                    index=list(pkg["fitted"].keys()).index(melhor_p),
                )
            else:
                modelo_escolhido = melhor_p
            submit = st.form_submit_button("Recomendar cultura", type="primary")

        if submit:
            x_in = np.array([[n_in, p_in, k_in, temp_in, umid_in, ph_in, chuva_in]], dtype=float)
            x_scaled = pkg["scaler"].transform(x_in)
            clf = pkg["fitted"][modelo_escolhido]
            if hasattr(clf, "predict_proba"):
                probs = clf.predict_proba(x_scaled)[0]
            else:
                probs = np.zeros(len(classes_p))
                probs[list(classes_p).index(clf.predict(x_scaled)[0])] = 1.0

            rank = pd.DataFrame({"Cultura": classes_p, "Probabilidade": probs}).sort_values(
                "Probabilidade", ascending=False
            ).reset_index(drop=True)
            top_n = min(5, len(rank))
            top = rank.head(top_n)

            r1, r2 = st.columns([1, 1.2])
            with r1:
                st.success(
                    f"**Cultura recomendada:** `{top.iloc[0]['Cultura']}` "
                    f"({top.iloc[0]['Probabilidade']:.1%}) — modelo `{modelo_escolhido}`."
                )
                if len(top) > 1:
                    runner = top.iloc[1]
                    margem = top.iloc[0]["Probabilidade"] - runner["Probabilidade"]
                    st.caption(
                        f"2ª opção: `{runner['Cultura']}` ({runner['Probabilidade']:.1%}) · "
                        f"margem de confiança: **{margem:.1%}**."
                    )
                fig_top = px.bar(
                    top,
                    x="Probabilidade",
                    y="Cultura",
                    orientation="h",
                    text=top["Probabilidade"].map(lambda v: f"{v:.1%}"),
                    color="Probabilidade",
                    color_continuous_scale="Greens",
                    range_color=(0, max(0.01, float(top["Probabilidade"].max()))),
                )
                fig_top.update_layout(
                    yaxis=dict(autorange="reversed"),
                    xaxis=dict(range=[0, 1], tickformat=".0%"),
                    coloraxis_showscale=False,
                    title=f"Top {top_n} culturas mais prováveis",
                    height=320,
                    margin=dict(t=48, b=32, l=24, r=24),
                )
                st.plotly_chart(fig_top, width="stretch")

            with r2:
                cult_top = top.iloc[0]["Cultura"]
                perfil_ideal_row = pkg["perfil_culturas"][
                    pkg["perfil_culturas"]["Cultura"] == cult_top
                ]
                if not perfil_ideal_row.empty:
                    perfil_ideal = perfil_ideal_row.iloc[0][_PRODUTOS_FEATURES].astype(float)
                    perfil_atual = pd.Series(
                        [n_in, p_in, k_in, temp_in, umid_in, ph_in, chuva_in],
                        index=_PRODUTOS_FEATURES,
                    )
                    norm = perfil_ideal.abs().clip(lower=1e-6) + perfil_atual.abs().clip(lower=1e-6)
                    ideal_norm = (perfil_ideal / norm).fillna(0).tolist()
                    atual_norm = (perfil_atual / norm).fillna(0).tolist()
                    radar_categorias = _PRODUTOS_FEATURES + [_PRODUTOS_FEATURES[0]]
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
                            name="Solo agora",
                            line=dict(color="#e76f51"),
                            opacity=0.7,
                        )
                    )
                    fig_radar.update_layout(
                        title="Perfil ideal vs solo agora (escala normalizada por feature)",
                        polar=dict(radialaxis=dict(visible=False)),
                        height=360,
                        margin=dict(t=48, b=24, l=24, r=24),
                        legend=dict(orientation="h", yanchor="top", y=-0.05, x=0),
                    )
                    st.plotly_chart(fig_radar, width="stretch")

                    delta = (perfil_atual - perfil_ideal).round(2)
                    delta_pct = (
                        ((perfil_atual - perfil_ideal) / perfil_ideal.abs().replace(0, np.nan)) * 100
                    ).round(1)
                    diag = pd.DataFrame(
                        {
                            "Variavel": _PRODUTOS_FEATURES,
                            f"Ideal ({cult_top})": perfil_ideal.values.round(2),
                            "Solo agora": perfil_atual.values.round(2),
                            "Delta": delta.values,
                            "Delta %": delta_pct.values,
                        }
                    )
                    st.markdown(f"**Ajustes recomendados para `{cult_top}`:**")
                    st.dataframe(diag, width="stretch", hide_index=True)

            with st.expander("Ver distribuição completa por cultura"):
                fig_full = px.bar(
                    rank,
                    x="Cultura",
                    y="Probabilidade",
                    color="Probabilidade",
                    color_continuous_scale="Greens",
                )
                fig_full.update_layout(
                    yaxis=dict(range=[0, 1], tickformat=".0%"),
                    xaxis_tickangle=-30,
                    coloraxis_showscale=False,
                    height=360,
                    margin=dict(t=24, b=80, l=24, r=24),
                )
                st.plotly_chart(fig_full, width="stretch")

        st.markdown("---")
        st.subheader("Detalhes do modelo treinado")

        topo = resultado_p.iloc[0]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Linhas", f"{len(df_p):,}")
        k2.metric("Culturas", f"{len(classes_p)}")
        k3.metric("Melhor modelo", melhor_p)
        k4.metric(
            "Acurácia (teste)",
            f"{topo['Acuracia_teste']:.1%}",
            delta=(
                f"F1 pond. {topo['F1_ponderado']:.1%}"
                + (f" · CV {topo['Acuracia_CV']:.1%}" if pd.notna(topo["Acuracia_CV"]) else "")
            ),
        )

        st.markdown("**Comparação dos cinco modelos**")
        st.dataframe(resultado_p.round(4), width="stretch", hide_index=True)
        fig2 = go.Figure()
        fig2.add_trace(
            go.Bar(name="Acurácia (teste)", x=resultado_p["Modelo"], y=resultado_p["Acuracia_teste"], offsetgroup=0)
        )
        fig2.add_trace(
            go.Bar(name="F1 ponderado", x=resultado_p["Modelo"], y=resultado_p["F1_ponderado"], offsetgroup=1)
        )
        fig2.update_layout(
            title="Comparação dos cinco modelos — cultura (multiclasse)",
            barmode="group",
            yaxis=dict(range=[0, 1.05]),
            xaxis_tickangle=-20,
            height=380,
            margin=dict(t=56, b=70, l=48, r=24),
        )
        st.plotly_chart(fig2, width="stretch")

        col_cm, col_fi = st.columns([1.2, 1])
        with col_cm:
            st.markdown(f"**Matriz de confusão · {melhor_p}** (teste)")
            fig_cm = px.imshow(
                cm_p,
                x=classes_p,
                y=classes_p,
                color_continuous_scale="Blues",
                aspect="auto",
                labels=dict(x="Previsto", y="Real", color="Contagem"),
                text_auto=True,
            )
            fig_cm.update_layout(
                height=max(360, 24 * len(classes_p) + 120),
                margin=dict(t=24, b=24, l=24, r=24),
            )
            st.plotly_chart(fig_cm, width="stretch")
        with col_fi:
            imp_df, modo_imp = _feature_importance(pkg)
            st.markdown(f"**Importância das variáveis** ({modo_imp})")
            if imp_df.empty:
                st.info(
                    f"O modelo **{melhor_p}** não expõe importâncias diretamente "
                    "(k-NN/Naive Bayes). Use Random Forest ou Gradient Boosting para esta visão."
                )
            else:
                fig_imp = px.bar(
                    imp_df,
                    x="Importancia",
                    y="Feature",
                    orientation="h",
                    text=imp_df["Importancia"].map(lambda v: f"{v:.2f}"),
                    color="Importancia",
                    color_continuous_scale="Greens",
                )
                fig_imp.update_layout(
                    yaxis=dict(autorange="reversed"),
                    coloraxis_showscale=False,
                    height=max(360, 32 * len(imp_df) + 120),
                    margin=dict(t=24, b=24, l=24, r=24),
                )
                st.plotly_chart(fig_imp, width="stretch")

        st.markdown("**Métricas por cultura** (precisão · recall · F1 · suporte no teste)")
        st.dataframe(
            pkg["per_class"].round(3),
            width="stretch",
            hide_index=True,
        )

st.divider()
st.subheader("2) Sugestão de irrigação — próximos **5 dias**")

ultima_umid = (
    float(pd.to_numeric(df_iot.iloc[-1]["umidade"], errors="coerce"))
    if df_iot is not None and len(df_iot) and "umidade" in df_iot.columns
    else float("nan")
)
p_media = _media_prob_bomba(probs_bomba if probs_bomba else {})

if cur:
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("T agora (prev.)", f"{_num(cur, 'nr_temperature_2m'):.1f} °C")
    q2.metric("Humidade do ar", f"{_num(cur, 'nr_humidity'):.0f} %")
    q3.metric("Prob. chuva (agora)", f"{_num(cur, 'nr_precip_prob'):.0f} %")
    q4.metric("Chuva mm (agora)", f"{_num(cur, 'nr_precipitation') + _num(cur, 'nr_rain'):.2f}")

st.markdown(
    "**Ligada** = tendência a **ligar** a bomba · **Desligada** = tendência a **manter desligada** · "
    "**Rever** = confirme no campo (solo / cultura)."
)

if id_loc is None:
    st.info(
        "Não há local meteorológico. Arranque a API (**`python run.py`**) para gravar previsões no Oracle "
        "e voltar aqui para ver os 5 dias."
    )
else:
    df5 = _previsao_diaria_5_dias(id_loc)
    if df5.empty:
        st.warning(
            "Ainda não há linhas diárias em **`WTH_DAILY_FORECAST`** para esta localização. "
            "Com a API a correr, os dados aparecem em poucos minutos."
        )
    else:
        linhas_tab: list[dict] = []
        for _, row in df5.iterrows():
            prob = float(_num(row, "nr_precip_prob_max"))
            mm_day = float(_num(row, "nr_precip_sum") + _num(row, "nr_rain_sum"))
            tmax = float(_num(row, "nr_temp_max"))
            dt = row.get("dt_forecast")
            data_label = pd.to_datetime(dt).strftime("%d/%m/%Y") if dt is not None else "—"
            bomba, motive = _classificar_irrigacao_dia(prob, mm_day, tmax, p_media, ultima_umid)
            linhas_tab.append(
                {
                    "Dia": data_label,
                    "Bomba (sugestão)": bomba,
                    "Resumo": motive,
                    "Prob. chuva máx. (dia) %": round(prob, 0),
                    "Chuva prevista (mm)": round(mm_day, 1),
                    "T máx. (°C)": round(tmax, 1),
                }
            )
        st.dataframe(pd.DataFrame(linhas_tab), width="stretch", hide_index=True)

if p_media is not None:
    tend = "**ligar**" if p_media >= 0.5 else "**não ligar**"
    st.success(
        f"**Modelos (última leitura IoT):** em média, tendem a **{tend}** a bomba "
        f"(probabilidade média de estar ligada: **{p_media:.0%}**)."
    )
else:
    st.caption(
        "Abra o separador **Irrigação (`bomba_fw`)** acima para treinar os modelos; "
        "a coluna «Bomba» continua útil só com o tempo, mas fica mais completa com a IA."
    )

st.caption("Para detalhe técnico dos cinco modelos, use **Notebook ML (Ir além)**.")
