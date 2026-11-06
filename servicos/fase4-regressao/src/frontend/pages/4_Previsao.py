"""
Pagina: Previsao Agricola — formulario com cultura e NPK/temp/pH.
"""

import sys
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from farmtech_integracao.ui import info_card
from src.db.database import get_culturas, inserir_previsao, inserir_previsoes
from src.ml.train import carregar_modelo, carregar_metricas, preparar_entrada_historica
from src.frontend.feedback import erro_publico, HISTORICAL_LIMITATION, COMPATIBILITY_LIMITATION
from src.ml.ph_model import (
    FEATURES as PH_FEATURES,
    DATASET_PATH as PH_DATASET_PATH,
    carregar_metricas_ph,
    carregar_modelo_ph,
    preparar_entrada_ph,
)

st.set_page_config(page_title="Previsao — FarmTech", layout="wide")

st.title("Previsao Agricola")
st.caption("Estime o proxy de necessidade hidrica (rainfall) e a umidade esperada (humidity) para uma cultura")

# ── Carregar culturas ─────────────────────────────────────────────────────────
try:
    culturas = get_culturas()
except Exception as e:
    erro_publico("Banco indisponível ou inválido. Confira a configuração e a ingestão dos dados.", e)
    st.stop()

if not culturas:
    st.warning("Banco nao inicializado. Execute scripts/init_db.py.")
    st.stop()

# ── Verificar modelos ────────────────────────────────────────────────────────
try:
    modelo_rainfall = carregar_modelo("rainfall")
    modelo_humidity = carregar_modelo("humidity")
    metricas = carregar_metricas() or {}
except Exception as e:
    erro_publico("Modelos ou métricas indisponíveis, alterados ou incompatíveis. Recupere os artefatos do backup verificado e confira o ambiente.", e)
    st.stop()

if not modelo_rainfall or not modelo_humidity:
    st.warning("Modelos históricos indisponíveis. Recupere os artefatos do backup verificado.")
    st.stop()

st.warning(
    "Modelo experimental: o conjunto de teste participou da seleção do modelo "
    "e da validação cruzada. As métricas históricas não representam avaliação "
    "independente de generalização nem validação agronômica."
)
st.caption(COMPATIBILITY_LIMITATION)

# ── Formulario de previsao ────────────────────────────────────────────────────
st.markdown("### Parametros de Entrada")

with st.form("form_previsao"):
    col1, col2 = st.columns(2)

    with col1:
        cultura = st.selectbox("Cultura", culturas)
        n = st.slider("Nitrogenio — N (kg/ha)", min_value=0, max_value=140, value=60)
        p = st.slider("Fosforo — P (kg/ha)", min_value=5, max_value=145, value=55)

    with col2:
        k = st.slider("Potassio — K (kg/ha)", min_value=5, max_value=205, value=44)
        temperatura = st.slider("Temperatura (C)", min_value=5.0, max_value=50.0, value=25.0, step=0.5)
        ph = st.slider("pH do solo", min_value=3.5, max_value=10.0, value=6.5, step=0.1)

    submeter = st.form_submit_button("Prever")

# ── Resultado da previsao ─────────────────────────────────────────────────────
if submeter:
    try:
        entrada = preparar_entrada_historica(n, p, k, temperatura, ph, cultura)
        prev_rainfall = float(modelo_rainfall.predict(entrada)[0])
        prev_humidity = float(modelo_humidity.predict(entrada)[0])

        # Clipping para faixas plausíveis
        prev_rainfall = max(0.0, prev_rainfall)
        prev_humidity = max(0.0, min(100.0, prev_humidity))

        st.markdown("---")
        st.markdown("### Resultado do Modelo Treinado")

        c1, c2 = st.columns(2)
        with c1:
            st.metric(
                label="Proxy de Necessidade Hidrica (rainfall)",
                value=f"{prev_rainfall:.2f} mm",
                help="Valor previsto para rainfall, usado como proxy de necessidade hidrica. Nao deve ser interpretado como volume direto de irrigacao.",
            )
            met_r = metricas.get("rainfall", {})
            if met_r:
                melhor_r = met_r.get("melhor_modelo", "?")
                r2_r = next((m["r2"] for m in met_r.get("metricas", []) if m["modelo"] == melhor_r), None)
                st.caption(f"Modelo: {melhor_r} | R² no teste: {r2_r:.4f}" if r2_r else f"Modelo: {melhor_r}")

        with c2:
            st.metric(
                label="Umidade Esperada do Ambiente",
                value=f"{prev_humidity:.2f} %",
                help="Umidade ambiental esperada para esta cultura nessas condicoes.",
            )
            met_h = metricas.get("humidity", {})
            if met_h:
                melhor_h = met_h.get("melhor_modelo", "?")
                r2_h = next((m["r2"] for m in met_h.get("metricas", []) if m["modelo"] == melhor_h), None)
                st.caption(f"Modelo: {melhor_h} | R² no teste: {r2_h:.4f}" if r2_h else f"Modelo: {melhor_h}")

        # Interpretacao da necessidade hidrica
        if prev_rainfall > 150:
            st.warning("Proxy indica alta necessidade hidrica; avalie o manejo de irrigacao com dados agronomicos complementares.")
        elif prev_rainfall > 80:
            info_card("Proxy indica necessidade hidrica moderada.")
        else:
            st.success("Proxy indica baixa necessidade hidrica no cenario informado.")

        # Gravar na tabela previsoes
        params = json.dumps({
            "cultura": cultura, "n": n, "p": p, "k": k,
            "temperatura": temperatura, "ph": ph,
        }, ensure_ascii=False)
        nome_modelo_r = metricas.get("rainfall", {}).get("melhor_modelo", "modelo_rainfall")
        nome_modelo_h = metricas.get("humidity", {}).get("melhor_modelo", "modelo_humidity")

        inserir_previsoes([
            (nome_modelo_r, "rainfall", prev_rainfall, params),
            (nome_modelo_h, "humidity", prev_humidity, params),
        ])

        st.caption("Previsao registrada na tabela previsoes do banco de dados.")

    except Exception as e:
        erro_publico("Previsão não concluída. Verifique as entradas e a disponibilidade do banco; nenhuma operação parcial foi confirmada.", e)

# ── Informacoes dos modelos ────────────────────────────────────────────────────
with st.expander("Informacoes sobre os modelos utilizados"):
    st.markdown(
        """
**Premissas importantes:**

- `rainfall` e usado como **proxy de necessidade hidrica** da cultura, nao como volume direto
  de irrigacao. O dataset agronômico usa chuva como variavel de condicao de cultivo.
- `humidity` representa a **umidade ambiental esperada** para a cultura nas condicoes fornecidas.
- Features: N, P, K, temperatura, pH e cultura (one-hot encoding).
- Modelos comparados: LinearRegression, Ridge (GridSearchCV), RandomForestRegressor.
- Split treino/teste: 80/20 com random_state=42.
- Validacao cruzada k-fold (k=5) para R².
        """
    )

st.markdown("---")
st.markdown("## Estimativa experimental de pH")
info_card(
    "O dataset acadêmico é a fonte de treinamento. Os valores do formulário são um "
    "cenário informado pelo usuário, não medições atuais. pH não é entrada do modelo; "
    "a cultura é tratada como previamente conhecida. A estimativa não é recomendação "
    "agronômica e não demonstra efeito causal."
)

try:
    modelo_ph = carregar_modelo_ph()
    metricas_ph = carregar_metricas_ph()
except (OSError, RuntimeError, ValueError) as e:
    erro_publico("Modelo experimental de pH indisponível ou inválido. Confira os artefatos e o ambiente.", e)
    modelo_ph = None
    metricas_ph = None

if modelo_ph is None or metricas_ph is None:
    st.warning(
        "Modelo de pH indisponível. Recupere os artefatos do backup verificado "
        "e utilize o ambiente declarado antes de usar esta seção."
    )
else:
    with st.form("form_previsao_ph"):
        st.markdown("#### Cenário agronômico conhecido antes da estimativa")
        ph_col1, ph_col2, ph_col3 = st.columns(3)
        with ph_col1:
            cultura_ph = st.selectbox(
                "Cultura previamente conhecida",
                culturas,
                key="ph_cultura",
            )
            n_ph = st.number_input("N (kg/ha)", min_value=0.0, max_value=140.0, value=60.0, key="ph_n")
            p_ph = st.number_input("P (kg/ha)", min_value=0.0, max_value=145.0, value=55.0, key="ph_p")
        with ph_col2:
            k_ph = st.number_input("K (kg/ha)", min_value=0.0, max_value=205.0, value=44.0, key="ph_k")
            temp_ph = st.number_input("Temperatura (°C)", min_value=5.0, max_value=50.0, value=25.0, key="ph_temp")
        with ph_col3:
            humidity_ph = st.number_input(
                "Umidade do dataset (%)", min_value=0.0, max_value=100.0, value=70.0, key="ph_humidity"
            )
            rainfall_ph = st.number_input(
                "Precipitação do cenário (mm)", min_value=0.0, max_value=300.0, value=100.0, key="ph_rainfall"
            )
        submeter_ph = st.form_submit_button("Estimar pH")

    if submeter_ph:
        try:
            entrada_ph = preparar_entrada_ph(
                n_ph, p_ph, k_ph, temp_ph, humidity_ph, rainfall_ph, cultura_ph,
            )
            previsto_ph = float(modelo_ph.predict(entrada_ph)[0])
            st.markdown("### Resultado — previsão do modelo")
            st.metric("pH estimado", f"{previsto_ph:.3f}")
            st.caption(
                f"Algoritmo: {metricas_ph['modelo_selecionado']} | "
                f"validação cruzada R²: {metricas_ph['cv_r2_medio_selecionado']:.3f} | "
                f"teste reservado R²: {metricas_ph['teste_reservado']['r2']:.3f}"
            )
            st.warning(
                "Resultado experimental baseado no dataset acadêmico; não possui "
                "validação agronômica independente ou garantia de desempenho em campo."
            )
            st.caption("No mesmo teste, a média simples de pH por cultura praticamente igualou o modelo (MAE 0,4278; R² 0,3288).")

            model_metrics = pd.DataFrame(metricas_ph["modelos"])
            fig_cv = px.bar(
                model_metrics,
                x="modelo",
                y="cv_r2_medio",
                title="Comparação de modelos — R² médio na validação do treino",
                labels={"modelo": "Modelo", "cv_r2_medio": "R² CV (treino)"},
                color="cv_r2_medio",
            )
            st.plotly_chart(fig_cv, use_container_width=True)

            ph_observed = pd.read_csv(PH_DATASET_PATH)
            fig_distribution = px.histogram(
                ph_observed,
                x="ph",
                nbins=35,
                title="pH observado no dataset acadêmico e estimativa atual",
                labels={"ph": "pH observado", "count": "Amostras"},
            )
            fig_distribution.add_vline(
                x=previsto_ph,
                line_dash="dash",
                line_color="red",
                annotation_text="Estimativa do cenário",
            )
            st.plotly_chart(fig_distribution, use_container_width=True)

            residual_path = ROOT / "src" / "ml" / "models" / "residuos_ph.csv"
            if residual_path.is_file():
                residuals = pd.read_csv(residual_path)
                fig_residuals = px.scatter(
                    residuals,
                    x="observado",
                    y="previsto",
                    title="pH observado no teste reservado vs. previsto",
                    labels={"observado": "pH observado", "previsto": "pH previsto"},
                )
                low = float(min(residuals["observado"].min(), residuals["previsto"].min()))
                high = float(max(residuals["observado"].max(), residuals["previsto"].max()))
                fig_residuals.add_scatter(
                    x=[low, high],
                    y=[low, high],
                    mode="lines",
                    name="Referência ideal",
                    line={"dash": "dash"},
                )
                st.plotly_chart(fig_residuals, use_container_width=True)

            st.caption(
                "Features efetivas (sem pH): "
                + ", ".join(PH_FEATURES)
                + ". A distribuição de pH no teste é independente do cenário informado."
            )
            parametros_ph = entrada_ph.iloc[0].to_dict()
            parametros_ph["cultura"] = parametros_ph["label"]
            try:
                inserir_previsao(
                    metricas_ph["modelo_selecionado"],
                    "ph",
                    previsto_ph,
                    json.dumps(parametros_ph, ensure_ascii=False),
                )
                st.caption("Estimativa registrada no histórico de previsões.")
            except sqlite3.Error as e:
                erro_publico("Estimativa exibida, mas não registrada. Verifique a disponibilidade do banco antes de tentar novamente.", e, aviso=True)
        except Exception as e:
            erro_publico("Não foi possível concluir a estimativa de pH. Verifique entradas, dados e artefatos antes de tentar novamente.", e)
