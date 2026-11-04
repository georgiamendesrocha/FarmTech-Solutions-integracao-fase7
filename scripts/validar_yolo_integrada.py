"""Validação real por botão, somente com checkout existente e revisão conferida."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from farmtech_integracao.fase6 import REVISAO_YOLO
from farmtech_integracao.runtime import SERVICE_DIRS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yolo-repo",type=Path,required=True)
    args=parser.parse_args()
    repo=args.yolo_repo.expanduser().resolve()
    if not repo.is_dir() or not (repo/".git").exists():
        raise RuntimeError("Checkout Git local ausente.")
    env=dict(os.environ,GIT_OPTIONAL_LOCKS="0",GIT_TERMINAL_PROMPT="0")
    def git(*arguments):
        return subprocess.run(["git","-C",str(repo),*arguments],capture_output=True,
                              text=True,encoding="utf-8",check=True,timeout=15,env=env).stdout.strip()
    head=git("rev-parse","--verify","HEAD^{commit}")
    if head!=REVISAO_YOLO:
        raise RuntimeError("Revisão Git diferente da revisão exigida.")
    file_filters=("*.py","*.yaml","*.yml","*.txt","*.toml","*.cfg","*.ini","*.json","*.pyd","*.so","*.pth")
    before_status=git("status","--porcelain","--untracked-files=all","--ignored=matching","--",*file_filters)
    if before_status:
        raise RuntimeError("Checkout com fontes/configuração alterados; avaliação recusada.")
    print("Checkout existente, revisão completa correta e fontes limpas; iniciando avaliação integrada.",flush=True)
    models=SERVICE_DIRS["fase6"]/"entrega_2/modelos"
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in models.iterdir() if p.suffix in (".pt",".keras")}
    from streamlit.testing.v1 import AppTest
    page=AppTest.from_file(str(SERVICE_DIRS["fase4"]/"src/frontend/pages/12_Visao_Computacional.py"),default_timeout=180).run()
    page.text_input[0].set_value(str(repo)).run()
    if page.exception:
        raise RuntimeError("Erro ao abrir a página integrada de visão.")
    button=next(item for item in page.button if item.label=="Avaliar YOLO customizada")
    if button.disabled:
        raise RuntimeError("Pré-condições do botão YOLO não atendidas.")
    button.click().run()
    if page.exception:
        raise RuntimeError("Erro de interface ao avaliar a YOLO.")
    result=page.session_state["fase6_avaliacao"]["resultado"]
    preserved=before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in models.iterdir() if p.suffix in (".pt",".keras")}
    checkout_unchanged=git("status","--porcelain","--untracked-files=all","--ignored=matching","--",*file_filters)==before_status
    evidence={"validation":"real Streamlit button -> adapter -> worker Python3.13.13 -> avaliar_yolo.py",
              "revision":head,"models_preserved":preserved,"checkout_unchanged":checkout_unchanged,
              "ui_exceptions":len(page.exception),"plotly_charts":len(page.get("plotly_chart")),"result":result}
    directory=ROOT/".runtime/validation"
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"yolo-integrada.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(evidence,ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if result["status"]=="ok" and preserved and checkout_unchanged else 1


if __name__=="__main__":
    raise SystemExit(main())
