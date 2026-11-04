"""Gestão agrícola da Fase 1 dentro da dashboard preservada da Fase 4."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st
from farmtech_integracao import fase1
from farmtech_integracao.ui import info_card


st.set_page_config(page_title="Gestão agrícola | FarmTech", page_icon="🌱", layout="wide")
st.title("Gestão agrícola")
st.caption("Fase 1 · áreas, linhas de plantio e comparação de insumos")
st.write("Calcule a área de um talhão e consulte quantidades e custos do catálogo original.")

available = fase1.availability()
if not available.ok:
    st.warning(available.message)
    st.stop()

shapes = {
    "Retângulo": ("rectangle", 2), "Círculo": ("circle", 1), "Triângulo": ("triangle", 3),
    "Pentágono regular": ("pentagon", 5), "Hexágono regular": ("hexagon", 6),
    "Heptágono regular": ("heptagon", 7), "Octógono regular": ("octagon", 8),
}
geometry = st.selectbox("Geometria do talhão", list(shapes))
shape, count = shapes[geometry]
with st.form("fase1_plot"):
    culture = st.selectbox("Cultura", ["Soja", "Milho", "Café", "Trigo", "Cana-de-açúcar"])
    if shape == "circle":
        measurements = [st.number_input("Raio (m)", min_value=0.01, max_value=1_000_000.0, value=10.0)]
    elif shape == "rectangle":
        cols = st.columns(2)
        measurements = [cols[0].number_input("Largura (m)", min_value=0.01, max_value=1_000_000.0, value=10.0),
                        cols[1].number_input("Comprimento (m)", min_value=0.01, max_value=1_000_000.0, value=20.0)]
        st.caption("O cálculo de quatro lados da Fase 1 pressupõe um retângulo.")
    elif shape == "triangle":
        cols = st.columns(3)
        measurements = [cols[i].number_input(f"Lado {i + 1} (m)", min_value=0.01, max_value=1_000_000.0,
                                              value=10.0, key=f"fase1_triangle_{i}") for i in range(3)]
    else:
        side = st.number_input("Medida de cada lado (m)", min_value=0.01, max_value=1_000_000.0, value=10.0)
        measurements = [side] * count
    spacing = st.number_input("Espaçamento entre linhas (m)", min_value=0.01, max_value=1_000_000.0, value=0.5)
    submitted = st.form_submit_button("Calcular talhão", type="primary")

if submitted:
    with st.spinner("Calculando área e insumos…"):
        result = fase1.calculate_plot(shape, measurements, crop=culture, spacing=spacing)
    st.session_state["fase1_integration_result"] = result.as_dict()

stored = st.session_state.get("fase1_integration_result")
if stored:
    if stored["status"] != "ok":
        st.warning(stored["message"])
    else:
        data = stored["data"]
        st.subheader(f"Resultado · {data['crop']} · {data['geometry']}")
        cols = st.columns(4)
        cols[0].metric("Área", f"{data['area_m2']:,.2f} m²")
        cols[1].metric("Hectares", f"{data['hectares']:,.4f} ha")
        cols[2].metric("Alqueires", f"{data['alqueires']:,.4f}")
        cols[3].metric("Linhas estimadas", f"{data['estimated_line_count']:,}")
        products = pd.DataFrame(data["products"])
        if not products.empty:
            st.plotly_chart(px.bar(products, x="product", y="total_cost", color="category",
                                   labels={"product": "Produto", "total_cost": "Custo total estimado (R$)",
                                           "category": "Categoria"},
                                   title="Compare produtos concorrentes dentro da mesma categoria"),
                            width="stretch")
            st.dataframe(products.rename(columns={
                "category": "Categoria", "product": "Produto", "manufacturer": "Fabricante",
                "dose": "Dose/ha", "dose_unit": "Unidade/ha", "quantity": "Quantidade total",
                "quantity_unit": "Unidade", "cost_per_ha": "R$/ha", "total_cost": "Custo total (R$)",
                "dose_per_m": "Dose por metro", "dose_per_m_unit": "Unidade por metro",
                "lowest_cost_in_category": "Menor custo na categoria",
            }), width="stretch", hide_index=True)
        for note in data["notes"]:
            st.caption(note)
        info_card("O resultado fica nesta sessão. O catálogo ilustrativo exige avaliação agronômica antes do uso em campo.")
