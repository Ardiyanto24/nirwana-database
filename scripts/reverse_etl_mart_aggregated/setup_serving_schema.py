"""
Milestone 5.5 -- create the mart_aggregated schema on the (existing, M2.4)
serving Supabase project and verify connectivity. Run once (idempotent,
CREATE SCHEMA IF NOT EXISTS) after SERVING_DB_URL is already set in .env
(it will be -- M2.4 already needed it).

Usage: python scripts/reverse_etl_mart_aggregated/setup_serving_schema.py
"""
import os

from connections import get_serving_connection

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA_SQL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def main():
    conn = get_serving_connection()
    try:
        with open(SCHEMA_SQL, "r", encoding="utf-8") as f:
            ddl = f.read()
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'mart_aggregated'"
            )
            row = cur.fetchone()
        if row:
            print("OK: schema 'mart_aggregated' exists on serving project.")
        else:
            print("FAILED: schema 'mart_aggregated' not found after CREATE SCHEMA.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
