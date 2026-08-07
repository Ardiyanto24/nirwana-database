"""
Milestone 1.4 - Task 4: snapshot skema terkini, diff terhadap baseline `approved`
(monitoring.schema_column_baseline), tulis drift event baru ke monitoring.schema_drift_events.

Idempotent: kalau drift yang sama sudah tercatat `pending` dari run sebelumnya, TIDAK
membuat duplikat -- baseline approved yang jadi acuan (bukan snapshot sebelumnya), jadi
drift yang belum di-acknowledge akan terus terdeteksi tapi tidak digandakan.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import get_connection  # noqa: E402

from tables_list import TABLES
from sensitive_keywords import classify_severity
from baseline_columns import fetch_current_columns


def _fetch_baseline(cur, schema, table):
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable FROM monitoring.schema_column_baseline
        WHERE schema_name = %s AND table_name = %s;
        """,
        (schema, table),
    )
    return {row[0]: {"data_type": row[1], "is_nullable": row[2]} for row in cur.fetchall()}


def _has_pending_event(cur, schema, table, column, drift_type):
    cur.execute(
        """
        SELECT 1 FROM monitoring.schema_drift_events
        WHERE schema_name=%s AND table_name=%s AND column_name=%s AND drift_type=%s AND status='pending';
        """,
        (schema, table, column, drift_type),
    )
    return cur.fetchone() is not None


def _insert_event(cur, schema, table, column, drift_type, detail, severity):
    cur.execute(
        """
        INSERT INTO monitoring.schema_drift_events
            (schema_name, table_name, column_name, drift_type, detail, severity)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (schema, table, column, drift_type, detail, severity),
    )


def run_diff(conn, tables=None):
    tables = tables if tables is not None else TABLES
    cur = conn.cursor()
    new_events = []

    for schema, table in tables:
        baseline = _fetch_baseline(cur, schema, table)
        current_rows = fetch_current_columns(cur, schema, table)
        current = {row[0]: {"data_type": row[1], "is_nullable": row[2] == "YES"} for row in current_rows}

        # Kolom baru
        for column in current.keys() - baseline.keys():
            if _has_pending_event(cur, schema, table, column, "column_added"):
                continue
            severity = classify_severity(column)
            detail = f"Kolom baru: {column} ({current[column]['data_type']})"
            _insert_event(cur, schema, table, column, "column_added", detail, severity)
            new_events.append((schema, table, column, "column_added", severity))

        # Kolom hilang
        for column in baseline.keys() - current.keys():
            if _has_pending_event(cur, schema, table, column, "column_removed"):
                continue
            detail = f"Kolom hilang: {column} (sebelumnya {baseline[column]['data_type']})"
            _insert_event(cur, schema, table, column, "column_removed", detail, "normal")
            new_events.append((schema, table, column, "column_removed", "normal"))

        # Tipe data berubah
        for column in current.keys() & baseline.keys():
            if current[column]["data_type"] != baseline[column]["data_type"]:
                if _has_pending_event(cur, schema, table, column, "type_changed"):
                    continue
                detail = f"Tipe berubah: {column} {baseline[column]['data_type']} -> {current[column]['data_type']}"
                _insert_event(cur, schema, table, column, "type_changed", detail, "normal")
                new_events.append((schema, table, column, "type_changed", "normal"))

    conn.commit()
    cur.close()
    return new_events


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        events = run_diff(conn)
        if not events:
            print("Tidak ada drift baru terdeteksi (23 tabel production).")
        for schema, table, column, drift_type, severity in events:
            print(f"[{severity.upper()}] {schema}.{table}.{column}: {drift_type}")
    finally:
        conn.close()
