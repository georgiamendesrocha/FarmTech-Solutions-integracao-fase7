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
from farmtech_integracao.fase2_r import validar_fase2_r

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
        if stored.get("source", {}).get("csv_exported") is False:
            st.error("A consulta funcionou, mas a exportação CSV falhou. Consulte o log da aplicação.")
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

# A verificação usa o mesmo caminho absoluto usado pela exportação.
arquivo_csv = fase2.forecast_csv_path()
if arquivo_csv.is_file():
    st.success("CSV meteorológico disponível para análise.")
    with arquivo_csv.open("rb") as arquivo:
        st.download_button("Baixar CSV da previsão", data=arquivo.read(),
                           file_name="previsao_tempo.csv", mime="text/csv")
else:
    st.caption("CSV meteorológico não gerado nesta instalação. Consulte uma previsão para criá-lo.")

available = fase2.availability()
with st.expander("Informações técnicas e análises R"):
    capabilities = available.data
    st.write("Histórico IoT:", "presente" if capabilities.get("history_available") else "ausente")
    st.write("CSV meteorológico:", "presente" if arquivo_csv.is_file() else "ausente")
    st.write("Análises R:", "Rscript localizado" if capabilities.get("r_detected") else "Rscript não localizado")
    st.caption("As análises R são executadas somente quando solicitadas. A integração de dados reais exige períodos coincidentes.")
    st.caption("O ESP32/Wokwi é um protótipo didático; dados de sensores simulados não são observações meteorológicas reais.")


# Integração real e prova demonstrativa são apresentadas separadamente.
st.divider()
st.subheader("Validação R — Fase 2")
st.caption("Teste sob demanda: analisa uma cópia do histórico IoT original e integra dois CSVs sintéticos temporalmente compatíveis. Não altera dados históricos nem associa maio a novembro.")
if st.button("Executar validação R", type="primary", disabled=not capabilities.get("r_execution_enabled")):
    with st.spinner("Executando scripts R e verificando arquivos e cálculos..."):
        st.session_state["fase2_r_resultado"] = validar_fase2_r()

r_resultado = st.session_state.get("fase2_r_resultado")
if r_resultado:
    if r_resultado["status"] == "ok":
        st.success(r_resultado["message"])
        left, right = st.columns(2)
        left.metric("Registros do histórico IoT analisados", r_resultado["historico_linhas"])
        right.metric("Registros integrados (dados sintéticos)", r_resultado["demonstracao_linhas"])
        st.caption(r_resultado["origem"])
        st.dataframe(pd.DataFrame(r_resultado["amostra"]), hide_index=True, width="stretch")
        st.download_button("Baixar integração demonstrativa (CSV)", data=r_resultado["csv_demonstrativo"], file_name="validacao_r_demonstrativa.csv", mime="text/csv")
        st.download_button("Baixar relatório R do histórico IoT", data=r_resultado["relatorio_historico"], file_name="analise_r_historico.txt", mime="text/plain")
    else:
        st.error(r_resultado["message"])
