"""
Connection helpers for Milestone 4.3 AI Chatbot credential scripts.

Copy of scripts/data_analyst_credentials/connections.py (not imported --
project convention since M2.1), with get_mart_cleaned_owner_connection
DELIBERATELY OMITTED: Milestone 4.3's decisions.md Keputusan #3 forbids any
GRANT on mart_cleaned/mart_aggregated tables at all -- every grant target is
a chatbot_views.<view>, and all 67 of those views are owned by the same admin
role (verified empirically, Fase 0 -- pg_class.relowner all = 'postgres',
same role as SERVING_DB_URL). No owner-routing complexity needed here.
"""
import os
import re

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
_POOLER_URL_RE = re.compile(r"postgresql://postgres\.([^:]+):[^@]+@([^:]+):(\d+)/(.+)")


def get_serving_connection(readonly=False):
    """Admin connection to the serving project -- role/grant setup only."""
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["SERVING_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn


def build_role_connection_string(role, password):
    """Builds a Supavisor pooler connection string for a newly created role,
    reusing the admin SERVING_DB_URL's project ref/host/port/db."""
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    m = _POOLER_URL_RE.match(env["SERVING_DB_URL"])
    if not m:
        raise ValueError("SERVING_DB_URL is not in the expected Supavisor pooler format")
    project_ref, host, port, db = m.groups()
    return f"postgresql://{role}.{project_ref}:{password}@{host}:{port}/{db}"


def write_env_var(key, value):
    """Read/filter-out-old-key/append/rewrite .env -- same idiom as M3.5/M3.6.
    Never prints the value. Ensures the last existing line ends with \\n
    before appending (M3.6 finding: naive append can glue onto a
    no-trailing-newline last line and silently corrupt both entries)."""
    env_path = os.path.join(REPO_ROOT, ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith(f"{key}=")]
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append(f"{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
