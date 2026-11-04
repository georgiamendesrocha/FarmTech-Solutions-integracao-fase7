"""
Exporta as imagens do README do módulo IoT (dashboard Streamlit atual).

Este script cobre TODOS os gráficos exibidos na página `src/frontend/pages/iot.py`.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "readme"
CSV_PATH = ROOT / "src" / "dados" / "historico_irrigacao.csv"

load_dotenv(ROOT / ".env", override=True)


def _bomba_label(val) -> str:
    if val is None or pd.isna(val):
        return "Desligada"
    if isinstance(val, Decimal):
        return "Ligada" if int(val) == 1 else "Desligada"
    if isinstance(val, (int, float, np.integer, np.bool_)):
        return "Ligada" if int(val) == 1 else "Desligada"
    t = str(val).strip().lower()
    return "Ligada" if t in ("ligada", "1", "true", "sim") else "Desligada"


def _padronizar_df(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]

    aliases = {
        "temperatura": "temp_c",
        "ph": "ph_corr",
        "nitrogenio": "n",
        "fosforo": "p",
        "potassio": "k",
        "irrigacao_bin": "bomba_fw",
    }
    for old, new in aliases.items():
        if new not in d.columns and old in d.columns:
            d[new] = d[old]

    if "instante" not in d.columns:
        d["instante"] = pd.to_datetime(d.get("ts_iso"), errors="coerce")
    else:
        d["instante"] = pd.to_datetime(d["instante"], errors="coerce")

    for c in ("umidade", "temp_c", "ph_corr"):
        if c not in d.columns:
            d[c] = np.nan
        d[c] = pd.to_numeric(d[c], errors="coerce")

    for c in ("n", "p", "k"):
        if c not in d.columns:
            d[c] = 0
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int).clip(0, 1)

    if "bomba_fw" not in d.columns:
        d["bomba_fw"] = 0
    d["bomba_fw"] = pd.to_numeric(d["bomba_fw"], errors="coerce").fillna(0).astype(int).clip(0, 1)
    d["irrigacao"] = d["bomba_fw"].apply(_bomba_label)

    d = d.dropna(subset=["umidade", "temp_c", "ph_corr", "instante"]).copy()
    d = d.sort_values("instante").reset_index(drop=True)
    d.insert(0, "id", np.arange(1, len(d) + 1, dtype=int))
    return d


def _carregar_oracle() -> pd.DataFrame:
    import oracledb

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


def _export(fig: "go.Figure", filename: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(OUT_DIR / filename), width=1600, height=900, scale=2)
    print(f"[OK] {filename}")


def main() -> None:
    # Capturas "sem filtros": dff == df (logo, não aplicamos recortes)
    try:
        df_raw = _carregar_oracle()
    except Exception as e:
        print(f"[INFO] Oracle indisponivel ({e}). Usando CSV fallback.")
        df_raw = _carregar_csv()

    dff = _padronizar_df(df_raw)
    if dff.empty:
        raise RuntimeError("Dataset IoT vazio apos normalizacao.")

    # ===== Bloco principal de solo =====
    fig_u = px.histogram(
        dff,
        x="umidade",
        nbins=24,
        histnorm="percent",
        color_discrete_sequence=["#2d7a4f"],
        title="Distribuicao da umidade",
    )
    fig_u.add_vline(x=40, line_dash="dash", line_color="red", annotation_text="40%")
    _export(fig_u, "readme_01_umidade.png")

    fig_sc = px.scatter(
        dff,
        x="temp_c",
        y="umidade",
        color="irrigacao",
        color_discrete_map={"Ligada": "#1a5f3a", "Desligada": "#c0392b"},
        title="Temperatura x umidade",
    )
    _export(fig_sc, "readme_02_dispersao.png")

    fig_u2 = px.histogram(
        dff,
        x="umidade",
        color="irrigacao",
        barmode="overlay",
        histnorm="percent",
        nbins=20,
        title="Umidade por bomba",
    )
    _export(fig_u2, "readme_03a_umidade_por_bomba.png")

    fig_box_u = px.box(dff, x="irrigacao", y="umidade", color="irrigacao", title="Box umidade")
    _export(fig_box_u, "readme_03b_box_umidade.png")

    fig_box_t = px.box(dff, x="irrigacao", y="temp_c", color="irrigacao", title="Box temperatura")
    _export(fig_box_t, "readme_03c_box_temperatura.png")

    fig_ph = px.histogram(
        dff,
        x="ph_corr",
        nbins=20,
        histnorm="percent",
        color_discrete_sequence=["#3b82f6"],
        title="Distribuicao do pH",
    )
    fig_ph.add_vrect(x0=6.0, x1=7.0, fillcolor="green", opacity=0.1, annotation_text="faixa ideal")
    _export(fig_ph, "readme_04_ph.png")

    irr_counts = dff["irrigacao"].value_counts().reset_index()
    irr_counts.columns = ["status", "count"]
    fig_pie = px.pie(
        irr_counts,
        names="status",
        values="count",
        hole=0.45,
        color="status",
        color_discrete_map={"Ligada": "#2d7a4f", "Desligada": "#e74c3c"},
        title="Irrigacao",
    )
    _export(fig_pie, "readme_05_irrigacao.png")

    # ===== Nutrientes (seção dedicada) =====
    # 06 NPK (0 vs 1) — gráfico atual em `iot.py` (_render_nutrientes)
    ni, pi, ki = dff["n"].astype(int), dff["p"].astype(int), dff["k"].astype(int)
    n0, n1 = int((ni == 0).sum()), int((ni == 1).sum())
    p0, p1 = int((pi == 0).sum()), int((pi == 1).sum())
    k0, k1 = int((ki == 0).sum()), int((ki == 1).sum())

    fig_cnt = go.Figure()
    fig_cnt.add_bar(
        name="Ausente (0)",
        x=["N", "P", "K"],
        y=[n0, p0, k0],
        marker_color="#cbd5e1",
    )
    fig_cnt.add_bar(
        name="Presente (1)",
        x=["N", "P", "K"],
        y=[n1, p1, k1],
        marker_color=["#0ea5e9", "#f59e0b", "#8b5cf6"],
    )
    fig_cnt.update_layout(barmode="group", title="Contagem de leituras por nutriente (0 vs 1)")
    _export(fig_cnt, "readme_06_npk.png")

    # Proporção média NPK por irrigação (fig_m)
    medias_irr = dff.groupby("irrigacao", observed=True)[["n", "p", "k"]].mean().reset_index()
    medias_irr_m = medias_irr.melt(id_vars=["irrigacao"], var_name="nutriente", value_name="media")
    fig_m = px.bar(
        medias_irr_m,
        x="irrigacao",
        y="media",
        color="nutriente",
        barmode="group",
        title="Proporção média N, P, K por estado da irrigação",
        labels={"media": "Média (0–1)", "irrigacao": "Irrigação"},
        color_discrete_map={"n": "#0ea5e9", "p": "#f59e0b", "k": "#8b5cf6"},
    )
    fig_m.update_layout(yaxis_range=[0, 1.05], height=360)
    _export(fig_m, "readme_08_npk_media_por_irrigacao.png")

    # Perfis combinados N-P-K (fig_pf)
    perfil = dff["n"].astype(int).astype(str) + "-" + dff["p"].astype(int).astype(str) + "-" + dff["k"].astype(int).astype(str)
    vc_perfil = perfil.value_counts().sort_values(ascending=False)
    fig_pf = px.bar(
        x=vc_perfil.index.astype(str),
        y=vc_perfil.values,
        labels={"x": "Perfil N-P-K", "y": "Registros"},
        title="Distribuição dos oito padrões possíveis",
        color=vc_perfil.values,
        color_continuous_scale="Teal",
    )
    fig_pf.update_layout(showlegend=False, height=320, xaxis_tickangle=-25)
    _export(fig_pf, "readme_09_npk_perfis.png")

    # Série temporal NPK (fig_ts)
    ts = dff.sort_values("instante")
    step = max(1, len(ts) // 400)
    ts_plot = ts.iloc[::step] if len(ts) > 400 else ts
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=ts_plot["instante"], y=ts_plot["n"], name="N", line=dict(color="#0ea5e9", width=1), connectgaps=True))
    fig_ts.add_trace(go.Scatter(x=ts_plot["instante"], y=ts_plot["p"], name="P", line=dict(color="#f59e0b", width=1), connectgaps=True))
    fig_ts.add_trace(go.Scatter(x=ts_plot["instante"], y=ts_plot["k"], name="K", line=dict(color="#8b5cf6", width=1), connectgaps=True))
    fig_ts.update_layout(
        title="Série temporal dos nutrientes (0/1)" + (f" — amostra 1/{step}" if step > 1 else ""),
        yaxis=dict(range=[-0.05, 1.05], tickvals=[0, 1]),
        height=340,
        legend=dict(orientation="h"),
    )
    _export(fig_ts, "readme_10_npk_serie_temporal.png")

    # Heatmap irrigação x perfil NPK (fig_hm)
    tmp = dff.copy()
    tmp["perfil_npk"] = perfil.to_numpy()
    cx = tmp.pivot_table(index="irrigacao", columns="perfil_npk", aggfunc="size", fill_value=0)
    if len(vc_perfil) <= 12 and not cx.empty:
        fig_hm = px.imshow(
            cx.values,
            x=[str(c) for c in cx.columns],
            y=[str(i) for i in cx.index],
            aspect="auto",
            labels=dict(x="Perfil N-P-K", y="Irrigação", color="Registros"),
            title="Cruzamento: irrigação × perfil NPK",
            color_continuous_scale="Blues",
        )
        fig_hm.update_layout(height=max(280, 80 + 40 * len(cx.index)))
        _export(fig_hm, "readme_11_npk_heatmap_perfil_irrigacao.png")

    # Pizzas individuais N/P/K
    for fname, titulo, serie in [
        ("readme_12_n_pizza.png", "Nitrogênio (N)", dff["n"]),
        ("readme_13_p_pizza.png", "Fósforo (P)", dff["p"]),
        ("readme_14_k_pizza.png", "Potássio (K)", dff["k"]),
    ]:
        vc = serie.astype(int).value_counts().reindex([0, 1], fill_value=0)
        fig_p = px.pie(
            names=["Ausente (0)", "Presente (1)"],
            values=[int(vc.iloc[0]), int(vc.iloc[1])],
            title=titulo,
            color_discrete_sequence=["#94a3b8", "#22c55e"],
            hole=0.35,
        )
        fig_p.update_layout(height=300, margin=dict(t=40, b=20))
        _export(fig_p, fname)

    dff_corr = dff.rename(columns={"temp_c": "temperatura", "ph_corr": "ph", "n": "nitrogenio", "p": "fosforo", "k": "potassio"})
    corr = dff_corr[["umidade", "temperatura", "ph", "nitrogenio", "fosforo", "potassio"]].corr(numeric_only=True)

    fig_corr = px.imshow(
        corr,
        text_auto=".2f",
        aspect="equal",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Correlação entre sensores",
    )
    _export(fig_corr, "readme_07_correlacao.png")


if __name__ == "__main__":
    main()

