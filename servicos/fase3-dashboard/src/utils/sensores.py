"""Normalização dos sensores da Fase 3, sem inicializar interface ou serviços."""

from decimal import Decimal

import numpy as np
import pandas as pd


def _bomba_label(val) -> str:
    if val is None or pd.isna(val):
        return "Desligada"
    if isinstance(val, Decimal):
        return "Ligada" if int(val) == 1 else "Desligada"
    if isinstance(val, (int, float, np.integer, np.bool_)):
        return "Ligada" if int(val) == 1 else "Desligada"
    t = str(val).strip().lower()
    return "Ligada" if t in ("ligada", "1", "true", "sim") else "Desligada"


def _padronizar_df(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]

    # Mapeamento de nomes legacy -> nomes canônicos FIAP
    aliases = {
        "temperatura": "temp_c",
        "ph": "ph_corr",
        "nitrogenio": "n",
        "fosforo": "p",
        "potassio": "k",
        "irrigacao_bin": "bomba_fw",
    }
    for old, new in aliases.items():
        if new not in d.columns and old in d.columns:
            d[new] = d[old]

    if "instante" not in d.columns:
        d["instante"] = pd.to_datetime(d.get("ts_iso"), errors="coerce")
    else:
        d["instante"] = pd.to_datetime(d["instante"], errors="coerce")

    for c in ("umidade", "temp_c", "ph_corr"):
        if c not in d.columns:
            d[c] = np.nan
        d[c] = pd.to_numeric(d[c], errors="coerce")

    for c in ("n", "p", "k"):
        if c not in d.columns:
            d[c] = 0
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int).clip(0, 1)

    if "bomba_fw" not in d.columns:
        d["bomba_fw"] = 0
    d["bomba_fw"] = pd.to_numeric(d["bomba_fw"], errors="coerce").fillna(0).astype(int).clip(0, 1)
    d["irrigacao"] = d["bomba_fw"].apply(_bomba_label)

    d = d.dropna(subset=["umidade", "temp_c", "ph_corr", "instante"]).copy()
    d = d.sort_values("instante").reset_index(drop=True)

    # Oracle já possui coluna ID; evitar colisão "cannot insert id, already exists".
    if "id" in d.columns:
        d["id"] = pd.to_numeric(d["id"], errors="coerce")
        # Se houver nulos no ID vindo do banco, completa com sequência estável.
        if d["id"].isna().any():
            d["id"] = d["id"].fillna(pd.Series(np.arange(1, len(d) + 1), index=d.index))
        d["id"] = d["id"].astype(int)
        cols = ["id"] + [c for c in d.columns if c != "id"]
        d = d[cols]
    else:
        d.insert(0, "id", np.arange(1, len(d) + 1, dtype=int))
    return d
