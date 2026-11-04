"""Acesso à gestão da Fase 1 sem menu interativo ou persistência."""

from .contracts import Result
from .runtime import SERVICE_DIRS, run_json_worker


def availability() -> Result:
    ready = (SERVICE_DIRS["fase1"] / "src" / "farm.py").is_file()
    return Result(
        "ok" if ready else "unavailable",
        "Cálculos da Fase 1 disponíveis." if ready else "Fonte da Fase 1 ausente.",
        {"calculations": ready, "persistence": False, "interactive_menu": False},
        {"phase": "fase1", "implementation": "src/farm.py"},
    )


def calculate_plot(shape, measurements, *, crop="Soja", spacing=0.5) -> Result:
    """Calcula um talhão e seus insumos no worker; nenhuma saída CSV é gravada."""
    return run_json_worker(
        "fase1",
        {"operation": "calculate", "shape": shape, "measurements": measurements,
         "crop": crop, "spacing": spacing},
        timeout=30,
    )
