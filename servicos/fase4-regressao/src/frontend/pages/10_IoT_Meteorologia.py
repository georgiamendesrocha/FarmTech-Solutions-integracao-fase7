"""Consulta meteorológica da Fase 2, sob demanda e sem captura de hardware."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st
from farmtech_integracao import fase2

st.set_page_config(page_title="IoT e meteorologia | FarmTech", page_icon="🌦️", layout="wide")
st.title("IoT e meteorologia")
st.caption("Fase 2 · previsão Open-Meteo e condições de disponibilidade")
st.write("Consulte a previsão horária de uma cidade. Os horários dos gráficos são apresentados em America/Bahia.")

available = fase2.availability()
if not available.ok:
    st.warning(available.message)
else:
    with st.form("fase2_forecast"):
        city = st.text_input("Cidade", value="Irecê", max_chars=120)
        submitted = st.form_submit_button("Consultar previsão", type="primary")
    if submitted:
        with st.spinner("Consultando a Open-Meteo…"):
            result = fase2.forecast(city)
        st.session_state["fase2_integration_result"] = result.as_dict()

stored = st.session_state.get("fase2_integration_result")
if stored:
    if stored["status"] != "ok":
        st.warning(stored["message"])
    else:
        data = stored["data"]
        location = data["location"]
        st.subheader(" · ".join(str(location[key]) for key in ("name", "admin1", "country") if location[key]))
        st.caption(f"Localização retornada: {location['latitude']:.4f}, {location['longitude']:.4f}. Confira a cidade antes de interpretar os dados.")
        frame = pd.DataFrame(data["hourly"])
        frame["Horário (Bahia)"] = pd.to_datetime(frame["ts_iso"], utc=True).dt.tz_convert("America/Bahia")
        cols = st.columns(2)
        charts = [("temp_c", "Temperatura (°C)"), ("umidade", "Umidade relativa (%)"),
                  ("rain_mm", "Precipitação (mm)"), ("wind_ms", "Vento (m/s)")]
        for index, (column, label) in enumerate(charts):
            figure = px.line(frame, x="Horário (Bahia)", y=column, labels={column: label}, title=label)
            cols[index % 2].plotly_chart(figure, width="stretch")
        st.dataframe(frame[["Horário (Bahia)", "temp_c", "umidade", "rain_mm", "wind_ms"]].rename(columns={
            "temp_c": "Temperatura (°C)", "umidade": "Umidade (%)", "rain_mm": "Chuva (mm)", "wind_ms": "Vento (m/s)",
        }), hide_index=True, width="stretch")
        st.caption(f"Fonte: Open-Meteo · consulta em {stored['source']['retrieved_at']} · dados originais em UTC.")
        st.caption("A previsão apoia a análise; ela não comanda o firmware de irrigação.")

with st.expander("Disponibilidade de IoT e análises R"):
    capabilities = available.data
    st.write("Histórico IoT local:", "presente" if capabilities.get("history_available") else "ausente")
    st.write("CSV meteorológico local:", "presente" if capabilities.get("forecast_csv_available") else "ausente")
    st.write("Rscript no PATH:", "disponível" if capabilities.get("r_installed_on_path") else "não localizado")
    st.write("A captura serial e as análises R exigem preparação externa; esta página disponibiliza a consulta meteorológica.")
    for condition in capabilities.get("preconditions", []):
        st.caption(condition)
    st.caption("O ESP32/Wokwi é um protótipo didático com sensores simulados. O histórico local precisa ter origem e fuso identificados.")
