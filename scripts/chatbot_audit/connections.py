"""
Connection helpers for Milestone 4.5 audit log credential setup.

Copy of the .env-loading idiom used across scripts/* (convention since M2.1).
Unlike scripts/chatbot_credentials/connections.py (targets the SERVING
project via Supavisor pooler, SERVING_DB_URL), this targets a DIFFERENT
physical instance -- production Supabase (SUPABASE_DB_URL) -- because
monitoring.* lives there (CLAUDE.md "monitoring schema -- the shared
backbone"), not in the serving project the rest of scripts/chatbot_* talks to
(decisions.md M4.5 Keputusan #1/#2). SUPABASE_DB_URL turns out to ALSO be a
Supavisor pooler URL in this repo's actual .env (not the direct connection
.env.example's comment describes, discovered empirically when the direct-
connection regex first tried here failed) -- same pooler-cache-staleness
considerations as SERVING_DB_URL apply here too.
"""
import os
import re

import psycopg2

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env.example's comment for SUPABASE_DB_URL describes a direct connection
# (postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co) -- but the actually
# configured value in this repo's .env is a Supavisor POOLER URL
# (postgres.[PROJECT-REF]@aws-0-[REGION].pooler.supabase.com), same shape as
# SERVING_DB_URL (M2.4). Discovered empirically (setup_audit_writer.py failed
# with a direct-connection regex on the first run) -- code here matches the
# actual configured format, not the stale .env.example comment.
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


def get_production_connection(readonly=False):
    """Admin connection to production Supabase -- role/grant/schema setup only."""
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["SUPABASE_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn


def build_role_connection_string(role, password):
    """Builds a Supavisor pooler connection string for a newly created role,
    reusing the admin SUPABASE_DB_URL's project ref/host/port/db (same idiom
    as scripts/chatbot_credentials/connections.py for SERVING_DB_URL)."""
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    m = _POOLER_URL_RE.match(env["SUPABASE_DB_URL"])
    if not m:
        raise ValueError("SUPABASE_DB_URL is not in the expected Supavisor pooler format")
    project_ref, host, port, db = m.groups()
    return f"postgresql://{role}.{project_ref}:{password}@{host}:{port}/{db}"


def write_env_var(key, value):
    """Read/filter-out-old-key/append/rewrite .env -- same idiom as M3.5/M3.6/M4.3.
    Never prints the value."""
    env_path = os.path.join(REPO_ROOT, ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith(f"{key}=")]
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append(f"{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
