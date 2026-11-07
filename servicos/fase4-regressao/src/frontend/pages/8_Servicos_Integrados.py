"""Visão geral adicional da Fase 7; inspeção local sem disparar os serviços."""

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from farmtech_integracao.demo import configure_dashboard, demo_path, inspect_database
configure_dashboard()

import streamlit as st
import plotly.express as px
from farmtech_integracao import fase1, fase2, fase3, fase6, fase7
from farmtech_integracao.ui import apply_theme, navigation_link
from farmtech_integracao.ui import info_card

st.set_page_config(page_title="Serviços integrados — FarmTech", page_icon="🌱", layout="wide")
apply_theme()
st.caption("FARMTECH SOLUTIONS · FASE 7")
st.title("Serviços integrados")
st.write("Uma entrada para gestão, IoT, consultas e visão computacional, com as análises da Fase 4 preservadas.")
info_card("Os indicadores verificam pré-condições locais. Rede, Oracle e inferência só são acionados nas páginas de cada serviço.")

services = [
    ("Gestão agrícola", "fase1", fase1, "pages/9_Gestao_Agricola.py", "Geometria e insumos com as funções da Fase 1."),
    ("IoT e meteorologia", "fase2", fase2, "pages/10_IoT_Meteorologia.py", "Previsão por cidade; requisitos de R, Wokwi e captura."),
    ("Consultas Oracle / CSV", "fase3", fase3, "pages/11_Oracle_Consultas.py", "Leitura com origem selecionada explicitamente."),
    ("Visão computacional", "fase6", fase6, "pages/12_Visao_Computacional.py", "Avaliação experimental da YOLO customizada em CPU."),
    ("Alertas — Fase 7", "fase7", fase7, "pages/13_Alertas_Fase7.py", "Avaliação local de sensores, demonstrações e prévia da mensagem. Sem envio SNS."),
]
statuses = []
for column, (label, phase, module, page, description) in zip(st.columns(len(services)), services):
    result = module.availability()
    statuses.append({"Serviço": label, "Pré-condições locais": "Disponível" if result.ok else "Pendente", "Quantidade": 1})
    with column:
        with st.container(border=True):
            st.subheader(label)
            st.caption(phase.upper())
            st.write(description)
            (st.success if result.ok else st.warning)(result.message)
            navigation_link(page, label="Acessar serviço", icon="↗️")

st.divider()
left, right = st.columns([1, 2])
with left:
    st.subheader("Prontidão local")
    chart = px.bar(statuses, x="Pré-condições locais", y="Quantidade", color="Serviço",
                   color_discrete_sequence=["#166534", "#43936c", "#a67724", "#274b69"])
    chart.update_layout(yaxis_title="Serviços", showlegend=False, height=270)
    chart.update_yaxes(dtick=1)
    st.plotly_chart(chart, width="stretch")
with right:
    st.subheader("Dados da Fase 4")
    database = inspect_database(Path(os.getenv("DB_PATH", str(demo_path()))))
    (st.success if database.ok else st.warning)(database.message)
    if database.ok:
        st.dataframe([{"Tabela": key, "Registros": value} for key, value in database.data["counts"].items()], hide_index=True, width="stretch")
    st.caption("A base reconstruída usa CSVs acadêmicos e leituras registradas/simuladas. Não é histórico real recuperado.")
    st.caption("NOAA, INMET e IBGE/SIDRA permanecem separados por origem, unidade, período e localidade na página Dados Oficiais.")
    navigation_link("pages/7_Dados_Oficiais.py", label="Consultar dados oficiais", icon="📊")
    st.code("python iniciar.py --preparar-demo", language="powershell")
    st.caption("Preparação explícita por terminal; recusa um destino existente. A simulação está desativada na entrada integrada.")
