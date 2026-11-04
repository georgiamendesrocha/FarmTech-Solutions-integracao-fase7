#!/usr/bin/env python3
"""
Busca previsão do tempo por cidade usando a API pública Open-Meteo e salva localmente para análise em R.

Uso:
  python scripts/weather_forecast.py
  python scripts/weather_forecast.py --city "São Paulo"

O script salva:
  dados/previsao_tempo/previsao_tempo.json
  dados/previsao_tempo/previsao_tempo.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

GEO_API_BASE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API_BASE = "https://api.open-meteo.com/v1/forecast"
DEFAULT_OUTPUT_DIR = Path("dados") / "previsao_tempo"


def build_geocode_url(city: str) -> str:
    query = {
        "name": city,
        "count": 1,
        "language": "pt",
        "format": "json",
    }
    return f"{GEO_API_BASE}?{urllib.parse.urlencode(query)}"


def build_forecast_url(latitude: float, longitude: float) -> str:
    query = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join([
            "temperature_2m",
            "relativehumidity_2m",
            "precipitation",
            "windspeed_10m",
            "weathercode",
        ]),
        "current_weather": "true",
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    }
    return f"{FORECAST_API_BASE}?{urllib.parse.urlencode(query)}"


def fetch_json(url: str, *, max_bytes: int | None = None) -> dict:
    """Lê JSON; consumidores integrados podem limitar o corpo antes da decodificação."""
    if max_bytes is not None and (type(max_bytes) is not int or max_bytes <= 0):
        raise ValueError("O limite de resposta deve ser um inteiro positivo.")
    with urllib.request.urlopen(url, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"Resposta inválida da API: {response.status}")
        payload = response.read() if max_bytes is None else response.read(max_bytes + 1)
        if max_bytes is not None and len(payload) > max_bytes:
            raise ValueError("Resposta meteorológica excede o limite permitido.")
    return json.loads(payload.decode("utf-8"))


def normalize_forecast(geo: dict, forecast: dict) -> list[dict[str, str | int | float]]:
    city_name = geo.get("name", "")
    country = geo.get("country", "")
    latitude = geo.get("latitude", "")
    longitude = geo.get("longitude", "")

    hourly = forecast.get("hourly", {})
    timestamps = hourly.get("time", [])
    if timestamps:
        wind_unit = forecast.get("hourly_units", {}).get("windspeed_10m")
        if wind_unit != "m/s":
            raise ValueError("Unidade de vento inesperada na resposta; esperado m/s. Nenhuma conversao automatica foi aplicada.")
        if forecast.get("utc_offset_seconds") != 0 or forecast.get("timezone") not in ("UTC", "GMT", "Etc/UTC", "Etc/GMT"):
            raise ValueError("Fuso inesperado na resposta meteorologica; esperado UTC com deslocamento zero.")
    temps = hourly.get("temperature_2m", [])
    umidade = hourly.get("relativehumidity_2m", [])
    precipitation = hourly.get("precipitation", [])
    wind = hourly.get("windspeed_10m", [])
    weathercodes = hourly.get("weathercode", [])

    rows: list[dict[str, str | int | float]] = []
    for i, ts in enumerate(timestamps):
        timestamp = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        # A resposta foi validada como UTC; o sufixo torna isso explícito no CSV.
        timestamp_utc = timestamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        rows.append(
            {
                "city": city_name,
                "country": country,
                "latitude": latitude,
                "longitude": longitude,
                "ts_iso": timestamp_utc,
                "temp_c": temps[i] if i < len(temps) else "",
                "umidade": umidade[i] if i < len(umidade) else "",
                "rain_mm": precipitation[i] if i < len(precipitation) else "",
                "wind_ms": wind[i] if i < len(wind) else "",
                "weathercode": weathercodes[i] if i < len(weathercodes) else "",
            }
        )
    return rows


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)


def save_csv(rows: list[dict[str, str | int | float]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "city",
        "country",
        "latitude",
        "longitude",
        "ts_iso",
        "temp_c",
        "umidade",
        "rain_mm",
        "wind_ms",
        "weathercode",
    ]
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca previsão do tempo e grava localmente para análise em R.")
    parser.add_argument("--city", default="São Paulo", help="Cidade para consulta (ex: São Paulo)")
    parser.add_argument("--out-json", default=DEFAULT_OUTPUT_DIR / "previsao_tempo.json", help="Arquivo JSON de saída")
    parser.add_argument("--out-csv", default=DEFAULT_OUTPUT_DIR / "previsao_tempo.csv", help="Arquivo CSV de saída")
    args = parser.parse_args()

    url_geo = build_geocode_url(args.city)
    print(f"Consultando localização para: {args.city}")
    try:
        geo_data = fetch_json(url_geo)
    except Exception as exc:
        print(f"Erro ao consultar geocoding: {exc}", file=sys.stderr)
        return 1

    results = geo_data.get("results")
    if not results:
        print(f"Cidade não encontrada: {args.city}", file=sys.stderr)
        return 2

    location = results[0]
    latitude = location["latitude"]
    longitude = location["longitude"]

    url_forecast = build_forecast_url(latitude, longitude)
    print(f"Consultando previsão para {location.get('name')} ({location.get('country')})")
    try:
        forecast_data = fetch_json(url_forecast)
    except Exception as exc:
        print(f"Erro ao consultar previsão: {exc}", file=sys.stderr)
        return 3

    try:
        rows = normalize_forecast(location, forecast_data)
    except (ValueError, TypeError) as exc:
        print(f"Erro ao validar previsao: {exc}", file=sys.stderr)
        return 4

    try:
        print(f"Salvando JSON em: {args.out_json}")
        save_json({"geocoding": location, "forecast": forecast_data}, Path(args.out_json))
        print(f"Salvando CSV em: {args.out_csv}")
        save_csv(rows, Path(args.out_csv))
    except OSError as exc:
        print(f"Erro ao salvar previsao: {exc}", file=sys.stderr)
        return 5

    print("Conclusão: previsão do tempo salva para análise posterior.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
