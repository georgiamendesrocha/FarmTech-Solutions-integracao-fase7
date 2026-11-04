from pathlib import Path
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import oracledb
from dotenv import load_dotenv

from src.api.db import execute_query
from src.utils.sensores import _bomba_label, _padronizar_df

_ROOT = Path(__file__).resolve().parents[2]
_CSV_PATH = _ROOT / "dados" / "historico_irrigacao.csv"
_CACHE_TTL = 20

load_dotenv(_ROOT / ".env", override=True)


def _load_oracle() -> pd.DataFrame:
    """Carrega diretamente de SENSORES_FARMTECH via oracledb, como nos scripts/testes."""
    user = os.getenv("ORACLE_USER")
    pwd = os.getenv("ORACLE_PASS")
    dsn = os.getenv("ORACLE_DSN")
    if not (user and pwd and dsn):
        raise ValueError("Variáveis ORACLE_USER/ORACLE_PASS/ORACLE_DSN ausentes.")

    with oracledb.connect(user=user, password=pwd, dsn=dsn) as conn:
        df = pd.read_sql("SELECT * FROM SENSORES_FARMTECH", conn)
    if df.empty:
        raise ValueError("Tabela SENSORES_FARMTECH está vazia no Oracle.")
    return _padronizar_df(df)


def _load_csv() -> pd.DataFrame:
    if not _CSV_PATH.is_file():
        raise FileNotFoundError(f"CSV não encontrado: {_CSV_PATH}")
    return _padronizar_df(pd.read_csv(_CSV_PATH, encoding="utf-8"))


@st.cache_data(ttl=_CACHE_TTL, show_spinner="Carregando dados IoT...")
def _load_data(fonte: str):
    if fonte == "oracle":
        # Sem fallback automático para CSV: Oracle selecionado deve usar Oracle.
        # Se falhar, o erro é mostrado de forma explícita.
        try:
            return _load_oracle(), "oracle", None
        except Exception as e:
            return None, "erro", str(e)
    try:
        return _load_csv(), "csv", None
    except Exception as e:
        return None, "erro", str(e)


def _render_nutrientes(dff: pd.DataFrame) -> None:
    """Vistas NPK agregadas (uma passagem por groupby / value_counts) — alinhado ao notebook/README."""
    st.subheader("🧪 Nutrientes N, P, K")
    st.caption("Flags **0/1** por leitura (presença detectada no solo). Média = proporção de leituras com nutriente ativo.")

    ni, pi, ki = dff["n"].astype(int), dff["p"].astype(int), dff["k"].astype(int)
    perfil = ni.astype(str) + "-" + pi.astype(str) + "-" + ki.astype(str)
    vc_perfil = perfil.value_counts().sort_values(ascending=False)
    medias_irr = dff.groupby("irrigacao", observed=True)[["n", "p", "k"]].mean().reset_index()
    medias_irr_m = medias_irr.melt(id_vars=["irrigacao"], var_name="nutriente", value_name="media")

    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("N ativo", f"{dff['n'].mean() * 100:.1f}%")
    r2.metric("P ativo", f"{dff['p'].mean() * 100:.1f}%")
    r3.metric("K ativo", f"{dff['k'].mean() * 100:.1f}%")
    todos = int(((ni == 1) & (pi == 1) & (ki == 1)).sum())
    nenhum = int(((ni == 0) & (pi == 0) & (ki == 0)).sum())
    r4.metric("Perfil 1-1-1", str(todos))
    r5.metric("Perfil 0-0-0", str(nenhum))

    g1, g2 = st.columns(2)
    with g1:
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
        st.plotly_chart(fig_m, width="stretch")
    with g2:
        n0, n1 = int((ni == 0).sum()), int((ni == 1).sum())
        p0, p1 = int((pi == 0).sum()), int((pi == 1).sum())
        k0, k1 = int((ki == 0).sum()), int((ki == 1).sum())
        fig_cnt = go.Figure()
        fig_cnt.add_bar(name="Ausente (0)", x=["N", "P", "K"], y=[n0, p0, k0], marker_color="#cbd5e1")
        fig_cnt.add_bar(name="Presente (1)", x=["N", "P", "K"], y=[n1, p1, k1], marker_color=["#0ea5e9", "#f59e0b", "#8b5cf6"])
        fig_cnt.update_layout(barmode="group", title="Contagem de leituras por nutriente (0 vs 1)", height=360)
        st.plotly_chart(fig_cnt, width="stretch")

    st.markdown("**Perfis combinados** (cada registo: `N-P-K` binário)")
    fig_pf = px.bar(
        x=vc_perfil.index.astype(str),
        y=vc_perfil.values,
        labels={"x": "Perfil N-P-K", "y": "Registros"},
        title="Distribuição dos oito padrões possíveis",
        color=vc_perfil.values,
        color_continuous_scale="Teal",
    )
    fig_pf.update_layout(showlegend=False, height=320, xaxis_tickangle=-25)
    st.plotly_chart(fig_pf, width="stretch")

    ts = dff.sort_values("instante")
    if len(ts) > 1:
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
        st.plotly_chart(fig_ts, width="stretch")

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
        st.plotly_chart(fig_hm, width="stretch")

    pie_c1, pie_c2, pie_c3 = st.columns(3)
    for col, name, s in (
        (pie_c1, "Nitrogênio (N)", dff["n"]),
        (pie_c2, "Fósforo (P)", dff["p"]),
        (pie_c3, "Potássio (K)", dff["k"]),
    ):
        with col:
            vc = s.astype(int).value_counts().reindex([0, 1], fill_value=0)
            fig_p = px.pie(
                names=["Ausente (0)", "Presente (1)"],
                values=[int(vc.iloc[0]), int(vc.iloc[1])],
                title=name,
                color_discrete_sequence=["#94a3b8", "#22c55e"],
                hole=0.35,
            )
            fig_p.update_layout(height=300, margin=dict(t=40, b=20))
            st.plotly_chart(fig_p, width="stretch")


st.title("🌱 Sensores IoT — FarmTech Solutions")

if "iot_fonte" not in st.session_state:
    st.session_state["iot_fonte"] = "oracle"

with st.sidebar:
    st.markdown("### Fonte de dados")
    c1, c2 = st.columns(2)
    if c1.button("Oracle", width="stretch", type="primary" if st.session_state["iot_fonte"] == "oracle" else "secondary"):
        st.session_state["iot_fonte"] = "oracle"
        st.rerun()
    if c2.button("CSV", width="stretch", type="primary" if st.session_state["iot_fonte"] == "csv" else "secondary"):
        st.session_state["iot_fonte"] = "csv"
        st.rerun()
    if st.button("🔄 Atualizar", width="stretch"):
        st.cache_data.clear()
        st.rerun()

df, status, err = _load_data(st.session_state["iot_fonte"])
if df is None:
    st.error(f"Falha ao carregar dados: {err}")
    st.stop()

if status == "oracle":
    st.success("Dados carregados do Oracle (`SENSORES_FARMTECH`).")
else:
    st.info(f"Dados carregados do CSV: `{_CSV_PATH.name}`")

with st.sidebar:
    st.divider()
    st.markdown("### Filtros")
    irr_opts = sorted(df["irrigacao"].dropna().unique().tolist())
    irr_sel = st.multiselect("Irrigação", irr_opts, default=irr_opts)
    u_min, u_max = float(df["umidade"].min()), float(df["umidade"].max())
    ph_min, ph_max = float(df["ph_corr"].min()), float(df["ph_corr"].max())
    u_rng = st.slider("Umidade (%)", min_value=u_min, max_value=u_max, value=(u_min, u_max))
    ph_rng = st.slider("pH", min_value=ph_min, max_value=ph_max, value=(ph_min, ph_max))

    ts = pd.to_datetime(df["instante"], errors="coerce")
    i0, i1 = 0, max(0, len(df) - 1)
    if len(df) > 1:
        i0, i1 = st.slider("Janela temporal (índice)", min_value=0, max_value=len(df) - 1, value=(0, len(df) - 1))
    t_lo = ts.iloc[i0]
    t_hi = ts.iloc[i1]

mask = (
    df["irrigacao"].isin(irr_sel)
    & df["umidade"].between(*u_rng)
    & df["ph_corr"].between(*ph_rng)
    & pd.to_datetime(df["instante"], errors="coerce").between(t_lo, t_hi, inclusive="both")
)
dff = df[mask].copy()

if dff.empty:
    st.warning("Nenhum dado com os filtros atuais.")
    st.stop()

# KPIs (visão geral do solo — nutrientes detalhados na secção seguinte)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📦 Registros", f"{len(dff):,}")
k2.metric("💧 Umidade média", f"{dff['umidade'].mean():.1f}%")
k3.metric("🌡️ Temp. média", f"{dff['temp_c'].mean():.1f}°C")
k4.metric("⚗️ pH médio", f"{dff['ph_corr'].mean():.2f}")
lig = int((dff["irrigacao"] == "Ligada").sum())
k5.metric("🚿 Irrigação ligada", f"{lig} ({(lig / max(len(dff), 1)) * 100:.0f}%)")

st.divider()
_render_nutrientes(dff)

st.divider()

col1, col2 = st.columns(2)
with col1:
    fig_u = px.histogram(dff, x="umidade", nbins=24, histnorm="percent", color_discrete_sequence=["#2d7a4f"], title="Distribuição da umidade")
    fig_u.add_vline(x=40, line_dash="dash", line_color="red", annotation_text="40%")
    st.plotly_chart(fig_u, width="stretch")

with col2:
    fig_sc = px.scatter(dff, x="temp_c", y="umidade", color="irrigacao", color_discrete_map={"Ligada": "#1a5f3a", "Desligada": "#c0392b"}, title="Temperatura × umidade")
    st.plotly_chart(fig_sc, width="stretch")

v1, v2, v3 = st.columns(3)
with v1:
    st.plotly_chart(px.histogram(dff, x="umidade", color="irrigacao", barmode="overlay", histnorm="percent", nbins=20, title="Umidade por bomba"), width="stretch")
with v2:
    st.plotly_chart(px.box(dff, x="irrigacao", y="umidade", color="irrigacao", title="Box umidade"), width="stretch")
with v3:
    st.plotly_chart(px.box(dff, x="irrigacao", y="temp_c", color="irrigacao", title="Box temperatura"), width="stretch")

col3, col4 = st.columns(2)
with col3:
    fig_ph = px.histogram(dff, x="ph_corr", nbins=20, histnorm="percent", color_discrete_sequence=["#3b82f6"], title="Distribuição do pH")
    fig_ph.add_vrect(x0=6.0, x1=7.0, fillcolor="green", opacity=0.1, annotation_text="faixa ideal")
    st.plotly_chart(fig_ph, width="stretch")

with col4:
    irr_counts = dff["irrigacao"].value_counts().reset_index()
    irr_counts.columns = ["status", "count"]
    fig_pie = px.pie(irr_counts, names="status", values="count", hole=0.45, color="status", color_discrete_map={"Ligada": "#2d7a4f", "Desligada": "#e74c3c"}, title="Irrigação")
    st.plotly_chart(fig_pie, width="stretch")

st.divider()
dff_corr = dff.rename(columns={"temp_c": "temperatura", "ph_corr": "ph", "n": "nitrogenio", "p": "fosforo", "k": "potassio"})
corr = dff_corr[["umidade", "temperatura", "ph", "nitrogenio", "fosforo", "potassio"]].corr(numeric_only=True)
st.plotly_chart(px.imshow(corr, text_auto=".2f", aspect="equal", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, title="Correlação entre sensores"), width="stretch")

st.subheader("📋 Dados filtrados")
out = dff.copy()
out["instante"] = pd.to_datetime(out["instante"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M:%S")
out = out.rename(columns={"temp_c": "temperatura", "ph_corr": "ph", "n": "nitrogenio", "p": "fosforo", "k": "potassio"})
st.dataframe(
    out[["id", "instante", "umidade", "temperatura", "ph", "nitrogenio", "fosforo", "potassio", "irrigacao"]],
    width="stretch",
    hide_index=True,
)
st.caption(f"Exibindo {len(out)} de {len(df)} linhas.")
