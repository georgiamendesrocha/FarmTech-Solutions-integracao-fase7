"""Painel ML alinhado ao notebook ``Edemir_RM571375_fase3_cap1.ipynb`` — mesma lógica (``preparar``, modelos, métricas).

O `.ipynb` foi reestruturado para seguir esta página: Parte A (sensores) e Parte B (produtos), com cabeçalhos equivalentes aos `st.subheader`.
"""

import os
import secrets
import socket
import subprocess
import sys
import time
import warnings
import webbrowser
from pathlib import Path

import numpy as np
import oracledb
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

_NOTEBOOK_REL = Path("src") / "ml" / "Edemir_RM571375_fase3_cap1.ipynb"
_FEATURE_WIDTH = "stretch"
_DF_WIDTH = "stretch"


def _encontrar_raiz_repo() -> Path:
    aqui = Path(__file__).resolve()
    for cand in [aqui, *aqui.parents]:
        if (cand / ".env").is_file() and (cand / "src").is_dir():
            return cand
    return aqui.parents[3]


REPO = _encontrar_raiz_repo()
CSV_PATH = REPO / "src" / "dados" / "historico_irrigacao.csv"
AGRI_CSV_PATH = REPO / "src" / "dados" / "Atividade_Cap10_produtos_agricolas.csv"
NOTEBOOK_PATH = REPO / _NOTEBOOK_REL
load_dotenv(REPO / ".env", override=True)


def _carregar_oracle() -> pd.DataFrame:
    user = os.getenv("ORACLE_USER")
    pwd = os.getenv("ORACLE_PASS")
    dsn = os.getenv("ORACLE_DSN")
    if not (user and pwd and dsn):
        raise ValueError("Variaveis ORACLE_USER/ORACLE_PASS/ORACLE_DSN ausentes.")
    with oracledb.connect(user=user, password=pwd, dsn=dsn) as conn:
        query = """
        SELECT TS_ISO, UMIDADE, TEMP_C, PH_CORR, N, P, K, BOMBA_FW
        FROM SENSORES_FARMTECH
        """
        return pd.read_sql(query, conn)


def _carregar_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"CSV nao encontrado: {path}")
    return pd.read_csv(path)


def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Igual ao cell 3 do notebook."""
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {"n": "N", "p": "P", "k": "K"}
    for a, b in rename.items():
        if a in df.columns and b not in df.columns:
            df = df.rename(columns={a: b})
    required = ["umidade", "temp_c", "ph_corr", "N", "P", "K", "bomba_fw"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")
    df = df.dropna(subset=required).copy()
    df["bomba_fw"] = pd.to_numeric(df["bomba_fw"], errors="coerce").fillna(0).astype(int).clip(0, 1)
    df["temp_c"] = pd.to_numeric(df["temp_c"], errors="coerce")
    df["umidade"] = pd.to_numeric(df["umidade"], errors="coerce")
    df["ph_corr"] = pd.to_numeric(df["ph_corr"], errors="coerce")
    df = df.dropna(subset=["temp_c", "umidade", "ph_corr"])
    return df


def _preparar_produtos(df: pd.DataFrame) -> pd.DataFrame:
    """Esquema do CSV `Atividade_Cap10_produtos_agricolas.csv`:
    `N,P,K,temperature,humidity,ph,rainfall,label` (variáveis do enunciado).
    """
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    rename = {
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
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns and v not in df.columns})
    required = ["temp_c", "umidade", "ph_corr", "chuva", "N", "P", "K", "label"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes na base de produtos: {missing}")
    for col in ["temp_c", "umidade", "ph_corr", "chuva", "N", "P", "K"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["label"] = df["label"].astype(str).str.strip()
    df = df.dropna(subset=required).copy()
    return df


def _port_em_uso(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


def _iniciar_jupyter_se_preciso(port: int) -> tuple[bool, str, str | None]:
    if _port_em_uso("127.0.0.1", port):
        return True, "Jupyter já estava em execução.", None
    try:
        token = secrets.token_urlsafe(32)
        cmd = [
            sys.executable,
            "-m",
            "jupyter",
            "notebook",
            "--no-browser",
            "--port",
            str(port),
            "--ServerApp.ip=127.0.0.1",
            f"--ServerApp.token={token}",
        ]
        kwargs: dict = {"cwd": str(REPO), "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform.startswith("win"):
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        subprocess.Popen(cmd, **kwargs)
        for _ in range(24):
            time.sleep(0.25)
            if _port_em_uso("127.0.0.1", port):
                return True, "Jupyter iniciado.", token
        return False, "Jupyter não respondeu.", None
    except Exception as e:
        return False, f"Erro ao iniciar Jupyter: {e}", None


def _plot_eda(df: pd.DataFrame) -> None:
    st.subheader("2. EDA (espelho do notebook)")
    fig1 = px.histogram(df, x="umidade", nbins=20, title="Distribuicao da umidade do solo")
    fig1.update_traces(marker_line_width=1, marker_line_color="white", marker_color="#2d7a4f")
    st.plotly_chart(fig1, width="stretch")

    fig2 = px.scatter(
        df,
        x="temp_c",
        y="umidade",
        color="bomba_fw",
        color_continuous_scale=[(0.0, "#3b4cc0"), (0.5, "#f7f7f7"), (1.0, "#d73027")],
        opacity=0.7,
        title="Temperatura x umidade (cor = bomba_fw)",
        labels={"temp_c": "Temperatura (C)", "umidade": "Umidade (%)"},
    )
    fig2.update_coloraxes(colorbar_title="bomba_fw")
    st.plotly_chart(fig2, width=_FEATURE_WIDTH)

    fig3 = px.histogram(df, x="ph_corr", nbins=20, title="Distribuicao do pH corrigido")
    fig3.update_traces(marker_line_width=1, marker_line_color="white", marker_color="#457b9d")
    st.plotly_chart(fig3, width=_FEATURE_WIDTH)

    vc = df["bomba_fw"].value_counts().sort_index()
    labels_pie = ["Desligada (0)", "Ligada (1)"] if len(vc) == 2 else [str(i) for i in vc.index]
    colors_pie = ["#e76f51", "#2d7a4f"][: len(vc)]
    fig4 = px.pie(
        names=labels_pie,
        values=vc.values,
        title="Proporcao por estado da irrigacao",
        color_discrete_sequence=colors_pie,
    )
    fig4.update_traces(textinfo="percent+label")
    st.plotly_chart(fig4, width=_FEATURE_WIDTH)

    medias = df.groupby("bomba_fw")[["N", "P", "K"]].mean().reset_index()
    medias["bomba_fw"] = medias["bomba_fw"].astype(str)
    fig5 = px.bar(
        medias.melt(id_vars=["bomba_fw"], var_name="nutriente", value_name="media"),
        x="bomba_fw",
        y="media",
        color="nutriente",
        barmode="group",
        title="Medias N, P e K por estado da bomba",
        labels={"bomba_fw": "bomba_fw", "media": "Media"},
    )
    st.plotly_chart(fig5, width=_FEATURE_WIDTH)

    corr = df[["umidade", "temp_c", "ph_corr", "N", "P", "K", "bomba_fw"]].corr()
    fig6 = px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        title="Correlacao entre variaveis",
        color_continuous_scale="RdYlGn",
        zmin=-1,
        zmax=1,
    )
    st.plotly_chart(fig6, width=_FEATURE_WIDTH)


def _secao_cluster(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    referencia = pd.DataFrame(
        {
            "cultura": ["Milho", "Soja", "Tomate"],
            "umidade_min": [55, 50, 60],
            "umidade_max": [75, 70, 80],
            "temp_min": [18, 20, 20],
            "temp_max": [30, 28, 28],
            "ph_min": [5.8, 5.5, 6.0],
            "ph_max": [7.0, 6.8, 6.8],
        }
    )
    X_clima = df[["umidade", "temp_c", "ph_corr"]].values.astype(float)
    scaler = StandardScaler().fit(X_clima)
    Z = scaler.transform(X_clima)
    km = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = km.fit_predict(Z)
    centros = pd.DataFrame(
        scaler.inverse_transform(km.cluster_centers_),
        columns=["umidade", "temp_c", "ph_corr"],
    )
    centros["cluster"] = range(3)
    return referencia, centros, clusters


def _secao_modelos(df: pd.DataFrame):
    FEATURES = ["umidade", "temp_c", "ph_corr", "N", "P", "K"]
    TARGET = "bomba_fw"
    X = df[FEATURES].values.astype(float)
    y = df[TARGET].values.astype(int)
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
    for nome, modelo in modelos.items():
        modelo.fit(X_train, y_train)
        pred = modelo.predict(X_test)
        acc = float(accuracy_score(y_test, pred))
        f1 = float(f1_score(y_test, pred, average="binary", zero_division=0))
        cv_acc = float("nan")
        if usar_cv:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            cv_acc = float(cross_val_score(modelo, X_scaled, y, cv=cv, scoring="accuracy").mean())
        linhas.append({"Modelo": nome, "Acuracia_teste": acc, "F1_teste": f1, "Acuracia_CV": cv_acc})

    resultado = pd.DataFrame(linhas).sort_values("Acuracia_teste", ascending=False)
    return modelos, resultado, X_test, y_test


def _secao_modelos_produtos(df: pd.DataFrame):
    features = ["N", "P", "K", "temp_c", "umidade", "ph_corr", "chuva"]
    target = "label"
    X = df[features].to_numpy(dtype=float, copy=True)
    y = df[target].astype(str).to_numpy(copy=True)
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
    for nome, modelo in modelos.items():
        modelo.fit(X_train, y_train)
        pred = modelo.predict(X_test)
        acc = float(accuracy_score(y_test, pred))
        f1w = float(f1_score(y_test, pred, average="weighted", zero_division=0))
        cv_acc = float("nan")
        if usar_cv:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            cv_acc = float(cross_val_score(modelo, X_scaled, y, cv=cv, scoring="accuracy").mean())
        linhas.append({"Modelo": nome, "Acuracia_teste": acc, "F1_ponderado": f1w, "Acuracia_CV": cv_acc})
    resultado = pd.DataFrame(linhas).sort_values("Acuracia_teste", ascending=False)
    return modelos, resultado, X_test, y_test


st.title("Notebook ML (Ir Além)")
st.caption(
    "Fluxo alinhado ao Jupyter `Edemir_RM571375_fase3_cap1.ipynb` · "
    "**Parte A** = sensores Fase 2 (bomba) + dados de cultura · **Parte B** = produtos agrícolas (multiclasse)."
)

with st.sidebar:
    dataset = st.selectbox(
        "Base do Ir Além (ML)",
        [
            "Parte A — Sensores Fase 2 (bomba) + culturas",
            "Parte B — Produtos Agricolas (culturas)",
        ],
        index=1,
    )
    st.markdown("### Jupyter")
    jport = st.number_input("Porta", min_value=1024, max_value=65535, value=8888, step=1)
    if st.button("Abrir notebook no navegador"):
        ok, msg, token = _iniciar_jupyter_se_preciso(int(jport))
        if ok and NOTEBOOK_PATH.is_file():
            rel = _NOTEBOOK_REL.as_posix()
            url = f"http://127.0.0.1:{int(jport)}/notebooks/{rel}"
            if token:
                url += f"?token={token}"
            webbrowser.open_new_tab(url)
            st.success(msg)
        elif ok:
            st.warning(msg + " Caminho do .ipynb não encontrado.")
        else:
            st.error(msg)

if dataset.startswith("Parte A"):
    try:
        raw = _carregar_oracle()
        fonte = "oracle"
        err_oracle = None
    except Exception as e:
        err_oracle = str(e)
        try:
            raw = _carregar_csv(CSV_PATH)
            fonte = "csv_fallback"
        except Exception as e2:
            st.error(f"Oracle: {err_oracle}. CSV: {e2}")
            st.stop()

    st.markdown(
        "## Parte A — Sensores Fase 2 (bomba) + dados de cultura\n"
        "Espelho da **Parte A** do `Edemir_RM571375_fase3_cap1.ipynb`. Combina dois blocos:\n\n"
        "1. **Sensores Fase 2** — `bomba_fw` como alvo, EDA, K-Means (k=3) e cinco classificadores.\n"
        "2. **Dados de cultura reais** — leitura de `src/dados/Atividade_Cap10_produtos_agricolas.csv` "
        "(variáveis do enunciado: **N, P, K, temperatura, umidade, pH, chuva, label**) com amostra, "
        "distribuição, perfil real por cultura e dispersão temperatura × umidade — apresentados em paralelo aos sensores."
    )
    st.info(f"Repositório: `{REPO}` · Fonte (sensores): **{fonte}** · CSV fallback: `{CSV_PATH}`")
    if fonte == "csv_fallback" and err_oracle:
        st.warning(f"Oracle indisponível: {err_oracle}")

    try:
        df = _preparar(raw)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    st.subheader("1. Amostra e estatísticas — sensores (espelho do notebook)")
    st.dataframe(df.head(), width=_DF_WIDTH)
    st.dataframe(df.describe().round(2), width=_DF_WIDTH)
    st.write("Distribuicao de classes (bomba_fw):")
    st.write(df["bomba_fw"].value_counts().sort_index())

    _plot_eda(df)

    st.subheader("3. Referência de culturas e K-Means (k=3) no espaço clima")
    referencia, centros, clusters = _secao_cluster(df)
    st.dataframe(referencia, width=_DF_WIDTH)
    st.dataframe(centros.round(2), width=_DF_WIDTH)

    df_k = df.assign(cluster_str=clusters.astype(str))
    fig_k = px.scatter(
        df_k,
        x="temp_c",
        y="umidade",
        color="cluster_str",
        opacity=0.6,
        title="K-Means (k=3): temperatura x umidade",
        labels={"temp_c": "Temperatura (C)", "umidade": "Umidade (%)"},
        color_discrete_sequence=px.colors.qualitative.Dark2,
    )
    fig_k.add_trace(
        go.Scatter(
            x=centros["temp_c"],
            y=centros["umidade"],
            mode="markers",
            marker=dict(symbol="x", size=14, color="black", line=dict(width=0)),
            name="Centroides",
        )
    )
    fig_k.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_k, width=_FEATURE_WIDTH)

    st.subheader("3.b. Dados de cultura reais (`Atividade_Cap10_produtos_agricolas.csv`)")
    st.caption(
        "Variáveis do enunciado: **N, P, K, temperatura, umidade, pH, chuva, label**. "
        "Estes dados de cultura aparecem **na Parte A** para complementar a referência hard-coded "
        "do K-Means com perfis **reais** observados no dataset."
    )
    try:
        df_cult = _preparar_produtos(_carregar_csv(AGRI_CSV_PATH))
    except Exception as e:
        st.warning(f"Nao foi possivel carregar o CSV de produtos agricolas: {e}")
    else:
        st.dataframe(df_cult.head(), width=_DF_WIDTH)
        st.dataframe(df_cult.describe().round(2), width=_DF_WIDTH)

        st.markdown("**Distribuição de classes (cultura):**")
        st.dataframe(
            df_cult["label"].value_counts().rename_axis("cultura").reset_index(name="contagem"),
            width=_DF_WIDTH,
        )

        st.markdown("**Perfil real por cultura — média das variáveis do enunciado:**")
        perfil_cult = (
            df_cult.groupby("label", as_index=False)[
                ["N", "P", "K", "temp_c", "umidade", "ph_corr", "chuva"]
            ]
            .mean()
            .round(2)
            .sort_values("label")
        )
        st.dataframe(perfil_cult, width=_DF_WIDTH)

        fig_disp_cult = px.scatter(
            df_cult,
            x="temp_c",
            y="umidade",
            color="label",
            opacity=0.7,
            title="Temperatura x umidade por cultura (CSV produtos agricolas)",
            labels={"temp_c": "Temperatura (C)", "umidade": "Umidade (%)"},
        )
        st.plotly_chart(fig_disp_cult, width=_FEATURE_WIDTH)

        top3_a = df_cult["label"].value_counts().head(3).index.tolist()
        st.markdown(
            f"**Três culturas mais frequentes** (escolhidas para o perfil ideal): "
            f"`{', '.join(top3_a)}`."
        )
        st.dataframe(
            perfil_cult[perfil_cult["label"].isin(top3_a)].reset_index(drop=True),
            width=_DF_WIDTH,
        )

    if len(df) < 4:
        st.warning("Poucas linhas para treinar/testar modelos como no notebook.")
        st.stop()

    modelos_dict, resultado, X_test, y_test = _secao_modelos(df)

    st.subheader("4. Cinco modelos (treino igual ao notebook)")
    st.dataframe(resultado.round(4), width=_DF_WIDTH)

    st.subheader("5. Comparação e matriz de confusão (melhor por Acuracia_teste)")
    fig_cmp = go.Figure()
    fig_cmp.add_trace(
        go.Bar(
            name="Acuracia (teste)",
            x=resultado["Modelo"],
            y=resultado["Acuracia_teste"],
            offsetgroup=0,
        )
    )
    fig_cmp.add_trace(
        go.Bar(name="F1 (teste)", x=resultado["Modelo"], y=resultado["F1_teste"], offsetgroup=1)
    )
    fig_cmp.update_layout(
        title="Comparacao dos 5 modelos",
        barmode="group",
        yaxis=dict(range=[0, 1.05]),
        xaxis_tickangle=-15,
    )
    st.plotly_chart(fig_cmp, width=_FEATURE_WIDTH)

    melhor_nome = resultado.iloc[0]["Modelo"]
    melhor_modelo = modelos_dict[melhor_nome]

    pred_best = melhor_modelo.predict(X_test)
    cm = confusion_matrix(y_test, pred_best, labels=[0, 1])
    fig_cm = px.imshow(
        cm,
        text_auto=True,
        aspect="equal",
        labels=dict(x="Previsto", y="Real", color="Contagem"),
        x=["OFF", "ON"],
        y=["OFF", "ON"],
        color_continuous_scale="Blues",
        title=f"Matriz de confusao - {melhor_nome}",
    )
    st.plotly_chart(fig_cm, width=_FEATURE_WIDTH)
    st.success(f"Melhor modelo nesta execução: **{melhor_nome}**")
else:
    try:
        df = _preparar_produtos(_carregar_csv(AGRI_CSV_PATH))
    except Exception as e:
        st.error(f"Falha na base de produtos: {e}")
        st.stop()

    st.markdown(
        "## Parte B — Produtos agrícolas (multiclasse)\n"
        "Espelho da **Parte B** do `Edemir_RM571375_fase3_cap1.ipynb`. "
        "Classifica **`label`** (cultura) com **N, P, K, temperatura, umidade, pH, chuva** — exatamente as variáveis do enunciado."
    )
    st.info(f"Repositório: `{REPO}` · Fonte: **csv_produtos** · Arquivo: `{AGRI_CSV_PATH}`")
    st.subheader("1. Amostra e estatísticas (base Atividade_Cap10_produtos_agricolas)")
    st.dataframe(df.head(), width=_DF_WIDTH)
    st.dataframe(df.describe().round(2), width=_DF_WIDTH)
    st.write("Distribuicao de classes (label/cultura):")
    st.write(df["label"].value_counts())

    st.subheader("2. EDA (5+ gráficos)")
    st.plotly_chart(px.histogram(df, x="label", title="Distribuicao das culturas (label)"), width=_FEATURE_WIDTH)
    st.plotly_chart(px.histogram(df, x="umidade", nbins=20, title="Distribuicao da umidade"), width=_FEATURE_WIDTH)
    st.plotly_chart(px.scatter(df, x="temp_c", y="umidade", color="label", title="Temperatura x umidade por cultura"), width=_FEATURE_WIDTH)
    st.plotly_chart(px.box(df, x="label", y="N", title="N por cultura"), width=_FEATURE_WIDTH)
    st.plotly_chart(px.box(df, x="label", y="ph_corr", title="pH por cultura"), width=_FEATURE_WIDTH)
    st.plotly_chart(px.box(df, x="label", y="chuva", title="Chuva (mm) por cultura"), width=_FEATURE_WIDTH)
    st.plotly_chart(
        px.imshow(
            df[["N", "P", "K", "temp_c", "umidade", "ph_corr", "chuva"]].corr(),
            text_auto=".2f",
            title="Correlacao entre variaveis",
            color_continuous_scale="RdYlGn",
            zmin=-1,
            zmax=1,
        ),
        width=_FEATURE_WIDTH,
    )

    st.subheader("3. Perfil ideal de solo/clima para 3 culturas")
    top3 = df["label"].value_counts().head(3).index.tolist()
    perfil = (
        df[df["label"].isin(top3)]
        .groupby("label", as_index=False)[["N", "P", "K", "temp_c", "umidade", "ph_corr", "chuva"]]
        .mean()
        .round(2)
    )
    st.dataframe(perfil, width=_DF_WIDTH)

    if len(df) < 10:
        st.warning("Poucas linhas para treinar os 5 modelos.")
        st.stop()

    modelos_dict, resultado, X_test, y_test = _secao_modelos_produtos(df)
    st.subheader("4. Cinco modelos preditivos (classificação de cultura)")
    st.dataframe(resultado.round(4), width=_DF_WIDTH)

    st.subheader("5. Avaliação comparativa e matriz de confusão")
    fig_cmp = go.Figure()
    fig_cmp.add_trace(go.Bar(name="Acuracia (teste)", x=resultado["Modelo"], y=resultado["Acuracia_teste"]))
    fig_cmp.add_trace(go.Bar(name="F1 ponderado", x=resultado["Modelo"], y=resultado["F1_ponderado"]))
    fig_cmp.update_layout(title="Comparacao dos 5 modelos", barmode="group", yaxis=dict(range=[0, 1.05]))
    st.plotly_chart(fig_cmp, width=_FEATURE_WIDTH)

    melhor_nome = resultado.iloc[0]["Modelo"]
    melhor_modelo = modelos_dict[melhor_nome]
    pred_best = melhor_modelo.predict(X_test)
    classes = sorted(pd.Series(y_test).astype(str).unique().tolist())
    cm = confusion_matrix(y_test, pred_best, labels=classes)
    fig_cm = px.imshow(
        cm,
        text_auto=True,
        aspect="auto",
        labels=dict(x="Previsto", y="Real", color="Contagem"),
        x=classes,
        y=classes,
        color_continuous_scale="Blues",
        title=f"Matriz de confusao multiclasses - {melhor_nome}",
    )
    st.plotly_chart(fig_cm, width=_FEATURE_WIDTH)
    st.success(f"Melhor modelo nesta execução: **{melhor_nome}**")
