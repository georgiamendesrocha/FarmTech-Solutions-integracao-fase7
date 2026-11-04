import os
from contextlib import contextmanager
from pathlib import Path

import oracledb
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

_pool = None


def _dsn() -> str:
    return os.getenv("ORACLE_DSN", "localhost:1521/xepdb1")


def _user() -> str:
    return os.getenv("ORACLE_USER", "weather_user")


def _pass() -> str:
    return os.getenv("ORACLE_PASS", "")


def get_pool():
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=_user(),
            password=_pass(),
            dsn=_dsn(),
            min=1,
            max=5,
            increment=1,
        )
    return _pool


@contextmanager
def get_conn():
    conn = get_pool().acquire()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        get_pool().release(conn)


def execute_query(sql: str, params: dict = None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            cols = [c[0].lower() for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def execute_many(sql: str, data: list[dict]):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, data)


def ping() -> bool:
    try:
        execute_query("SELECT 1 FROM DUAL")
        return True
    except Exception:
        return False
