"""Regras de irrigação do tomate usadas no alerta da Parte 2."""

from datetime import datetime, timedelta, timezone
from math import isfinite

UMIDADE_BAIXA = 45.0
UMIDADE_ALTA = 80.0
CHUVA_SUSPENDE_MM = 1.0
JANELA_HORAS = 12


def _numero(valor, *, minimo=None, maximo=None):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    try:
        numero = float(valor)
    except OverflowError:
        return None
    if not isfinite(numero):
        return None
    if minimo is not None and numero < minimo:
        return None
    if maximo is not None and numero > maximo:
        return None
    return numero


def _instante(texto):
    if not isinstance(texto, str) or not texto.strip():
        return None
    try:
        instante = datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))
        if instante.tzinfo is None:
            instante = instante.replace(tzinfo=timezone.utc)
        return instante.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def avaliar(hourly, *, agora=None, horas=JANELA_HORAS):
    """Devolve um alerta ou None. Chuva na janela impede o pedido de irrigação."""
    if not isinstance(hourly, list):
        raise ValueError("A previsão horária precisa ser uma lista.")
    if type(horas) is not int or horas < 1 or horas > 48:
        raise ValueError("A janela deve ficar entre 1 e 48 horas.")
    if agora is not None and not isinstance(agora, datetime):
        raise ValueError("O instante de referência precisa ser datetime.")
    referencia = agora if agora is not None else datetime.now(timezone.utc)
    if referencia.tzinfo is None:
        referencia = referencia.replace(tzinfo=timezone.utc)
    limite = referencia + timedelta(hours=horas)

    chuva = None
    baixa = None
    alta = None
    for row in hourly:
        if not isinstance(row, dict):
            continue
        instante = _instante(row.get("ts_iso"))
        if instante is None or instante < referencia or instante >= limite:
            continue
        chuva_mm = _numero(row.get("rain_mm"), minimo=0)
        umidade = _numero(row.get("umidade"), minimo=0, maximo=100)
        if chuva is None and chuva_mm is not None and chuva_mm >= CHUVA_SUSPENDE_MM:
            chuva = (instante, chuva_mm, umidade)
        if baixa is None and umidade is not None and umidade < UMIDADE_BAIXA:
            baixa = (instante, umidade)
        if alta is None and umidade is not None and umidade > UMIDADE_ALTA:
            alta = (instante, umidade)

    if chuva is not None:
        instante, chuva_mm, umidade = chuva
        return {
            "tipo": "chuva",
            "instante": instante.isoformat().replace("+00:00", "Z"),
            "chuva_mm": chuva_mm,
            "umidade": umidade,
            "alerta": "Chuva prevista na lavoura de tomate.",
            "acao": "Manter a bomba de irrigação desligada.",
        }
    if baixa is not None:
        instante, umidade = baixa
        return {
            "tipo": "umidade_baixa",
            "instante": instante.isoformat().replace("+00:00", "Z"),
            "chuva_mm": None,
            "umidade": umidade,
            "alerta": "Umidade prevista abaixo de 45% para o tomate.",
            "acao": "Verificar a umidade do solo e as necessidades da cultura antes de decidir pelo acionamento da irrigação.",
        }
    if alta is not None:
        instante, umidade = alta
        return {
            "tipo": "umidade_alta",
            "instante": instante.isoformat().replace("+00:00", "Z"),
            "chuva_mm": None,
            "umidade": umidade,
            "alerta": "Umidade prevista acima de 80% para o tomate.",
            "acao": "Manter a bomba de irrigação desligada.",
        }
    return None
