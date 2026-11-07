"""Gera CSV IoT sintético em Python: não é captura Wokwi nem sensor físico.

Os exemplos têm timestamps recentes somente para testes locais. O marcador
obrigatório identifica dados de exemplo, que não podem ser publicados no SNS.
"""

import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sensores import MARCADOR_EXEMPLO

TIPOS = ("umidade_baixa", "umidade_alta", "ph_fora_faixa", "npk_ausente", "normal")
CAMPOS = ("ts_iso", "t_rel_ms", "umidade", "temp_c", "ldr", "ph_base", "ph_corr",
          "N", "P", "K", "bomba_fw")
PASTA = Path(__file__).resolve().parent


def gerar_leitura(tipo, *, agora=None):
    """Devolve os onze campos F2; a origem sintética é marcada ao gravar o CSV."""
    if not isinstance(tipo, str) or tipo not in TIPOS:
        raise ValueError("Tipo de exemplo IoT inválido.")
    if agora is not None and not isinstance(agora, datetime):
        raise ValueError("O instante de referência precisa ser datetime.")
    referencia = agora if agora is not None else datetime.now(timezone.utc)
    if referencia.tzinfo is None:
        referencia = referencia.replace(tzinfo=timezone.utc)
    instante = referencia.astimezone(timezone.utc) - timedelta(seconds=30)
    umidade = {"umidade_baixa": 40, "umidade_alta": 85}.get(tipo, 60)
    ldr = 1989 if tipo == "ph_fora_faixa" else 2223
    ph_base = round(14.0 - (ldr / 4095.0 * 14.0), 3)
    n = 0 if tipo == "npk_ausente" else 1
    ph_corr = round(ph_base - (0.3 if n == 0 else 0), 3)
    bomba = int(umidade < 45 or (umidade <= 80 and (not 6.0 <= ph_corr <= 6.8 or n == 0)))
    return {
        "ts_iso": instante.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "t_rel_ms": 30000, "umidade": umidade, "temp_c": 25,
        "ldr": ldr, "ph_base": ph_base, "ph_corr": ph_corr,
        "N": n, "P": 1, "K": 1, "bomba_fw": bomba,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tipo", choices=TIPOS, default="umidade_baixa")
    parser.add_argument("--saida", type=Path, help="Novo CSV; arquivos existentes são recusados.")
    args = parser.parse_args(argv)
    caminho = (args.saida if args.saida is not None
               else PASTA / f".exemplo-iot-{uuid4().hex}.csv").resolve()
    try:
        with caminho.open("x", encoding="utf-8", newline="") as arquivo:
            arquivo.write(MARCADOR_EXEMPLO + "\n")
            writer = csv.DictWriter(arquivo, fieldnames=CAMPOS, lineterminator="\n")
            writer.writeheader()
            writer.writerow(gerar_leitura(args.tipo))
    except (OSError, ValueError) as exc:
        parser.error(f"Não foi possível criar um novo exemplo IoT: {exc}")
    print(caminho)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
