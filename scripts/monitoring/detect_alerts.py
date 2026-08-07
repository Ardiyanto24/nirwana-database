"""
Milestone 1.2 - Task 6: logic alert.

Dua jenis deteksi, dua-duanya baca dari tabel monitoring.* (bukan query
langsung ke production), supaya bisa dipakai untuk data snapshot asli
MAUPUN snapshot buatan (uji coba terkontrol, Task 7) tanpa duplikasi logic.
"""
import statistics
from db import get_connection
from tables_config import FRESHNESS_THRESHOLDS_HOURS

WINDOW_WEEKS = 8
MIN_HISTORY_POINTS = 3
VOLUME_WARNING_SIGMA = 2
VOLUME_CRITICAL_SIGMA = 3


def evaluate_volume(cur, schema, table, snapshot_date):
    """Bandingkan row_count snapshot_date vs histori hari-yang-sama-dalam-minggu (rolling, WINDOW_WEEKS)."""
    cur.execute(
        """
        SELECT row_count, day_of_week FROM monitoring.volume_daily_snapshot
        WHERE schema_name=%s AND table_name=%s AND snapshot_date=%s;
        """,
        (schema, table, snapshot_date),
    )
    row = cur.fetchone()
    if row is None:
        return None
    today_count, dow = row

    cur.execute(
        """
        SELECT row_count FROM monitoring.volume_daily_snapshot
        WHERE schema_name=%s AND table_name=%s AND day_of_week=%s AND snapshot_date < %s
        ORDER BY snapshot_date DESC LIMIT %s;
        """,
        (schema, table, dow, snapshot_date, WINDOW_WEEKS),
    )
    history = [r[0] for r in cur.fetchall()]

    if len(history) < MIN_HISTORY_POINTS:
        return {"status": "insufficient_history", "history_points": len(history)}

    mean = statistics.mean(history)
    stdev = statistics.pstdev(history) or 1e-9  # hindari div-by-zero kalau histori identik
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


def evaluate_freshness(cur, schema, table, snapshot_date, cadence_class):
    if cadence_class is None:
        return None  # volume-only table, tidak dicek freshness

    cur.execute(
        """
        SELECT lag_hours FROM monitoring.freshness_snapshot
        WHERE schema_name=%s AND table_name=%s AND snapshot_date=%s;
        """,
        (schema, table, snapshot_date),
    )
    row = cur.fetchone()
    if row is None or row[0] is None:
        return None
    lag_hours = float(row[0])

    warning_h, critical_h = FRESHNESS_THRESHOLDS_HOURS[cadence_class]
    if lag_hours >= critical_h:
        severity = "critical"
    elif lag_hours >= warning_h:
        severity = "warning"
    else:
        severity = None

    return {"status": "evaluated", "lag_hours": lag_hours, "threshold_warning_h": warning_h,
            "threshold_critical_h": critical_h, "severity": severity}


def _insert_alert(cur, schema, table, alert_type, severity, detail, snapshot_date, is_simulated):
    cur.execute(
        """
        INSERT INTO monitoring.alerts
            (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        (schema, table, alert_type, severity, detail, snapshot_date, is_simulated),
    )


def run_for_table(conn, schema, table, snapshot_date, cadence_class, is_simulated=False, persist=True):
    """Evaluasi volume + freshness untuk satu tabel, opsional tulis alert ke monitoring.alerts."""
    cur = conn.cursor()
    outcome = {"schema": schema, "table": table, "volume": None, "freshness": None, "alerts_raised": []}

    vol = evaluate_volume(cur, schema, table, snapshot_date)
    outcome["volume"] = vol
    if vol and vol.get("severity"):
        detail = (f"row_count={vol['today_count']} vs baseline mean={vol['baseline_mean']} "
                  f"stdev={vol['baseline_stdev']} (z={vol['z_score']})")
        if persist:
            _insert_alert(cur, schema, table, "volume_anomaly", vol["severity"], detail, snapshot_date, is_simulated)
        outcome["alerts_raised"].append(("volume_anomaly", vol["severity"], detail))

    fresh = evaluate_freshness(cur, schema, table, snapshot_date, cadence_class)
    outcome["freshness"] = fresh
    if fresh and fresh.get("severity"):
        detail = (f"lag={fresh['lag_hours']}h (warning>={fresh['threshold_warning_h']}h, "
                  f"critical>={fresh['threshold_critical_h']}h)")
        if persist:
            _insert_alert(cur, schema, table, "freshness_delay", fresh["severity"], detail, snapshot_date, is_simulated)
        outcome["alerts_raised"].append(("freshness_delay", fresh["severity"], detail))

    if persist:
        conn.commit()
    cur.close()
    return outcome


if __name__ == "__main__":
    import datetime
    from tables_config import TABLES

    conn = get_connection(readonly=False)
    try:
        today = datetime.date.today()
        for schema, table, priority, freshness_col, col_type, cadence in TABLES:
            result = run_for_table(conn, schema, table, today, cadence, is_simulated=False)
            if result["alerts_raised"]:
                for atype, sev, detail in result["alerts_raised"]:
                    print(f"[{sev.upper()}] {schema}.{table} {atype}: {detail}")
            else:
                vstatus = result["volume"]["status"] if result["volume"] else "n/a"
                print(f"[ok] {schema}.{table}: volume={vstatus}, no alert")
    finally:
        conn.close()
