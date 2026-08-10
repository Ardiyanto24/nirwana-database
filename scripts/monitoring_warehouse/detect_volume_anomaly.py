"""
Milestone 6.3 -- deteksi anomali volume BigQuery, replikasi PERSIS algoritma
scripts/monitoring/detect_alerts.py::evaluate_volume (Fase 1, M1.2) terhadap
monitoring.warehouse_volume_snapshot (bukan volume_daily_snapshot) -- lihat
decisions.md Keputusan #6. Rolling baseline per hari-dalam-minggu, WINDOW_WEEKS=8,
MIN_HISTORY_POINTS=3, sigma warning=2/critical=3.

Beda dari Fase 1: daftar tabel diambil dinamis dari isi warehouse_volume_snapshot
hari ini (Keputusan #5), bukan config statis -- otomatis mengikuti tabel apa pun
yang ada saat itu di 3 dataset.
"""
import statistics
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection

WINDOW_WEEKS = 8
MIN_HISTORY_POINTS = 3
VOLUME_WARNING_SIGMA = 2
VOLUME_CRITICAL_SIGMA = 3


def evaluate_volume(cur, dataset, table, snapshot_date):
    cur.execute(
        """
        SELECT row_count, day_of_week FROM monitoring.warehouse_volume_snapshot
        WHERE dataset_name=%s AND table_name=%s AND snapshot_date=%s;
        """,
        (dataset, table, snapshot_date),
    )
    row = cur.fetchone()
    if row is None:
        return None
    today_count, dow = row

    cur.execute(
        """
        SELECT row_count FROM monitoring.warehouse_volume_snapshot
        WHERE dataset_name=%s AND table_name=%s AND day_of_week=%s AND snapshot_date < %s
        ORDER BY snapshot_date DESC LIMIT %s;
        """,
        (dataset, table, dow, snapshot_date, WINDOW_WEEKS),
    )
    history = [r[0] for r in cur.fetchall()]

    if len(history) < MIN_HISTORY_POINTS:
        return {"status": "insufficient_history", "history_points": len(history)}

    mean = statistics.mean(history)
    stdev = statistics.pstdev(history) or 1e-9
    z = (today_count - mean) / stdev

    if abs(z) >= VOLUME_CRITICAL_SIGMA:
        severity = "critical"
    elif abs(z) >= VOLUME_WARNING_SIGMA:
        severity = "warning"
    else:
        severity = None

    return {
        "status": "evaluated",
        "today_count": today_count,
        "baseline_mean": round(mean, 1),
        "baseline_stdev": round(stdev, 1),
        "z_score": round(z, 2),
        "severity": severity,
    }


def _insert_alert(cur, dataset, table, severity, detail, snapshot_date, is_simulated):
    cur.execute(
        """
        INSERT INTO monitoring.alerts
            (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
        VALUES (%s, %s, 'warehouse_volume_anomaly', %s, %s, %s, %s);
        """,
        (dataset, table, severity, detail, snapshot_date, is_simulated),
    )


def run_for_table(conn, dataset, table, snapshot_date, is_simulated=False, persist=True):
    cur = conn.cursor()
    vol = evaluate_volume(cur, dataset, table, snapshot_date)
    alerts_raised = []
    if vol and vol.get("severity"):
        detail = (f"row_count={vol['today_count']} vs baseline mean={vol['baseline_mean']} "
                  f"stdev={vol['baseline_stdev']} (z={vol['z_score']})")
        if persist:
            _insert_alert(cur, dataset, table, vol["severity"], detail, snapshot_date, is_simulated)
        alerts_raised.append((vol["severity"], detail))
    if persist:
        conn.commit()
    cur.close()
    return {"dataset": dataset, "table": table, "volume": vol, "alerts_raised": alerts_raised}


def list_tables_for_date(conn, snapshot_date):
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT dataset_name, table_name FROM monitoring.warehouse_volume_snapshot WHERE snapshot_date=%s",
        (snapshot_date,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


if __name__ == "__main__":
    import datetime

    conn = get_connection(readonly=False)
    try:
        today = datetime.date.today()
        tables = list_tables_for_date(conn, today)
        for dataset, table in tables:
            result = run_for_table(conn, dataset, table, today, is_simulated=False)
            if result["alerts_raised"]:
                for sev, detail in result["alerts_raised"]:
                    print(f"[{sev.upper()}] {dataset}.{table} warehouse_volume_anomaly: {detail}")
            else:
                vstatus = result["volume"]["status"] if result["volume"] else "n/a"
                print(f"[ok] {dataset}.{table}: volume={vstatus}, no alert")
    finally:
        conn.close()
