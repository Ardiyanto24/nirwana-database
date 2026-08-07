"""
Milestone 1.4 - Task 5: alur acknowledgment.

Menandai satu drift event sebagai direview (`status='acknowledged'`), dan MEMPERBARUI
baseline `approved` sesuai jenis drift-nya -- ini satu-satunya cara baseline berubah.
snapshot_and_diff.py tidak pernah menulis ke schema_column_baseline.
"""
import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import get_connection  # noqa: E402


def acknowledge_event(conn, event_id, note=None):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT schema_name, table_name, column_name, drift_type, status
        FROM monitoring.schema_drift_events WHERE id = %s;
        """,
        (event_id,),
    )
    row = cur.fetchone()
    if row is None:
        cur.close()
        raise ValueError(f"Drift event id={event_id} tidak ditemukan")
    schema, table, column, drift_type, status = row
    if status == "acknowledged":
        cur.close()
        return False  # sudah pernah di-acknowledge, no-op

    if drift_type == "column_added":
        cur.execute(
            """
            SELECT data_type, is_nullable, ordinal_position FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s AND column_name=%s;
            """,
            (schema, table, column),
        )
        col_info = cur.fetchone()
        if col_info:
            data_type, is_nullable, ordinal_position = col_info
            cur.execute(
                """
                INSERT INTO monitoring.schema_column_baseline
                    (schema_name, table_name, column_name, data_type, is_nullable, ordinal_position)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (schema_name, table_name, column_name)
                DO UPDATE SET data_type = EXCLUDED.data_type, is_nullable = EXCLUDED.is_nullable,
                              ordinal_position = EXCLUDED.ordinal_position, approved_at = now();
                """,
                (schema, table, column, data_type, is_nullable == "YES", ordinal_position),
            )
        # Kalau kolomnya sudah tidak ada lagi saat di-acknowledge (mis. ditambah lalu
        # dihapus lagi sebelum sempat direview), tidak perlu masuk baseline -- biarkan
        # drift_type column_removed berikutnya yang menangani kalau relevan.

    elif drift_type == "column_removed":
        cur.execute(
            """
            DELETE FROM monitoring.schema_column_baseline
            WHERE schema_name=%s AND table_name=%s AND column_name=%s;
            """,
            (schema, table, column),
        )

    elif drift_type == "type_changed":
        cur.execute(
            """
            SELECT data_type FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s AND column_name=%s;
            """,
            (schema, table, column),
        )
        col_info = cur.fetchone()
        if col_info:
            cur.execute(
                """
                UPDATE monitoring.schema_column_baseline SET data_type=%s, approved_at=now()
                WHERE schema_name=%s AND table_name=%s AND column_name=%s;
                """,
                (col_info[0], schema, table, column),
            )

    cur.execute(
        """
        UPDATE monitoring.schema_drift_events
        SET status='acknowledged', acknowledged_at=%s, acknowledged_note=%s
        WHERE id=%s;
        """,
        (datetime.datetime.now(datetime.timezone.utc), note, event_id),
    )
    conn.commit()
    cur.close()
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Acknowledge satu schema drift event")
    parser.add_argument("event_id", type=int)
    parser.add_argument("--note", default=None)
    args = parser.parse_args()

    conn = get_connection(readonly=False)
    try:
        ok = acknowledge_event(conn, args.event_id, note=args.note)
        print(f"Event {args.event_id} {'berhasil di-acknowledge' if ok else 'sudah acknowledged sebelumnya (no-op)'}.")
    finally:
        conn.close()
