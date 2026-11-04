"""
Scheduler de simulação IoT — um produtor por processo, compartilhado entre sessões.

Não há coordenação entre processos: em implantação com workers, desative a
simulação nos consumidores e execute apenas um produtor designado.
"""

import os
import random
import time
from pathlib import Path
import sys
import atexit
import math
import threading

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
from apscheduler.schedulers.base import STATE_PAUSED
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

UMIDADE_LIMIAR = float(os.getenv("UMIDADE_LIMIAR", "60.0"))
INTERVALO = int(os.getenv("SCHEDULER_INTERVALO", "30"))
_SCHEDULER = None
_INICIADO_EM = None
_LOCK = threading.RLock()

# Parâmetros aproximados usados para simular leituras do protótipo ESP32/Wokwi.
_DIST = {
    "umidade":  {"media": 73.5,  "desvio": 12.0,  "min": 30.0, "max": 95.0},
    "temp_c":   {"media": 28.5,  "desvio": 5.5,   "min": 14.0, "max": 40.0},
    "ldr":      {"media": 1800.0,"desvio": 600.0,  "min": 1000.0,"max": 2531.0},
    "ph":       {"media": 7.2,   "desvio": 1.8,   "min": 4.5,  "max": 10.5},
}


def _gerar_leitura() -> dict:
    """Gera uma leitura simulada para registro do protótipo ESP32/Wokwi."""
    def sample(chave: str) -> float:
        d = _DIST[chave]
        v = np.random.normal(d["media"], d["desvio"])
        return float(np.clip(v, d["min"], d["max"]))

    umidade = round(sample("umidade"), 1)
    temp_c  = round(sample("temp_c"), 1)
    ldr     = round(sample("ldr"), 0)
    ph      = round(sample("ph"), 3)
    n = random.randint(0, 1)
    p = random.randint(0, 1)
    k = random.randint(0, 1)
    bomba_fw = 1 if umidade < UMIDADE_LIMIAR else 0

    return dict(umidade=umidade, temp_c=temp_c, ldr=ldr, ph=ph, n=n, p=p, k=k, bomba_fw=bomba_fw)


def estado_simulacao(scheduler_holder: dict) -> str:
    """Resume configuração, falhas e execução real para as páginas do painel."""
    if os.getenv("FARMTECH_SIMULACAO", "1") == "0" and os.getenv("FARMTECH_INTEGRACAO") != "1":
        return "desativada"
    if scheduler_holder.get("erro"):
        return "indisponivel"
    sched = scheduler_holder.get("scheduler")
    if sched is not None and sched.running:
        if getattr(sched, "state", None) == STATE_PAUSED:
            return "pausada"
        return "ativa"
    return "parada"


def iniciar_scheduler(scheduler_holder: dict, *, manual: bool = False) -> None:
    """
    Inicia uma instância por processo e associa o holder da sessão a ela.
    Um objeto previamente encerrado é substituído, permitindo reinício seguro.
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from src.db.database import inserir_leitura_simulada

    global _SCHEDULER, _INICIADO_EM
    if not isinstance(scheduler_holder, dict):
        raise ValueError("Estado do scheduler inválido.")
    if manual:
        from farmtech_integracao.demo import demo_path
        from src.db.database import resolve_db_path
        if os.getenv("FARMTECH_INTEGRACAO") != "1" or resolve_db_path() != demo_path().resolve():
            raise ValueError("Simulacao restrita ao banco de demonstracao.")
    elif os.getenv("FARMTECH_SIMULACAO", "1") == "0":
        encerrar_scheduler(scheduler_holder)
        scheduler_holder.pop("erro", None)
        return
    if not math.isfinite(UMIDADE_LIMIAR) or not 0 <= UMIDADE_LIMIAR <= 100 or INTERVALO <= 0:
        raise ValueError("Configuração da simulação inválida.")
    with _LOCK:
        if _SCHEDULER is None or not _SCHEDULER.running:
            def job():
                inserir_leitura_simulada(**_gerar_leitura())

            sched = BackgroundScheduler()
            sched.add_job(job, "interval", seconds=INTERVALO, id="simulacao_iot",
                          max_instances=1, coalesce=True)
            try:
                sched.start()
            except BaseException:
                if sched.running:
                    sched.shutdown(wait=True)
                raise
            _SCHEDULER = sched
            _INICIADO_EM = time.time()
        scheduler_holder["scheduler"] = _SCHEDULER
        scheduler_holder["iniciado_em"] = _INICIADO_EM
        scheduler_holder.pop("erro", None)


def encerrar_scheduler(scheduler_holder: dict | None = None) -> None:
    """Encerra o produtor global e aguarda o job em andamento; chamada idempotente."""
    global _SCHEDULER, _INICIADO_EM
    with _LOCK:
        if _SCHEDULER is not None and _SCHEDULER.running:
            _SCHEDULER.shutdown(wait=True)
        _SCHEDULER = None
        _INICIADO_EM = None
        if scheduler_holder is not None:
            scheduler_holder.pop("scheduler", None)
            scheduler_holder.pop("iniciado_em", None)


atexit.register(encerrar_scheduler)
