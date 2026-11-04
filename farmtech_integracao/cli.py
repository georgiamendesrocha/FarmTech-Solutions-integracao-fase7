"""CLI integrada: ações deliberadas; abrir a dashboard não prepara serviços."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from farmtech_integracao.demo import configure_dashboard, demo_path, inspect_database, prepare_demo
from farmtech_integracao.runtime import SERVICE_DIRS


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_mutually_exclusive_group()
    actions.add_argument("--dashboard", action="store_true", help="Abre a dashboard existente da F4 (padrão).")
    actions.add_argument("--status", action="store_true", help="Pré-condições locais; não conecta Oracle nem executa inferências.")
    actions.add_argument("--preparar-demo", action="store_true", help="Cria exclusivamente uma base reconstruída nova; nunca sobrescreve.")
    actions.add_argument("--gestao", action="store_true", help="Calcula área e insumos da F1.")
    actions.add_argument("--meteorologia", metavar="CIDADE", help="Consulta explicitamente Open-Meteo pela F2; requer rede.")
    actions.add_argument("--consultar-fase3", choices=("csv", "oracle"), help="Consulta F3 com origem explícita.")
    actions.add_argument("--avaliar-yolo", action="store_true", help="Executa avaliação experimental customizada F6 em CPU.")
    cli.add_argument("--forma", default="retangulo")
    cli.add_argument("--medidas", nargs="+", type=float, default=[100.0, 50.0])
    cli.add_argument("--cultura", default="Soja")
    cli.add_argument("--espacamento", type=float, default=0.5)
    cli.add_argument("--yolo-repo", help="Checkout YOLOv5 local verificado; alternativa FARMTECH_YOLO_REPO.")
    cli.add_argument("--port", type=int, default=8501)
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    if sys.version_info[:3] != (3, 11, 9):
        print("Esta entrada requer o ambiente validado Python 3.11.9 da Fase 4.", file=sys.stderr)
        return 2
    os.environ["FARMTECH_INTEGRACAO"] = "1"
    configure_dashboard()
    if args.status:
        from farmtech_integracao import fase1, fase2, fase3, fase6
        result = {name: module.availability().as_dict() for name, module in
                  (("fase1", fase1), ("fase2", fase2), ("fase3", fase3), ("fase6", fase6))}
        result["fase4"] = inspect_database(Path(os.environ["DB_PATH"])).as_dict()
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    if args.preparar_demo:
        result = prepare_demo()
    elif args.gestao:
        from farmtech_integracao.fase1 import calculate_plot
        result = calculate_plot(args.forma, args.medidas, crop=args.cultura, spacing=args.espacamento)
    elif args.meteorologia is not None:
        from farmtech_integracao.fase2 import forecast
        result = forecast(args.meteorologia)
    elif args.consultar_fase3:
        from farmtech_integracao.fase3 import query_sensors
        result = query_sensors(args.consultar_fase3)
    elif args.avaliar_yolo:
        from farmtech_integracao.fase6 import evaluate_customizada
        result = evaluate_customizada(args.yolo_repo)
    else:
        if not 1 <= args.port <= 65535:
            print("Porta inválida.", file=sys.stderr)
            return 2
        command = [sys.executable, "-B", "-m", "streamlit", "run",
                   str(SERVICE_DIRS["fase4"] / "src" / "frontend" / "app.py"),
                   "--server.address", "127.0.0.1", "--server.port", str(args.port),
                   "--server.headless", "true", "--server.enableCORS", "true",
                   "--server.enableXsrfProtection", "true", "--browser.gatherUsageStats", "false"]
        from farmtech_integracao.runtime import _stop_tree
        options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
                   if os.name == "nt" else {"start_new_session": True})
        process = subprocess.Popen(command, cwd=SERVICE_DIRS["fase4"], env=os.environ.copy(),
                                   stdout=sys.stdout, stderr=sys.stderr, **options)
        try:
            return process.wait()
        except KeyboardInterrupt:
            _stop_tree(process)
            return 130
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
