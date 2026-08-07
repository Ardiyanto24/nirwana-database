"""
Milestone 1.3 - Task 8: uji coba terkontrol.

Membuktikan Kriteria Keberhasilan #2 (anomali buatan di luar pola dikenal berhasil
terdeteksi) dan #3 (proporsi dirty data yang dikenal TIDAK memicu false alert),
terisolasi di schema_name='_simulation' -- tidak menyentuh data production nyata.

7 skenario:
  1. dq_normal_case            -> hasil test PASS         -> EXPECT no alert
  2. dq_failure_case           -> hasil test FAIL          -> EXPECT alert
  3. dirty_normal_case         -> proporsi stabil di histori -> EXPECT no alert (KK#3)
  4. dirty_drift_case          -> proporsi melonjak drastis  -> EXPECT alert (KK#2)
  5. dirty_bootstrap_normal    -> histori <3 titik, dalam toleransi bootstrap -> EXPECT no alert (KK#3)
  6. value_anomaly_normal_case -> proporsi outlier stabil     -> EXPECT no alert
  7. value_anomaly_spike_case  -> proporsi outlier melonjak   -> EXPECT alert (KK#2)
"""
import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import get_connection  # noqa: E402

from snapshot_dirty_proportion import evaluate_drift
from snapshot_value_anomaly import evaluate_outlier_drift
from dq_alerts import detect_dq_failures, _insert_alert

SIM_SCHEMA = "_simulation"
TEST_DATE = datetime.date(2026, 8, 3)
HISTORY_DAYS = 8


def _cleanup(cur):
    for tbl in ("alerts", "dq_test_results", "dirty_proportion_snapshot", "value_anomaly_snapshot"):
        cur.execute(f"DELETE FROM monitoring.{tbl} WHERE schema_name = %s;", (SIM_SCHEMA,))


def _seed_dq_result(cur, table, success):
    cur.execute(
        """
        INSERT INTO monitoring.dq_test_results
            (schema_name, table_name, suite_name, expectation_type, expectation_detail,
             success, unexpected_count, run_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (SIM_SCHEMA, table, f"{SIM_SCHEMA}.{table}", "unexpected_rows_expectation", "synthetic_rule",
         success, 0 if success else 42, TEST_DATE),
    )


def _seed_dirty_history(cur, table, column, baseline_pct, test_day_pct):
    for i in range(1, HISTORY_DAYS + 1):
        d = TEST_DATE - datetime.timedelta(days=i)
        pct = baseline_pct + (i % 3 - 1) * 0.2
        cur.execute(
            """
            INSERT INTO monitoring.dirty_proportion_snapshot
                (schema_name, table_name, column_name, snapshot_date, total_rows, dirty_rows, dirty_pct)
            VALUES (%s, %s, %s, %s, 1000, %s, %s)
            ON CONFLICT (schema_name, table_name, column_name, snapshot_date) DO UPDATE SET dirty_pct = EXCLUDED.dirty_pct;
            """,
            (SIM_SCHEMA, table, column, d, int(pct * 10), pct),
        )
    cur.execute(
        """
        INSERT INTO monitoring.dirty_proportion_snapshot
            (schema_name, table_name, column_name, snapshot_date, total_rows, dirty_rows, dirty_pct)
        VALUES (%s, %s, %s, %s, 1000, %s, %s)
        ON CONFLICT (schema_name, table_name, column_name, snapshot_date) DO UPDATE SET dirty_pct = EXCLUDED.dirty_pct;
        """,
        (SIM_SCHEMA, table, column, TEST_DATE, int(test_day_pct * 10), test_day_pct),
    )


def _seed_value_anomaly_history(cur, table, column, baseline_outlier_pct, test_day_outlier_pct):
    row_count = 1000
    for i in range(1, HISTORY_DAYS + 1):
        d = TEST_DATE - datetime.timedelta(days=i)
        pct = baseline_outlier_pct + (i % 3 - 1) * 0.3
        outliers = int(row_count * pct / 100)
        cur.execute(
            """
            INSERT INTO monitoring.value_anomaly_snapshot
                (schema_name, table_name, column_name, snapshot_date, q1, median, q3, iqr,
                 lower_fence, upper_fence, outlier_count, row_count)
            VALUES (%s, %s, %s, %s, 100, 200, 300, 200, -200, 600, %s, %s)
            ON CONFLICT (schema_name, table_name, column_name, snapshot_date)
            DO UPDATE SET outlier_count = EXCLUDED.outlier_count, row_count = EXCLUDED.row_count;
            """,
            (SIM_SCHEMA, table, column, d, outliers, row_count),
        )
    test_outliers = int(row_count * test_day_outlier_pct / 100)
    cur.execute(
        """
        INSERT INTO monitoring.value_anomaly_snapshot
            (schema_name, table_name, column_name, snapshot_date, q1, median, q3, iqr,
             lower_fence, upper_fence, outlier_count, row_count)
        VALUES (%s, %s, %s, %s, 100, 200, 300, 200, -200, 600, %s, %s)
        ON CONFLICT (schema_name, table_name, column_name, snapshot_date)
        DO UPDATE SET outlier_count = EXCLUDED.outlier_count, row_count = EXCLUDED.row_count;
        """,
        (SIM_SCHEMA, table, column, TEST_DATE, test_outliers, row_count),
    )


def run_simulation():
    conn = get_connection(readonly=False)
    cur = conn.cursor()
    _cleanup(cur)
    conn.commit()

    _seed_dq_result(cur, "dq_normal_case", success=True)
    _seed_dq_result(cur, "dq_failure_case", success=False)
    _seed_dirty_history(cur, "dirty_normal_case", "col_a", baseline_pct=5.0, test_day_pct=5.1)
    _seed_dirty_history(cur, "dirty_drift_case", "col_a", baseline_pct=5.0, test_day_pct=45.0)
    _seed_value_anomaly_history(cur, "value_normal_case", "col_a", baseline_outlier_pct=3.0, test_day_outlier_pct=3.2)
    _seed_value_anomaly_history(cur, "value_spike_case", "col_a", baseline_outlier_pct=3.0, test_day_outlier_pct=40.0)
    conn.commit()

    # dirty_bootstrap_normal: hanya 1 titik histori (mode bootstrap), dalam toleransi
    cur.execute(
        """
        INSERT INTO monitoring.dirty_proportion_snapshot
            (schema_name, table_name, column_name, snapshot_date, total_rows, dirty_rows, dirty_pct)
        VALUES (%s, 'dirty_bootstrap_normal', 'col_a', %s, 1000, 40, 4.0)
        ON CONFLICT (schema_name, table_name, column_name, snapshot_date) DO UPDATE SET dirty_pct = EXCLUDED.dirty_pct;
        """,
        (SIM_SCHEMA, TEST_DATE),
    )
    conn.commit()

    print(f"=== Uji Coba Terkontrol Milestone 1.3 (Task 8) — test_date={TEST_DATE} ===\n")
    all_passed = True

    dq_alerts = detect_dq_failures(conn, TEST_DATE, is_simulated=True)
    dq_alert_tables = {t for _, t, *_ in dq_alerts}
    for table, expected_alert in [("dq_normal_case", False), ("dq_failure_case", True)]:
        got = table in dq_alert_tables
        passed = got == expected_alert
        all_passed &= passed
        print(f"[{'PASS' if passed else 'FAIL'}] {table}: expected_alert={expected_alert} -> got={got}")

    # detect_dirty_drift/detect_value_anomalies asli berjalan atas DIRTY_COLUMNS/VALUE_COLUMNS
    # (konfigurasi tabel production nyata) -- di sini panggil evaluate_drift/evaluate_outlier_drift
    # langsung dengan tabel `_simulation`, supaya tetap satu logic yang sama persis yang dipakai
    # jalur production, tanpa perlu memasukkan entitas sintetis ke rules_config production.
    for table, dummy_bootstrap, expected_alert in [
        ("dirty_normal_case", 5.0, False),
        ("dirty_drift_case", 5.0, True),
        ("dirty_bootstrap_normal", 4.0, False),
    ]:
        drift = evaluate_drift(cur, SIM_SCHEMA, table, "col_a", TEST_DATE, dummy_bootstrap)
        got = bool(drift and drift.get("severity"))
        if got:
            _insert_alert(cur, SIM_SCHEMA, table, "dirty_proportion_drift", drift["severity"], str(drift), TEST_DATE, True)
        passed = got == expected_alert
        all_passed &= passed
        print(f"[{'PASS' if passed else 'FAIL'}] {table}: expected_alert={expected_alert} -> got={got} ({drift})")
    conn.commit()

    for table, expected_alert in [("value_normal_case", False), ("value_spike_case", True)]:
        result = evaluate_outlier_drift(cur, SIM_SCHEMA, table, "col_a", TEST_DATE)
        got = bool(result and result.get("severity"))
        if got:
            _insert_alert(cur, SIM_SCHEMA, table, "value_anomaly", result["severity"], str(result), TEST_DATE, True)
        passed = got == expected_alert
        all_passed &= passed
        print(f"[{'PASS' if passed else 'FAIL'}] {table}: expected_alert={expected_alert} -> got={got} ({result})")
    conn.commit()

    cur.close()
    conn.close()
    print(f"\n=== Hasil akhir: {'SEMUA SKENARIO SESUAI EKSPEKTASI' if all_passed else 'ADA SKENARIO YANG TIDAK SESUAI'} ===")
    return all_passed


if __name__ == "__main__":
    ok = run_simulation()
    raise SystemExit(0 if ok else 1)
