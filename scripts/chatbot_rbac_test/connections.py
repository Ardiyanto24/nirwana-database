"""
Connection helper for Milestone 4.6 RBAC matrix testing.

Copy of the .env-loading idiom used across scripts/* (convention since M2.1).
Reads mart_cleaned.role_permissions/employees directly via the admin serving
connection (SERVING_DB_URL) -- this is test tooling reading ground truth to
build expectations, not production code, so it's a different context from
chatbot_authz_reader (M4.4 Keputusan #6 / M4.5), which is scoped strictly for
the API's OWN internal authorization decisions and never meant to be read by
anything else (decisions.md M4.6 Keputusan #2).
"""
import os

import psycopg2

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["SERVING_DB_URL"])
    if readonly:
        conn.set_session(readonly=True, autocommit=True)
    return conn
