from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.db import execute_query

OUTPUT_DIR = ROOT / "assets" / "readme"
DEFAULT_DIAS_ANALISE = 90


def _locations() -> list[dict]:
    return execute_query(
        """
        SELECT ID_LOCATION, NM_CITY||' - '||NM_COUNTRY AS LABEL
        FROM WTH_LOCATIONS
        ORDER BY NM_CITY
        """
    )


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


def _write(fig: go.Figure, filename: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(OUTPUT_DIR / filename), width=1600, height=900, scale=2)
    print(f"[OK] {filename}")


def main() -> None:
    locs = _locations()
    if not locs:
        raise RuntimeError("Nenhuma localizacao encontrada em WTH_LOCATIONS.")
    id_loc = int(locs[0]["id_location"])

    df_h = _hourly_24h(id_loc)
    if not df_h.empty:
        fig_24h = make_subplots(specs=[[{"secondary_y": True}]])
        fig_24h.add_trace(go.Scatter(x=df_h["dt_forecast"], y=df_h["nr_temperature_2m"], name="Temperatura °C", line=dict(color="#FF6B35", width=2)))
        fig_24h.add_trace(go.Scatter(x=df_h["dt_forecast"], y=df_h["nr_apparent_temp"], name="Sensação térmica °C", line=dict(color="#FFA559", dash="dot")))
        fig_24h.add_trace(go.Bar(x=df_h["dt_forecast"], y=df_h["nr_precipitation"], name="Chuva mm", marker_color="#4FC3F7", opacity=0.6), secondary_y=True)
        fig_24h.update_layout(title="Previsão 24h — temperatura, sensação térmica e chuva", legend=dict(orientation="h"))
        fig_24h.update_yaxes(title_text="°C", secondary_y=False)
        fig_24h.update_yaxes(title_text="mm", secondary_y=True)
        _write(fig_24h, "weather_01_previsao_24h_temp_chuva.png")

        fig_humidity = px.area(df_h, x="dt_forecast", y="nr_humidity", title="Humidade nas próximas 24h (%)", color_discrete_sequence=["#29B6F6"])
        _write(fig_humidity, "weather_02_umidade_24h.png")

        fig_precip_prob = px.bar(df_h, x="dt_forecast", y="nr_precip_prob", title="Probabilidade de chuva nas próximas 24h (%)", color_discrete_sequence=["#0288D1"])
        _write(fig_precip_prob, "weather_03_prob_chuva_24h.png")

    df_d = _daily_7d(id_loc)
    if not df_d.empty:
        fig_amp = go.Figure()
        fig_amp.add_trace(go.Scatter(x=df_d["dt_forecast"], y=df_d["nr_temp_max"], fill=None, name="Max", line=dict(color="#FF6B35")))
        fig_amp.add_trace(go.Scatter(x=df_d["dt_forecast"], y=df_d["nr_temp_min"], fill="tonexty", name="Min", line=dict(color="#4FC3F7"), fillcolor="rgba(79,195,247,0.15)"))
        fig_amp.update_layout(title="Amplitude térmica 7 dias")
        _write(fig_amp, "weather_04_amplitude_termica_7d.png")

    df_m = _monthly(id_loc)
    if not df_m.empty:
        fig_m = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Temperatura média mensal (°C)", "Precipitação total mensal (mm)"))
        fig_m.add_trace(go.Scatter(x=df_m["mes"], y=df_m["temp_media"], name="Média", line=dict(color="#FF6B35")), row=1, col=1)
        fig_m.add_trace(go.Scatter(x=df_m["mes"], y=df_m["temp_max"], name="Max", line=dict(color="#FF6B35", dash="dot"), opacity=0.5), row=1, col=1)
        fig_m.add_trace(go.Scatter(x=df_m["mes"], y=df_m["temp_min"], name="Min", line=dict(color="#4FC3F7", dash="dot"), opacity=0.5), row=1, col=1)
        fig_m.add_trace(go.Bar(x=df_m["mes"], y=df_m["precip_total"], name="Precipitação", marker_color="#0288D1"), row=2, col=1)
        fig_m.update_layout(title="Série temporal mensal")
        _write(fig_m, "weather_05_serie_mensal_temperatura_precip.png")

    df_ml = _ml_dataset(id_loc, dias=DEFAULT_DIAS_ANALISE)
    if not df_ml.empty:
        num_cols = ["nr_temperature_2m", "nr_humidity", "nr_precipitation", "nr_pressure_msl", "nr_windspeed_10m", "nr_cloudcover", "nr_uv_index", "nr_shortwave_rad"]
        available = [c for c in num_cols if c in df_ml.columns]
        if len(available) >= 2:
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
            fig_corr = go.Figure(go.Heatmap(z=corr.values, x=[labels.get(c, c) for c in corr.columns], y=[labels.get(c, c) for c in corr.index], colorscale="RdBu", zmid=0, text=corr.round(2).values, texttemplate="%{text}"))
            fig_corr.update_layout(title="Matriz de correlação (Pearson)")
            _write(fig_corr, "weather_06_correlacao_variaveis.png")

    df_w = _wind_pattern(id_loc)
    if not df_w.empty:
        fig_w = px.bar(df_w, x="hora", y="vento_medio", color="vento_medio", color_continuous_scale="Blues", labels={"hora": "Hora", "vento_medio": "Vento médio (km/h)"}, title="Padrão de vento por hora do dia")
        _write(fig_w, "weather_07_vento_por_hora.png")

    print("[OK] Exportação análise concluída.")


if __name__ == "__main__":
    main()

