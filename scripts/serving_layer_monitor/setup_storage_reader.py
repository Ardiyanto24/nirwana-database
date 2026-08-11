"""
Milestone 6.6 -- creates/rotates serving_storage_reader, the credential used
to read storage/vacuum health (pg_stat_user_tables, pg_total_relation_size)
for mart_cleaned + mart_aggregated on the SERVING project.

Grant pg_monitor (pg_stat_user_tables/pg_stat_activity -- though empirically
pg_stat_user_tables didn't strictly need it in the M6.6 research spike, kept
for consistency with chatbot_perf_reader's M6.5 pattern and pg_stat_activity
access) + USAGE on both schemas (REQUIRED for pg_total_relation_size() to
resolve a table name -- confirmed empirically during planning: denied with
"permission denied for schema" when tried without it). Deliberately NO
SELECT grant on any table -- this credential only reads catalog/stats
metadata (sizes, row counts, vacuum timestamps), never actual row data.

Usage: python setup_storage_reader.py
"""
import secrets

from connections import (
    build_serving_role_connection_string,
    get_serving_connection,
    write_env_var,
)
from verify_role_isolation import verify_role_isolation

ROLE = "serving_storage_reader"
ENV_VAR = "SERVING_STORAGE_READER_DB_URL"

ALLOW_CHECKS = [
    ("SELECT pg_stat_user_tables (mart_cleaned)",
     "SELECT count(*) FROM pg_stat_user_tables WHERE schemaname='mart_cleaned'"),
    ("SELECT pg_stat_user_tables (mart_aggregated)",
     "SELECT count(*) FROM pg_stat_user_tables WHERE schemaname='mart_aggregated'"),
    ("pg_total_relation_size on a real table",
     "SELECT pg_total_relation_size('mart_aggregated.dim_property'::regclass)"),
]
DENY_CHECKS = [
    ("SELECT mart_cleaned.payroll (row data, out of scope)", "SELECT count(*) FROM mart_cleaned.payroll"),
    ("SELECT mart_aggregated.dim_property (row data, out of scope)", "SELECT count(*) FROM mart_aggregated.dim_property"),
    ("SELECT analyst_views schema (out of scope)", "SELECT count(*) FROM analyst_views.v_revenue_daily"),
    ("INSERT into mart_aggregated table", "INSERT INTO mart_aggregated.dim_property (property_id) VALUES ('X')"),
    ("CREATE TABLE (no CREATE privilege)", "CREATE TABLE public._storage_reader_probe (id int)"),
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
        cur.execute(f'GRANT USAGE ON SCHEMA mart_cleaned TO "{ROLE}"')
        cur.execute(f'GRANT USAGE ON SCHEMA mart_aggregated TO "{ROLE}"')
    print("  GRANT pg_monitor + USAGE on mart_cleaned/mart_aggregated applied.")


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
