"""
Re-applies GRANT SELECT to downstream reader roles after every reverse ETL
swap (scripts/reverse_etl/sync.py). Sibling to reindex_analyze.py (M3.3) --
same root cause, different casualty: sync.py's RENAME-swap makes the "new"
live table a brand new physical object, so it inherits neither the old
table's indexes (M3.3's problem) nor its GRANTs (this script's problem). Any
role granted SELECT DIRECTLY on a mart_cleaned table -- not through
analyst_views/chatbot_views, which survive swaps fine because
CREATE OR REPLACE VIEW keeps the same view OID -- loses that grant on every
swap and stays broken until someone hits "permission denied" in production
and it gets noticed.

Found 2026-08-17: reported by the AI Chatbot team as chatbot_authz_reader
(M4.4) losing SELECT on mart_cleaned.role_permissions. Investigating the
mechanism (RENAME-swap replaces the table object; nothing in sync.py,
reindex_analyze.py, or reverse-etl-mart-cleaned.yml re-grants afterward)
showed the same root cause had already silently broken all 6 domain
data_analyst_reader roles' (M3.5) own row-level table -- verified empty via
information_schema.role_table_grants before this script existed.
property_gm_analyst_reader needs no entry here -- it holds no direct
grant_targets of its own, only membership in the 6 domain roles (M3.5
Keputusan #3), so Postgres resolves its access live via role inheritance
once the domain roles' grants are restored below.

REGRANTS is hand-maintained, derived once from each role's grant_targets/
GRANT_TARGETS at the time this script was written -- not auto-derived from
scripts/data_analyst_credentials/role_config_*.py or
scripts/chatbot_credentials/role_config_authz.py (would require importing
across scripts/* subfolders, the exact pattern this repo avoids -- see this
module's sibling connections.py docstring on the tables_config.py collision).
If a future milestone grants a new role directly on a mart_cleaned table,
add it here too, or it will silently break on the next sync.

Usage:
  python scripts/reverse_etl/regrant_downstream_readers.py --table bookings
  python scripts/reverse_etl/regrant_downstream_readers.py --all
"""
import argparse

from connections import get_serving_writer_connection

PG_SCHEMA = "mart_cleaned"

REGRANTS = {
    "role_permissions": ["chatbot_authz_reader"],
    "employee_performance": ["hr_analyst_reader"],
    "staff_shifts": ["hr_analyst_reader"],
    "bookings": ["revenue_analyst_reader"],
    "pricing_history": ["revenue_analyst_reader"],
    "fnb_transactions": ["fnb_analyst_reader"],
    "maintenance_tickets": ["facility_analyst_reader"],
    "event_bookings": ["spa_event_analyst_reader"],
    "financial_summary": ["corporate_financial_analyst_reader"],
    "payroll": ["corporate_financial_analyst_reader"],
}


def regrant_table(pg_conn, table):
    roles = REGRANTS.get(table, [])
    with pg_conn.cursor() as cur:
        for role in roles:
            cur.execute(f'GRANT SELECT ON {PG_SCHEMA}."{table}" TO {role}')
    pg_conn.commit()
    return {"table": table, "roles_granted": roles}


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--table", help="Re-grant a single table (no-op if it has no mapped reader)")
    group.add_argument("--all", action="store_true", help="Re-grant every table in REGRANTS")
    args = parser.parse_args()

    tables = list(REGRANTS.keys()) if args.all else [args.table]

    pg_conn = get_serving_writer_connection()
    try:
        for table in tables:
            result = regrant_table(pg_conn, table)
            if result["roles_granted"]:
                print(f"  {table}: GRANT SELECT re-applied to {result['roles_granted']}")
            else:
                print(f"  {table}: no downstream reader mapped -- skipped")
    finally:
        pg_conn.close()

    print(f"\n{len(tables)} table(s) processed.")


if __name__ == "__main__":
    main()
