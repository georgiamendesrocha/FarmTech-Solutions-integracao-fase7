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


def _locations() -> list[dict]:
    return execute_query("SELECT ID_LOCATION, NM_CITY||' - '||NM_COUNTRY AS LABEL FROM WTH_LOCATIONS ORDER BY NM_CITY")


def _hourly(id_loc: int, hours: int = 48) -> pd.DataFrame:
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


def _daily(id_loc: int) -> pd.DataFrame:
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


def _write(fig: go.Figure, filename: str, height: int = 900) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(OUTPUT_DIR / filename), width=1600, height=height, scale=2)
    print(f"[OK] {filename}")


def main() -> None:
    locs = _locations()
    if not locs:
        raise RuntimeError("Nenhuma localização encontrada em WTH_LOCATIONS.")
    id_loc = int(locs[0]["id_location"])

    df_h = _hourly(id_loc, hours=48)
    if not df_h.empty:
        fig_main = make_subplots(specs=[[{"secondary_y": True}]])
        fig_main.add_trace(go.Scatter(x=df_h["dt_forecast"], y=df_h["nr_temperature_2m"], name="Temperatura °C", line=dict(color="#FF6B35", width=2)))
        fig_main.add_trace(go.Scatter(x=df_h["dt_forecast"], y=df_h["nr_apparent_temp"], name="Sensação térmica °C", line=dict(color="#FFA559", dash="dot")))
        fig_main.add_trace(go.Bar(x=df_h["dt_forecast"], y=df_h["nr_precipitation"], name="Precipitação mm", marker_color="#4FC3F7", opacity=0.65), secondary_y=True)
        fig_main.update_layout(title="Temperatura, sensação térmica e precipitação por hora", legend=dict(orientation="h", yanchor="bottom", y=1.02), height=380, margin=dict(t=48))
        fig_main.update_yaxes(title_text="°C", secondary_y=False)
        fig_main.update_yaxes(title_text="mm", secondary_y=True)
        _write(fig_main, "forecast_01_temp_sensacao_precip_horaria.png", height=760)

        fig_hum = px.area(df_h, x="dt_forecast", y="nr_humidity", title="Humidade relativa prevista (%)", color_discrete_sequence=["#29B6F6"])
        fig_hum.update_layout(height=320, margin=dict(t=40))
        _write(fig_hum, "forecast_02_humidade_horaria.png", height=640)

        fig_pb = px.bar(df_h, x="dt_forecast", y="nr_precip_prob", title="Probabilidade de precipitação (%)", color_discrete_sequence=["#0288D1"])
        fig_pb.update_layout(height=320, margin=dict(t=40))
        _write(fig_pb, "forecast_03_probabilidade_chuva_horaria.png", height=640)

        fig_wind = go.Figure()
        fig_wind.add_trace(go.Scatter(x=df_h["dt_forecast"], y=df_h["nr_windspeed_10m"], name="Vento km/h", line=dict(color="#5C6BC0", width=2), fill="tozeroy", fillcolor="rgba(92,107,192,0.12)"))
        fig_wind.update_layout(title="Velocidade do vento à superfície (10 m)", height=300, margin=dict(t=40))
        _write(fig_wind, "forecast_04_vento_horario.png", height=620)

        if "nr_pressure_msl" in df_h.columns and df_h["nr_pressure_msl"].notna().any():
            fig_pr = px.line(df_h.dropna(subset=["nr_pressure_msl"]), x="dt_forecast", y="nr_pressure_msl", title="Pressão ao nível do mar (hPa)", markers=True)
            fig_pr.update_traces(line=dict(color="#00695C", width=2))
            fig_pr.update_layout(height=280, margin=dict(t=40))
            _write(fig_pr, "forecast_05_pressao_horaria.png", height=620)

    df_d = _daily(id_loc)
    if not df_d.empty:
        fig_amp = go.Figure()
        fig_amp.add_trace(go.Scatter(x=df_d["dt_forecast"], y=df_d["nr_temp_max"], fill=None, name="Máx. °C", line=dict(color="#FF6B35", width=2)))
        fig_amp.add_trace(go.Scatter(x=df_d["dt_forecast"], y=df_d["nr_temp_min"], fill="tonexty", name="Mín. °C", line=dict(color="#4FC3F7", width=2), fillcolor="rgba(79,195,247,0.2)"))
        fig_amp.add_trace(go.Scatter(x=df_d["dt_forecast"], y=df_d["nr_apparent_max"], name="Sensação máx.", line=dict(color="#E65100", dash="dash")))
        fig_amp.add_trace(go.Scatter(x=df_d["dt_forecast"], y=df_d["nr_apparent_min"], name="Sensação mín.", line=dict(color="#01579B", dash="dash")))
        fig_amp.update_layout(title="Temperatura e sensação térmica (diária)", height=340, legend=dict(orientation="h", yanchor="bottom", y=1.02), margin=dict(t=48))
        _write(fig_amp, "forecast_06_amplitude_termica_diaria.png", height=700)

        fig_rain = go.Figure()
        fig_rain.add_trace(go.Bar(x=df_d["dt_forecast"], y=df_d["nr_precip_sum"], name="Precipitação total (mm)", marker_color="#0288D1"))
        fig_rain.add_trace(go.Scatter(x=df_d["dt_forecast"], y=df_d["nr_precip_prob_max"], name="Prob. máx. chuva %", yaxis="y2", line=dict(color="#F9A825", width=2), mode="lines+markers"))
        fig_rain.update_layout(title="Precipitação diária e probabilidade máxima", height=320, yaxis=dict(title="mm"), yaxis2=dict(title="%", overlaying="y", side="right", showgrid=False), margin=dict(t=40), legend=dict(orientation="h"))
        _write(fig_rain, "forecast_07_precipitacao_diaria_prob_max.png", height=680)

        fig_wx = make_subplots(rows=1, cols=2, subplot_titles=("Vento máx. e rajada (km/h)", "Índice UV máx."))
        fig_wx.add_trace(go.Bar(x=df_d["dt_forecast"], y=df_d["nr_windspeed_max"], name="Vento máx.", marker_color="#5C6BC0"), row=1, col=1)
        fig_wx.add_trace(go.Bar(x=df_d["dt_forecast"], y=df_d["nr_windgusts_max"], name="Rajada máx.", marker_color="#3949AB"), row=1, col=1)
        fig_wx.add_trace(go.Bar(x=df_d["dt_forecast"], y=df_d["nr_uv_max"], name="UV máx.", marker_color="#FDD835", showlegend=False), row=1, col=2)
        fig_wx.update_layout(height=360, title_text="Ventos e UV por dia", margin=dict(t=56), barmode="group")
        _write(fig_wx, "forecast_08_vento_uv_diario.png", height=760)

    print("[OK] Exportação previsão concluída.")


if __name__ == "__main__":
    main()

