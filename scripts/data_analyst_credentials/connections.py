"""
Connection helpers for Milestone 3.5 Data Analyst credential scripts.

Copy of scripts/reverse_etl/connections.py's get_serving_connection (not
imported -- project convention since M2.1). Adds build_role_connection_string,
which reconstructs the Supavisor pooler connection format
(postgresql://<role>.<project_ref>:<password>@<host>:<port>/<db>) from the
admin SERVING_DB_URL, same idiom as scripts/api_reader/setup_reader_role.py.
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
    """Read/filter-out-old-key/append/rewrite .env -- same idiom as
    setup_reader_role.py/setup_writer_role.py. Never prints the value."""
    env_path = os.path.join(REPO_ROOT, ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith(f"{key}=")]
    lines.append(f"{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
