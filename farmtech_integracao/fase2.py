"""Integração da meteorologia F2: consulta explícita e CSV local rastreável."""

import csv
import os
from pathlib import Path
import shutil
import uuid

from .contracts import Result
from .fase2_r import localizar_rscript
from .runtime import PROJECT_ROOT, SERVICE_DIRS, run_json_worker

_CSV_COLS = ("city", "country", "latitude", "longitude", "ts_iso", "temp_c",
             "umidade", "rain_mm", "wind_ms", "weathercode", "cidade", "fonte",
             "consulta_utc")


def forecast_csv_path() -> Path:
    """Arquivo exportado no espaço de execução, nunca na base histórica F2."""
    return PROJECT_ROOT / ".runtime" / "exports" / "fase2" / "previsao_tempo.csv"


def availability() -> Result:
    root = SERVICE_DIRS["fase2"]
    weather = (root / "scripts" / "weather_forecast.py").is_file()
    r_installed = localizar_rscript() is not None
    return Result("ok" if weather else "unavailable",
                  "Meteorologia sob demanda; captura IoT permanece externa.", {
        "weather": weather, "r_source": (root / "app.r").is_file(),
        "r_installed_on_path": shutil.which("Rscript") is not None,
        "r_detected": r_installed,
        "r_execution_enabled": r_installed and (root / "app.r").is_file() and (root / "r" / "02_integrar_previsao.R").is_file() and (root / "dados" / "historico_irrigacao.csv").is_file(), "serial_execution_enabled": False,
        "history_available": (root / "dados" / "historico_irrigacao.csv").is_file(),
        "forecast_csv_available": forecast_csv_path().is_file(),
        "preconditions": [
            "Previsão: acesso HTTPS à geocodificação e à previsão Open-Meteo.",
            "Captura externa: PySerial, porta COM ou Wokwi/RFC2217 ativo a 115200 baud.",
            "Análises R: Rscript, CSVs legítimos e diretório de saída exclusivo.",
        ],
    }, {"phase": "fase2", "provider": "Open-Meteo"})


def _export_csv(result: Result) -> Path:
    """Publica CSV por substituição atômica. Não altera arquivos originais."""
    rows = result.data.get("hourly")
    loc = result.data.get("location", {})
    retrieved = result.source.get("retrieved_at")
    if not isinstance(rows, list) or not rows or len(rows) > 5000 or not retrieved:
        raise ValueError("Previsão inválida para exportação.")
    destino = forecast_csv_path()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + f".{uuid.uuid4().hex}.tmp")
    try:
        with temporario.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=_CSV_COLS, lineterminator="\n",
                                    extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                if not isinstance(row, dict) or not all(k in row for k in _CSV_COLS[:10]):
                    raise ValueError("Linha meteorológica incompatível com o script R.")
                writer.writerow({**row, "cidade": loc.get("name", ""),
                                 "fonte": "Open-Meteo", "consulta_utc": retrieved})
        os.replace(temporario, destino)
    finally:
        temporario.unlink(missing_ok=True)
    return destino


def forecast(city) -> Result:
    """Consulta sob demanda; só exporta após resultado válido e completo."""
    result = run_json_worker("fase2", {"operation": "forecast", "city": city}, timeout=40)
    if result.ok:
        try:
            arquivo = _export_csv(result)
        except (OSError, ValueError, TypeError):
            result.source["csv_exported"] = False
            result.message = "Previsão consultada, mas não foi possível salvar o CSV."
        else:
            result.source["csv_exported"] = True
            result.source["csv_path"] = str(arquivo)
            result.data["persistence"] = True
            result.message = "Previsão consultada e CSV meteorológico atualizado."
    return result
