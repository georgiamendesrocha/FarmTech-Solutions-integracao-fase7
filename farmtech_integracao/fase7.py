"""Prévia local dos alertas da Fase 7; nenhuma operação de publicação é exposta."""

from datetime import datetime, timezone
import os
from pathlib import Path
import stat
import uuid

from .contracts import Result
from .runtime import PROJECT_ROOT, run_json_worker

SERVICE_ROOT = PROJECT_ROOT / "servicos" / "fase7-alertas-aws"
UPLOAD_DIR = PROJECT_ROOT / ".runtime" / "fase7"
MAX_CSV_BYTES = 1024 * 1024
_SOURCES = ("sensores.py", "regras.py", "mensagem.py", "gerar_exemplo.py", "gerar_exemplo_iot.py")


def _safe_path(value):
    """Recusa redirecionamentos existentes; não substitui permissões do SO."""
    lexical = Path(value).absolute()
    if lexical.resolve() != lexical:
        raise ValueError("O caminho local contém redirecionamento não permitido.")
    for component in (lexical, *lexical.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
            raise ValueError("O caminho local contém redirecionamento não permitido.")
    return lexical


def _remove_created_file(path, identity):
    """Remove somente o arquivo criado, sem seguir uma raiz redirecionada."""
    safe = _safe_path(path)
    try:
        info = safe.stat()
    except FileNotFoundError:
        return
    if identity is None or (info.st_dev, info.st_ino) != identity:
        raise ValueError("A identidade do arquivo temporário foi alterada.")
    safe.unlink()


def _local_result(status, message):
    return Result(status, message, {
        "alert": None, "has_alert": False, "subject": "", "body": "", "reading": {},
        "local": {}, "preview_only": True, "sns_enabled": False,
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "demonstracao",
    }, {"phase": "fase7", "provider": "FarmTech local", "origin": "desconhecida",
        "historical": False, "synthetic": False, "resource": "avaliacao_local"})


def _run(payload):
    result = run_json_worker("fase7", payload, timeout=20)
    defaults = _local_result(result.status, result.message)
    defaults.data.update(result.data)
    defaults.source.update(result.source)
    defaults.data.update(preview_only=True, sns_enabled=False)
    return defaults


def availability() -> Result:
    """Confere apenas os fontes locais, sem ler configurações ou estado SNS."""
    try:
        missing = [name for name in _SOURCES if not (SERVICE_ROOT / name).is_file()]
    except OSError:
        result = _local_result("unavailable", "Não foi possível verificar os fontes locais da Fase 7.")
        result.data.update(available=False, missing=[], iot_csv=False,
                           demonstrations=False, weather_evaluation=False)
        result.source.update(origin="metadata", resource="fontes_locais")
        return result
    result = _local_result("unavailable" if missing else "ok",
                           "Fontes de avaliação indisponíveis." if missing else
                           "Avaliação local disponível; publicação SNS desabilitada na dashboard.")
    result.data.update(available=not missing, missing=missing, iot_csv=not missing,
                       demonstrations=not missing, weather_evaluation=not missing)
    result.source.update(origin="metadata", resource="fontes_locais")
    return result


def evaluate_iot_csv(content: bytes | None = None, *, origem="desconhecida", fuso=None,
                     historico=False, local="", dispositivo="") -> Result:
    """Avalia upload ou somente o histórico F2 de caminho fixo; preserva os originais."""
    if content is not None and not isinstance(content, bytes):
        return _local_result("invalid", "O upload precisa conter bytes CSV, sem caminhos de arquivo.")
    if content is not None and (not content or len(content) > MAX_CSV_BYTES):
        return _local_result("invalid", "O CSV deve conter dados e ter no máximo 1 MiB.")
    payload = {"operation": "evaluate_iot_csv", "origem": origem, "fuso": fuso,
               "historico": historico, "local": local, "dispositivo": dispositivo}
    if content is None:
        return _run(payload)
    temporary = None
    identity = None
    result = None
    try:
        directory = _safe_path(UPLOAD_DIR)
        directory.mkdir(parents=True, exist_ok=True)
        _safe_path(directory)
        token = uuid.uuid4().hex
        candidate = _safe_path(directory / f"upload-{token}.csv")
        with candidate.open("xb") as handle:
            temporary = candidate
            info = os.fstat(handle.fileno())
            identity = (info.st_dev, info.st_ino)
            handle.write(content)
        payload["upload_id"] = token
        result = _run(payload)
    except OSError:
        result = _local_result("unavailable", "Não foi possível preparar a cópia temporária do upload CSV.")
    except ValueError:
        result = _local_result("invalid", "O diretório temporário do CSV possui redirecionamento não permitido.")
    finally:
        if temporary is not None:
            try:
                _safe_path(UPLOAD_DIR)
                _remove_created_file(temporary, identity)
            except (OSError, ValueError):
                result = _local_result("error", "Não foi possível remover a cópia temporária do upload CSV.")
    return result


def demo_iot(tipo) -> Result:
    """Gera e avalia em memória um dos cinco cenários sintéticos do serviço."""
    return _run({"operation": "demo_iot", "tipo": tipo})


def evaluate_weather(previsao: dict) -> Result:
    """Avalia um Result F2 já obtido. Esta função não consulta a Open-Meteo."""
    try:
        result = Result.from_dict(previsao)
    except ValueError:
        return _local_result("invalid", "Forneça um Result estruturado da previsão da Fase 2.")
    # Só transmite os campos consumidos pela regra; a série completa F2 contém
    # outros campos e pode ultrapassar o limite JSON do runtime desnecessariamente.
    data = result.data
    hourly = data.get("hourly")
    if isinstance(hourly, list):
        hourly = [{key: row.get(key) for key in ("ts_iso", "umidade", "rain_mm")}
                  if isinstance(row, dict) else None for row in hourly]
    payload = {"status": result.status, "message": result.message,
               "data": {"location": data.get("location", {}), "hourly": hourly,
                        "timezone": data.get("timezone", "UTC")},
               "source": {key: result.source[key] for key in
                          ("provider", "synthetic", "retrieved_at") if key in result.source}}
    return _run({"operation": "evaluate_weather", "previsao": payload})


def demo_weather(tipo) -> Result:
    """Avalia previsão sintética em memória, sem arquivos, rede ou envio."""
    return _run({"operation": "demo_weather", "tipo": tipo})
