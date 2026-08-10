"""Milestone 4.5 -- apply schema.sql (monitoring.chatbot_query_log) to
production Supabase. Additive DDL only (CREATE TABLE/INDEX IF NOT EXISTS),
same pattern as scripts/monitoring/apply_schema.py."""
import os

from connections import get_production_connection

if __name__ == "__main__":
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        ddl = f.read()

    conn = get_production_connection(readonly=False)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute(ddl)
        conn.commit()
        print("Schema applied successfully.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
