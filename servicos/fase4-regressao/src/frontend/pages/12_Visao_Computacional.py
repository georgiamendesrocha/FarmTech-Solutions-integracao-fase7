"""Avaliação explícita da YOLO preservada, em ambiente independente da dashboard."""

import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import plotly.graph_objects as go
import streamlit as st

from farmtech_integracao.fase6 import REVISAO_YOLO, availability, evaluate_customizada

st.set_page_config(page_title="Visão Computacional — FarmTech", layout="wide")
st.title("Visão computacional — banana e milho")
st.caption("YOLOv5s customizada preservada: avaliação das oito imagens de teste, em CPU.")

repo = st.text_input(
    "Checkout Git local da YOLOv5",
    value=os.environ.get("FARMTECH_YOLO_REPO", ""),
    help=f"Use um checkout existente e limpo na revisão {REVISAO_YOLO}. Um cache do PyTorch Hub não substitui esse checkout.",
)
state = availability(repo)
if state.ok:
    st.info(state.message)
else:
    st.warning(state.message)
    with st.expander("Verificar pré-requisitos locais"):
        labels = {
            "python_existe": "Executável Python da Fase 6",
            "avaliador_existe": "Avaliador preservado",
            "checkpoint_existe": "Checkpoint customizado",
            "checkout_configurado": "Caminho do checkout informado",
            "checkout_git": "Metadados Git do checkout",
            "hubconf_existe": "Carregador local hubconf.py",
            "teste_banana": "Quatro imagens e rótulos de banana",
            "teste_milho": "Quatro imagens e rótulos de milho",
        }
        for key, present in state.data.get("checks", {}).items():
            st.write(f"{'✓' if present else '○'} {labels.get(key, key)}")

st.caption("O Python 3.13.13, a revisão e o hash dos pesos são verificados ao solicitar a avaliação. Os resultados históricos permanecem separados.")
if st.button("Avaliar YOLO customizada", type="primary", disabled=not state.ok):
    with st.spinner("Avaliando as imagens no ambiente de visão computacional…"):
        result = evaluate_customizada(repo)
    st.session_state["fase6_avaliacao"] = {"repo": repo, "resultado": result.as_dict()}

stored = st.session_state.get("fase6_avaliacao", {})
if stored.get("repo") == repo and stored.get("resultado"):
    result = stored["resultado"]
    if result["status"] != "ok":
        st.error(result["message"])
    else:
        st.success(result["message"])
        data = result["data"]
        left, right = st.columns(2)
        left.metric("Imagens de teste", data["total_imagens"])
        right.metric("Tempo médio em CPU", f"{data['tempo_medio_ms']:.2f} ms/imagem")
        metrics = data["metricas"]
        figure = go.Figure()
        for key, label in (("precision", "Precisão"), ("recall", "Recall"), ("f1", "F1")):
            figure.add_bar(name=label, x=list(metrics), y=[100 * values[key] for values in metrics.values()])
        figure.update_layout(barmode="group", yaxis_title="%", yaxis_range=[0, 100], xaxis_title="Classe")
        st.plotly_chart(figure, width="stretch")
        st.dataframe([
            {"Classe": name, "TP": values["tp"], "FP": values["fp"], "FN": values["fn"]}
            for name, values in metrics.items()
        ], hide_index=True)
        st.caption("Confiança 0,25 · IoU de associação 0,50 · imagem 640. Precision, Recall e F1 descrevem este pequeno conjunto de teste; não representam mAP.")
