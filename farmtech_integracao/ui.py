
"""Identidade visual e apresentação de resultados da FarmTech Solutions."""

from html import escape

import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError

from farmtech_integracao.contracts import Result


def apply_theme():
    """Aplica estilos complementares ao tema nativo do Streamlit."""
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1400px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stMetric"] {
            background-color: #454E57;
            border: 1px solid #59666E;
            border-radius: 12px;
            padding: 1rem;
        }

        [data-testid="stMetricLabel"] {
            color: #C1CACD;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid #456055;
        }

        div.stButton > button {
            border-radius: 9px;
            min-height: 2.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def info_card(message: str, *, title: str | None = None):
    """Exibe informações com a identidade visual FarmTech."""
    safe_message = escape(str(message)).replace("\n", "<br>")

    heading = (
        f'<div style="font-weight:700; margin-bottom:0.4rem;">'
        f'{escape(title)}</div>'
        if title
        else ""
    )

    html = (
        '<div style="'
        'background-color:#40534E;'
        'color:#CBD5D3;'
        'border-left:3px solid #71BE9C;'
        'border-radius:10px;'
        'padding:1rem 1.2rem;'
        'margin:0.5rem 0;'
        'line-height:1.55;'
        '">'
        f'{heading}<div>{safe_message}</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)



def show_result(result: Result):
    """Apresenta os resultados preservando seus estados semânticos."""
    renderer = {
        "ok": st.success,
        "invalid": st.warning,
        "unavailable": st.warning,
    }.get(result.status, st.error)

    renderer(result.message)

    if result.source:
        with st.expander("Origem e condições do resultado"):
            st.json(result.source)


def navigation_link(page, *, label, icon):
    """Link para uma página da dashboard integrada."""
    try:
        st.page_link(page, label=label, icon=icon)
    except StreamlitPageNotFoundError:
        st.caption(
            "Acesse este serviço pela navegação lateral da dashboard principal."
        )
