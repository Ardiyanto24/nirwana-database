"""Apply schema.sql to Supabase. Additive DDL only (CREATE SCHEMA/TABLE/INDEX/VIEW IF NOT EXISTS / OR REPLACE)."""
import os
from db import get_connection

if __name__ == "__main__":
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        ddl = f.read()

    conn = get_connection(readonly=False)
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
