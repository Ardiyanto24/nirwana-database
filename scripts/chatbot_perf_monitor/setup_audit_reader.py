"""
Milestone 6.5 -- creates/rotates chatbot_audit_reader, the credential used to
read monitoring.chatbot_query_log (production Supabase) for latency
percentile / volume / denied-trend computation.

Anticipated by name since M4.5 (report.md: "kredensial baca terpisah
chatbot_audit_reader kemungkinan perlu dibuat M6.5 sendiri, karena
chatbot_audit_writer sengaja INSERT-only"). SELECT-only, exactly one table --
chatbot_audit_writer itself is NEVER touched/re-granted (decisions.md M4.5
Keputusan #2 explicitly scoped it INSERT-only, staying that way).

monitoring.chatbot_query_log is owned by admin (created via
scripts/chatbot_audit/apply_schema.py) -- no owner-routing needed.

Usage: python setup_audit_reader.py
"""
import secrets

from connections import (
    build_production_role_connection_string,
    get_production_connection,
    write_env_var,
)
from verify_role_isolation import verify_role_isolation

ROLE = "chatbot_audit_reader"
ENV_VAR = "CHATBOT_AUDIT_READER_DB_URL"

ALLOW_CHECKS = [
    ("SELECT chatbot_query_log", "SELECT count(*) FROM monitoring.chatbot_query_log"),
]
DENY_CHECKS = [
    ("SELECT other monitoring table (alerts)", "SELECT count(*) FROM monitoring.alerts"),
    ("SELECT other monitoring table (reverse_etl_sync_log)", "SELECT count(*) FROM monitoring.reverse_etl_sync_log"),
    ("SELECT production table (corporate_master.role_permissions)", "SELECT count(*) FROM corporate_master.role_permissions"),
    ("INSERT into chatbot_query_log (read-only)", "INSERT INTO monitoring.chatbot_query_log (domain, status) VALUES ('_probe', 'denied')"),
    ("UPDATE chatbot_query_log (read-only)", "UPDATE monitoring.chatbot_query_log SET status = 'success' WHERE false"),
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
    with admin_conn.cursor() as cur:
        cur.execute(f"GRANT USAGE ON SCHEMA monitoring TO {ROLE}")
        cur.execute(f"GRANT SELECT ON monitoring.chatbot_query_log TO {ROLE}")
    print("  GRANT USAGE ON SCHEMA monitoring + GRANT SELECT ON chatbot_query_log applied.")


def main():
    admin_conn = get_production_connection(readonly=False)
    admin_conn.autocommit = True
    try:
        print(f"--- {ROLE} ---")
        password = secrets.token_urlsafe(24)

        create_or_rotate_role(admin_conn, password)
        apply_grants(admin_conn)

        conn_str = build_production_role_connection_string(ROLE, password)
        ok = verify_role_isolation(conn_str, ALLOW_CHECKS, DENY_CHECKS)

        if not ok:
            print(f"  Isolation verification FAILED for {ROLE} -- .env NOT written.")
            raise SystemExit(1)

        write_env_var(ENV_VAR, conn_str)
        print(f"  {ENV_VAR} written to .env.")
        print(f"\n{ROLE} set up and verified successfully.")
    finally:
        admin_conn.close()


if __name__ == "__main__":
    main()
