"""Atualiza cópias locais de observações NOAA/USCRN e estatísticas IBGE/SIDRA."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_sources import importar_inmet, importar_noaa, importar_sidra


def _run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--noaa", action="store_true", help="Atualiza observações USCRN.")
    parser.add_argument("--inmet", action="store_true", help="Atualiza observações meteorológicas INMET.")
    parser.add_argument("--inmet-zip", type=Path, help="Importa um ZIP INMET já baixado localmente.")
    parser.add_argument("--sidra", action="store_true", help="Atualiza rendimentos da tabela SIDRA 1612.")
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Atualiza NOAA, INMET e SIDRA.",
    )
    args = parser.parse_args()
    if not (args.noaa or args.inmet or args.inmet_zip or args.sidra or args.todos):
        parser.error("Informe --noaa, --inmet, --inmet-zip, --sidra ou --todos.")

    if args.noaa or args.todos:
        frame, metadata = importar_noaa()
        print(
            f"[OK] NOAA/USCRN: {len(frame)} observações da estação "
            f"{metadata['estacao']} ({metadata['inicio_utc']} a {metadata['fim_utc']})."
        )
    if args.inmet or args.inmet_zip or args.todos:
        frame, metadata = importar_inmet(archive_path=args.inmet_zip)
        print(
            f"[OK] INMET: {len(frame)} observações da estação "
            f"{metadata['station']} ({metadata['inicio_utc']} a {metadata['fim_utc']})."
        )
    if args.sidra or args.todos:
        national, municipalities, metadata = importar_sidra()
        print(
            f"[OK] SIDRA 1612: {len(national)} observações nacionais e "
            f"{len(municipalities)} observações municipais."
        )
        print(f"[OK] Proveniência: {metadata['fonte']}.")


def main() -> int:
    try:
        _run()
    except (OSError, ValueError, RuntimeError):
        print("[ERRO] Importação não concluída. Confira o arquivo, a fonte e a permissão de escrita; os conjuntos anteriores permanecem recuperáveis.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
