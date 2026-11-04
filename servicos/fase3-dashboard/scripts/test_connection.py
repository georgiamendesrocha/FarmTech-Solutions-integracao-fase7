"""Testa conexão Oracle e verifica tabelas esperadas.

Uso:
    python scripts/test_connection.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

import os

REQUIRED_VARS = ("ORACLE_USER", "ORACLE_PASS", "ORACLE_DSN")
EXPECTED_TABLES = (
    "WTH_LOCATIONS", "WTH_HOURLY_FORECAST",
    "WTH_DAILY_FORECAST", "WTH_COLLECTION_LOG",
    "SENSORES_FARMTECH",
)

def main() -> int:
    faltando = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if faltando:
        print(f"[ERRO] Variáveis ausentes no .env: {', '.join(faltando)}")
        print("       Consulte config/.env.example")
        return 1

    print(f"[INFO] DSN: {os.getenv('ORACLE_DSN')} | Usuário: {os.getenv('ORACLE_USER')}")

    try:
        import oracledb
    except ImportError:
        print("[ERRO] oracledb não instalado: pip install oracledb")
        return 1

    try:
        conn = oracledb.connect(
            user=os.getenv("ORACLE_USER"),
            password=os.getenv("ORACLE_PASS"),
            dsn=os.getenv("ORACLE_DSN"),
        )
    except Exception as e:
        print(f"[ERRO] Falha na conexão: {e}")
        return 1

    cur = conn.cursor()
    cur.execute("SELECT SYSDATE FROM DUAL")
    row = cur.fetchone()
    print(f"[OK]   Conexão OK — SYSDATE: {row[0]}")

    cur.execute("SELECT TABLE_NAME FROM USER_TABLES ORDER BY TABLE_NAME")
    existentes = {r[0] for r in cur.fetchall()}

    all_ok = True
    for t in EXPECTED_TABLES:
        status = "[OK]  " if t in existentes else "[FALTA]"
        print(f"  {status} {t}")
        if t not in existentes:
            all_ok = False

    cur.close()
    conn.close()

    if not all_ok:
        print("\n[AVISO] Execute src/sql/createtable.sql para criar as tabelas faltantes.")
        return 1

    print("\n[OK] Banco pronto para uso.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
