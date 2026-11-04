"""Worker JSON que reutiliza a consulta meteorológica original sem persistência."""

import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from farmtech_integracao.contracts import Result

MAX_HTTP_BYTES = 1_048_576


def load_weather_module():
    source = PROJECT_ROOT / "servicos" / "fase2-iot" / "scripts" / "weather_forecast.py"
    if not source.is_file():
        return None
    spec = importlib.util.spec_from_file_location("farmtech_fase2_weather", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def forecast(payload):
    if not isinstance(payload, dict) or payload.get("operation") != "forecast":
        raise ValueError("Operação meteorológica inválida.")
    city = payload.get("city")
    if not isinstance(city, str) or not 2 <= len(city.strip()) <= 120:
        raise ValueError("Informe uma cidade entre 2 e 120 caracteres.")
    if any(ord(char) < 32 or ord(char) == 127 for char in city):
        raise ValueError("Nome de cidade contém caracteres de controle.")
    city = city.strip()
    module = load_weather_module()
    if module is None:
        return Result("unavailable", "Fonte meteorológica da Fase 2 ausente.")
    geodata = module.fetch_json(module.build_geocode_url(city), max_bytes=MAX_HTTP_BYTES)
    locations = geodata.get("results")
    if not locations:
        return Result("unavailable", "Cidade não encontrada. Revise o nome e tente novamente.")
    location = locations[0]
    latitude, longitude = float(location["latitude"]), float(location["longitude"])
    if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Coordenadas inválidas na resposta meteorológica.")
    response = module.fetch_json(module.build_forecast_url(latitude, longitude), max_bytes=MAX_HTTP_BYTES)
    rows = module.normalize_forecast(location, response)
    if not rows or len(rows) > 5_000:
        return Result("unavailable", "A previsão não retornou uma série horária utilizável.")
    numeric_columns = ("temp_c", "umidade", "rain_mm", "wind_ms", "weathercode")
    useful_values = 0
    for row in rows:
        for column in numeric_columns:
            value = row[column]
            if value == "" or value is None:
                row[column] = None
            elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Valor meteorológico inválido.")
            elif column != "weathercode":
                useful_values += 1
    if useful_values == 0:
        return Result("unavailable", "A previsão não retornou medições meteorológicas utilizáveis.")
    return Result("ok", "Previsão consultada sem gravar arquivos da Fase 2.", {
        "location": {"name": location.get("name", city), "admin1": location.get("admin1", ""),
                     "country": location.get("country", ""), "latitude": latitude, "longitude": longitude},
        "hourly": rows, "units": {"temp_c": "°C", "umidade": "%", "rain_mm": "mm", "wind_ms": "m/s"},
        "timezone": "UTC", "persistence": False,
    }, {"phase": "fase2", "provider": "Open-Meteo", "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "geocoding": "https://geocoding-api.open-meteo.com/v1/search",
        "forecast": "https://api.open-meteo.com/v1/forecast"})


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    try:
        raw = sys.stdin.read(65_537)
        if len(raw) > 65_536:
            raise ValueError("Solicitação excede o limite permitido.")
        result = forecast(json.loads(raw))
    except (HTTPError, URLError, TimeoutError, OSError):
        result = Result("unavailable", "Serviço meteorológico indisponível. Tente novamente mais tarde.")
    except (ValueError, TypeError, KeyError, IndexError, OverflowError):
        result = Result("invalid", "Revise a cidade; a resposta deve conter horários UTC e vento em m/s válidos.")
    except ImportError:
        result = Result("unavailable", "Fonte meteorológica indisponível neste ambiente.")
    except Exception:
        result = Result("error", "Não foi possível concluir a consulta meteorológica.")
    sys.stdout.write(json.dumps(result.as_dict(), ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
