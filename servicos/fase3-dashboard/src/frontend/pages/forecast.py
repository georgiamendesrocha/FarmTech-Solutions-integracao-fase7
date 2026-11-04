import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.api.db import execute_query

TTL = 300

WMO_LABEL = {
    0: "Céu limpo",
    1: "Predominantemente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Névoa",
    48: "Névoa com gelo",
    51: "Garoa leve",
    53: "Garoa moderada",
    55: "Garoa intensa",
    61: "Chuva leve",
    63: "Chuva moderada",
    65: "Chuva forte",
    71: "Neve leve",
    73: "Neve moderada",
    75: "Neve forte",
    80: "Pancadas leves",
    81: "Pancadas moderadas",
    82: "Pancadas fortes",
    95: "Tempestade",
    96: "Tempestade c/ granizo",
    99: "Tempestade c/ granizo forte",
}
WMO_ICON = {
    0: "☀️",
    1: "🌤️",
    2: "⛅",
    3: "☁️",
    45: "🌫️",
    48: "🌫️",
    51: "🌦️",
    53: "🌦️",
    55: "🌧️",
    61: "🌧️",
    63: "🌧️",
    65: "🌧️",
    71: "❄️",
    73: "❄️",
    75: "❄️",
    80: "🌦️",
    81: "🌧️",
    82: "⛈️",
    95: "⛈️",
    96: "⛈️",
    99: "⛈️",
}


def _num(cur: dict, key: str, default=0.0):
    v = cur.get(key)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _format_visibility(metric_m: float) -> tuple[str, str]:
    """Open‑Meteo / Oracle guardam NR_VISIBILITY em metros (ver `createtable.sql`)."""
    if metric_m is None or metric_m <= 0 or pd.isna(metric_m):
        return "—", ""
    m = float(metric_m)
    if m < 1500:
        return f"{m:.0f} m", "Open‑Meteo (m)"
    km = m / 1000.0
    return f"{km:.1f} km", f"≈ {int(round(m))} m na fonte"


def _bomba_hint_clima(cur: dict) -> tuple[str, str]:
    """Indicação curta para esta hora — fácil de ler e traduzir."""
    p_chuva = _num(cur, "nr_precip_prob")
    chuva_mm = _num(cur, "nr_precipitation") + _num(cur, "nr_rain")
    temp = _num(cur, "nr_temperature_2m")
    um_ar = _num(cur, "nr_humidity")
    uv = _num(cur, "nr_uv_index")

    if p_chuva >= 55 or chuva_mm >= 0.4:
        return (
            "off",
            "Bomba **desligada** neste período previsto: chuva provável ou chuva já a cair.",
        )
    if p_chuva < 28 and temp >= 31 and um_ar < 42:
        return (
            "on",
            "Bomba **ligada ou a preparar rega**: tempo quente e seco ao ar; confira a umidade real do solo em **Sensores IoT** antes de aplicar água.",
        )
    if uv >= 8 and temp >= 28:
        return (
            "tip",
            "Condições **misturadas**: há sol forte — se precisar de irrigação, **prefira madrugada ou final da tarde** para perder menos água por evaporação.",
        )
    return (
        "rev",
        "Bomba **a rever**: o clima neste momento é moderado — use como apoio e **decida no campo** com sensores e prática local.",
    )


def _layout_main_chart(title: str, height: int, bottom_legend: int = 108) -> dict:
    """Legenda em baixo para não colidir com o título."""
    return dict(
        title=dict(text=title, x=0.0, xanchor="left", y=0.98, yanchor="top", font=dict(size=15)),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            x=0,
            xanchor="left",
        ),
        height=height,
        margin=dict(t=54, l=56, r=42, b=bottom_legend),
    )


@st.cache_data(ttl=TTL)
def _locations():
    return execute_query(
        "SELECT ID_LOCATION, NM_CITY||' - '||NM_COUNTRY AS LABEL FROM WTH_LOCATIONS ORDER BY NM_CITY"
    )


@st.cache_data(ttl=TTL)
def _current(id_loc: int):
    rows = execute_query(
        """
        SELECT DT_FORECAST, NR_TEMPERATURE_2M, NR_APPARENT_TEMP, NR_HUMIDITY, NR_DEWPOINT,
               NR_PRECIPITATION, NR_RAIN, NR_PRECIP_PROB, NR_WEATHERCODE, NR_PRESSURE_MSL,
               NR_CLOUDCOVER, NR_VISIBILITY, NR_WINDSPEED_10M, NR_WINDDIR_10M,
               NR_WINDGUSTS, NR_UV_INDEX, NR_SHORTWAVE_RAD
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


@st.cache_data(ttl=TTL)
def _hourly(id_loc: int, hours: int = 24):
    return pd.DataFrame(
        execute_query(
            """
            SELECT DT_FORECAST, NR_TEMPERATURE_2M, NR_APPARENT_TEMP, NR_HUMIDITY,
                   NR_PRECIPITATION, NR_PRECIP_PROB, NR_CLOUDCOVER, NR_WINDSPEED_10M,
                   NR_WEATHERCODE, NR_PRESSURE_MSL, NR_UV_INDEX
            FROM WTH_HOURLY_FORECAST
            WHERE ID_LOCATION = :l
              AND DT_FORECAST BETWEEN SYSTIMESTAMP
                  AND SYSTIMESTAMP + NUMTODSINTERVAL(:h, 'HOUR')
            ORDER BY DT_FORECAST
            """,
            {"l": id_loc, "h": hours},
        )
    )


@st.cache_data(ttl=TTL)
def _daily(id_loc: int):
    return pd.DataFrame(
        execute_query(
            """
            SELECT DT_FORECAST, NR_TEMP_MAX, NR_TEMP_MIN, NR_APPARENT_MAX, NR_APPARENT_MIN,
                   NR_SUNRISE, NR_SUNSET, NR_PRECIP_SUM, NR_RAIN_SUM, NR_PRECIP_HOURS,
                   NR_PRECIP_PROB_MAX, NR_WINDSPEED_MAX, NR_WINDGUSTS_MAX, NR_WINDDIR_DOM,
                   NR_UV_MAX, NR_WEATHERCODE
            FROM WTH_DAILY_FORECAST
            WHERE ID_LOCATION = :l AND DT_FORECAST BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE) + 6
            ORDER BY DT_FORECAST
            """,
            {"l": id_loc},
        )
    )


st.title("🌤️ Previsão do tempo")
st.caption(
    "Dados horários e diários **Open‑Meteo** gravados no Oracle (`WTH_HOURLY_FORECAST`, `WTH_DAILY_FORECAST`). "
    "Atualização pela API em segundo plano (~5 min)."
)

locs = _locations()
if not locs:
    st.warning("Nenhuma localização cadastrada. Arranque a API (`python run.py` ou `uvicorn`) para coletar dados.")
    st.stop()

loc_map = {r["label"]: r["id_location"] for r in locs}
id_loc = loc_map[st.sidebar.selectbox("📍 Localização", list(loc_map.keys()))]
horas_prev = st.sidebar.slider("Horizonte horário (painel detalhe)", min_value=24, max_value=168, value=48, step=24)
if st.sidebar.button("🔄 Atualizar cache"):
    st.cache_data.clear()
    st.rerun()

cur = _current(id_loc)
if cur:
    code = int(_num(cur, "nr_weathercode", 0))
    icon = WMO_ICON.get(code, "🌡️")
    lbl = WMO_LABEL.get(code, "—")
    st.markdown(f"### {icon} Condições atuais ({lbl})")
    dt = cur.get("dt_forecast")
    if dt is not None:
        st.caption(f"Instante da previsão mais recente (≤ agora): `{dt}`")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(
        "Temperatura",
        f"{_num(cur, 'nr_temperature_2m'):.1f} °C",
        f"Sensação {_num(cur, 'nr_apparent_temp'):.1f} °C",
    )
    m2.metric("Humidade", f"{_num(cur, 'nr_humidity'):.0f}%", f"Orvalho {_num(cur, 'nr_dewpoint'):.1f} °C")
    m3.metric(
        "Chuva / prob.",
        f"{_num(cur, 'nr_precipitation'):.2f} mm",
        f"P {_num(cur, 'nr_precip_prob'):.0f}% · Chuva {_num(cur, 'nr_rain'):.2f} mm",
    )
    m4.metric(
        "Vento",
        f"{_num(cur, 'nr_windspeed_10m'):.1f} km/h",
        f"Rajada {_num(cur, 'nr_windgusts'):.1f} km/h · {_num(cur, 'nr_winddir_10m'):.0f}°",
    )
    m5.metric(
        "Ambiente",
        f"{_num(cur, 'nr_cloudcover'):.0f}% nuvens",
        f"UV {_num(cur, 'nr_uv_index'):.1f} · {_num(cur, 'nr_pressure_msl'):.0f} hPa",
    )

    viz = _num(cur, "nr_visibility")
    rad = _num(cur, "nr_shortwave_rad")
    x1, x2 = st.columns(2)
    vz_main, vz_sub = _format_visibility(viz)
    if vz_sub:
        x1.metric("Visibilidade", vz_main, vz_sub, delta_color="off")
    else:
        x1.metric("Visibilidade", vz_main)
    x2.metric("Radiação curta (instante)", f"{rad:.1f} W/m²")

    st.subheader("Irrigação — indicação simples")
    st.caption(
        "Baseada apenas na **hora atual** da previsão Open‑Meteo. Para decisão nos **vários próximos dias**, use "
        "**Ir além → Painel IA · soluções**. Confira sempre solo e cultivo no campo."
    )
    cod, texto = _bomba_hint_clima(cur)
    if cod == "off":
        st.error(texto)
    elif cod == "on":
        st.success(texto)
    elif cod == "tip":
        st.warning(texto)
    else:
        st.info(texto)
else:
    st.warning("Sem leitura horária atual para esta localização.")

df_h = _hourly(id_loc, hours=horas_prev)

if not df_h.empty:
    st.subheader(f"Perspectiva horária ({horas_prev} h)")
    fig_main = make_subplots(specs=[[{"secondary_y": True}]])
    fig_main.add_trace(
        go.Scatter(
            x=df_h["dt_forecast"],
            y=df_h["nr_temperature_2m"],
            name="Temperatura °C",
            line=dict(color="#FF6B35", width=2),
        )
    )
    fig_main.add_trace(
        go.Scatter(
            x=df_h["dt_forecast"],
            y=df_h["nr_apparent_temp"],
            name="Sensação térmica °C",
            line=dict(color="#FFA559", dash="dot"),
        )
    )
    fig_main.add_trace(
        go.Bar(
            x=df_h["dt_forecast"],
            y=df_h["nr_precipitation"],
            name="Precipitação mm",
            marker_color="#4FC3F7",
            opacity=0.65,
        ),
        secondary_y=True,
    )
    fig_main.update_layout(**_layout_main_chart("Temperatura, sensação térmica e precipitação (por hora)", height=410))
    fig_main.update_yaxes(title_text="°C", secondary_y=False)
    fig_main.update_yaxes(title_text="mm", secondary_y=True)
    st.plotly_chart(fig_main, width="stretch")

    c_a, c_b = st.columns(2)
    with c_a:
        fig_hum = px.area(
            df_h,
            x="dt_forecast",
            y="nr_humidity",
            title="Humidade relativa prevista (%)",
            color_discrete_sequence=["#29B6F6"],
        )
        fig_hum.update_layout(
            height=320,
            margin=dict(t=48, l=48, r=28, b=56),
            title=dict(x=0, xanchor="left"),
        )
        st.plotly_chart(fig_hum, width="stretch")
    with c_b:
        fig_pb = px.bar(
            df_h,
            x="dt_forecast",
            y="nr_precip_prob",
            title="Probabilidade de precipitação (%)",
            color_discrete_sequence=["#0288D1"],
        )
        fig_pb.update_layout(
            height=320,
            margin=dict(t=48, l=48, r=28, b=72),
            title=dict(x=0, xanchor="left"),
            xaxis=dict(tickangle=-35),
        )
        st.plotly_chart(fig_pb, width="stretch")

    fig_wind = go.Figure()
    fig_wind.add_trace(
        go.Scatter(
            x=df_h["dt_forecast"],
            y=df_h["nr_windspeed_10m"],
            name="Vento km/h",
            line=dict(color="#5C6BC0", width=2),
            fill="tozeroy",
            fillcolor="rgba(92,107,192,0.12)",
        )
    )
    fig_wind.update_layout(
        title=dict(text="Velocidade do vento à superfície (10 m)", x=0, xanchor="left"),
        height=310,
        margin=dict(t=50, l=48, r=28, b=56),
        legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
    )
    st.plotly_chart(fig_wind, width="stretch")

    if "nr_pressure_msl" in df_h.columns and df_h["nr_pressure_msl"].notna().any():
        fig_pr = px.line(
            df_h.dropna(subset=["nr_pressure_msl"]),
            x="dt_forecast",
            y="nr_pressure_msl",
            title="Pressão ao nível do mar (hPa)",
            markers=True,
        )
        fig_pr.update_traces(line=dict(color="#00695C", width=2))
        fig_pr.update_layout(
            height=280,
            margin=dict(t=46, l=48, r=28, b=48),
            title=dict(x=0, xanchor="left"),
        )
        st.plotly_chart(fig_pr, width="stretch")
else:
    st.error(f"Sem dados horários para as próximas {horas_prev} h nesta localização.")

df_d = _daily(id_loc)
if not df_d.empty:
    st.subheader("Próximos 7 dias (agregado diário)")
    fig_amp = go.Figure()
    fig_amp.add_trace(
        go.Scatter(
            x=df_d["dt_forecast"],
            y=df_d["nr_temp_max"],
            fill=None,
            name="Máx. °C",
            line=dict(color="#FF6B35", width=2),
        )
    )
    fig_amp.add_trace(
        go.Scatter(
            x=df_d["dt_forecast"],
            y=df_d["nr_temp_min"],
            fill="tonexty",
            name="Mín. °C",
            line=dict(color="#4FC3F7", width=2),
            fillcolor="rgba(79,195,247,0.2)",
        )
    )
    fig_amp.add_trace(
        go.Scatter(
            x=df_d["dt_forecast"],
            y=df_d["nr_apparent_max"],
            name="Sensação máx.",
            line=dict(color="#E65100", dash="dash"),
        )
    )
    fig_amp.add_trace(
        go.Scatter(
            x=df_d["dt_forecast"],
            y=df_d["nr_apparent_min"],
            name="Sensação mín.",
            line=dict(color="#01579B", dash="dash"),
        )
    )
    fig_amp.update_layout(**_layout_main_chart("Temperatura e sensação térmica (diária)", height=370, bottom_legend=102))
    st.plotly_chart(fig_amp, width="stretch")

    fig_rain = go.Figure()
    fig_rain.add_trace(
        go.Bar(
            x=df_d["dt_forecast"],
            y=df_d["nr_precip_sum"],
            name="Precipitação total (mm)",
            marker_color="#0288D1",
        )
    )
    fig_rain.add_trace(
        go.Scatter(
            x=df_d["dt_forecast"],
            y=df_d["nr_precip_prob_max"],
            name="Prob. máx. chuva %",
            yaxis="y2",
            line=dict(color="#F9A825", width=2),
            mode="lines+markers",
        )
    )
    fig_rain.update_layout(
        title=dict(text="Precipitação diária e probabilidade máxima", x=0, xanchor="left", y=0.98),
        height=328,
        yaxis=dict(title="mm"),
        yaxis2=dict(title="%", overlaying="y", side="right", showgrid=False),
        margin=dict(t=54, l=52, r=52, b=88),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0),
    )
    st.plotly_chart(fig_rain, width="stretch")

    fig_wx = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Vento máx. e rajada (km/h)", "Índice UV máx."),
    )
    fig_wx.add_trace(
        go.Bar(x=df_d["dt_forecast"], y=df_d["nr_windspeed_max"], name="Vento máx.", marker_color="#5C6BC0"),
        row=1,
        col=1,
    )
    fig_wx.add_trace(
        go.Bar(x=df_d["dt_forecast"], y=df_d["nr_windgusts_max"], name="Rajada máx.", marker_color="#3949AB"),
        row=1,
        col=1,
    )
    fig_wx.add_trace(
        go.Bar(x=df_d["dt_forecast"], y=df_d["nr_uv_max"], name="UV máx.", marker_color="#FDD835", showlegend=False),
        row=1,
        col=2,
    )
    fig_wx.update_layout(
        height=368,
        title=dict(text="Ventos e UV por dia", x=0.02, xanchor="left", y=0.98),
        margin=dict(t=62, l=52, r=36, b=72),
        barmode="group",
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0),
    )
    st.plotly_chart(fig_wx, width="stretch")

    tab = df_d.copy()
    tab["data"] = pd.to_datetime(tab["dt_forecast"]).dt.strftime("%d/%m/%Y")
    tab["situação"] = tab["nr_weathercode"].apply(lambda c: WMO_LABEL.get(int(c or 0), "—"))
    tab["ícone"] = tab["nr_weathercode"].apply(lambda c: WMO_ICON.get(int(c or 0), ""))
    tab = tab.rename(
        columns={
            "nr_temp_max": "t_máx",
            "nr_temp_min": "t_mín",
            "nr_precip_sum": "chuva_mm",
            "nr_precip_prob_max": "prob_%",
            "nr_windspeed_max": "vento_km/h",
            "nr_uv_max": "uv",
        }
    )
    cols_show = ["data", "ícone", "situação", "t_máx", "t_mín", "chuva_mm", "prob_%", "vento_km/h", "uv"]
    cols_show = [c for c in cols_show if c in tab.columns]
    st.markdown("##### Tabela resumo (7 dias)")
    st.dataframe(
        tab[cols_show],
        width="stretch",
        hide_index=True,
    )

    if df_d["nr_sunrise"].notna().any() or df_d["nr_sunset"].notna().any():
        st.caption("Nascer / pôr do sol (quando disponíveis na base)")
        sun = df_d[["dt_forecast", "nr_sunrise", "nr_sunset"]].copy()
        sun["dia"] = pd.to_datetime(sun["dt_forecast"]).dt.strftime("%d/%m")
        st.dataframe(sun.rename(columns={"nr_sunrise": "nascer", "nr_sunset": "pôr"}), width="stretch", hide_index=True)
else:
    st.warning("Sem previsão diária (7 dias) para esta localização.")
