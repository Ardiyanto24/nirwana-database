"""
Milestone 4.5 -- writes one row per API request to monitoring.chatbot_query_log
(production Supabase) via chatbot_audit_writer (INSERT-only, scripts/chatbot_audit/).

Called from main.py through FastAPI BackgroundTasks -- AFTER the response is
already on its way back to the caller, so a slow/unreachable production
Supabase never adds latency to the actual data response (decisions.md
Keputusan #3). Best-effort: a failed log write is printed to stderr and
swallowed, never raised -- audit logging observes the API, it is not part of
the API's own critical path.

This module only ever sees requests that already passed Lapis 1 (decisions.md
Keputusan #7) -- role_title/employee_id recorded here are the CLAIMS Lapis 1
forwarded to this API, not independently verified identity.
"""
import os
import sys

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


def log_query(
    role_title,
    domain,
    view_name=None,
    employee_id=None,
    access_scope=None,
    resolved_property_id=None,
    status="denied",
    denial_reason=None,
    row_count=None,
):
    try:
        conn_str = _load_env(os.path.join(REPO_ROOT, ".env"))["CHATBOT_AUDIT_WRITER_DB_URL"]
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO monitoring.chatbot_query_log
                        (role_title, domain, view_name, employee_id, access_scope,
                         resolved_property_id, status, denial_reason, row_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        role_title,
                        domain,
                        view_name,
                        employee_id,
                        access_scope,
                        resolved_property_id,
                        status,
                        denial_reason,
                        row_count,
                    ),
                )
        finally:
            conn.close()
    except Exception as e:
        print(f"[audit] failed to write chatbot_query_log: {e}", file=sys.stderr)
