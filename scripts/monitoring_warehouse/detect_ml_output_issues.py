"""
Milestone 6.3 -- Output 4 (KK4): 2 sub-deteksi terkait ml_output.

(a) Freshness lag terhadap monitoring.ml_output_freshness_snapshot -- threshold
    direplikasi dari scripts/monitoring/tables_config.py::FRESHNESS_THRESHOLDS_HOURS
    kelas 'daily' (warning=48h, critical=96h) -- ml_output ditulis harian oleh
    mock_score.py, kadensi yang sama persis.

(b) Sensor duration anomaly terhadap monitoring.pipeline_run_log WHERE titik_id=5
    (M6.2) -- 0 instrumentasi baru ke wait_for_ml_output.py (decisions.md
    Keputusan #10). BEDA dari algoritma volume (Keputusan #6): TIDAK pakai
    filter same-day-of-week -- durasi sensor tidak punya pola mingguan yang
    berarti (beda dari volume bisnis), jadi baseline dihitung dari N run
    TERAKHIR apa pun harinya, bukan dibagi per hari-dalam-minggu. Konstanta
    lain (MIN_HISTORY_POINTS, sigma) tetap sama supaya konsisten.

Keduanya sengaja alert_type SAMA ('ml_output_freshness_delay') tapi detail
text berbeda -- supaya KK4 "bukan cuma kegagalan sensor" tetap eksplisit
kelihatan alasannya (freshness lag vs durasi sensor tidak wajar), bukan
disamakan begitu saja dengan kegagalan step biasa.
"""
import datetime
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection

FRESHNESS_WARNING_H = 48
FRESHNESS_CRITICAL_H = 96

SENSOR_WINDOW_RUNS = 8
SENSOR_MIN_HISTORY_POINTS = 3
SENSOR_WARNING_SIGMA = 2
SENSOR_CRITICAL_SIGMA = 3


def _insert_alert(cur, table_name, detail, severity, snapshot_date, is_simulated):
    cur.execute(
        """
        INSERT INTO monitoring.alerts
            (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
        VALUES ('ml_output', %s, 'ml_output_freshness_delay', %s, %s, %s, %s);
        """,
        (table_name, severity, detail, snapshot_date, is_simulated),
    )


def evaluate_freshness(cur, snapshot_date):
    cur.execute(
        "SELECT lag_hours FROM monitoring.ml_output_freshness_snapshot WHERE snapshot_date=%s",
        (snapshot_date,),
    )
    row = cur.fetchone()
    if row is None or row[0] is None:
        return None
    lag_hours = float(row[0])
    if lag_hours >= FRESHNESS_CRITICAL_H:
        severity = "critical"
    elif lag_hours >= FRESHNESS_WARNING_H:
        severity = "warning"
    else:
        severity = None
    return {"lag_hours": lag_hours, "severity": severity}


def evaluate_sensor_duration(cur, as_of_run_id=None):
    """Baseline dari SENSOR_WINDOW_RUNS run titik 5 terakhir (tanpa filter
    day-of-week -- lihat catatan modul), dibandingkan run TERBARU (atau
    as_of_run_id kalau diberikan, dipakai uji coba terkontrol)."""
    if as_of_run_id is not None:
        cur.execute(
            "SELECT duration_seconds FROM monitoring.pipeline_run_log WHERE titik_id=5 AND run_id=%s",
            (as_of_run_id,),
        )
    else:
        cur.execute(
            "SELECT duration_seconds FROM monitoring.pipeline_run_log WHERE titik_id=5 ORDER BY completed_at DESC LIMIT 1"
        )
    row = cur.fetchone()
    if row is None:
        return None
    latest_duration = row[0]

    if as_of_run_id is not None:
        cur.execute(
            """
            SELECT duration_seconds FROM monitoring.pipeline_run_log
            WHERE titik_id=5 AND run_id != %s
            ORDER BY completed_at DESC LIMIT %s
            """,
            (as_of_run_id, SENSOR_WINDOW_RUNS),
        )
    else:
        cur.execute(
            """
            SELECT duration_seconds FROM monitoring.pipeline_run_log
            WHERE titik_id=5
            ORDER BY completed_at DESC OFFSET 1 LIMIT %s
            """,
            (SENSOR_WINDOW_RUNS,),
        )
    history = [r[0] for r in cur.fetchall()]

    if len(history) < SENSOR_MIN_HISTORY_POINTS:
        return {"status": "insufficient_history", "history_points": len(history)}

    mean = statistics.mean(history)
    stdev = statistics.pstdev(history) or 1e-9
    z = (latest_duration - mean) / stdev

    if abs(z) >= SENSOR_CRITICAL_SIGMA:
        severity = "critical"
    elif abs(z) >= SENSOR_WARNING_SIGMA:
        severity = "warning"
    else:
        severity = None

    return {
        "status": "evaluated",
        "latest_duration_seconds": latest_duration,
        "baseline_mean": round(mean, 1),
        "baseline_stdev": round(stdev, 1),
        "z_score": round(z, 2),
        "severity": severity,
    }


def run(conn, snapshot_date=None, sensor_run_id=None, persist=True, is_simulated=False):
    # UTC, BUKAN datetime.date.today() (local/naive) -- harus konsisten dengan
    # snapshot_ml_output_freshness.py yang menulis snapshot_date berbasis UTC.
    # Ditemukan sebagai bug nyata saat testing lokal (timezone WIB, UTC+7):
    # date.today() lokal sudah maju ke hari berikutnya ~7 jam sebelum UTC,
    # bikin detector tidak pernah menemukan snapshot "hari ini" di jendela itu.
    snapshot_date = snapshot_date or datetime.datetime.now(datetime.timezone.utc).date()
    cur = conn.cursor()
    alerts_raised = []

    fresh = evaluate_freshness(cur, snapshot_date)
    if fresh and fresh.get("severity"):
        detail = f"ml_output.predictions lag={fresh['lag_hours']}h (warning>={FRESHNESS_WARNING_H}h, critical>={FRESHNESS_CRITICAL_H}h)"
        if persist:
            _insert_alert(cur, "predictions", detail, fresh["severity"], snapshot_date, is_simulated)
        alerts_raised.append(("freshness", fresh["severity"], detail))

    sensor = evaluate_sensor_duration(cur, as_of_run_id=sensor_run_id)
    if sensor and sensor.get("severity"):
        detail = (f"sensor wait_for_ml_output duration={sensor['latest_duration_seconds']}s vs baseline "
                  f"mean={sensor['baseline_mean']}s stdev={sensor['baseline_stdev']} (z={sensor['z_score']})")
        if persist:
            _insert_alert(cur, "sensor_titik5", detail, sensor["severity"], snapshot_date, is_simulated)
        alerts_raised.append(("sensor_duration", sensor["severity"], detail))

    if persist:
        conn.commit()
    cur.close()
    return {"freshness": fresh, "sensor": sensor, "alerts_raised": alerts_raised}


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        result = run(conn, is_simulated=False)
        if result["alerts_raised"]:
            for kind, sev, detail in result["alerts_raised"]:
                print(f"[{sev.upper()}] ml_output {kind}: {detail}")
        else:
            print(f"[ok] freshness={result['freshness']}, sensor={result['sensor']}")
    finally:
        conn.close()
