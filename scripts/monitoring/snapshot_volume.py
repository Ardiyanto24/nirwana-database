"""
Milestone 1.2 - Task 4: snapshot volume harian per tabel.

Untuk tiap tabel di TABLES, hitung COUNT(*) hari ini dan simpan ke
monitoring.volume_daily_snapshot (upsert per hari, aman dijalankan ulang).
"""
import datetime
from db import get_connection
from tables_config import TABLES


def snapshot_volume(conn, snapshot_date=None):
    snapshot_date = snapshot_date or datetime.date.today()
    day_of_week = snapshot_date.isoweekday() % 7  # Postgres EXTRACT(DOW): 0=Sunday
    cur = conn.cursor()
    results = []
    for schema, table, *_ in TABLES:
        cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}";')
        row_count = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO monitoring.volume_daily_snapshot
                (schema_name, table_name, snapshot_date, row_count, day_of_week)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (schema_name, table_name, snapshot_date)
            DO UPDATE SET row_count = EXCLUDED.row_count, created_at = now();
            """,
            (schema, table, snapshot_date, row_count, day_of_week),
        )
        results.append((schema, table, row_count))
    conn.commit()
    cur.close()
    return results


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        rows = snapshot_volume(conn)
        print(f"Snapshot volume untuk {len(rows)} tabel tersimpan.")
        for schema, table, count in rows:
            print(f"  {schema}.{table}: {count:,}")
    finally:
        conn.close()
