"""Leitura offline do CSV IoT Fase 2 e regras didáticas do protótipo de tomate."""

import csv
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMPOS_CSV = ("ts_iso", "t_rel_ms", "umidade", "temp_c", "ldr", "ph_base", "ph_corr",
              "N", "P", "K", "bomba_fw")
MARCADOR_EXEMPLO = "# FARMTECH_EXEMPLO_IOT_SINTETICO"
TIPOS_IOT = {"iot_umidade_baixa", "iot_umidade_alta", "iot_ph_fora_faixa", "iot_npk_ausente"}
ORIGENS = {"wokwi", "esp32", "desconhecida", "exemplo"}
IDADE_MAXIMA_SEGUNDOS = 300


def _fuso_explicito(fuso):
    if fuso is None:
        return None
    if fuso == "UTC":
        return timezone.utc
    if not isinstance(fuso, str) or not re.fullmatch(r"[+-](?:[01][0-9]|2[0-3]):[0-5][0-9]", fuso):
        raise ValueError("O fuso IoT deve ser UTC ou um offset explícito como -03:00.")
    minutos = int(fuso[1:3]) * 60 + int(fuso[4:6])
    return timezone(timedelta(minutes=minutos if fuso[0] == "+" else -minutos))


def _instante(texto, fuso=None):
    if not isinstance(texto, str) or "T" not in texto:
        raise ValueError("Timestamp IoT inválido; esperado ISO 8601 com data e horário.")
    try:
        instante = datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))
        if instante.tzinfo is None:
            if fuso is None:
                raise ValueError("Timestamp IoT sem offset; informe --fuso-iot UTC ou +/-HH:MM do PC de captura.")
            instante = instante.replace(tzinfo=fuso)
        return instante.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"Timestamp IoT inválido: {exc}") from None


def _numero(valor, campo, *, minimo=None, maximo=None, inteiro=False, flag=False):
    if isinstance(valor, bool) or not isinstance(valor, (str, int, float)):
        raise ValueError(f"Campo IoT {campo} precisa ser numérico.")
    texto = str(valor).strip()
    try:
        numero = float(texto)
        if not math.isfinite(numero):
            raise ValueError("não finito")
        if flag and texto not in {"0", "1"}:
            raise ValueError("esperado 0 ou 1")
        numero = int(texto) if inteiro or flag else numero
        if minimo is not None and numero < minimo or maximo is not None and numero > maximo:
            raise ValueError("fora da faixa")
    except (ValueError, OverflowError):
        raise ValueError(f"Campo IoT {campo} inválido, não finito ou fora da faixa permitida.") from None
    return numero


def _normalizar(linha, fuso=None):
    if not isinstance(linha, dict) or any(campo not in linha for campo in CAMPOS_CSV):
        raise ValueError("Leitura IoT incompleta; esperado o contrato CSV da Fase 2.")
    instante = _instante(linha["ts_iso"], fuso)
    return {
        "ts_iso": instante.isoformat().replace("+00:00", "Z"),
        "t_rel_ms": _numero(linha["t_rel_ms"], "t_rel_ms", minimo=0, maximo=4294967295, inteiro=True),
        "umidade": _numero(linha["umidade"], "umidade", minimo=0, maximo=100),
        "temp_c": _numero(linha["temp_c"], "temp_c"),
        "ldr": _numero(linha["ldr"], "ldr", minimo=0, maximo=4095, inteiro=True),
        "ph_base": _numero(linha["ph_base"], "ph_base", minimo=0, maximo=14),
        "ph_corr": _numero(linha["ph_corr"], "ph_corr", minimo=0, maximo=14),
        **{campo: _numero(linha[campo], campo, flag=True) for campo in ("N", "P", "K", "bomba_fw")},
    }


def ler_leitura_csv(caminho, *, fuso=None):
    """Valida todo o CSV e seleciona a leitura mais recente, sem alterar o arquivo.

    No mesmo segundo UTC, prevalece a última linha na ordem append do coletor,
    inclusive se t_rel_ms diminuir por reset/wrap. Arquivos reordenados manualmente
    não preservam essa garantia. Conteúdos conflitantes para o mesmo par
    (ts_iso UTC, t_rel_ms) e linhas incompletas causam erro, sem recuo silencioso
    para uma leitura anterior. Uma linha completa sem newline final é CSV válido.
    """
    fuso_padrao = _fuso_explicito(fuso)
    registros = {}
    observadas = {}
    with Path(caminho).open(encoding="utf-8", newline="") as arquivo:
        primeira = arquivo.readline()
        sintetico = primeira.rstrip("\r\n") == MARCADOR_EXEMPLO
        if not sintetico:
            arquivo.seek(0)
        leitor = csv.reader(arquivo, strict=True)
        try:
            if tuple(next(leitor, ())) != CAMPOS_CSV:
                raise ValueError("Cabeçalho IoT incompatível com os onze campos CSV da Fase 2.")
            for numero, valores in enumerate(leitor, start=3 if sintetico else 2):
                if len(valores) != len(CAMPOS_CSV):
                    raise ValueError(f"Linha IoT {numero} possui quantidade de campos inválida.")
                linha = dict(zip(CAMPOS_CSV, valores))
                try:
                    leitura = _normalizar(linha, fuso_padrao)
                except ValueError as exc:
                    raise ValueError(f"Linha IoT {numero}: {exc}") from None
                instante = _instante(leitura["ts_iso"])
                chave = (instante, leitura["t_rel_ms"])
                anterior = observadas.get(chave)
                if anterior is not None and any(anterior[campo] != leitura[campo] for campo in CAMPOS_CSV):
                    raise ValueError(f"Leituras IoT conflitantes no mesmo timestamp e t_rel_ms: {leitura['ts_iso']}.")
                leitura["_sintetico"] = sintetico
                leitura["_ts_original"] = linha["ts_iso"]
                observadas[chave] = leitura
                registros[instante] = leitura
        except csv.Error as exc:
            raise ValueError(f"CSV IoT inválido: {exc}") from None
    if not registros:
        raise ValueError("O CSV IoT não contém leituras.")
    return registros[max(registros)]


def condicoes_sensor(leitura):
    """Lista condições didáticas simultâneas sem modificar o alerta prioritário.

    Valida o contrato da leitura; idade e proveniência continuam sob a avaliação
    principal. pH e N/P/K são exibidos mesmo quando a umidade tem prioridade.
    """
    dados = _normalizar(leitura)
    condicoes = []
    umidade = dados["umidade"]
    if umidade < 45:
        condicoes.append({
            "tipo": "iot_umidade_baixa", "condicao": "Umidade do DHT22/protótipo abaixo de 45%",
            "valor": umidade, "limiar": "<45% (didático)",
        })
    elif umidade > 80:
        condicoes.append({
            "tipo": "iot_umidade_alta", "condicao": "Umidade do DHT22/protótipo acima de 80%",
            "valor": umidade, "limiar": ">80% (didático)",
        })
    if not 6.0 <= dados["ph_corr"] <= 6.8:
        condicoes.append({
            "tipo": "iot_ph_fora_faixa", "condicao": "pH corrigido simulado fora de 6,0–6,8",
            "valor": dados["ph_corr"], "limiar": "6,0–6,8 (didático)",
        })
    ausentes = [campo for campo in ("N", "P", "K") if dados[campo] == 0]
    if ausentes:
        condicoes.append({
            "tipo": "iot_npk_ausente",
            "condicao": "Indicadores simulados de presença: " + ", ".join(f"{campo} ausente" for campo in ausentes),
            "valor": "/".join(str(dados[campo]) for campo in ("N", "P", "K")),
            "limiar": "N/P/K = 1/1/1 (presença didática)",
        })
    return condicoes


def avaliar_sensor(leitura, *, origem="desconhecida", historico=False, agora=None):
    """Avalia sensores simulados; o limite de recepção não prova a idade da leitura DHT22."""
    if not isinstance(origem, str) or origem not in ORIGENS:
        raise ValueError("Origem IoT inválida; use wokwi, esp32, desconhecida ou exemplo.")
    if type(historico) is not bool:
        raise ValueError("A indicação de histórico IoT precisa ser booleana.")
    if agora is not None and (not isinstance(agora, datetime) or agora.tzinfo is None):
        raise ValueError("O instante de referência precisa ser datetime com fuso explícito.")
    dados = _normalizar(leitura)
    sintetico = leitura.get("_sintetico", False)
    if type(sintetico) is not bool:
        raise ValueError("Marcador sintético IoT inválido.")
    referencia = agora if agora is not None else datetime.now(timezone.utc)
    idade = (referencia - _instante(dados["ts_iso"])).total_seconds()
    if idade < 0:
        raise ValueError("Leitura IoT no futuro; confira o relógio e o fuso da captura.")
    if idade > IDADE_MAXIMA_SEGUNDOS and not historico:
        raise ValueError("Leitura IoT com mais de cinco minutos; use --historico-iot para replay sem publicação.")
    umidade, ph = dados["umidade"], dados["ph_corr"]
    nutrientes_ausentes = any(dados[campo] == 0 for campo in ("N", "P", "K"))
    ph_fora = not 6.0 <= ph <= 6.8
    bomba_esperada = int(umidade < 45 or (umidade <= 80 and (ph_fora or nutrientes_ausentes)))
    if umidade < 45:
        tipo = "iot_umidade_baixa"
        alerta = "Umidade do DHT22/protótipo abaixo de 45% para o tomate."
        acao = "Conferir no protótipo a irrigação prevista pela regra de umidade baixa."
    elif umidade > 80:
        tipo = "iot_umidade_alta"
        alerta = "Umidade do DHT22/protótipo acima de 80% para o tomate."
        acao = "Conferir no protótipo a bomba desligada pela regra de umidade alta."
    elif ph_fora:
        tipo = "iot_ph_fora_faixa"
        alerta = "pH corrigido simulado fora de 6,0–6,8 no protótipo de tomate."
        acao = "Conferir a simulação do LDR e o pH corrigido do protótipo."
    elif nutrientes_ausentes:
        tipo = "iot_npk_ausente"
        alerta = "Indicador simulado de presença N/P/K ausente no protótipo."
        acao = "Conferir os estados dos botões N/P/K; não representam concentrações de nutrientes."
    else:
        return None
    return {
        "tipo": tipo, "instante": dados["ts_iso"], "alerta": alerta,
        "acao": acao + " Não acionar bomba física com base neste alerta.", "umidade": umidade,
        "fonte": "iot_fase2", "origem": "exemplo" if sintetico else origem,
        "historico": historico, "sintetico": sintetico, "idade_segundos": idade,
        "leitura": {**dados, "_sintetico": sintetico, "_ts_original": leitura.get("_ts_original", leitura["ts_iso"])},
        "bomba_esperada": bomba_esperada,
    }
