"""
Milestone 6.6 -- Output 2 (KK2): deteksi swap yang berjalan lambat, rolling-
baseline SAMA algoritma sensor duration anomaly M6.3
(scripts/monitoring_warehouse/detect_ml_output_issues.py::evaluate_sensor_duration)
-- TANPA filter day-of-week (Keputusan E, decisions.md): durasi swap tidak
punya pola mingguan berarti, sama alasan durasi sensor M6.3 dan connection
pool M6.5.

Baseline dihitung PER (dataset_name, table_name) -- durasi swap wajar
berbeda jauh antar tabel (tabel besar vs kecil), membandingkan lintas tabel
akan salah kaprah.

Usage: python detect_swap_duration_anomaly.py --table employees --dataset mart_cleaned
"""
import argparse
import datetime
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection

WINDOW = 8
MIN_HISTORY_POINTS = 3
WARNING_SIGMA = 2
CRITICAL_SIGMA = 3


def evaluate(cur, dataset_name, table_name, as_of_id=None):
    if as_of_id is not None:
        cur.execute(
            "SELECT swap_duration_ms, synced_at FROM monitoring.reverse_etl_sync_log WHERE id=%s",
            (as_of_id,),
        )
    else:
        cur.execute(
            """
            SELECT swap_duration_ms, synced_at FROM monitoring.reverse_etl_sync_log
            WHERE dataset_name=%s AND table_name=%s AND swap_duration_ms IS NOT NULL
            ORDER BY synced_at DESC LIMIT 1
            """,
            (dataset_name, table_name),
        )
    row = cur.fetchone()
    if row is None or row[0] is None:
        return None
    latest_duration, latest_time = row

    if as_of_id is not None:
        cur.execute(
            """
            SELECT swap_duration_ms FROM monitoring.reverse_etl_sync_log
            WHERE dataset_name=%s AND table_name=%s AND id != %s AND swap_duration_ms IS NOT NULL
            ORDER BY synced_at DESC LIMIT %s
            """,
            (dataset_name, table_name, as_of_id, WINDOW),
        )
    else:
        cur.execute(
            """
            SELECT swap_duration_ms FROM monitoring.reverse_etl_sync_log
            WHERE dataset_name=%s AND table_name=%s AND swap_duration_ms IS NOT NULL
            ORDER BY synced_at DESC OFFSET 1 LIMIT %s
            """,
            (dataset_name, table_name, WINDOW),
        )
    history = [float(r[0]) for r in cur.fetchall()]

    if len(history) < MIN_HISTORY_POINTS:
        return {"status": "insufficient_history", "history_points": len(history), "latest_duration_ms": float(latest_duration)}

    mean = statistics.mean(history)
    stdev = statistics.pstdev(history) or 1e-9
    z = (float(latest_duration) - mean) / stdev

    if abs(z) >= CRITICAL_SIGMA:
        severity = "critical"
    elif abs(z) >= WARNING_SIGMA:
        severity = "warning"
    else:
        severity = None

    return {
        "status": "evaluated",
        "latest_duration_ms": float(latest_duration),
        "baseline_mean": round(mean, 1),
        "baseline_stdev": round(stdev, 1),
        "z_score": round(z, 2),
        "severity": severity,
    }


def _insert_alert(cur, dataset_name, table_name, detail, severity, snapshot_date, is_simulated):
    cur.execute(
        """
        INSERT INTO monitoring.alerts
            (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
        VALUES (%s, %s, 'serving_swap_slow', %s, %s, %s, %s)
        """,
        (dataset_name, table_name, severity, detail, snapshot_date, is_simulated),
    )


def run(conn, dataset_name, table_name, as_of_id=None, persist=True, is_simulated=False):
    cur = conn.cursor()
    result = evaluate(cur, dataset_name, table_name, as_of_id=as_of_id)

    alert_raised = None
    if result and result.get("severity"):
        detail = (f"swap {dataset_name}.{table_name} duration={result['latest_duration_ms']}ms vs baseline "
                  f"mean={result['baseline_mean']}ms stdev={result['baseline_stdev']} (z={result['z_score']})")
        snapshot_date = datetime.datetime.now(datetime.timezone.utc).date()
        if persist:
            _insert_alert(cur, dataset_name, table_name, detail, result["severity"], snapshot_date, is_simulated)
            conn.commit()
        alert_raised = (result["severity"], detail)

    cur.close()
    return {"result": result, "alert_raised": alert_raised}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", required=True)
    parser.add_argument("--dataset", required=True, choices=["mart_cleaned", "mart_aggregated"])
    args = parser.parse_args()

    conn = get_connection(readonly=False)
    try:
        outcome = run(conn, args.dataset, args.table, is_simulated=False)
        if outcome["alert_raised"]:
            severity, detail = outcome["alert_raised"]
            print(f"[{severity.upper()}] serving_swap_slow: {detail}")
        else:
            print(f"[ok] {outcome['result']}")
    finally:
        conn.close()
