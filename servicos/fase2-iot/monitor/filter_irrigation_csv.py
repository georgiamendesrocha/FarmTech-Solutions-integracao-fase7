# Filtro do PlatformIO: grava linhas CSV_ROW em dados/historico_irrigacao.csv
# ao usar "Monitor Serial" no VSCode (inclui simulacao Wokwi com porta virtual).
#
# Reabre em modo append sempre que o ficheiro estiver fechado (nova sessao do
# monitor ou objeto reutilizado apos __del__), para novas linhas serem acrescentadas.

import os
import sys
from datetime import datetime
from pathlib import Path

from platformio.public import DeviceMonitorFilterBase

CSV_HEADER = (
    "ts_iso,t_rel_ms,umidade,temp_c,ldr,ph_base,ph_corr,N,P,K,bomba_fw\n"
)


class IrrigationCsvLogger(DeviceMonitorFilterBase):
    NAME = "irrigation_csv"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buf = ""
        self._fp = None
        self._csv_path = None

    def _ensure_open_append(self):
        """Abre (ou reabre) o CSV em append; cabecalho so se o ficheiro estiver vazio."""
        fp = getattr(self, "_fp", None)
        if fp is not None and not fp.closed:
            return
        if fp is not None:
            try:
                fp.close()
            except Exception:
                pass
            self._fp = None

        base = self.project_dir or os.getcwd()
        dados = Path(base) / "dados"
        dados.mkdir(parents=True, exist_ok=True)
        self._csv_path = dados / "historico_irrigacao.csv"

        precisa_cabecalho = (
            not self._csv_path.exists() or self._csv_path.stat().st_size == 0
        )

        self._fp = open(self._csv_path, "a", encoding="utf-8", newline="")
        if precisa_cabecalho:
            self._fp.write(CSV_HEADER)
            self._fp.flush()

    def __call__(self):
        # Nova sessao do monitor: limpa buffer de linha incompleta
        self._buf = ""
        self._ensure_open_append()
        print(
            "Irrigacao CSV -> %s" % self._csv_path.resolve(),
            file=sys.stderr,
            flush=True,
        )
        return self

    def rx(self, text):
        # __call__ pode nao correr antes do primeiro rx em algumas versoes;
        # ou o ficheiro ja foi fechado apos parar o monitor — reabrir sempre que preciso.
        self._ensure_open_append()

        self._buf += text
        while True:
            if "\r\n" in self._buf:
                line, self._buf = self._buf.split("\r\n", 1)
            elif "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
            else:
                break

            line = line.strip()
            if line.startswith("CSV_ROW,"):
                ts = datetime.now().replace(microsecond=0).isoformat()
                payload = line[len("CSV_ROW,") :]
                try:
                    self._fp.write("%s,%s\n" % (ts, payload))
                    self._fp.flush()
                except ValueError:
                    # ficheiro fechado entre flush e write — reabrir e repetir uma vez
                    self._fp = None
                    self._ensure_open_append()
                    self._fp.write("%s,%s\n" % (ts, payload))
                    self._fp.flush()

        return text

    def __del__(self):
        fp = getattr(self, "_fp", None)
        if fp is not None:
            try:
                fp.close()
            except Exception:
                pass
            self._fp = None
