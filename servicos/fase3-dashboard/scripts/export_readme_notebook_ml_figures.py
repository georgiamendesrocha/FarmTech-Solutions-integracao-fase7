"""
Exporta as imagens do README da secção Notebook ML (Ir Além).

Espelha o notebook `src/ml/Edemir_RM571375_fase3_cap1.ipynb`:

Parte A — Sensores Fase 2 (bomba):
  - notebook_ml_01_histograma_umidade.png
  - notebook_ml_02_temp_umidade_bomba.png
  - notebook_ml_03_ph.png
  - notebook_ml_04_pizza_irrigacao.png
  - notebook_ml_05_npk_medias.png
  - notebook_ml_06_correlacoes.png
  - notebook_ml_07_kmeans_clusters.png
  - notebook_ml_08_comparacao_modelos.png
  - notebook_ml_09_matriz_confusao.png

Parte A 3.b — Dados de cultura reais (Atividade_Cap10_produtos_agricolas.csv):
  - notebook_ml_10_culturas_distribuicao.png
  - notebook_ml_11_culturas_perfil_real.png
  - notebook_ml_12_culturas_temp_umidade.png

Parte B — Produtos agrícolas (multiclasse):
  - notebook_ml_13_partB_distribuicao_culturas.png
  - notebook_ml_14_partB_histograma_umidade.png
  - notebook_ml_15_partB_temp_umidade_por_cultura.png
  - notebook_ml_16_partB_box_n.png
  - notebook_ml_17_partB_box_ph.png
  - notebook_ml_18_partB_box_chuva.png
  - notebook_ml_19_partB_correlacoes.png
  - notebook_ml_20_partB_perfil_top3.png
  - notebook_ml_21_partB_comparacao_modelos.png
  - notebook_ml_22_partB_matriz_confusao.png
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import oracledb
import pandas as pd
import seaborn as sns
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

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "readme"
CSV_PATH = ROOT / "src" / "dados" / "historico_irrigacao.csv"
AGRI_CSV_PATH = ROOT / "src" / "dados" / "Atividade_Cap10_produtos_agricolas.csv"

load_dotenv(ROOT / ".env", override=True)

plt.rcParams["figure.figsize"] = (9, 4)
plt.rcParams["figure.dpi"] = 120
sns.set_theme(style="whitegrid")


def _encontrar_raiz_repo() -> Path:
    aqui = Path.cwd().resolve()
    for cand in [aqui, *aqui.parents]:
        if (cand / ".env").is_file() and (cand / "src").is_dir():
            return cand
    return aqui


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


def _carregar_csv() -> pd.DataFrame:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"CSV nao encontrado: {CSV_PATH}")
    return pd.read_csv(CSV_PATH)


def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    # Igual ao notebook (cell 3)
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
    """Igual ao `_preparar_produtos` do dashboard / notebook (cell 1).

    Esquema do CSV `Atividade_Cap10_produtos_agricolas.csv`:
    `N,P,K,temperature,humidity,ph,rainfall,label`.
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
    df = df.dropna(subset=required).reset_index(drop=True)
    return df


def _savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(str(path), bbox_inches="tight")
    plt.close()


def main() -> None:
    # Carrega (Oracle -> fallback CSV) como no notebook
    try:
        raw = _carregar_oracle()
        fonte = "oracle"
    except Exception as e:
        print(f"[INFO] Oracle indisponivel: {e}. Usando CSV fallback.")
        raw = _carregar_csv()
        fonte = "csv_fallback"

    df = _preparar(raw)
    print(f"[INFO] Fonte: {fonte} | Linhas apos preparo: {len(df)}")

    # --- 1) EDA / Grafico 1-6 (cell 5) ---
    # 1. Histograma de umidade
    plt.figure()
    plt.hist(df["umidade"], bins=20, color="#2d7a4f", edgecolor="white")
    plt.title("Distribuicao da umidade do solo")
    plt.xlabel("Umidade (%)")
    plt.ylabel("Frequencia")
    _savefig(OUT_DIR / "notebook_ml_01_histograma_umidade.png")

    # 2. Dispersao temperatura x umidade
    plt.figure()
    plt.scatter(df["temp_c"], df["umidade"], c=df["bomba_fw"], cmap="coolwarm", alpha=0.7)
    plt.title("Temperatura x umidade (cor = bomba_fw)")
    plt.xlabel("Temperatura (C)")
    plt.ylabel("Umidade (%)")
    cbar = plt.colorbar()
    cbar.set_label("bomba_fw")
    _savefig(OUT_DIR / "notebook_ml_02_temp_umidade_bomba.png")

    # 3. Histograma de pH
    plt.figure()
    plt.hist(df["ph_corr"], bins=20, color="#457b9d", edgecolor="white")
    plt.title("Distribuicao do pH corrigido")
    plt.xlabel("pH")
    plt.ylabel("Frequencia")
    _savefig(OUT_DIR / "notebook_ml_03_ph.png")

    # 4. Pizza da irrigacao
    vc = df["bomba_fw"].value_counts().sort_index()
    labels = ["Desligada (0)", "Ligada (1)"] if len(vc) == 2 else [str(i) for i in vc.index]
    plt.figure(figsize=(5, 5))
    colors = ["#e76f51", "#2d7a4f"][: len(vc)]
    plt.pie(vc.values, labels=labels, autopct="%1.1f%%", colors=colors)
    plt.title("Proporcao por estado da irrigacao")
    _savefig(OUT_DIR / "notebook_ml_04_pizza_irrigacao.png")

    # 5. Medias NPK por estado da bomba
    medias = df.groupby("bomba_fw")[["N", "P", "K"]].mean()
    plt.figure()
    medias.plot(kind="bar")
    plt.title("Medias N, P e K por estado da bomba")
    plt.xlabel("bomba_fw")
    plt.ylabel("Media")
    _savefig(OUT_DIR / "notebook_ml_05_npk_medias.png")

    # 6. Heatmap correlação
    corr = df[["umidade", "temp_c", "ph_corr", "N", "P", "K", "bomba_fw"]].corr()
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdYlGn", center=0)
    plt.title("Correlacao entre variaveis")
    _savefig(OUT_DIR / "notebook_ml_06_correlacoes.png")

    # --- 2) Referencia + KMeans (cell 7) ---
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
    _ = referencia  # mantido para fidelidade do notebook

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

    plt.figure(figsize=(8, 5))
    plt.scatter(df["temp_c"], df["umidade"], c=clusters, cmap="viridis", alpha=0.6)
    plt.scatter(centros["temp_c"], centros["umidade"], c="black", marker="X", s=140, label="Centroides")
    plt.title("K-Means (k=3): temperatura x umidade")
    plt.xlabel("Temperatura (C)")
    plt.ylabel("Umidade (%)")
    plt.legend()
    _savefig(OUT_DIR / "notebook_ml_07_kmeans_clusters.png")

    # --- 3) Modelos + grafico comparacao (cell 9-11) ---
    FEATURES = ["umidade", "temp_c", "ph_corr", "N", "P", "K"]
    TARGET = "bomba_fw"

    X = df[FEATURES].values.astype(float)
    y = df[TARGET].values.astype(int)

    X_scaled = StandardScaler().fit_transform(X)
    split_kwargs = {"test_size": 0.25, "random_state": 42}
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

    # 8) Comparacao 5 modelos (cell 11, parte 1)
    plt.figure(figsize=(10, 4))
    x = np.arange(len(resultado))
    w = 0.35
    plt.bar(x - w / 2, resultado["Acuracia_teste"], w, label="Acuracia (teste)")
    plt.bar(x + w / 2, resultado["F1_teste"], w, label="F1 (teste)")
    plt.xticks(x, resultado["Modelo"], rotation=15, ha="right")
    plt.ylim(0, 1.05)
    plt.title("Comparacao dos 5 modelos")
    plt.legend()
    _savefig(OUT_DIR / "notebook_ml_08_comparacao_modelos.png")

    # 9) Matriz de confusao (cell 11, parte 2)
    melhor_nome = resultado.iloc[0]["Modelo"]
    melhor_modelo = modelos[melhor_nome]
    pred_best = melhor_modelo.predict(X_test)
    cm = confusion_matrix(y_test, pred_best, labels=[0, 1])
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=["OFF", "ON"], yticklabels=["OFF", "ON"])
    plt.title(f"Matriz de confusao - {melhor_nome}")
    plt.xlabel("Previsto")
    plt.ylabel("Real")
    plt.tight_layout()
    plt.savefig(str(OUT_DIR / "notebook_ml_09_matriz_confusao.png"), bbox_inches="tight")
    plt.close()

    # ========================================================================
    # Parte A 3.b — Dados de cultura reais (cell 9 do notebook)
    # ========================================================================
    if not AGRI_CSV_PATH.is_file():
        print(f"[SKIP] Atividade_Cap10_produtos_agricolas.csv ausente em {AGRI_CSV_PATH} — pula Parte A 3.b e Parte B.")
        print("[OK] Exportacao concluida.")
        return

    dfa_pre = _preparar_produtos(pd.read_csv(AGRI_CSV_PATH, encoding="utf-8"))
    print(f"[INFO] Parte A 3.b / Parte B: {len(dfa_pre)} linhas em {AGRI_CSV_PATH.name}.")

    # 10) Distribuicao das culturas (Parte A 3.b)
    cfa_a = dfa_pre["label"].value_counts().sort_values(ascending=True)
    plt.figure(figsize=(9, max(4, 0.32 * len(cfa_a) + 1)))
    plt.barh(cfa_a.index.astype(str), cfa_a.values, color="#2d7a4f", edgecolor="white")
    plt.title("Distribuicao das culturas — base produtos agricolas")
    plt.xlabel("Contagem")
    plt.ylabel("Cultura")
    _savefig(OUT_DIR / "notebook_ml_10_culturas_distribuicao.png")

    # 11) Perfil real por cultura — heatmap das medias (Parte A 3.b)
    feats_perfil = ["N", "P", "K", "temp_c", "umidade", "ph_corr", "chuva"]
    perfil_real = (
        dfa_pre.groupby("label")[feats_perfil]
        .mean()
        .round(2)
        .sort_index()
    )
    perfil_norm = (perfil_real - perfil_real.min()) / (perfil_real.max() - perfil_real.min()).replace(0, 1)
    plt.figure(figsize=(9, max(4.5, 0.32 * len(perfil_real) + 1.2)))
    sns.heatmap(
        perfil_norm,
        annot=perfil_real.values,
        fmt=".1f",
        cmap="YlGn",
        cbar_kws={"label": "Normalizado por feature"},
    )
    plt.title("Perfil real por cultura — medias (anotacao = valor original)")
    plt.xlabel("")
    plt.ylabel("Cultura")
    _savefig(OUT_DIR / "notebook_ml_11_culturas_perfil_real.png")

    # 12) Dispersao temperatura x umidade colorida por cultura (Parte A 3.b)
    plt.figure(figsize=(9, 5))
    sns.scatterplot(data=dfa_pre, x="temp_c", y="umidade", hue="label", alpha=0.7, s=22, legend="brief")
    plt.title("Temperatura x umidade por cultura — base produtos agricolas")
    plt.xlabel("Temperatura (C)")
    plt.ylabel("Umidade (%)")
    plt.legend(title="cultura", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=7, ncol=1)
    _savefig(OUT_DIR / "notebook_ml_12_culturas_temp_umidade.png")

    # ========================================================================
    # Parte B — Produtos agricolas (multiclasse)
    # ========================================================================
    dfa = dfa_pre.copy()

    # 13) Distribuicao das culturas (Parte B)
    cfa = dfa["label"].value_counts().sort_values(ascending=False)
    plt.figure(figsize=(11, max(4, 0.18 * len(cfa) + 1)))
    plt.bar(cfa.index.astype(str), cfa.values, color="#2d7a4f", edgecolor="white")
    plt.title("Distribuicao das culturas (label)")
    plt.xlabel("Cultura")
    plt.ylabel("Contagem")
    plt.xticks(rotation=45, ha="right")
    _savefig(OUT_DIR / "notebook_ml_13_partB_distribuicao_culturas.png")

    # 14) Histograma de umidade (Parte B)
    plt.figure()
    plt.hist(dfa["umidade"], bins=20, color="#2d7a4f", edgecolor="white")
    plt.title("Distribuicao da umidade (Parte B)")
    plt.xlabel("Umidade (%)")
    plt.ylabel("Frequencia")
    _savefig(OUT_DIR / "notebook_ml_14_partB_histograma_umidade.png")

    # 15) Temp x umidade por cultura (Parte B)
    plt.figure(figsize=(9, 5))
    sns.scatterplot(data=dfa, x="temp_c", y="umidade", hue="label", alpha=0.75, s=22, legend="brief")
    plt.title("Temperatura x umidade por cultura")
    plt.xlabel("Temperatura (C)")
    plt.ylabel("Umidade (%)")
    plt.legend(title="label", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=7)
    _savefig(OUT_DIR / "notebook_ml_15_partB_temp_umidade_por_cultura.png")

    # 16) Boxplot N por cultura (Parte B)
    plt.figure(figsize=(11, 4))
    sns.boxplot(data=dfa, x="label", y="N")
    plt.xticks(rotation=45, ha="right")
    plt.title("N por cultura")
    _savefig(OUT_DIR / "notebook_ml_16_partB_box_n.png")

    # 17) Boxplot pH por cultura (Parte B)
    plt.figure(figsize=(11, 4))
    sns.boxplot(data=dfa, x="label", y="ph_corr")
    plt.xticks(rotation=45, ha="right")
    plt.title("pH por cultura")
    plt.ylabel("pH")
    _savefig(OUT_DIR / "notebook_ml_17_partB_box_ph.png")

    # 18) Boxplot chuva por cultura (Parte B)
    plt.figure(figsize=(11, 4))
    sns.boxplot(data=dfa, x="label", y="chuva")
    plt.xticks(rotation=45, ha="right")
    plt.title("Chuva (mm) por cultura")
    plt.ylabel("Chuva (mm)")
    _savefig(OUT_DIR / "notebook_ml_18_partB_box_chuva.png")

    # 19) Heatmap correlacao (Parte B - 7 variaveis)
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        dfa[feats_perfil].corr(),
        annot=True,
        fmt=".2f",
        cmap="RdYlGn",
        center=0,
        vmin=-1,
        vmax=1,
    )
    plt.title("Correlacao entre variaveis (Parte B)")
    _savefig(OUT_DIR / "notebook_ml_19_partB_correlacoes.png")

    # 20) Perfil ideal das 3 culturas mais frequentes (Parte B - cell 17 do notebook)
    top3 = dfa["label"].value_counts().head(3).index.tolist()
    perfil_top3 = (
        dfa[dfa["label"].isin(top3)]
        .groupby("label", as_index=True)[feats_perfil]
        .mean()
        .round(2)
        .reindex(top3)
    )
    perfil_top3_norm = (perfil_top3 - perfil_top3.min()) / (perfil_top3.max() - perfil_top3.min()).replace(0, 1)
    plt.figure(figsize=(8, 3.6))
    sns.heatmap(
        perfil_top3_norm,
        annot=perfil_top3.values,
        fmt=".1f",
        cmap="YlGn",
        cbar_kws={"label": "Normalizado por feature"},
    )
    plt.title(f"Perfil ideal — 3 culturas mais frequentes ({', '.join(top3)})")
    plt.xlabel("")
    plt.ylabel("Cultura")
    _savefig(OUT_DIR / "notebook_ml_20_partB_perfil_top3.png")

    # 21) Comparacao 5 modelos (Parte B - multiclasse)
    Xb = dfa[feats_perfil].to_numpy(dtype=float, copy=True)
    yb = dfa["label"].astype(str).to_numpy(copy=True)
    Xb_scaled = StandardScaler().fit_transform(Xb)
    sk_b: dict = {"test_size": 0.25, "random_state": 42}
    if pd.Series(yb).value_counts().min() >= 2:
        sk_b["stratify"] = yb
    try:
        Xtr_b, Xte_b, ytr_b, yte_b = train_test_split(Xb_scaled, yb, **sk_b)
    except ValueError:
        sk_b.pop("stratify", None)
        Xtr_b, Xte_b, ytr_b, yte_b = train_test_split(Xb_scaled, yb, **sk_b)

    modelos_b = {
        "Regressao Logistica": LogisticRegression(max_iter=1200, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42, max_depth=10),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42),
        "k-NN": KNeighborsClassifier(n_neighbors=max(3, min(7, len(Xtr_b) // 6))),
        "Naive Bayes": GaussianNB(),
    }
    min_cls_b = int(pd.Series(yb).value_counts().min())
    n_splits_b = min(5, min_cls_b) if min_cls_b >= 2 else 0
    usar_cv_b = n_splits_b >= 2 and len(yb) >= 10

    linhas_b = []
    fitted_b: dict = {}
    for nome, modelo in modelos_b.items():
        modelo.fit(Xtr_b, ytr_b)
        fitted_b[nome] = modelo
        pred_b = modelo.predict(Xte_b)
        acc_b = float(accuracy_score(yte_b, pred_b))
        f1w_b = float(f1_score(yte_b, pred_b, average="weighted", zero_division=0))
        cv_acc_b = float("nan")
        if usar_cv_b:
            cv_b = StratifiedKFold(n_splits=n_splits_b, shuffle=True, random_state=42)
            cv_acc_b = float(cross_val_score(modelo, Xb_scaled, yb, cv=cv_b, scoring="accuracy").mean())
        linhas_b.append({"Modelo": nome, "Acuracia_teste": acc_b, "F1_ponderado": f1w_b, "Acuracia_CV": cv_acc_b})

    resultado_b = pd.DataFrame(linhas_b).sort_values("Acuracia_teste", ascending=False).reset_index(drop=True)
    plt.figure(figsize=(10, 4))
    xb_pos = np.arange(len(resultado_b))
    wb_ = 0.35
    plt.bar(xb_pos - wb_ / 2, resultado_b["Acuracia_teste"], wb_, label="Acuracia (teste)")
    plt.bar(xb_pos + wb_ / 2, resultado_b["F1_ponderado"], wb_, label="F1 ponderado")
    plt.xticks(xb_pos, resultado_b["Modelo"], rotation=15, ha="right")
    plt.ylim(0, 1.05)
    plt.title("Comparacao dos 5 modelos — Parte B (multiclasse)")
    plt.legend()
    _savefig(OUT_DIR / "notebook_ml_21_partB_comparacao_modelos.png")

    # 22) Matriz de confusao multiclasse (Parte B)
    melhor_b = resultado_b.iloc[0]["Modelo"]
    pred_best_b = fitted_b[melhor_b].predict(Xte_b)
    classes_b = sorted(pd.Series(yte_b).astype(str).unique().tolist())
    cm_b = confusion_matrix(yte_b, pred_best_b, labels=classes_b)
    plt.figure(figsize=(max(8, 0.55 * len(classes_b) + 4), max(7, 0.55 * len(classes_b) + 3)))
    sns.heatmap(
        cm_b,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=classes_b,
        yticklabels=classes_b,
        cbar_kws={"label": "Contagem"},
    )
    plt.title(f"Matriz de confusao multiclasses — {melhor_b}")
    plt.ylabel("Real")
    plt.xlabel("Previsto")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    _savefig(OUT_DIR / "notebook_ml_22_partB_matriz_confusao.png")

    print("[OK] Exportacao concluida.")


if __name__ == "__main__":
    main()

