"""Avaliação explícita da YOLO preservada, em ambiente independente da dashboard."""

import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import plotly.graph_objects as go
import streamlit as st

from farmtech_integracao.fase6 import REVISAO_YOLO, availability, evaluate_customizada, infer_availability, inferir_imagem, _configuracao
from PIL import Image, ImageDraw
from io import BytesIO
from farmtech_integracao.ui import info_card

st.set_page_config(page_title="Visão Computacional — FarmTech", layout="wide")
st.title("Visão computacional — banana e milho")
st.caption("YOLOv5s customizada preservada: avaliação das oito imagens de teste, em CPU.")

st.subheader("Analisar imagem")
st.caption("Envie JPG ou PNG (até 5 MB). Modelo experimental de banana e milho.")
upload = st.file_uploader("Selecionar imagem", type=["jpg", "jpeg", "png"], key="upload_yolo")
state_image = infer_availability()
if not state_image.ok:
    st.warning("Inferência temporariamente indisponível neste ambiente.")
    with st.expander("Detalhes técnicos para manutenção"):
        st.write(state_image.data.get("checks", {}))
if upload is not None:
    blob = upload.getvalue()
    if len(blob) > 5 * 1024 * 1024:
        st.error("Arquivo maior que 5 MB.")
    else:
        try:
            image = Image.open(BytesIO(blob))
            image.verify()
            st.image(blob, caption="Imagem enviada", width=480)
        except Image.DecompressionBombError:
            st.error("Imagem com dimensões excessivas. Envie uma versão menor em JPG ou PNG.")
        except (OSError, ValueError):
            st.error("Imagem inválida.")
        else:
            if st.button("Identificar banana ou milho", type="primary", disabled=not state_image.ok):
                with st.spinner("Executando inferência em CPU..."):
                    result_image = inferir_imagem(blob, upload.name)
                st.session_state["fase6_inferencia"] = {"name": upload.name,
                                                        "resultado": result_image.as_dict(),
                                                        "content": blob}
            stored_image = st.session_state.get("fase6_inferencia", {})
            if stored_image.get("name") == upload.name and stored_image.get("content") == blob:
                result_image = stored_image.get("resultado", {})
                if result_image.get("status") != "ok":
                    st.error(result_image.get("message", "Inferência indisponível."))
                else:
                    detections = result_image["data"]["deteccoes"]
                    if detections:
                        marked = Image.open(BytesIO(blob)).convert("RGB")
                        drawer = ImageDraw.Draw(marked)
                        for detection in detections:
                            drawer.rectangle(detection["caixa"], outline="green", width=3)
                            drawer.text((detection["caixa"][0], detection["caixa"][1]),
                                        f"{detection['classe']}: {detection['confianca']:.1%}", fill="green")
                        st.image(marked, caption="Detecções (modelo experimental)", width=480)
                        st.dataframe([{"Classe": d["classe"], "Confiança": f"{d['confianca']:.1%}"}
                                      for d in detections], hide_index=True)
                    else:
                        info_card("Nenhuma banana ou milho detectado na imagem.")
                    st.caption("Limitação: avaliação histórica pequena; desempenho insuficiente para decisões automáticas.")

st.divider()
st.subheader("Avaliação histórica: oito imagens de teste")
try:
    repo_path = _configuracao()[2]
except (OSError, TypeError, ValueError):
    repo_path = None
repo = str(repo_path) if repo_path else ""
state = availability()
if state.ok:
    avaliacao = st.session_state.get("fase6_avaliacao", {})
    concluida = (
        avaliacao.get("repo") == repo
        and avaliacao.get("resultado", {}).get("status") == "ok"
    )
    if not concluida:
        info_card("Pré-requisitos locais encontrados. A avaliação histórica ainda não foi concluída nesta sessão.")
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

st.caption("Avaliação independente das oito imagens preservadas; métricas não são garantia de acerto em novas fotos.")
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
