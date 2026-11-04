"""Executa uma suíte permitida e registra evidência local, sem instalar pacotes.

A seleção F4 exclui testes de reprodução que ajustam estimadores em diretórios
temporários; exercita segurança, persistência, interface e bloqueio de treino.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

F4_TESTS = [
    "test_assets_safety", "test_data_sources", "test_data_safety", "test_db_safety",
    "test_frontend_safety", "test_history_audit", "test_launcher_safety",
    "test_recommendations_audit", "test_scheduler", "test_scheduler_audit",
    "test_model_safety.InputContractTests", "test_model_safety.ModelProvenanceTests",
    "test_model_safety.ProductivityArtifactTests",
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite",required=True,choices=("integracao","fase1","fase2","fase4"))
    args=parser.parse_args()
    directories={"integracao":ROOT, "fase1":ROOT/"servicos/fase1-gestao",
                 "fase2":ROOT/"servicos/fase2-iot", "fase4":ROOT/"servicos/fase4-regressao"}
    service=directories[args.suite]
    os.chdir(service)
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    sys.path.insert(0,str(service))
    folder=service/("tests/integracao" if args.suite=="integracao" else "tests")
    sys.path.insert(0,str(folder))
    loader=unittest.TestLoader()
    suite=(loader.loadTestsFromNames(F4_TESTS) if args.suite=="fase4"
           else loader.discover(str(folder)))
    directory=ROOT/".runtime/validation"
    directory.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    with (directory/f"{args.suite}-tests.log").open("w",encoding="utf-8") as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    summary={"suite":args.suite,"python":".".join(map(str,sys.version_info[:3])),
             "tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
             "skipped":len(result.skipped),"successful":result.wasSuccessful(),
             "elapsed_seconds":round(time.monotonic()-start,2),
             "training_executed":False,"external_network_executed":False}
    (directory/f"{args.suite}-results.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary))
    return 0 if result.wasSuccessful() else 1


if __name__=="__main__":
    raise SystemExit(main())
