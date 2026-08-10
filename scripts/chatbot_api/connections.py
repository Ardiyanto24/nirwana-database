"""
Connection + authorization helpers for Milestone 4.4 AI Chatbot API.

Copy of the .env-loading idiom used across scripts/* (not imported --
convention since M2.1). Unlike scripts/data_analyst_api/connections.py (M3.4,
1 shared admin connection for everything -- isolation deferred to M3.5, used
by humans OUTSIDE that API), this module holds a SEPARATE connection getter
per data_domain credential (M4.3) plus the authz-only credential (M4.4
Keputusan #6) -- the API itself is the trust boundary here, so it must
actually execute data queries through the scoped domain credential, not an
admin connection (decisions.md Keputusan #4).
"""
import os

import psycopg2
import psycopg2.extras

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DOMAIN_ENV_VARS = {
    "reservation": "RESERVATION_CHATBOT_READER_DB_URL",
    "fnb": "FNB_CHATBOT_READER_DB_URL",
    "facility": "FACILITY_CHATBOT_READER_DB_URL",
    "spa_event": "SPA_EVENT_CHATBOT_READER_DB_URL",
    "hr": "HR_CHATBOT_READER_DB_URL",
    "financial": "FINANCIAL_CHATBOT_READER_DB_URL",
    "properties_ref": "PROPERTIES_REF_CHATBOT_READER_DB_URL",
    "employees_directory": "EMPLOYEES_DIRECTORY_CHATBOT_READER_DB_URL",
    "guests_pii": "GUESTS_PII_CHATBOT_READER_DB_URL",
    "guests_profile": "GUESTS_PROFILE_CHATBOT_READER_DB_URL",
}


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


def _env():
    return _load_env(os.path.join(REPO_ROOT, ".env"))


def query_as_domain(domain, sql, params=None):
    """Executes sql using the M4.3 credential scoped to `domain` -- never the
    admin connection. Raises KeyError if `domain` isn't one of the 10 known
    data_domain credentials (caller's whitelist lookup should already have
    rejected an unknown domain before reaching here)."""
    env_var = DOMAIN_ENV_VARS[domain]
    conn_str = _env()[env_var]
    conn = psycopg2.connect(conn_str)
    conn.set_session(readonly=True, autocommit=True)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def query_authz(sql, params=None):
    """Executes sql using chatbot_authz_reader (M4.4 Keputusan #6) --
    role_permissions lookups only. Results from this connection must never be
    returned directly as an API response body (enforced by callers only using
    it inside authorize_request(), never inside a route handler)."""
    conn_str = _env()["CHATBOT_AUTHZ_READER_DB_URL"]
    conn = psycopg2.connect(conn_str)
    conn.set_session(readonly=True, autocommit=True)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def resolve_property_id(employee_id):
    """Resolves an employee's ACTUAL assigned property_id via
    chatbot_views.v_employees_directory, using employees_directory_chatbot_reader
    (M4.3) -- never trusts a client-claimed property_id for own_property
    access (decisions.md Keputusan #5). Returns None if employee_id not found."""
    rows = query_as_domain(
        "employees_directory",
        "SELECT property_id FROM chatbot_views.v_employees_directory WHERE employee_id = %s",
        (employee_id,),
    )
    return rows[0]["property_id"] if rows else None
