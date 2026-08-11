"""
Milestone 6.5 -- Output 3 (KK3): deteksi lonjakan koneksi chatbot di
pg_stat_activity, rolling-baseline SAMA algoritma sensor duration anomaly
M6.3 (scripts/monitoring_warehouse/detect_ml_output_issues.py::evaluate_sensor_duration)
-- TANPA filter day-of-week (Keputusan F, decisions.md M6.5): jumlah koneksi
aktif tidak punya pola mingguan berarti, sama alasan durasi sensor M6.3.

Usage: python detect_connection_pool_spike.py
"""
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


def evaluate(cur, as_of_id=None):
    """Baseline dari WINDOW snapshot TERAKHIR (tanpa filter day-of-week),
    dibandingkan snapshot TERBARU (atau as_of_id kalau diberikan, dipakai
    uji coba terkontrol)."""
    if as_of_id is not None:
        cur.execute(
            "SELECT active_connection_count, snapshot_time FROM monitoring.chatbot_connection_snapshot WHERE id=%s",
            (as_of_id,),
        )
    else:
        cur.execute(
            "SELECT active_connection_count, snapshot_time FROM monitoring.chatbot_connection_snapshot "
            "ORDER BY snapshot_time DESC LIMIT 1"
        )
    row = cur.fetchone()
    if row is None:
        return None
    latest_count, latest_time = row

    if as_of_id is not None:
        cur.execute(
            """
            SELECT active_connection_count FROM monitoring.chatbot_connection_snapshot
            WHERE id != %s
            ORDER BY snapshot_time DESC LIMIT %s
            """,
            (as_of_id, WINDOW),
        )
    else:
        cur.execute(
            """
            SELECT active_connection_count FROM monitoring.chatbot_connection_snapshot
            ORDER BY snapshot_time DESC OFFSET 1 LIMIT %s
            """,
            (WINDOW,),
        )
    history = [r[0] for r in cur.fetchall()]

    if len(history) < MIN_HISTORY_POINTS:
        return {"status": "insufficient_history", "history_points": len(history), "latest_count": latest_count}

    mean = statistics.mean(history)
    stdev = statistics.pstdev(history) or 1e-9
    z = (latest_count - mean) / stdev

    if abs(z) >= CRITICAL_SIGMA:
        severity = "critical"
    elif abs(z) >= WARNING_SIGMA:
        severity = "warning"
    else:
        severity = None

    return {
        "status": "evaluated",
        "latest_count": latest_count,
        "latest_time": latest_time,
        "baseline_mean": round(mean, 1),
        "baseline_stdev": round(stdev, 1),
        "z_score": round(z, 2),
        "severity": severity,
    }


def _insert_alert(cur, detail, severity, snapshot_date, is_simulated):
    cur.execute(
        """
        INSERT INTO monitoring.alerts
            (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
        VALUES ('chatbot', 'connection_pool', 'chatbot_connection_pool_spike', %s, %s, %s, %s)
        """,
        (severity, detail, snapshot_date, is_simulated),
    )


def run(conn, as_of_id=None, persist=True, is_simulated=False):
    cur = conn.cursor()
    result = evaluate(cur, as_of_id=as_of_id)

    alert_raised = None
    if result and result.get("severity"):
        detail = (f"active_connection_count={result['latest_count']} vs baseline "
                  f"mean={result['baseline_mean']} stdev={result['baseline_stdev']} (z={result['z_score']})")
        snapshot_date = datetime.datetime.now(datetime.timezone.utc).date()
        if persist:
            _insert_alert(cur, detail, result["severity"], snapshot_date, is_simulated)
            conn.commit()
        alert_raised = (result["severity"], detail)

    cur.close()
    return {"result": result, "alert_raised": alert_raised}


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        outcome = run(conn, is_simulated=False)
        if outcome["alert_raised"]:
            severity, detail = outcome["alert_raised"]
            print(f"[{severity.upper()}] chatbot_connection_pool_spike: {detail}")
        else:
            print(f"[ok] {outcome['result']}")
    finally:
        conn.close()
