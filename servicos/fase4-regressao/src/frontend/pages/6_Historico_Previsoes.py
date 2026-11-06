"""
Pagina: Historico de Previsoes — consulta a tabela previsoes.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

import json
import pandas as pd
import plotly.express as px
import streamlit as st

from src.db.database import get_previsoes, get_total_previsoes
from src.frontend.feedback import erro_publico
from farmtech_integracao.ui import info_card

st.set_page_config(page_title="Historico de Previsoes — FarmTech", layout="wide")

TARGET_LABELS = {
    "rainfall": "Proxy de necessidade hidrica",
    "humidity": "Umidade prevista",
    "ph": "pH estimado (experimental)",
}


def rotulo_target(target: str) -> str:
    return TARGET_LABELS.get(target, target)


st.title("Histórico de Previsões")
st.caption("Registro de todas as previsões realizadas via formulário de Previsão Agrícola")

# ── Carregar dados ───────────────────────────────────────────────────────────
try:
    previsoes = get_previsoes(limite=500)
    total_previsoes = get_total_previsoes()
except Exception as e:
    erro_publico("Histórico indisponível ou inválido. Confira a configuração e o banco.", e)
    st.stop()

if not previsoes:
    info_card("Nenhuma previsão registrada ainda. Acesse a página 'Previsão Agrícola' para gerar previsões.")
    st.stop()

df = pd.DataFrame(previsoes)
st.caption(
    f"{len(df)} previsoes mais recentes carregadas de {total_previsoes} existentes no banco. "
    "Filtros, graficos e CSV consideram os registros carregados."
)
try:
    df["ts"] = pd.to_datetime(df["ts"], format="mixed", utc=True, errors="raise")
except (ValueError, TypeError) as e:
    erro_publico("O histórico contém datas inválidas. Preserve o banco e verifique os registros.", e)
    st.stop()

# ── Filtros ──────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    targets_disp = df["target"].unique().tolist()
    target_sel = st.multiselect("Filtrar por tipo de previsão", targets_disp, default=targets_disp, format_func=rotulo_target)
with c2:
    limite = st.slider("Numero de registros exibidos", 10, 500, 100)

df_filt = df[df["target"].isin(target_sel)].head(limite)
st.caption(f"{len(df_filt)} registros exibidos")

# ── Metricas gerais ───────────────────────────────────────────────────────────
st.markdown("### Resumo")
c1, c2, c3 = st.columns(3)
c1.metric("Total de previsoes", total_previsoes)
c2.metric("Tipos nas previsoes carregadas", df["target"].nunique())
c3.metric("Modelos nas previsoes carregadas", df["modelo"].nunique())

# ── Grafico de evolucao temporal ─────────────────────────────────────────────
st.markdown("### Evolução Temporal das Previsões")
for target in target_sel:
    df_t = df_filt[df_filt["target"] == target].sort_values(["ts", "id"])
    if len(df_t) > 0:
        target_label = rotulo_target(target)
        fig = px.line(
            df_t,
            x="ts",
            y="valor_previsto",
            title=f"Evolução das previsões — {target_label}",
            labels={"ts": "Timestamp", "valor_previsto": f"Valor previsto ({target_label})"},
            markers=True,
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Tabela completa ───────────────────────────────────────────────────────────
st.markdown("### Tabela de Previsões")

# Extrair cultura dos parametros JSON
def extrair_cultura(params_json: str) -> str:
    try:
        d = json.loads(params_json)
        return d.get("cultura") or d.get("label") or "—"
    except Exception:
        return "—"

df_filt = df_filt.copy()
df_filt["cultura"] = df_filt["parametros_entrada"].apply(extrair_cultura)
df_filt["target_label"] = df_filt["target"].apply(rotulo_target)
df_filt["ts_str"] = df_filt["ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
df_filt["valor_previsto"] = df_filt["valor_previsto"].round(4)

st.dataframe(
    df_filt[["id", "ts_str", "cultura", "target_label", "valor_previsto", "modelo"]].rename(columns={
        "id": "ID",
        "ts_str": "Timestamp",
        "cultura": "Cultura",
        "target_label": "Tipo de Previsao",
        "valor_previsto": "Valor Previsto",
        "modelo": "Modelo",
    }),
    use_container_width=True,
    hide_index=True,
)

# ── Download CSV ──────────────────────────────────────────────────────────────
csv_data = df_filt[["id", "ts_str", "cultura", "target", "valor_previsto", "modelo"]].to_csv(index=False).encode("utf-8")
st.download_button(
    label="Exportar como CSV",
    data=csv_data,
    file_name="historico_previsoes.csv",
    mime="text/csv",
)
