"""Consultas da Fase 3 a partir da dashboard preservada da Fase 4."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from farmtech_integracao.ui import info_card
from farmtech_integracao.fase3 import MAX_RECORDS, query_sensors

st.set_page_config(page_title="Consultas Oracle e CSV — FarmTech", layout="wide")
st.title("Consultas da Fase 3")
st.caption("Histórico agrícola da Fase 3: selecione a origem e consulte as leituras de sensores.")

with st.form("fase3_query_form"):
    selection = st.radio("Origem dos dados", ["CSV preservado", "Oracle — consulta real"])
    origin = "csv" if selection == "CSV preservado" else "oracle"
    limit = int(st.number_input("Limite de registros", min_value=1, max_value=MAX_RECORDS,
                                value=200, step=50))
    if origin == "csv":
        st.caption("Cópia local historico_irrigacao.csv preservada na Fase 3. A seleção usa as primeiras linhas do arquivo.")
    else:
        st.caption("Tabela SENSORES_FARMTECH. A consulta usa os últimos registros por ID e requer rede e credenciais de leitura configuradas no ambiente.")
    submitted = st.form_submit_button("Consultar leituras", type="primary")

if submitted:
    with st.spinner("Consultando a origem selecionada..."):
        result = query_sensors(origin, limit=limit)
    st.session_state["fase3_query_result"] = result.as_dict()
    st.session_state["fase3_query_origin"] = origin

response = st.session_state.get("fase3_query_result")
if response is None:
    info_card("Selecione a origem e clique em Consultar leituras para carregar o histórico.")
    st.stop()

source = response.get("source", {})
if st.session_state.get("fase3_query_origin") != origin:
    st.info("A origem foi alterada. Consulte novamente para exibir os dados selecionados.")
    st.stop()

if response.get("status") != "ok":
    st.warning(response.get("message", "A consulta está indisponível."))
    if origin == "oracle":
        st.info("Verifique a configuração ORACLE_USER, ORACLE_PASS e ORACLE_DSN com o responsável pelo ambiente e as permissões de leitura da tabela.")
    st.stop()

st.success(response["message"])
data = response.get("data", {})
rows = data.get("rows", [])
st.caption(f"Origem: {selection} · Recurso: {source.get('resource', '')} · Seleção: {data.get('selection', '')}.")
st.caption("Datas mantêm a informação da origem. Quando o fuso não está declarado, ele não é inferido.")
if not rows:
    st.info("A origem consultada não contém registros válidos para apresentação.")
    st.stop()

frame = pd.DataFrame(rows)
frame["instante"] = pd.to_datetime(frame["instante"], errors="coerce")
frame = frame.dropna(subset=["instante"]).sort_values("instante")
if frame.empty:
    st.warning("Os registros retornados não têm timestamps válidos para os gráficos.")
    st.stop()
last = frame.iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Umidade (%)", f"{last['umidade']:.1f}")
c2.metric("Temperatura (°C)", f"{last['temp_c']:.1f}")
c3.metric("pH", f"{last['ph_corr']:.2f}")
c4.metric("Irrigação", last["irrigacao"])
st.caption(f"Última leitura apresentada: {last['instante'].isoformat()}.")

chart_specs = [("umidade", "Umidade (%)"), ("temp_c", "Temperatura (°C)"),
               ("ph_corr", "pH"), ("bomba_fw", "Bomba (0 desligada / 1 ligada)")]
tabs = st.tabs([label for _, label in chart_specs])
for tab, (column, label) in zip(tabs, chart_specs):
    with tab:
        figure = px.line(frame, x="instante", y=column, markers=True,
                         title=f"{label} ao longo do tempo",
                         labels={"instante": "Timestamp da origem", column: label})
        if column == "bomba_fw":
            figure.update_yaxes(tickvals=[0, 1], range=[-0.1, 1.1])
        st.plotly_chart(figure, width="stretch")

st.caption("N, P e K usam flags 0/1. A normalização histórica da Fase 3 preenche flags ausentes com zero.")
st.dataframe(frame, width="stretch", hide_index=True)
