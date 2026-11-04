"""
Pagina: Recomendacoes de Manejo — cruzamento de previsão ML com leituras registradas do protótipo.
"""


import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from farmtech_integracao.ui import info_card
from src.db.database import get_culturas, get_ultima_leitura, media_cultura, validar_leitura
from src.ml.train import carregar_modelo, preparar_entrada_historica
from src.frontend.feedback import erro_publico, HISTORICAL_LIMITATION, COMPATIBILITY_LIMITATION
from src.frontend.scheduler import UMIDADE_LIMIAR

st.set_page_config(page_title="Recomendacoes — FarmTech", layout="wide")

st.title("Recomendações de Manejo")
st.caption("Leituras registradas/simuladas do protótipo ESP32/Wokwi; não são medições atuais de uma fazenda real.")

PH_FAIXAS: dict[str, tuple[float, float]] = {
    "rice": (6.0, 7.0),
    "maize": (5.8, 7.0),
    "chickpea": (6.0, 7.5),
    "kidneybeans": (6.0, 7.5),
    "pigeonpeas": (5.5, 7.0),
    "mothbeans": (6.0, 7.5),
    "mungbean": (6.0, 7.5),
    "blackgram": (6.0, 7.0),
    "lentil": (6.0, 7.0),
    "pomegranate": (5.5, 7.5),
    "banana": (5.5, 7.0),
    "mango": (5.5, 7.5),
    "grapes": (5.5, 6.5),
    "watermelon": (6.0, 7.0),
    "muskmelon": (6.0, 7.5),
    "apple": (5.5, 6.5),
    "orange": (6.0, 7.5),
    "papaya": (6.0, 7.0),
    "coconut": (5.0, 8.0),
    "cotton": (6.0, 8.0),
    "jute": (6.0, 7.0),
    "coffee": (6.0, 6.5),
}
PH_PADRAO = (6.0, 7.0)

# ── Dados ────────────────────────────────────────────────────────────────────
try:
    culturas = get_culturas()
    ultima = get_ultima_leitura()
    if ultima:
        validar_leitura(**{key: ultima[key] for key in ("umidade", "temp_c", "ldr", "ph", "n", "p", "k", "bomba_fw")})
except Exception as e:
    erro_publico("Banco indisponível ou inválido. Confira a ingestão e a configuração.", e)
    st.stop()

if not culturas:
    st.warning("Banco nao inicializado. Execute scripts/init_db.py.")
    st.stop()

try:
    modelo_rainfall = carregar_modelo("rainfall")
    modelo_humidity = carregar_modelo("humidity")
except Exception as e:
    erro_publico("Modelos históricos indisponíveis ou incompatíveis. Confira ambiente e integridade dos artefatos.", e)
    st.stop()
if not modelo_rainfall or not modelo_humidity:
    st.warning("Modelos históricos indisponíveis. Recupere os artefatos do backup verificado.")
    st.stop()

if not ultima:
    st.warning("Nenhuma leitura registrada de sensor disponível.")
    st.stop()
st.warning(HISTORICAL_LIMITATION)
st.caption(COMPATIBILITY_LIMITATION)

# ── Formulario ────────────────────────────────────────────────────────────────
st.markdown("### Selecione a Cultura e Parâmetros de Previsão")
st.caption(
    "N, P e K sao parâmetros de cenário editáveis, independentes dos indicadores binários de presença/ausência "
    "do sensor simulado. Os valores em kg/ha usados como entrada do modelo nao sao medições quantitativas "
    "desse sensor nem doses recomendadas de adubação."
)

with st.form("form_recom"):
    col1, col2 = st.columns(2)
    with col1:
        cultura = st.selectbox("Cultura", culturas)
        n = st.slider("N (kg/ha)", 0, 140, 40)
        p = st.slider("P (kg/ha)", 5, 145, 30)
    with col2:
        k = st.slider("K (kg/ha)", 5, 205, 20)
        temperatura = st.slider("Temperatura (C)", 5.0, 50.0, min(50.0, max(5.0, float(ultima.get("temp_c", 25.0)))), step=0.5)
        ph_entrada = st.slider("pH do solo", 3.5, 10.0, min(10.0, max(3.5, float(ultima.get("ph", 6.5)))), step=0.1)

    analisar = st.form_submit_button("Gerar Recomendacoes")

if not analisar:
    info_card("Preencha os parametros e clique em 'Gerar Recomendações'.")
    st.stop()

# ── Previsao ─────────────────────────────────────────────────────────────────
try:
    entrada = preparar_entrada_historica(n, p, k, temperatura, ph_entrada, cultura)
    prev_rainfall = max(0.0, float(modelo_rainfall.predict(entrada)[0]))
    prev_humidity = max(0.0, min(100.0, float(modelo_humidity.predict(entrada)[0])))
except Exception as e:
    erro_publico("Análise não concluída. Confira as entradas e os artefatos do modelo.", e)
    st.stop()

st.markdown("---")
st.markdown("### Leituras Registradas do Protótipo vs Previsão do Modelo")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Umidade registrada (%)", f"{ultima['umidade']:.1f}")
c2.metric("Proxy de necessidade hidrica", f"{prev_rainfall:.1f} mm")
c3.metric("pH registrado", f"{ultima['ph']:.3f}")
c4.metric("Umidade esperada pela cultura", f"{prev_humidity:.1f} %")
st.caption(
    "rainfall é um proxy acadêmico de necessidade hidrica; nao representa volume direto de irrigação "
    "nem permite estimar tempo de acionamento da bomba."
)

# ── Recomendacoes ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Recomendações de Manejo")
st.caption("Recomendações simplificadas do prototipo; nao substituem validacao agronomica.")
st.caption(
    "Médias de NPK do dataset acadêmico e faixas de pH sao referências indicativas do protótipo. "
    "Não constituem recomendação de adubação ou prescrição validada de correção do solo; "
    "decisões de manejo exigem análise do solo e avaliação agronômica local."
)

recomendacoes: list[dict] = []

# 1. Indicativo demonstrativo de umidade
umid_sensor = float(ultima["umidade"])
if umid_sensor < UMIDADE_LIMIAR:
    deficit = UMIDADE_LIMIAR - umid_sensor
    recomendacoes.append({
        "tipo": "warning",
        "titulo": "Umidade Abaixo do Limiar",
        "texto": (
            f"Umidade registrada pelo sensor do protótipo: {umid_sensor:.1f}% (limiar: {UMIDADE_LIMIAR}%). "
            f"Diferença: {deficit:.1f} pontos percentuais. Indicativo demonstrativo do protótipo, "
            "sem estimativa de tempo ou volume operacional de irrigação."
        ),
    })
else:
    recomendacoes.append({
        "tipo": "success",
        "titulo": "Umidade no Limiar ou Acima",
        "texto": (
            f"Umidade registrada pelo sensor do protótipo ({umid_sensor:.1f}%) no limiar ou acima ({UMIDADE_LIMIAR}%). "
            "Não ha indicativo imediato de irrigação pelo critério simplificado do protótipo."
        ),
    })

# 2. NPK — comparar com media da cultura
try:
    medias = media_cultura(cultura)
except Exception as e:
    erro_publico("Médias da cultura indisponíveis. Não foi possível concluir a análise de nutrientes.", e)
    st.stop()
if medias and all(medias.get(chave) is not None for chave in ("n_med", "p_med", "k_med")):
    n_med = medias["n_med"] or 0
    p_med = medias["p_med"] or 0
    k_med = medias["k_med"] or 0
    tol = 0.25  # Criterio demonstrativo de comparacao; nao e faixa de adubacao.

    ajustes = []
    if n is not None and abs(n - n_med) / (n_med + 1) > tol:
        direcao = "abaixo" if n < n_med else "acima"
        ajustes.append(f"N: {n:.0f} kg/ha no cenario, {direcao} da média do dataset acadêmico para a cultura ({n_med:.0f} kg/ha)")
    if p is not None and abs(p - p_med) / (p_med + 1) > tol:
        direcao = "abaixo" if p < p_med else "acima"
        ajustes.append(f"P: {p:.0f} kg/ha no cenario, {direcao} da média do dataset acadêmico para a cultura ({p_med:.0f} kg/ha)")
    if k is not None and abs(k - k_med) / (k_med + 1) > tol:
        direcao = "abaixo" if k < k_med else "acima"
        ajustes.append(f"K: {k:.0f} kg/ha no cenario, {direcao} da média do dataset acadêmico para a cultura ({k_med:.0f} kg/ha)")

    if ajustes:
        recomendacoes.append({
            "tipo": "warning",
            "titulo": "Comparação Descritiva de NPK",
            "texto": "Diferenças entre o cenário e a média do dataset acadêmico da cultura selecionada:\n\n" + "\n\n".join(f"- {a}" for a in ajustes),
        })
    else:
        recomendacoes.append({
            "tipo": "success",
            "titulo": "Comparação Descritiva de NPK",
            "texto": f"Os parametros NPK do cenário estão próximos das médias do dataset acadêmico para {cultura} pelo criterio demonstrativo de comparacao; isso nao comprova adequação agronômica.",
        })

else:
    st.info("Médias de nutrientes incompletas; comparação de N, P e K indisponível.")

# 3. Correção de pH
ph_sensor = float(ultima["ph"])
ph_min, ph_max = PH_FAIXAS.get(cultura.lower(), PH_PADRAO)

if ph_sensor < ph_min:
    recomendacoes.append({
        "tipo": "warning",
        "titulo": "pH Abaixo da Faixa de Referência",
        "texto": (
            f"pH registrado: {ph_sensor:.3f} | Faixa de referência para {cultura}: {ph_min}–{ph_max}. "
            f"Deficit: {ph_min - ph_sensor:.3f} unidades. "
            "Referência indicativa do protótipo; a diferença nao determina necessidade ou dose de corretivos."
        ),
    })
elif ph_sensor > ph_max:
    recomendacoes.append({
        "tipo": "warning",
        "titulo": "pH Acima da Faixa de Referência",
        "texto": (
            f"pH registrado: {ph_sensor:.3f} | Faixa de referência para {cultura}: {ph_min}–{ph_max}. "
            f"Excesso: {ph_sensor - ph_max:.3f} unidades. "
            "Referência indicativa do protótipo; a diferença não determina necessidade ou dose de corretivos."
        ),
    })
else:
    recomendacoes.append({
        "tipo": "success",
        "titulo": "pH Dentro da Faixa de Referência",
        "texto": (
            f"pH registrado ({ph_sensor:.3f}) dentro da faixa de referência para {cultura} ({ph_min}–{ph_max})."
        ),
    })

# Exibir recomendacoes
for rec in recomendacoes:
    if rec["tipo"] == "error":
        st.error(f"**{rec['titulo']}**\n\n{rec['texto']}")
    elif rec["tipo"] == "warning":
        st.warning(f"**{rec['titulo']}**\n\n{rec['texto']}")
    else:
        st.success(f"**{rec['titulo']}**\n\n{rec['texto']}")
