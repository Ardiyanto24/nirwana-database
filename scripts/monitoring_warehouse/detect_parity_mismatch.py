"""
Milestone 6.3 -- Output 3 (KK3): row-count parity BigQuery vs PostgreSQL.
Murni konsolidasi -- monitoring.reverse_etl_sync_log (M2.4/M5.5) sudah punya
seluruh data yang dibutuhkan, 0 mekanisme snapshot baru (decisions.md
Keputusan #7). Script ini membaca baris `mismatch_aborted` TERBARU per tabel
dan mem-push ke monitoring.alerts. sync.py TIDAK disentuh.

Catatan implementasi (ditemukan saat Checkpoint 4 Task 11): query LANGSUNG ke
monitoring.reverse_etl_sync_log dengan filter is_simulated eksplisit sebagai
parameter -- BUKAN lewat view monitoring.warehouse_parity_status (yang
hardcode `WHERE is_simulated = FALSE` supaya aman dikonsumsi dashboard/M6.7
secara default). Kalau detector ini dipanggil lewat view, uji coba terkontrol
KK3 (baris mismatch sintetis) tidak akan pernah terlihat -- view sengaja
menyaringnya. `warehouse_parity_status` tetap jadi cara konsumsi yang benar
untuk pemakaian normal (dashboard), detector ini yang butuh akses langsung.

Usage: python detect_parity_mismatch.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection


def find_mismatches(conn, include_simulated=False):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT ON (dataset_name, table_name)
            dataset_name, table_name, bq_row_count, pg_row_count, status, synced_at
        FROM monitoring.reverse_etl_sync_log
        WHERE is_simulated = %s
        ORDER BY dataset_name, table_name, synced_at DESC;
        """,
        (include_simulated,),
    )
    rows = [r for r in cur.fetchall() if r[4] == "mismatch_aborted"]
    cur.close()
    return [(r[0], r[1], r[2], r[3], r[5]) for r in rows]


def _insert_alert(cur, dataset, table, detail, snapshot_date, is_simulated):
    cur.execute(
        """
        INSERT INTO monitoring.alerts
            (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
        VALUES (%s, %s, 'reverse_etl_mismatch', 'critical', %s, %s, %s);
        """,
        (dataset, table, detail, snapshot_date, is_simulated),
    )


def run(conn, persist=True, is_simulated=False):
    mismatches = find_mismatches(conn, include_simulated=is_simulated)
    cur = conn.cursor()
    alerts_raised = []
    today = datetime.date.today()
    for dataset, table, bq_count, pg_count, synced_at in mismatches:
        detail = f"bq_row_count={bq_count} vs pg_row_count={pg_count} (synced_at={synced_at})"
        if persist:
            _insert_alert(cur, dataset, table, detail, today, is_simulated)
        alerts_raised.append((dataset, table, detail))
    if persist:
        conn.commit()
    cur.close()
    return alerts_raised


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        raised = run(conn, is_simulated=False)
        if raised:
            for dataset, table, detail in raised:
                print(f"[CRITICAL] {dataset}.{table} reverse_etl_mismatch: {detail}")
        else:
            print("[ok] no row-count mismatches found in monitoring.warehouse_parity_status")
    finally:
        conn.close()
