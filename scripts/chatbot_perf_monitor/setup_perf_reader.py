"""
Milestone 6.5 -- creates/rotates chatbot-perf-reader, the credential used to
read pg_stat_statements/pg_stat_activity (query performance, connection pool
usage) and chatbot_views (for EXPLAIN ANALYZE on representative queries) on
the SERVING project.

Grant pg_monitor (predefined Postgres role -- decisions.md Keputusan B: the
only way to read pg_stat_statements/pg_stat_activity without superuser, no
existing role in this project has it) + SELECT on ALL views in chatbot_views
schema (deliberately broader than the 10 domain-scoped *_chatbot_reader roles
from M4.3 -- this credential needs to run EXPLAIN ANALYZE across all 10
domains, precedent: analyst-readonly M3.6 spans 2 datasets for the same
cross-cutting reason).

Both chatbot_views (67 views) and pg_monitor grant authority are owned/held
by admin (postgres) directly -- verified empirically (chatbot_views schema
owner, and admin_option=true on pg_monitor membership) -- no owner-routing
needed, unlike M3.5/M4.4's mart_cleaned exception.

Usage: python setup_perf_reader.py
"""
import secrets

from connections import (
    build_serving_role_connection_string,
    get_serving_connection,
    write_env_var,
)
from verify_role_isolation import verify_role_isolation

ROLE = "chatbot_perf_reader"
ENV_VAR = "CHATBOT_PERF_READER_DB_URL"

ALLOW_CHECKS = [
    # pg_stat_statements is an extension-provided view living in Supabase's
    # "extensions" schema (NOT public/pg_catalog) -- discovered when the
    # first verify attempt failed "relation pg_stat_statements does not
    # exist" despite the extension being installed and pg_monitor granted;
    # admin's own search_path happens to include "extensions" so it never
    # needed the schema-qualified form. Always qualify it explicitly rather
    # than rely on a new role's search_path (which defaults to "$user", public).
    ("SELECT extensions.pg_stat_statements", "SELECT count(*) FROM extensions.pg_stat_statements"),
    ("SELECT pg_stat_activity", "SELECT count(*) FROM pg_stat_activity"),
    ("SELECT chatbot_views.v_properties_ref", "SELECT count(*) FROM chatbot_views.v_properties_ref"),
]
DENY_CHECKS = [
    ("SELECT mart_cleaned.payroll (HR, out of scope)", "SELECT count(*) FROM mart_cleaned.payroll"),
    ("SELECT mart_cleaned.role_permissions (out of scope)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
    ("SELECT analyst_views schema (out of scope)", "SELECT count(*) FROM analyst_views.v_revenue_daily"),
    ("INSERT into chatbot_views view (read-only)", "INSERT INTO chatbot_views.v_properties_ref (property_id) VALUES ('X')"),
    ("CREATE TABLE (no CREATE privilege)", "CREATE TABLE public._perf_reader_probe (id int)"),
]


def create_or_rotate_role(admin_conn, password):
    with admin_conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(f'ALTER ROLE "{ROLE}" WITH LOGIN PASSWORD %s', (password,))
            print(f"  Role {ROLE} already existed -- password rotated.")
        else:
            cur.execute(
                f'CREATE ROLE "{ROLE}" WITH LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE',
                (password,),
            )
            print(f"  Role {ROLE} created.")


def apply_grants(admin_conn):
    with admin_conn.cursor() as cur:
        cur.execute(f'GRANT pg_monitor TO "{ROLE}"')
        cur.execute(f'GRANT USAGE ON SCHEMA extensions TO "{ROLE}"')
        cur.execute(f'GRANT USAGE ON SCHEMA chatbot_views TO "{ROLE}"')
        cur.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA chatbot_views TO "{ROLE}"')
    print("  GRANT pg_monitor + USAGE on extensions + USAGE/SELECT on chatbot_views applied.")


def main():
    admin_conn = get_serving_connection(readonly=False)
    admin_conn.autocommit = True
    try:
        print(f"--- {ROLE} ---")
        password = secrets.token_urlsafe(24)

        create_or_rotate_role(admin_conn, password)
        apply_grants(admin_conn)

        conn_str = build_serving_role_connection_string(ROLE, password)
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
