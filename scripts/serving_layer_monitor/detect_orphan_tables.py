"""
Milestone 6.6 -- Output 2 (KK2): deteksi orphan table dari snapshot terbaru
(Keputusan C, decisions.md) -- sumber kebenaran tunggal `monitoring
.serving_storage_snapshot.is_orphan`, BUKAN kolom `old_table_status` di
`reverse_etl_sync_log` (yang cuma menangkap kejadian baru ke depan, tidak
retroaktif ke 73 orphan yang sudah ada sebelum instrumentasi ditambahkan).

1 alert per snapshot_date kalau ada orphan (bukan 1 per tabel -- daftar
tabel masuk ke detail text, supaya tidak banjir alert individual untuk
kejadian yang sama).

Usage: python detect_orphan_tables.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection


def find_orphans(conn, snapshot_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT schema_name, table_name, total_size_bytes
        FROM monitoring.serving_storage_snapshot
        WHERE snapshot_date = %s AND is_orphan = TRUE
        ORDER BY schema_name, table_name
        """,
        (snapshot_date,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def _insert_alert(cur, detail, snapshot_date, is_simulated):
    cur.execute(
        """
        INSERT INTO monitoring.alerts
            (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
        VALUES ('serving_layer', 'multiple', 'serving_swap_orphan_table', 'critical', %s, %s, %s)
        """,
        (detail, snapshot_date, is_simulated),
    )


def _latest_snapshot_date(conn):
    cur = conn.cursor()
    cur.execute("SELECT MAX(snapshot_date) FROM monitoring.serving_storage_snapshot")
    row = cur.fetchone()
    cur.close()
    return row[0]


def run(conn, snapshot_date=None, persist=True, is_simulated=False):
    # MAX(snapshot_date) from the table, NOT datetime.now().date() -- found
    # during Checkpoint 5 verification: a same-day re-snapshot after cleanup
    # merges into the SAME date bucket via ON CONFLICT, but rows for tables
    # that no longer exist (dropped orphans) are never removed by that
    # UPSERT, only rows for tables still present get refreshed. Querying by
    # calendar "today" found those stale pre-cleanup rows; querying by
    # MAX(snapshot_date) has the same practical effect in normal one-run-per-
    # day operation but doesn't silently assume "today" is what was captured
    # (same bug class as M6.3's UTC-vs-local date mismatch).
    snapshot_date = snapshot_date or _latest_snapshot_date(conn)
    cur = conn.cursor()
    orphans = find_orphans(conn, snapshot_date)

    alert_raised = None
    if orphans:
        total_size = sum(r[2] for r in orphans)
        names = [f"{schema}.{table}" for schema, table, _ in orphans]
        detail = (f"{len(orphans)} tabel orphan __old terdeteksi ({total_size/1024/1024:.1f}MB): "
                  + ", ".join(names[:15]) + (f" (+{len(names)-15} lainnya)" if len(names) > 15 else ""))
        if persist:
            _insert_alert(cur, detail, snapshot_date, is_simulated)
            conn.commit()
        alert_raised = ("critical", detail)

    cur.close()
    return {"orphans": orphans, "alert_raised": alert_raised}


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        outcome = run(conn, is_simulated=False)
        if outcome["alert_raised"]:
            severity, detail = outcome["alert_raised"]
            print(f"[{severity.upper()}] serving_swap_orphan_table: {detail}")
        else:
            print("[ok] tidak ada tabel orphan terdeteksi.")
    finally:
        conn.close()
