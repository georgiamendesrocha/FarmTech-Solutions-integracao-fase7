"""Worker JSON da Fase 1: funções originais, estado restrito ao processo filho."""

import contextlib
import importlib.util
import io
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from farmtech_integracao.contracts import Result

SHAPES = {
    "circle": (0, 1, "Círculo"),
    "triangle": (3, 3, "Triângulo"),
    "rectangle": (4, 2, "Retângulo"),
    "pentagon": (5, 5, "Pentágono regular"),
    "hexagon": (6, 6, "Hexágono regular"),
    "heptagon": (7, 7, "Heptágono regular"),
    "octagon": (8, 8, "Octógono regular"),
}
CROPS = ("Soja", "Milho", "Café", "Trigo", "Cana-de-açúcar")
SHAPE_ALIASES = {
    "retangulo": "rectangle", "retângulo": "rectangle", "circulo": "circle", "círculo": "circle",
    "triangulo": "triangle", "triângulo": "triangle", "pentagono": "pentagon", "pentágono": "pentagon",
    "hexagono": "hexagon", "hexágono": "hexagon", "heptagono": "heptagon", "heptágono": "heptagon",
    "octogono": "octagon", "octógono": "octagon",
}


def positive_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Informe apenas números nas medidas e no espaçamento.")
    value = float(value)
    if not math.isfinite(value) or not 0 < value <= 1_000_000:
        raise ValueError("Medidas e espaçamento devem ser finitos, positivos e até 1.000.000 m.")
    return value


def calculate(payload):
    if not isinstance(payload, dict) or payload.get("operation") != "calculate":
        raise ValueError("Operação de gestão inválida.")
    shape = payload.get("shape")
    if isinstance(shape, str):
        shape = shape.strip().lower()
        shape = SHAPE_ALIASES.get(shape, shape)
    if not isinstance(shape, str) or shape not in SHAPES:
        raise ValueError("Escolha uma geometria suportada.")
    sides, count, label = SHAPES[shape]
    values = payload.get("measurements")
    if not isinstance(values, list) or len(values) != count:
        raise ValueError("Quantidade de medidas incompatível com a geometria escolhida.")
    measures = [positive_number(value) for value in values]
    spacing = positive_number(payload.get("spacing", 0.5))
    crop = payload.get("crop", "Soja")
    if not isinstance(crop, str) or crop not in CROPS:
        raise ValueError("Cultura ausente do catálogo da Fase 1.")
    if sides >= 5 and any(abs(value - measures[0]) > 1e-6 for value in measures[1:]):
        raise ValueError("Polígonos regulares exigem lados iguais.")
    source_dir = PROJECT_ROOT / "servicos" / "fase1-gestao" / "src"
    source_path = source_dir / "farm.py"
    if not source_path.is_file():
        return Result("unavailable", "Fonte da Fase 1 ausente.")
    sys.path.insert(0, str(source_dir))
    spec = importlib.util.spec_from_file_location("farmtech_fase1_original", source_path)
    module = importlib.util.module_from_spec(spec)
    # O módulo original reconfigura stdio. O buffer preserva o protocolo JSON.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(module)
        area = module.calcular_area(sides, measures)
        hectares, alqueires = module.converter_area(area)
        dimension = module.dimensao_para_linhas(sides, measures)
        length = module.comprimento_linha(sides, measures)
        rows = []
        for product in module.produtos:
            culture, category, name, maker, dose, unit, price = product
            if culture != crop:
                continue
            if unit not in ("L/ha", "kg/ha"):
                raise ValueError("Unidade de insumo não suportada.")
            rows.append({
                "category": category, "product": name, "manufacturer": maker,
                "dose": dose, "dose_unit": unit,
                "quantity": hectares * dose, "quantity_unit": "L" if unit == "L/ha" else "kg",
                "cost_per_ha": dose * price, "total_cost": hectares * dose * price,
                "dose_per_m": module.dose_ha_para_por_metro(dose, unit, spacing),
                "dose_per_m_unit": "mL/m" if unit == "L/ha" else "g/m",
            })
    if not math.isfinite(area) or area <= 0:
        raise ValueError("As medidas devem produzir uma área positiva e finita.")
    for row in rows:
        row["lowest_cost_in_category"] = row["total_cost"] == min(
            item["total_cost"] for item in rows if item["category"] == row["category"]
        )
    return Result("ok", "Talhão calculado com as funções preservadas da Fase 1.", {
        "shape": shape, "geometry": label, "sides": sides, "measurements_m": measures,
        "crop": crop, "area_m2": area, "hectares": hectares, "alqueires": alqueires,
        "spacing_m": spacing, "reference_line_length_m": length,
        "estimated_line_count": max(1, int(round(dimension / spacing))),
        "products": rows,
        "notes": ["Linhas de plantio são estimativas geométricas.",
                  "Preços e doses são os exemplos do catálogo original; a comparação é financeira por categoria.",
                  "O alqueire usa a conversão original de 24.200 m²."]
                 + (["A forma de quatro lados usa a hipótese de terreno retangular."] if sides == 4 else []),
    }, {"phase": "fase1", "implementation": "src/farm.py", "persistence": False})


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    try:
        raw = sys.stdin.read(65_537)
        if len(raw) > 65_536:
            raise ValueError("Solicitação excede o limite permitido.")
        result = calculate(json.loads(raw))
    except (ValueError, TypeError, OverflowError, KeyError):
        result = Result("invalid", "Revise a geometria, as medidas positivas, a cultura e o espaçamento.")
    except (ImportError, FileNotFoundError):
        result = Result("unavailable", "Dependências ou fontes da Fase 1 indisponíveis neste ambiente.")
    except Exception:
        result = Result("error", "Não foi possível concluir o cálculo da Fase 1.")
    sys.stdout.write(json.dumps(result.as_dict(), ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
