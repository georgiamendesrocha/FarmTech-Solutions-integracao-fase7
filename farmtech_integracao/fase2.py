"""Integração sob demanda com a meteorologia da Fase 2."""

import shutil

from .contracts import Result
from .runtime import SERVICE_DIRS, run_json_worker


def availability() -> Result:
    root = SERVICE_DIRS["fase2"]
    weather = (root / "scripts" / "weather_forecast.py").is_file()
    r_source = (root / "app.r").is_file()
    r_installed = shutil.which("Rscript") is not None
    return Result("ok" if weather else "unavailable",
                  "Meteorologia sob demanda; captura IoT permanece externa.", {
        "weather": weather, "r_source": r_source, "r_installed_on_path": r_installed,
        "r_execution_enabled": False, "serial_execution_enabled": False,
        "history_available": (root / "dados" / "historico_irrigacao.csv").is_file(),
        "forecast_csv_available": (root / "dados" / "previsao_tempo" / "previsao_tempo.csv").is_file(),
        "preconditions": [
            "Previsão: acesso HTTPS à geocodificação e à previsão Open-Meteo.",
            "Captura externa: PySerial, porta COM ou Wokwi/RFC2217 ativo a 115200 baud.",
            "Análises R: Rscript, CSVs legítimos e diretório de saída exclusivo.",
        ],
    }, {"phase": "fase2", "provider": "Open-Meteo"})


def forecast(city) -> Result:
    """Consulta a API apenas nesta chamada explícita, sem salvar JSON/CSV histórico."""
    return run_json_worker("fase2", {"operation": "forecast", "city": city}, timeout=40)
