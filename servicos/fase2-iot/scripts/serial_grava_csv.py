#!/usr/bin/env python3
"""
Grava historico de leituras do ESP32 em CSV local (pasta dados/).

O firmware envia linhas CSV_ROW (e CSV_HDR). Este script acrescenta o carimbo
de data/hora do PC (ts_iso) para ordenar sessoes e juntar varias execucoes.

Uso (Windows, exemplo):
  python -m pip install -r scripts/requirements-serial.txt
  python scripts/serial_grava_csv.py --port COM6
  python scripts/serial_grava_csv.py --port rfc2217://127.0.0.1:4000

Por defeito: append em dados/historico_irrigacao.csv
Novo ficheiro limpo: python scripts/serial_grava_csv.py --port COM6 --fresh
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime
from pathlib import Path

CSV_HEADER_OUT = (
    "ts_iso,t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw\n"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "dados" / "historico_irrigacao.csv"
MAX_LINE_BYTES = 4096


def _now_iso_local() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def valid_payload(line: str) -> str | None:
    """Aceita apenas os dez campos numéricos emitidos pelo firmware."""
    if not line.startswith("CSV_ROW,"):
        return None
    fields = [field.strip() for field in line[len("CSV_ROW,"):].split(",")]
    if len(fields) != 10:
        return None
    try:
        numbers = [float(field) for field in fields]
        if not all(math.isfinite(value) for value in numbers):
            return None
        if not 0 <= int(fields[0]) <= 4294967295 or not 0 <= int(fields[3]) <= 4095:
            return None
    except (ValueError, OverflowError):
        return None
    if not 0 <= numbers[1] <= 100 or not all(0 <= numbers[i] <= 14 for i in (4, 5)):
        return None
    if any(field not in ("0", "1") for field in fields[6:]):
        return None
    return ",".join(fields)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serial -> CSV historico para R")
    parser.add_argument("--port", required=True, help="COM6, /dev/ttyUSB0 ou rfc2217://127.0.0.1:4000")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Ficheiro CSV de saida (append por defeito)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Apaga/recomeca o ficheiro de saida (sem juntar ao historico anterior)",
    )
    args = parser.parse_args()
    if args.baud <= 0:
        parser.error("--baud deve ser positivo")

    try:
        import serial
    except ImportError:
        print(
            "Dependencia ausente. Instale com: python -m pip install -r scripts/requirements-serial.txt",
            file=sys.stderr,
        )
        return 1

    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        if args.out.exists() and not args.out.is_file():
            print("O destino CSV deve ser um arquivo, nao um diretorio.", file=sys.stderr)
            return 4
        mode = "w" if args.fresh or not args.out.exists() or args.out.stat().st_size == 0 else "a"
        if mode == "a":
            with args.out.open(encoding="utf-8") as existing:
                if existing.readline().strip() != CSV_HEADER_OUT.strip():
                    print("Cabecalho CSV incompatível; use outro --out para preservar o arquivo.", file=sys.stderr)
                    return 4
    except (OSError, UnicodeError) as exc:
        print(f"Nao foi possivel preparar o CSV: {exc}", file=sys.stderr)
        return 4

    try:
        ser = serial.serial_for_url(args.port, baudrate=args.baud, timeout=0.5)
    except (serial.SerialException, OSError, ValueError) as e:
        print(f"Nao foi possivel abrir {args.port}: {e}", file=sys.stderr)
        return 2

    print(f"Historico -> {args.out.resolve()} (append={'sim' if mode == 'a' else 'nao'}; Ctrl+C para sair)")

    try:
        with args.out.open(mode, encoding="utf-8", newline="") as out:
            if mode == "w":
                out.write(CSV_HEADER_OUT)
                out.flush()

            pending = bytearray()
            discarding = False
            while True:
                raw = ser.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    continue
                if discarding:
                    discarding = not raw.endswith(b"\n")
                    continue
                pending.extend(raw)
                if len(pending) > MAX_LINE_BYTES:
                    print("Linha serial muito longa ignorada.", file=sys.stderr)
                    pending.clear()
                    discarding = not raw.endswith(b"\n")
                    continue
                if not pending.endswith(b"\n"):
                    continue
                line = pending.decode("utf-8", errors="replace").strip()
                pending.clear()
                payload = valid_payload(line)
                if payload is not None:
                    out.write(f"{_now_iso_local()},{payload}\n")
                    out.flush()
                elif line.startswith("CSV_ROW,"):
                    print("Linha CSV_ROW invalida ignorada.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuario.")
    except serial.SerialException as exc:
        print(f"Captura serial desconectada: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"Erro de leitura serial ou gravacao CSV: {exc}", file=sys.stderr)
        return 4
    finally:
        try:
            ser.close()
        except (serial.SerialException, OSError) as exc:
            print(f"Aviso ao fechar a serial: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
