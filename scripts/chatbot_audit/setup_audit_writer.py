"""
Milestone 4.5 -- creates/rotates chatbot_audit_writer, the credential the
chatbot API (scripts/chatbot_api/audit.py) uses to write to
monitoring.chatbot_query_log in production Supabase.

Scoped tighter than any existing monitoring.* writer in this project: every
prior monitoring write (scripts/monitoring/db.py, scripts/reverse_etl/
connections.py) uses the raw admin SUPABASE_DB_URL directly. This one is
INSERT-only on exactly one table -- no SELECT, no other monitoring.* table,
no production table -- because the writer here is a live-traffic API, not an
internal batch job (decisions.md M4.5 Keputusan #2).

monitoring.chatbot_query_log is owned by admin (created via apply_schema.py,
same admin connection) -- no owner-routing needed, unlike M3.5/M4.4's
mart_cleaned exception.

Usage:
  python apply_schema.py   # once, before this
  python setup_audit_writer.py
"""
import secrets

from connections import (
    build_role_connection_string,
    get_production_connection,
    write_env_var,
)
from verify_role_isolation import verify_role_isolation

ROLE = "chatbot_audit_writer"
ENV_VAR = "CHATBOT_AUDIT_WRITER_DB_URL"

# Sentinel domain value for the isolation-check row -- deleted via admin_conn
# after verification (the role itself has no DELETE privilege, by design).
_CHECK_DOMAIN = "_isolation_check"

ALLOW_CHECKS = [
    (
        "INSERT into chatbot_query_log",
        f"INSERT INTO monitoring.chatbot_query_log (domain, status) VALUES ('{_CHECK_DOMAIN}', 'denied')",
    ),
]
DENY_CHECKS = [
    ("SELECT own table (chatbot_query_log)", "SELECT count(*) FROM monitoring.chatbot_query_log"),
    ("SELECT other monitoring table (alerts)", "SELECT count(*) FROM monitoring.alerts"),
    ("SELECT other monitoring table (reverse_etl_sync_log)", "SELECT count(*) FROM monitoring.reverse_etl_sync_log"),
    ("SELECT production table (corporate_master.role_permissions)", "SELECT count(*) FROM corporate_master.role_permissions"),
    ("UPDATE own table", f"UPDATE monitoring.chatbot_query_log SET status = 'success' WHERE domain = '{_CHECK_DOMAIN}'"),
    ("DELETE own table", f"DELETE FROM monitoring.chatbot_query_log WHERE domain = '{_CHECK_DOMAIN}'"),
]


def create_or_rotate_role(admin_conn, password):
    with admin_conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(f"ALTER ROLE {ROLE} WITH LOGIN PASSWORD %s", (password,))
            print(f"  Role {ROLE} already existed -- password rotated.")
        else:
            cur.execute(
                f"CREATE ROLE {ROLE} WITH LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE",
                (password,),
            )
            print(f"  Role {ROLE} created.")


def apply_grants(admin_conn):
    """GRANT INSERT on the table alone is NOT enough -- id is bigserial,
    backed by a sequence (chatbot_query_log_id_seq), and nextval() on it
    requires its own USAGE grant (a real Postgres gotcha, discovered when the
    first verify attempt failed with "permission denied for sequence" instead
    of the pooler-staleness error the retry loop was built for)."""
    with admin_conn.cursor() as cur:
        cur.execute(f"GRANT USAGE ON SCHEMA monitoring TO {ROLE}")
        cur.execute(f"GRANT INSERT ON monitoring.chatbot_query_log TO {ROLE}")
        cur.execute(f"GRANT USAGE ON SEQUENCE monitoring.chatbot_query_log_id_seq TO {ROLE}")
    print("  GRANT USAGE ON SCHEMA monitoring + GRANT INSERT ON chatbot_query_log + GRANT USAGE ON sequence applied.")


def cleanup_check_rows(admin_conn):
    """The role's own DENY:DELETE check (by design) can't remove the row its
    ALLOW:INSERT check created -- admin cleans it up afterward."""
    with admin_conn.cursor() as cur:
        cur.execute("DELETE FROM monitoring.chatbot_query_log WHERE domain = %s", (_CHECK_DOMAIN,))
    admin_conn.commit()


def main():
    admin_conn = get_production_connection(readonly=False)
    admin_conn.autocommit = True
    try:
        print(f"--- {ROLE} ---")
        password = secrets.token_urlsafe(24)

        create_or_rotate_role(admin_conn, password)
        apply_grants(admin_conn)

        ok = verify_role_isolation(ROLE, password, ALLOW_CHECKS, DENY_CHECKS)
        cleanup_check_rows(admin_conn)

        if not ok:
            print(f"  Isolation verification FAILED for {ROLE} -- .env NOT written.")
            raise SystemExit(1)

        write_env_var(ENV_VAR, build_role_connection_string(ROLE, password))
        print(f"  {ENV_VAR} written to .env.")
        print(f"\n{ROLE} set up and verified successfully.")
    finally:
        admin_conn.close()


if __name__ == "__main__":
    main()
