"""Verifica a entrada HTTP local e encerra sua árvore; sem abrir navegador."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from farmtech_integracao.runtime import _stop_tree


def main():
    directory = ROOT / ".runtime" / "validation"
    directory.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    options = ({"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == "nt" else {"start_new_session": True})
    with (directory / "dashboard-startup.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-X", "utf8", "-B", str(ROOT/"iniciar.py"),
                                    "--dashboard", "--port", str(port)], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log, **options)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                if process.poll() is not None:
                    raise RuntimeError("A dashboard encerrou antes de responder.")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health",timeout=1) as response:
                        if response.status==200 and response.read(100)==b"ok":
                            evidence={"status":"ok","check":"Streamlit HTTP health","http_status":200,
                                      "bind":"127.0.0.1","browser_visual_check":False}
                            (directory/"dashboard-http.json").write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
                            print(json.dumps(evidence))
                            return 0
                except OSError:
                    time.sleep(.25)
            raise RuntimeError("A dashboard não respondeu no prazo.")
        finally:
            _stop_tree(process)


if __name__=="__main__":
    raise SystemExit(main())
