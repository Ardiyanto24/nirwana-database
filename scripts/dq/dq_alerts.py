"""
Milestone 1.3 - Task 7: hubungkan 3 sumber deteksi ke monitoring.alerts.

  1. dq_test_failure       <- monitoring.dq_test_results (hasil hari ini, success=FALSE)
  2. dirty_proportion_drift <- snapshot_dirty_proportion.evaluate_drift
  3. value_anomaly          <- snapshot_value_anomaly.evaluate_outlier_drift
"""
import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import get_connection  # noqa: E402

from dirty_columns_config import DIRTY_COLUMNS
from value_anomaly_config import VALUE_COLUMNS
from snapshot_dirty_proportion import evaluate_drift
from snapshot_value_anomaly import evaluate_outlier_drift


def _insert_alert(cur, schema, table, alert_type, severity, detail, snapshot_date, is_simulated):
    cur.execute(
        """
        INSERT INTO monitoring.alerts
            (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        (schema, table, alert_type, severity, detail, snapshot_date, is_simulated),
    )


def detect_dq_failures(conn, run_date, is_simulated=False, persist=True):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT schema_name, table_name, expectation_type, expectation_detail, unexpected_count
        FROM monitoring.dq_test_results
        WHERE run_date = %s AND success = FALSE;
        """,
        (run_date,),
    )
    rows = cur.fetchall()
    raised = []
    for schema, table, etype, detail, unexpected_count in rows:
        severity = "critical" if (unexpected_count or 0) > 0 else "warning"
        msg = f"{etype} :: {detail} (unexpected={unexpected_count})"
        if persist:
            _insert_alert(cur, schema, table, "dq_test_failure", severity, msg, run_date, is_simulated)
        raised.append((schema, table, "dq_test_failure", severity, msg))
    if persist:
        conn.commit()
    cur.close()
    return raised


def detect_dirty_drift(conn, run_date, is_simulated=False, persist=True):
    cur = conn.cursor()
    raised = []
    for schema, table, column, predicate, bootstrap_pct, desc in DIRTY_COLUMNS:
        drift = evaluate_drift(cur, schema, table, column, run_date, bootstrap_pct)
        if drift and drift.get("severity"):
            msg = f"{column}: {drift}"
            if persist:
                _insert_alert(cur, schema, table, "dirty_proportion_drift", drift["severity"], msg, run_date, is_simulated)
            raised.append((schema, table, "dirty_proportion_drift", drift["severity"], msg))
    if persist:
        conn.commit()
    cur.close()
    return raised


def detect_value_anomalies(conn, run_date, is_simulated=False, persist=True):
    cur = conn.cursor()
    raised = []
    for schema, table, column, _filter in VALUE_COLUMNS:
        result = evaluate_outlier_drift(cur, schema, table, column, run_date)
        if result and result.get("severity"):
            msg = f"{column}: {result}"
            if persist:
                _insert_alert(cur, schema, table, "value_anomaly", result["severity"], msg, run_date, is_simulated)
            raised.append((schema, table, "value_anomaly", result["severity"], msg))
    if persist:
        conn.commit()
    cur.close()
    return raised


if __name__ == "__main__":
    conn = get_connection(readonly=False)
    try:
        today = datetime.date.today()
        all_raised = (
            detect_dq_failures(conn, today)
            + detect_dirty_drift(conn, today)
            + detect_value_anomalies(conn, today)
        )
        if not all_raised:
            print("Tidak ada alert baru.")
        for schema, table, atype, severity, msg in all_raised:
            print(f"[{severity.upper()}] {schema}.{table} {atype}: {msg}")
    finally:
        conn.close()
