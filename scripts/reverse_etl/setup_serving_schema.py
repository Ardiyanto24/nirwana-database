"""
Milestone 2.4 Task 1 -- create the mart_cleaned schema on the new serving
Supabase project and verify connectivity. Run once (idempotent, CREATE SCHEMA
IF NOT EXISTS) after SERVING_DB_URL is set in .env.

Usage: python scripts/reverse_etl/setup_serving_schema.py
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
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'mart_cleaned'"
            )
            row = cur.fetchone()
        if row:
            print("OK: schema 'mart_cleaned' exists on serving project.")
        else:
            print("FAILED: schema 'mart_cleaned' not found after CREATE SCHEMA.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
