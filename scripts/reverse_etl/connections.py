"""
Shared connection helpers for Milestone 2.4 reverse ETL scripts.

Deliberately NOT named db.py -- scripts/monitoring/db.py is imported here via
sys.path append, and naming this module identically caused a self-referential
import collision (Python resolves `from db import ...` to whichever `db`
module is already cached in sys.modules, which is this file itself when run
as the entrypoint's own directory is first on sys.path). Same bug class
logged in M2.1 (tables_config.py collision) -- avoided here by using a
distinct filename instead of import ordering tricks.
"""
import os
import sys

import psycopg2

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env, get_connection as get_production_connection  # noqa: E402,F401

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_serving_connection(readonly=False):
    """Connect to the NEW serving Supabase project (mart_cleaned schema), not production."""
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["SERVING_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn
