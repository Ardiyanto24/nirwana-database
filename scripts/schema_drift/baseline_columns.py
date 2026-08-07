"""
Milestone 1.4 - Task 1: ambil baseline "disetujui" awal dari information_schema.columns
untuk 23 tabel. HANYA dijalankan sekali di awal (atau dipanggil ulang eksplisit lewat
acknowledge.py saat drift disetujui) -- snapshot_and_diff.py TIDAK PERNAH menulis ke sini.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import get_connection  # noqa: E402

from tables_list import TABLES


def fetch_current_columns(cur, schema, table):
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
        """,
        (schema, table),
    )
    return cur.fetchall()


def take_baseline(conn, overwrite=False):
    cur = conn.cursor()
    if overwrite:
        cur.execute("DELETE FROM monitoring.schema_column_baseline;")

    total_columns = 0
    for schema, table in TABLES:
        columns = fetch_current_columns(cur, schema, table)
        for column_name, data_type, is_nullable, ordinal_position in columns:
            cur.execute(
                """
                INSERT INTO monitoring.schema_column_baseline
                    (schema_name, table_name, column_name, data_type, is_nullable, ordinal_position)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (schema_name, table_name, column_name)
                DO UPDATE SET data_type = EXCLUDED.data_type, is_nullable = EXCLUDED.is_nullable,
                              ordinal_position = EXCLUDED.ordinal_position, approved_at = now();
                """,
                (schema, table, column_name, data_type, is_nullable == "YES", ordinal_position),
            )
            total_columns += 1
    conn.commit()
    cur.close()
    return total_columns


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        total = take_baseline(conn, overwrite=True)
        print(f"Baseline diambil: {len(TABLES)} tabel, {total} kolom.")
    finally:
        conn.close()
