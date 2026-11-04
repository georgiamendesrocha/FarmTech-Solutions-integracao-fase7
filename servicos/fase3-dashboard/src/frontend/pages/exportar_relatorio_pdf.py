"""
Exporta o relatório técnico em PDF a partir de `src/docs/relatorio.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_SRC = Path(__file__).resolve().parents[2]
_REPO = _SRC.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.utils.relatorio_pdf import relatorio_md_to_pdf_bytes

st.title("Exportar relatório PDF")
st.caption(
    "PDF gerado a partir de **`src/docs/relatorio.md`**, com **logo FIAP**, margens e texto alinhados às práticas usuais da **ABNT NBR 14724** "
    "(fonte **12 pt**, entrelinhas **1,5**, parágrafos justificados com recuo de **1,25 cm**, margens **3 cm** à esquerda e **2 cm** nos outros lados)."
)

md_path = _REPO / "src" / "docs" / "relatorio.md"
if not md_path.is_file():
    st.error(f"Não encontrei **`src/docs/relatorio.md`** em `{_REPO}`.")
    st.stop()

st.markdown(
    f"Fonte: `{md_path.relative_to(_REPO)}` · "
    f"Tamanho: **{md_path.stat().st_size // 1024}** KB (aprox.)."
)

try:
    pdf_bytes, fname = relatorio_md_to_pdf_bytes(_REPO)
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()
except RuntimeError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.exception(e)
    st.stop()

st.download_button(
    label="Descarregar PDF",
    data=pdf_bytes,
    file_name=fname,
    mime="application/pdf",
    type="primary",
    use_container_width=True,
)

with st.expander("Pré-visualização do Markdown (primeiras linhas)"):
    preview = md_path.read_text(encoding="utf-8")[:4000]
    st.code(preview if len(preview) < 4000 else preview + "\n\n…", language="markdown")
