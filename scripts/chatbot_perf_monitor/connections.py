"""
Connection helpers for Milestone 6.5 chatbot performance monitoring.

Copy of the .env-loading idiom used across scripts/* (convention since M2.1).
Unlike any single prior chatbot_* folder, M6.5 genuinely needs BOTH physical
instances: the SERVING project (pg_stat_statements/pg_stat_activity, chatbot_views
schema -- via SERVING_DB_URL) for chatbot-perf-reader, and production Supabase
(monitoring.* -- via SUPABASE_DB_URL) for chatbot_audit_reader and for writing
this milestone's own snapshot/alert tables (decisions.md Keputusan B/C).

Both admin URLs turned out to be Supavisor pooler URLs (M2.4/M4.5 findings) --
same pooler-cache-staleness considerations apply to freshly created roles here.
"""
import os
import re

import psycopg2

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_POOLER_URL_RE = re.compile(r"postgresql://postgres\.([^:]+):[^@]+@([^:]+):(\d+)/(.+)")


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


def get_serving_connection(readonly=False):
    """Admin connection to the serving project -- role/grant setup only."""
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["SERVING_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn


def get_production_connection(readonly=False):
    """Admin connection to production Supabase -- role/grant/schema setup only."""
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["SUPABASE_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn


def build_serving_role_connection_string(role, password):
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    m = _POOLER_URL_RE.match(env["SERVING_DB_URL"])
    if not m:
        raise ValueError("SERVING_DB_URL is not in the expected Supavisor pooler format")
    project_ref, host, port, db = m.groups()
    return f"postgresql://{role}.{project_ref}:{password}@{host}:{port}/{db}"


def build_production_role_connection_string(role, password):
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    m = _POOLER_URL_RE.match(env["SUPABASE_DB_URL"])
    if not m:
        raise ValueError("SUPABASE_DB_URL is not in the expected Supavisor pooler format")
    project_ref, host, port, db = m.groups()
    return f"postgresql://{role}.{project_ref}:{password}@{host}:{port}/{db}"


def write_env_var(key, value):
    """Read/filter-out-old-key/append/rewrite .env -- same idiom as M3.5/M3.6/M4.3/M4.5.
    Never prints the value."""
    env_path = os.path.join(REPO_ROOT, ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith(f"{key}=")]
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append(f"{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
