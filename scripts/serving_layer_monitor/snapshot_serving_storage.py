"""
Milestone 6.6 -- Output 1 (KK1): storage growth + table bloat/vacuum status,
murni dashboard/snapshot -- TIDAK ada alert (Keputusan D, decisions.md).
Snapshot SEMUA tabel mart_cleaned + mart_aggregated (termasuk __old orphan --
is_orphan dihitung di sini, jadi tabel ini jadi sumber kebenaran tunggal
untuk detect_orphan_tables.py, Keputusan C) via chatbot_perf_reader-style
scoped kredensial serving_storage_reader.

Usage: python snapshot_serving_storage.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection
from connections import _load_env
import psycopg2

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMAS = ("mart_cleaned", "mart_aggregated")


def get_storage_reader_connection():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    conn = psycopg2.connect(env["SERVING_STORAGE_READER_DB_URL"])
    conn.set_session(readonly=True, autocommit=True)
    return conn


def fetch_storage_stats(serving_conn):
    cur = serving_conn.cursor()
    cur.execute(
        """
        SELECT
            schemaname,
            relname,
            pg_total_relation_size(format('%%I.%%I', schemaname, relname)::regclass) AS total_size_bytes,
            n_live_tup,
            n_dead_tup,
            last_vacuum,
            last_autovacuum
        FROM pg_stat_user_tables
        WHERE schemaname = ANY(%s)
        """,
        (list(SCHEMAS),),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def upsert_snapshot(conn, snapshot_date, rows):
    cur = conn.cursor()
    for schema_name, table_name, total_size_bytes, live, dead, last_vacuum, last_autovacuum in rows:
        dead_pct = round(100.0 * dead / (live + dead), 2) if (live + dead) > 0 else None
        is_orphan = table_name.endswith("__old")
        cur.execute(
            """
            INSERT INTO monitoring.serving_storage_snapshot
                (schema_name, table_name, snapshot_date, total_size_bytes, live_row_count,
                 dead_row_count, dead_pct, last_vacuum, last_autovacuum, is_orphan)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (schema_name, table_name, snapshot_date)
            DO UPDATE SET total_size_bytes = EXCLUDED.total_size_bytes, live_row_count = EXCLUDED.live_row_count,
                           dead_row_count = EXCLUDED.dead_row_count, dead_pct = EXCLUDED.dead_pct,
                           last_vacuum = EXCLUDED.last_vacuum, last_autovacuum = EXCLUDED.last_autovacuum,
                           is_orphan = EXCLUDED.is_orphan, captured_at = now()
            """,
            (schema_name, table_name, snapshot_date, total_size_bytes, live, dead, dead_pct,
             last_vacuum, last_autovacuum, is_orphan),
        )
    conn.commit()
    cur.close()


def main():
    snapshot_date = datetime.datetime.now(datetime.timezone.utc).date()

    serving_conn = get_storage_reader_connection()
    try:
        rows = fetch_storage_stats(serving_conn)
    finally:
        serving_conn.close()

    conn = get_connection(readonly=False)
    try:
        upsert_snapshot(conn, snapshot_date, rows)
    finally:
        conn.close()

    total_size = sum(r[2] for r in rows)
    orphan_rows = [r for r in rows if r[1].endswith("__old")]
    orphan_size = sum(r[2] for r in orphan_rows)
    print(f"snapshot_date={snapshot_date}: {len(rows)} tabel tersimpan "
          f"({len(SCHEMAS)} schema), total_size={total_size/1024/1024:.1f}MB")
    print(f"  orphan (__old): {len(orphan_rows)} tabel, {orphan_size/1024/1024:.1f}MB")


if __name__ == "__main__":
    main()
