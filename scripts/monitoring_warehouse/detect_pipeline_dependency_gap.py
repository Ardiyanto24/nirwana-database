"""
Milestone 6.7 -- Keputusan B: sinyal turunan untuk gap dependency Titik 1 -> 2
yang belum digate lewat workflow_run (docs/keputusan-tertunda.md, ditemukan
M6.1). Tidak menyentuh extract-production.yml/transform-mart-cleaned.yml --
murni observasional, memakai monitoring.pipeline_run_log (M6.2) yang sudah
ada. sync.py/workflow YAML TIDAK disentuh.

Logic: kalau Titik 2 punya run hari ini, tapi Titik 1 TIDAK punya run
status='success' hari ini yang selesai SEBELUM Titik 2 mulai -- berarti
transform jalan tanpa konfirmasi ekstraksi sukses duluan, alert
'pipeline_dependency_gap' (Titik 1, karena akar masalahnya ketiadaan
konfirmasi Titik 1, bukan Titik 2 itu sendiri).

Usage: python detect_pipeline_dependency_gap.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection

TITIK_2_WORKFLOW = "Transform Staging and Mart Cleaned"
TITIK_2_STEP_SUBSTRING = "build->test->swap gate ke mart_cleaned"


def _titik2_earliest_start_today(cur, snapshot_date, is_simulated):
    cur.execute(
        """
        SELECT MIN(started_at)
        FROM monitoring.pipeline_run_log
        WHERE titik_id = 2
          AND started_at::date = %s
          AND (%s = FALSE OR trigger_event = 'simulated')
          AND (%s = TRUE OR trigger_event != 'simulated');
        """,
        (snapshot_date, is_simulated, is_simulated),
    )
    return cur.fetchone()[0]


def _titik1_confirmed_success(cur, snapshot_date, before, is_simulated):
    cur.execute(
        """
        SELECT COUNT(*)
        FROM monitoring.pipeline_run_log
        WHERE titik_id = 1
          AND started_at::date = %s
          AND status = 'success'
          AND completed_at < %s
          AND (%s = FALSE OR trigger_event = 'simulated')
          AND (%s = TRUE OR trigger_event != 'simulated');
        """,
        (snapshot_date, before, is_simulated, is_simulated),
    )
    return cur.fetchone()[0] > 0


def _insert_alert(cur, detail, snapshot_date, is_simulated):
    cur.execute(
        """
        INSERT INTO monitoring.alerts
            (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
        VALUES ('raw_production', 'extract_cursor', 'pipeline_dependency_gap', 'critical', %s, %s, %s);
        """,
        (detail, snapshot_date, is_simulated),
    )


def run(conn, snapshot_date=None, persist=True, is_simulated=False):
    snapshot_date = snapshot_date or datetime.date.today()
    cur = conn.cursor()
    alerts_raised = []

    titik2_start = _titik2_earliest_start_today(cur, snapshot_date, is_simulated)
    if titik2_start is not None:
        confirmed = _titik1_confirmed_success(cur, snapshot_date, titik2_start, is_simulated)
        if not confirmed:
            detail = (
                f"Titik 2 ({TITIK_2_WORKFLOW}) mulai jalan {titik2_start} tanpa Titik 1 "
                f"(Extract Production to Raw Warehouse) punya run status='success' yang "
                f"selesai sebelum itu pada {snapshot_date} -- dependency Titik 1->2 belum "
                f"digate lewat workflow_run (docs/keputusan-tertunda.md)."
            )
            if persist:
                _insert_alert(cur, detail, snapshot_date, is_simulated)
            alerts_raised.append(detail)

    if persist:
        conn.commit()
    cur.close()
    return alerts_raised


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        raised = run(conn, is_simulated=False)
        if raised:
            for detail in raised:
                print(f"[CRITICAL] pipeline_dependency_gap: {detail}")
        else:
            print("[ok] Titik 2 tidak jalan hari ini tanpa konfirmasi Titik 1, atau Titik 2 belum jalan hari ini.")
    finally:
        conn.close()
