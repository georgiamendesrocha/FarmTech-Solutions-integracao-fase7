"""Mensagens públicas sem conteúdo de exceções ou caminhos internos."""

import logging
import streamlit as st

HISTORICAL_LIMITATION = (
    "Métricas históricas do protótipo: o conjunto de teste participou da seleção "
    "do modelo e da validação cruzada. Esses valores não constituem uma avaliação "
    "independente de generalização nem validação agronômica."
)
COMPATIBILITY_LIMITATION = (
    "Artefatos históricos preservados: compatibilidade entre versões verificada "
    "por hashes e previsões de referência neste ambiente. A carga entre versões "
    "diferentes de scikit-learn não tem garantia de suporte geral."
)


def erro_publico(message: str, error: Exception, *, aviso: bool = False) -> None:
    # Tipo é suficiente para diagnóstico inicial; nunca publicar str(error).
    logging.getLogger(__name__).warning("%s [%s]", message, type(error).__name__)
    (st.warning if aviso else st.error)(message)
