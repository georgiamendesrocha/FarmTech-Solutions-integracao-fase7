"""Contratos do backend; os controles visuais não substituem estas validações."""

from collections.abc import Mapping
import math
from numbers import Real


# Domínio acadêmico usado pelos artefatos preservados, não catálogo agronômico.
CULTURAS = frozenset({
    "apple", "banana", "blackgram", "chickpea", "coconut", "coffee", "cotton",
    "grapes", "jute", "kidneybeans", "lentil", "maize", "mango", "mothbeans",
    "mungbean", "muskmelon", "orange", "papaya", "pigeonpeas", "pomegranate",
    "rice", "watermelon",
})


def numero_finito(value, nome: str, minimo=None, maximo=None) -> float:
    """Aceita número real finito, sem converter texto ou booleanos em medidas."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{nome}: informe um número válido.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{nome}: o número deve ser finito.")
    if minimo is not None and number < minimo:
        raise ValueError(f"{nome}: valor abaixo do limite permitido ({minimo}).")
    if maximo is not None and number > maximo:
        raise ValueError(f"{nome}: valor acima do limite permitido ({maximo}).")
    return number


def _validar(values: Mapping, ranges: dict, category: str) -> dict:
    if not isinstance(values, Mapping):
        raise ValueError("As entradas devem ser um objeto com campos nomeados.")
    required = set(ranges) | {category}
    if set(values) != required:
        raise ValueError("Campos de entrada ausentes ou não reconhecidos.")
    culture = values[category]
    if not isinstance(culture, str) or culture.strip() not in CULTURAS:
        raise ValueError("Informe uma cultura conhecida pelo modelo acadêmico.")
    normalized = {
        name: numero_finito(values[name], name, *limits)
        for name, limits in ranges.items()
    }
    normalized[category] = culture.strip()
    return normalized


def validar_entrada_original(values: Mapping) -> dict:
    return _validar(values, {
        "n": (0, 140), "p": (5, 145), "k": (5, 205),
        "temperatura": (5, 50), "ph": (3.5, 10),
    }, "cultura")


def validar_entrada_ph(values: Mapping) -> dict:
    if not isinstance(values, Mapping):
        raise ValueError("As entradas devem ser um objeto com campos nomeados.")
    values = dict(values)
    # Compatibilidade com a chave legível do histórico; divergência é um erro.
    if "cultura" in values:
        if "label" in values and values["label"] != values["cultura"]:
            raise ValueError("As identificações de cultura são inconsistentes.")
        values["label"] = values.pop("cultura")
    return _validar(values, {
        "N": (0, 140), "P": (0, 145), "K": (0, 205),
        "temperature": (5, 50), "humidity": (0, 100), "rainfall": (0, 300),
    }, "label")


def validar_valor_previsto(target: str, valor) -> float:
    ranges = {"ph": (0, 14), "rainfall": (0, None), "humidity": (0, 100)}
    if not isinstance(target, str) or target not in ranges:
        raise ValueError("Alvo de previsão não reconhecido.")
    return numero_finito(valor, "Resultado da previsão", *ranges[target])
