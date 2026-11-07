"""Worker de prévias F7: somente regras, mensagens e geradores locais permitidos."""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import sys
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from farmtech_integracao.contracts import Result
from farmtech_integracao.fase7 import _remove_created_file, _safe_path

SERVICE_ROOT = PROJECT_ROOT / "servicos" / "fase7-alertas-aws"
HISTORY_CSV = PROJECT_ROOT / "servicos" / "fase2-iot" / "dados" / "historico_irrigacao.csv"
UPLOAD_DIR = PROJECT_ROOT / ".runtime" / "fase7"
MAX_CSV_BYTES = 1024 * 1024
MAX_REQUEST_BYTES = 32768
OPERATIONS = {
    "evaluate_iot_csv": {"upload_id", "origem", "fuso", "historico", "local", "dispositivo"},
    "demo_iot": {"tipo"}, "evaluate_weather": {"previsao"}, "demo_weather": {"tipo"},
}


@lru_cache(maxsize=1)
def _modules():
    # O processo é isolado pelo runtime. Nenhum módulo de envio ou CLI é importado.
    if not all((SERVICE_ROOT / name).is_file() for name in
               ("sensores.py", "regras.py", "mensagem.py", "gerar_exemplo.py", "gerar_exemplo_iot.py")):
        raise FileNotFoundError("Fontes de avaliação local ausentes.")
    sys.path.insert(0, str(SERVICE_ROOT))
    import sensores
    import regras
    import mensagem
    import gerar_exemplo
    import gerar_exemplo_iot
    return sensores, regras, mensagem, gerar_exemplo, gerar_exemplo_iot


def _result(status, message, *, agora, mode="demonstracao", origin="desconhecida",
            historical=False, synthetic=False, resource="avaliacao_local", provider="FarmTech local"):
    return Result(status, message, {
        "alert": None, "has_alert": False, "subject": "", "body": "", "reading": {}, "conditions": [],
        "local": {}, "preview_only": True, "sns_enabled": False,
        "evaluated_at": agora.isoformat().replace("+00:00", "Z"), "mode": mode,
        "forecast_retrieved_at": None, "forecast_event_at": None,
    }, {"phase": "fase7", "provider": provider, "origin": origin,
        "historical": historical, "synthetic": synthetic, "resource": resource})


def _text(value, field):
    if not isinstance(value, str) or len(value) > 200 or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"Informe {field} como texto de até 200 caracteres, sem controles.")
    return value.strip()


def _validation_message(exc):
    """Traduz falhas para textos públicos, sem copiar valores ou detalhes do erro."""
    detail = str(exc)
    if "Timestamp IoT" in detail:
        if "sem offset" in detail:
            return "Timestamp IoT sem offset. Informe o fuso do PC de captura."
        return "Timestamp IoT inválido. Confira a data, o horário e o fuso da captura."
    if detail.startswith("Leitura IoT no futuro"):
        return "Leitura IoT no futuro. Confira o relógio e o fuso da captura."
    if detail.startswith("Leitura IoT com mais de cinco minutos"):
        return "Leitura IoT com mais de cinco minutos. Use --historico-iot para reprodução histórica."
    field = re.search(r"Campo IoT (t_rel_ms|umidade|temp_c|ldr|ph_base|ph_corr|N|P|K|bomba_fw)\b", detail)
    if field:
        return f"Campo IoT {field.group(1)} inválido. Confira o tipo, a faixa e os valores finitos."
    if detail.startswith("Cabeçalho IoT"):
        return "Cabeçalho IoT incompatível. Use os onze campos originais do coletor da Fase 2."
    if detail.startswith("Leituras IoT conflitantes"):
        return "O CSV contém leituras conflitantes para o mesmo instante e tempo relativo."
    if detail.startswith(("CSV IoT", "Linha IoT", "O CSV IoT")):
        return "CSV IoT inválido ou incompleto. Confira a codificação UTF-8 e os onze campos por linha."
    if detail.startswith("O CSV deve conter dados"):
        return "O CSV deve conter dados e ter no máximo 1 MiB."
    if detail.startswith("O fuso IoT"):
        return "Fuso IoT inválido. Informe UTC ou um offset como -03:00."
    if detail.startswith("Operação não permitida"):
        return "Operação não permitida. Esta integração apenas avalia prévias locais."
    if detail.startswith("A operação não aceita"):
        return "A operação não aceita envio, caminhos ou configurações adicionais."
    if detail.startswith(("O caminho local", "Upload precisa", "Identificador de upload")):
        return "Arquivo fora da área autorizada ou identificador de upload inválido."
    return "Dados inválidos. Confira o formato, os valores e as datas do CSV ou da previsão."


def _read_snapshot(arquivo, sensores, *, fuso=None):
    """Lê no máximo 1 MiB + 1 e analisa uma cópia fechada, nunca o original mutável."""
    source = _safe_path(arquivo)
    if not source.is_file():
        raise FileNotFoundError("CSV IoT indisponível.")
    # O limite é aplicado ao stream efetivamente aberto, inclusive se o original
    # crescer após a verificação de caminho/metadados.
    _safe_path(source)
    with source.open("rb") as handle:
        content = handle.read(MAX_CSV_BYTES + 1)
    if not content or len(content) > MAX_CSV_BYTES:
        raise ValueError("O CSV deve conter dados e ter no máximo 1 MiB.")
    directory = _safe_path(UPLOAD_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    _safe_path(directory)
    snapshot = None
    identity = None
    try:
        candidate = _safe_path(directory / f"snapshot-{uuid.uuid4().hex}.csv")
        with candidate.open("xb") as handle:
            snapshot = candidate
            info = os.fstat(handle.fileno())
            identity = (info.st_dev, info.st_ino)
            handle.write(content)
        _safe_path(directory)
        _safe_path(snapshot)
        info = snapshot.stat()
        if (info.st_dev, info.st_ino) != identity or info.st_size != len(content):
            raise ValueError("A cópia temporária do CSV foi alterada.")
        return sensores.ler_leitura_csv(snapshot, fuso=fuso)
    finally:
        if snapshot is not None:
            _safe_path(UPLOAD_DIR)
            _remove_created_file(snapshot, identity)


def _iot(payload, *, agora, demo=False):
    sensores, _, mensagem, _, generator = _modules()
    historico = payload.get("historico", False)
    if type(historico) is not bool:
        raise ValueError("A indicação de histórico deve ser booleana.")
    origem = "exemplo" if demo else payload.get("origem", "desconhecida")
    if not isinstance(origem, str) or origem not in sensores.ORIGENS:
        raise ValueError("Origem IoT inválida.")
    local = {"name": _text(payload.get("local", ""), "o local declarado"),
             "iot_dispositivo": _text(payload.get("dispositivo", ""), "o dispositivo declarado")}
    if demo:
        leitura = generator.gerar_leitura(payload.get("tipo"), agora=agora)
        leitura.update(_sintetico=True, _ts_original=leitura["ts_iso"])
        resource = "demonstracao_iot_em_memoria"
    else:
        token = payload.get("upload_id")
        if token is None:
            arquivo = HISTORY_CSV
            resource = "historico_irrigacao.csv"
        else:
            if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token):
                raise ValueError("Identificador de upload inválido.")
            directory = _safe_path(UPLOAD_DIR)
            arquivo = _safe_path(directory / f"upload-{token}.csv")
            if arquivo.parent != directory:
                raise ValueError("Upload precisa permanecer no diretório temporário permitido.")
            resource = "upload_csv"
        leitura = _read_snapshot(arquivo, sensores, fuso=payload.get("fuso"))
        if origem == "exemplo":
            leitura["_sintetico"] = True
    synthetic = leitura.get("_sintetico", False)
    effective_origin = "exemplo" if synthetic else origem
    mode = "historico" if historico else "demonstracao" if synthetic else "recepcao_recente"
    result = _result("ok", "Prévia local concluída; nenhuma mensagem foi publicada.",
                     agora=agora, mode=mode, origin=effective_origin, historical=historico,
                     synthetic=synthetic, resource=resource, provider="IoT Fase 2")
    result.data.update(reading=leitura, local=local)
    try:
        alerta = sensores.avaliar_sensor(leitura, origem=origem, historico=historico, agora=agora)
    except ValueError as exc:
        result.status, result.message = "invalid", _validation_message(exc)
        return result
    conditions = [{**condition, "primary": alerta is not None and condition["tipo"] == alerta["tipo"]}
                  for condition in sensores.condicoes_sensor(leitura)]
    result.data.update(alert=alerta, has_alert=alerta is not None, conditions=conditions)
    if alerta is not None:
        result.data.update(subject=mensagem.assunto(alerta), body=mensagem.corpo(alerta, local))
    else:
        result.message = "Leitura válida sem limiar de alerta; nenhuma mensagem foi publicada."
    return result


def _weather(previsao, *, agora, demo=False):
    _, regras, mensagem, _, _ = _modules()
    forecast = Result.from_dict(previsao)
    synthetic = demo or forecast.source.get("synthetic") is True
    result = _result("ok", "Prévia meteorológica concluída; nenhuma mensagem foi publicada.",
                     agora=agora, mode="demonstracao" if synthetic else "previsao",
                     origin="exemplo" if synthetic else "previsao_fase2", synthetic=synthetic,
                     resource="previsao_em_memoria", provider="Open-Meteo" if not synthetic else "Exemplo sintético")
    if not forecast.ok:
        result.status, result.message = forecast.status, "Previsão indisponível. Confira a consulta meteorológica."
        return result
    retrieved = forecast.source.get("retrieved_at")
    if isinstance(retrieved, str) and regras._instante(retrieved) is not None:
        result.source["retrieved_at"] = retrieved
        result.data["forecast_retrieved_at"] = retrieved
    rows = forecast.data.get("hourly")
    location = forecast.data.get("location", {})
    if not isinstance(location, dict):
        raise ValueError("Localização meteorológica inválida.")
    for field in ("name", "admin1", "country"):
        if field in location:
            _text(location[field], f"o campo {field} da localização")
    result.data["local"] = location
    if forecast.data.get("timezone", "UTC") != "UTC" or not isinstance(rows, list) or not rows:
        result.status, result.message = "invalid", "Previsão sem série horária UTC utilizável."
        return result
    limite = agora + timedelta(hours=regras.JANELA_HORAS)
    validas = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        instante = regras._instante(row.get("ts_iso"))
        if instante is None or not agora <= instante < limite:
            continue
        umidade = regras._numero(row.get("umidade"), minimo=0, maximo=100)
        chuva = regras._numero(row.get("rain_mm"), minimo=0)
        if umidade is not None or chuva is not None:
            validas.append(row)
    if not validas:
        result.status, result.message = "invalid", "Previsão sem leituras válidas nas próximas 12 horas."
        return result
    alerta = regras.avaliar(validas, agora=agora)
    result.data.update(alert=alerta, has_alert=alerta is not None)
    if alerta is not None:
        result.data["forecast_event_at"] = alerta["instante"]
        result.data.update(subject=mensagem.assunto(alerta), body=mensagem.corpo(alerta, location))
        if synthetic:
            result.data["subject"] = ("DEMONSTRAÇÃO SINTÉTICA | " + result.data["subject"])[:100]
            result.data["body"] = ("DEMONSTRAÇÃO SINTÉTICA — somente teste local; dados gerados em memória.\n"
                                   "Este conteúdo não comprova uma consulta meteorológica real.\n\n"
                                   + result.data["body"])
    else:
        result.message = "Previsão válida sem limiar de alerta na janela; nenhuma mensagem foi publicada."
    return result


def handle(payload):
    agora = datetime.now(timezone.utc)
    try:
        if not isinstance(payload, dict):
            raise ValueError("Solicitação local inválida.")
        operation = payload.get("operation")
        if not isinstance(operation, str) or operation not in OPERATIONS:
            raise ValueError("Operação não permitida; esta integração apenas avalia prévias locais.")
        if set(payload) - (OPERATIONS[operation] | {"operation"}):
            raise ValueError("A operação não aceita opções de envio, caminhos ou configurações adicionais.")
        if operation == "evaluate_iot_csv":
            return _iot(payload, agora=agora)
        if operation == "demo_iot":
            return _iot(payload, agora=agora, demo=True)
        if operation == "evaluate_weather":
            return _weather(payload.get("previsao"), agora=agora)
        generator = _modules()[3]
        return _weather(generator.gerar_previsao(payload.get("tipo"), agora=agora), agora=agora, demo=True)
    except (ValueError, TypeError, OverflowError, UnicodeError) as exc:
        return _result("invalid", _validation_message(exc), agora=agora)
    except (FileNotFoundError, ImportError):
        return _result("unavailable", "Fontes locais ou CSV IoT indisponíveis.", agora=agora)
    except OSError:
        return _result("unavailable", "Não foi possível ler os dados locais da Fase 7.", agora=agora)


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("Solicitação excede o limite local.")
        result = handle(json.loads(raw.decode("utf-8")))
    except (ValueError, UnicodeError):
        result = _result("invalid", "Solicitação JSON inválida ou acima do limite.", agora=datetime.now(timezone.utc))
    except Exception:
        result = _result("error", "Não foi possível avaliar a prévia local.", agora=datetime.now(timezone.utc))
    sys.stdout.write(json.dumps(result.as_dict(), ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
