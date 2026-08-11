"""Shared Supabase connection helper for Milestone 6.5 chatbot performance
monitoring scripts. Copy of scripts/monitoring_warehouse/db.py (project
convention since M2.1: copied, not imported, across scripts/* subfolders).

Admin SUPABASE_DB_URL is used here for WRITES to monitoring.* -- this is an
internal batch job, not a live-traffic API process (decisions.md Keputusan
B), same threat model as every other scripts/monitoring_warehouse/*.py writer.
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


def get_connection(readonly=False):
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env = _load_env(os.path.join(repo_root, ".env"))
    conn = psycopg2.connect(env["SUPABASE_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn
