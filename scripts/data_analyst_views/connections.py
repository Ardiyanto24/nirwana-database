"""
Connection helper for Milestone 3.2 Data Analyst view scripts.

Copied (not imported) from scripts/reverse_etl/connections.py, following the
project convention established since M2.1 of duplicating this small helper
per scripts/* subfolder rather than sys.path-importing across folders --
cross-folder imports caused a real module-name collision bug in M2.1
(tables_config.py), and again motivated the "db.py" -> "connections.py"
rename in scripts/reverse_etl.
"""
import os

import psycopg2


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


def get_serving_connection(readonly=False):
    """Admin connection to the serving project -- Milestone 3.2 authors/applies
    view DDL only, no ongoing writes, so the admin SERVING_DB_URL is used
    directly (same rationale as setup_serving_schema.py in M2.4/M5.5).
    Scoped read-only credentials for Data Analyst roles are Milestone 3.5's
    responsibility, not this milestone's."""
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["SERVING_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn
