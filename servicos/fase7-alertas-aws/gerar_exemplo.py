"""Gera previsão sintética atual para dry-run local, sem rede ou publicação."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

TIPOS = ("chuva", "umidade_baixa", "umidade_alta", "normal")
PASTA = Path(__file__).resolve().parent


def gerar_previsao(tipo, *, agora=None):
    """Devolve um Result sintético com evento em uma hora, exclusivamente para dry-run."""
    if not isinstance(tipo, str) or tipo not in TIPOS:
        raise ValueError("Tipo de exemplo inválido.")
    if agora is not None and not isinstance(agora, datetime):
        raise ValueError("O instante de referência precisa ser datetime.")
    referencia = agora if agora is not None else datetime.now(timezone.utc)
    if referencia.tzinfo is None:
        referencia = referencia.replace(tzinfo=timezone.utc)
    instante = referencia.astimezone(timezone.utc) + timedelta(hours=1)
    umidade, chuva = {
        "chuva": (42, 1.5),
        "umidade_baixa": (42, 0),
        "umidade_alta": (85, 0),
        "normal": (60, 0),
    }[tipo]
    return {
        "status": "ok",
        "message": "DADOS SINTÉTICOS: somente dry-run local; não publicar no SNS.",
        "data": {
            "location": {
                "name": "Irecê", "admin1": "Bahia", "country": "Brasil",
                "latitude": -11.304, "longitude": -41.8558,
            },
            "hourly": [{
                "city": "Irecê", "country": "Brasil", "latitude": -11.304,
                "longitude": -41.8558,
                "ts_iso": instante.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "temp_c": 29, "umidade": umidade, "rain_mm": chuva,
                "wind_ms": 2, "weathercode": 61 if chuva else 0,
            }],
            "units": {"temp_c": "°C", "umidade": "%", "rain_mm": "mm", "wind_ms": "m/s"},
            "timezone": "UTC",
            "persistence": False,
        },
        "source": {"phase": "fase2", "provider": "exemplo_sintetico", "synthetic": True},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tipo", choices=TIPOS, default="umidade_baixa")
    parser.add_argument("--saida", type=Path, help="Novo JSON de saída; arquivos existentes são recusados.")
    args = parser.parse_args(argv)
    caminho = (args.saida if args.saida is not None
               else PASTA / f".exemplo-previsao-{uuid4().hex}.json").resolve()
    try:
        with caminho.open("x", encoding="utf-8") as arquivo:
            json.dump(gerar_previsao(args.tipo), arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
    except (OSError, ValueError) as exc:
        parser.error(f"Não foi possível criar um novo exemplo: {exc}")
    print(caminho)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
