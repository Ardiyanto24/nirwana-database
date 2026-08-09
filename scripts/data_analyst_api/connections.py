"""
Connection helper for Milestone 3.4 Data Analyst API.

Copy of scripts/data_analyst_views/connections.py (M3.2), not imported --
project convention since M2.1 of duplicating this small helper per
scripts/* subfolder rather than sys.path-importing across folders.

M3.4 reuses the admin SERVING_DB_URL (same as M3.2) with readonly=True set at
the session level -- cheap defense-in-depth, not a real isolation mechanism.
Per-role scoped credentials are Milestone 3.5's responsibility.
"""
import os

import psycopg2
import psycopg2.extras


def _load_env(path):
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_serving_connection():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["SERVING_DB_URL"])
    conn.set_session(readonly=True, autocommit=True)
    return conn


def query(sql, params=None):
    with get_serving_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
