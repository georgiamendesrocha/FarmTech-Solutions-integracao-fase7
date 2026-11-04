import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env", override=True)

st.set_page_config(page_title="Weather & IoT Analytics", page_icon="🌦️", layout="wide", initial_sidebar_state="expanded")

_PAGES = Path(__file__).resolve().parent / "pages"
pg = st.navigation(
    {
        "Entrega": [
            st.Page(
                str(_PAGES / "iot.py"),
                title="Sensores IoT",
                icon="🌱",
                default=True,
            ),
        ],
        "Ir além": [
            st.Page(
                str(_PAGES / "painel_solucoes_ia.py"),
                title="Painel IA · soluções",
                icon="🤖",
            ),
            st.Page(str(_PAGES / "forecast.py"), title="Previsão do Tempo", icon="🌤️"),
            st.Page(
                str(_PAGES / "analysis.py"),
                title="Análise para IA (meteorologia)",
                icon="🧠",
            ),
            st.Page(str(_PAGES / "notebook_ml.py"), title="Notebook ML (Ir Além)", icon="📓"),
            st.Page(
                str(_PAGES / "exportar_relatorio_pdf.py"),
                title="Exportar relatório PDF",
                icon="📄",
            ),
        ],
    }
)
pg.run()
