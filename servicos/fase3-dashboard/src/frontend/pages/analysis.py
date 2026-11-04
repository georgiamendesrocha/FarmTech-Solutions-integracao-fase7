"""
Análise orientada a IA sobre séries de **previsão meteorológica** (`WTH_*`).

Replica as mesmas vistas que o README associa a `weather_01` … `weather_07`,
em linha com `scripts/export_readme_weather_figures.py`.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.api.db import execute_query

TTL = 300
_DIASES_CORREL = 90
_CHART_WIDTH = "stretch"


@st.cache_data(ttl=TTL)
def _locations():
    return execute_query(
        "SELECT ID_LOCATION, NM_CITY||' - '||NM_COUNTRY AS LABEL FROM WTH_LOCATIONS ORDER BY NM_CITY"
    )


@st.cache_data(ttl=TTL)
def _hourly_24h(id_loc: int) -> pd.DataFrame:
    return pd.DataFrame(
        execute_query(
            """
            SELECT DT_FORECAST,NR_TEMPERATURE_2M,NR_APPARENT_TEMP,NR_HUMIDITY,
                   NR_PRECIPITATION,NR_PRECIP_PROB,NR_CLOUDCOVER,NR_WINDSPEED_10M,NR_WEATHERCODE
            FROM WTH_HOURLY_FORECAST
            WHERE ID_LOCATION=:l
              AND DT_FORECAST BETWEEN SYSTIMESTAMP AND SYSTIMESTAMP+NUMTODSINTERVAL(24,'HOUR')
            ORDER BY DT_FORECAST
            """,
            {"l": id_loc},
        )
    )


@st.cache_data(ttl=TTL)
def _daily_7d(id_loc: int) -> pd.DataFrame:
    return pd.DataFrame(
        execute_query(
            """
            SELECT DT_FORECAST,NR_TEMP_MAX,NR_TEMP_MIN,NR_PRECIP_SUM,
                   NR_PRECIP_PROB_MAX,NR_WINDSPEED_MAX,NR_UV_MAX,NR_WEATHERCODE
            FROM WTH_DAILY_FORECAST
            WHERE ID_LOCATION=:l AND DT_FORECAST BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE)+6
            ORDER BY DT_FORECAST
            """,
            {"l": id_loc},
        )
    )


@st.cache_data(ttl=TTL)
def _monthly(id_loc: int) -> pd.DataFrame:
    return pd.DataFrame(
        execute_query(
            """
            SELECT TO_CHAR(DT_FORECAST,'YYYY-MM') AS MES,
                   ROUND(AVG(NR_TEMPERATURE_2M),2) AS TEMP_MEDIA,
                   ROUND(MAX(NR_TEMPERATURE_2M),2) AS TEMP_MAX,
                   ROUND(MIN(NR_TEMPERATURE_2M),2) AS TEMP_MIN,
                   ROUND(AVG(NR_HUMIDITY),2) AS UMIDADE_MEDIA,
                   ROUND(SUM(NR_PRECIPITATION),2) AS PRECIP_TOTAL,
                   COUNT(*) AS NR_REGISTROS
            FROM WTH_HOURLY_FORECAST
            WHERE ID_LOCATION=:l AND DT_FORECAST>=ADD_MONTHS(TRUNC(SYSDATE,'MM'),-12)
            GROUP BY TO_CHAR(DT_FORECAST,'YYYY-MM')
            ORDER BY MES
            """,
            {"l": id_loc},
        )
    )


@st.cache_data(ttl=TTL)
def _ml_dataset(id_loc: int, dias: int) -> pd.DataFrame:
    return pd.DataFrame(
        execute_query(
            """
            SELECT TO_NUMBER(TO_CHAR(DT_FORECAST,'HH24')) AS HORA,
                   TO_NUMBER(TO_CHAR(DT_FORECAST,'D')) AS DIA_SEMANA,
                   TO_NUMBER(TO_CHAR(DT_FORECAST,'MM')) AS MES,
                   NR_TEMPERATURE_2M, NR_PRECIPITATION, NR_PRECIP_PROB,
                   NR_HUMIDITY, NR_DEWPOINT, NR_PRESSURE_MSL, NR_CLOUDCOVER,
                   NR_WINDSPEED_10M, NR_WINDDIR_10M, NR_UV_INDEX, NR_SHORTWAVE_RAD
            FROM WTH_HOURLY_FORECAST
            WHERE ID_LOCATION=:l AND DT_FORECAST>=SYSDATE-:d
            ORDER BY DT_FORECAST
            """,
            {"l": id_loc, "d": dias},
        )
    )


@st.cache_data(ttl=TTL)
def _wind_pattern(id_loc: int) -> pd.DataFrame:
    return pd.DataFrame(
        execute_query(
            """
            SELECT TO_CHAR(DT_FORECAST,'HH24') AS HORA,
                   ROUND(AVG(NR_WINDSPEED_10M),2) AS VENTO_MEDIO
            FROM WTH_HOURLY_FORECAST
            WHERE ID_LOCATION=:l AND DT_FORECAST>=SYSDATE-90
            GROUP BY TO_CHAR(DT_FORECAST,'HH24')
            ORDER BY HORA
            """,
            {"l": id_loc},
        )
    )


def _plot_24h_temp_chuva(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df["dt_forecast"],
            y=df["nr_temperature_2m"],
            name="Temperatura °C",
            line=dict(color="#FF6B35", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["dt_forecast"],
            y=df["nr_apparent_temp"],
            name="Sensação térmica °C",
            line=dict(color="#FFA559", dash="dot"),
        )
    )
    fig.add_trace(
        go.Bar(
            x=df["dt_forecast"],
            y=df["nr_precipitation"],
            name="Chuva mm",
            marker_color="#4FC3F7",
            opacity=0.6,
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Previsão 24 h — temperatura, sensação térmica e barras de chuva "
        "(README: weather_01_previsao_24h_temp_chuva)",
        legend=dict(orientation="h"),
    )
    fig.update_yaxes(title_text="°C", secondary_y=False)
    fig.update_yaxes(title_text="mm", secondary_y=True)
    return fig


def _plot_correlation(df_ml: pd.DataFrame) -> go.Figure | None:
    num_cols = [
        "nr_temperature_2m",
        "nr_humidity",
        "nr_precipitation",
        "nr_pressure_msl",
        "nr_windspeed_10m",
        "nr_cloudcover",
        "nr_uv_index",
        "nr_shortwave_rad",
    ]
    available = [c for c in num_cols if c in df_ml.columns]
    if len(available) < 2:
        return None
    labels = {
        "nr_temperature_2m": "Temp",
        "nr_humidity": "Umidade",
        "nr_precipitation": "Precip",
        "nr_pressure_msl": "Pressão",
        "nr_windspeed_10m": "Vento",
        "nr_cloudcover": "Nuvens",
        "nr_uv_index": "UV",
        "nr_shortwave_rad": "Radiação",
    }
    corr = df_ml[available].dropna().corr()
    fig = go.Figure(
        go.Heatmap(
            z=corr.values,
            x=[labels.get(c, c) for c in corr.columns],
            y=[labels.get(c, c) for c in corr.index],
            colorscale="RdBu",
            zmid=0,
            text=corr.round(2).values,
            texttemplate="%{text}",
        )
    )
    fig.update_layout(
        title="Matriz de correlação (Pearson) das variáveis climáticas "
        "(README: weather_06_correlacao_variaveis)",
    )
    return fig


st.title("🧠 Análise para IA — previsão do tempo")
st.caption(
    "Séries de previsão gravadas no Oracle (**`WTH_*`**) e alimentadas pela API (Open‑Meteo). "
    "Detalhes e figuras estáticas correspondentes estão no **README** (`assets/readme/`)."
)

locs = _locations()
if not locs:
    st.warning("Nenhuma localização em `WTH_LOCATIONS`. Arranque a API (`python run.py` ou uvicorn) para popular dados.")
    st.stop()

loc_map = {r["label"]: r["id_location"] for r in locs}
id_loc = loc_map[st.sidebar.selectbox("📍 Localização", list(loc_map.keys()))]
if st.sidebar.button("🔄 Atualizar cache"):
    st.cache_data.clear()
    st.rerun()

df_h = _hourly_24h(id_loc)
if df_h.empty:
    st.error("Sem registos horários nas próximas 24 h para esta localização.")
else:
    st.subheader("1. Previsão 24 h — temperatura, sensação térmica e chuva")
    st.plotly_chart(_plot_24h_temp_chuva(df_h), width=_CHART_WIDTH)

    st.subheader("2. Humidade nas próximas 24 h (%)")
    fig2 = px.area(
        df_h,
        x="dt_forecast",
        y="nr_humidity",
        title="Humidade prevista nas próximas 24 h (README: weather_02_umidade_24h)",
        color_discrete_sequence=["#29B6F6"],
    )
    st.plotly_chart(fig2, width=_CHART_WIDTH)

    st.subheader("3. Probabilidade de chuva nas próximas 24 h (%)")
    fig3 = px.bar(
        df_h,
        x="dt_forecast",
        y="nr_precip_prob",
        title="Probabilidade de chuva nas próximas 24 h (README: weather_03_prob_chuva_24h)",
        color_discrete_sequence=["#0288D1"],
    )
    st.plotly_chart(fig3, width=_CHART_WIDTH)

df_d = _daily_7d(id_loc)
if df_d.empty:
    st.warning("Sem dados diários para amplitude térmica.")
else:
    st.subheader("4. Amplitude térmica — 7 dias")
    fig4 = go.Figure()
    fig4.add_trace(
        go.Scatter(
            x=df_d["dt_forecast"],
            y=df_d["nr_temp_max"],
            fill=None,
            name="Max",
            line=dict(color="#FF6B35"),
        )
    )
    fig4.add_trace(
        go.Scatter(
            x=df_d["dt_forecast"],
            y=df_d["nr_temp_min"],
            fill="tonexty",
            name="Min",
            line=dict(color="#4FC3F7"),
            fillcolor="rgba(79,195,247,0.15)",
        )
    )
    fig4.update_layout(title="Faixa de temperatura mínima e máxima (README: weather_04_amplitude_termica_7d)")
    st.plotly_chart(fig4, width=_CHART_WIDTH)

df_m = _monthly(id_loc)
if df_m.empty:
    st.warning("Sem série mensal (últimos 12 meses) para gráficos.")
else:
    st.subheader("5. Série mensal — temperatura e precipitação total")
    fig_m = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=(
            "Temperatura média mensal (°C) — com máx./mín.",
            "Precipitação total mensal (mm)",
        ),
    )
    fig_m.add_trace(
        go.Scatter(x=df_m["mes"], y=df_m["temp_media"], name="Média", line=dict(color="#FF6B35")),
        row=1,
        col=1,
    )
    fig_m.add_trace(
        go.Scatter(
            x=df_m["mes"],
            y=df_m["temp_max"],
            name="Max",
            line=dict(color="#FF6B35", dash="dot"),
            opacity=0.5,
            showlegend=True,
        ),
        row=1,
        col=1,
    )
    fig_m.add_trace(
        go.Scatter(
            x=df_m["mes"],
            y=df_m["temp_min"],
            name="Min",
            line=dict(color="#4FC3F7", dash="dot"),
            opacity=0.5,
            showlegend=True,
        ),
        row=1,
        col=1,
    )
    fig_m.add_trace(
        go.Bar(x=df_m["mes"], y=df_m["precip_total"], name="Precipitação", marker_color="#0288D1", showlegend=False),
        row=2,
        col=1,
    )
    fig_m.update_layout(
        title_text="Série temporal mensal (README: weather_05_serie_mensal_temperatura_precip)",
        height=520,
    )
    st.plotly_chart(fig_m, width=_CHART_WIDTH)

df_ml = _ml_dataset(id_loc, _DIASES_CORREL)
fig_corr = _plot_correlation(df_ml)
if fig_corr is None:
    st.warning("Dados insuficientes para a matriz de correlação (README: weather_06).")
else:
    st.subheader("6. Correlação entre variáveis climáticas (Pearson)")
    st.plotly_chart(fig_corr, width=_CHART_WIDTH)
    st.caption(f"Base: últimos {_DIASES_CORREL} dias de previsões horárias na base.")

df_w = _wind_pattern(id_loc)
if df_w.empty:
    st.warning("Sem padrão de vento por hora (README: weather_07).")
else:
    st.subheader("7. Padrão médio de vento por hora do dia")
    fig_w = px.bar(
        df_w,
        x="hora",
        y="vento_medio",
        color="vento_medio",
        color_continuous_scale="Blues",
        labels={"hora": "Hora", "vento_medio": "Vento médio (km/h)"},
        title="Padrão de vento por hora do dia (README: weather_07_vento_por_hora)",
    )
    st.plotly_chart(fig_w, width=_CHART_WIDTH)
