"""
Milestone 6.3 -- uji coba terkontrol, konsolidasi dari Checkpoint 3-5 (dijalankan
manual sekali saat implementasi, sekarang re-runnable) supaya regresi 3 mekanisme
deteksi bisa diuji ulang kapan saja tanpa mengulang manual. Pola sama
scripts/dq/simulate_test.py (Fase 1): seed data sintetis bertanda jelas,
jalankan detection logic PRODUCTION yang sama persis, verifikasi
alert/no-alert sesuai ekspektasi, cleanup dijalankan di AWAL run berikutnya
(bukan di akhir) -- hasil run terakhir sengaja dibiarkan sebagai bukti kerja.

KK1 (dbt test capture) TIDAK ada di sini -- itu butuh fault-injection nyata ke
model dbt (pola M2.3/M5.3), sudah dibuktikan terpisah Checkpoint 2 Task 6
(lihat logs.md), tidak bisa direplikasi lewat data snapshot sintetis karena
yang diuji adalah pipa capture-nya sendiri, bukan logic anomali di atasnya.

3 skenario (KK2, KK3, KK4 x2):
  1. warehouse_volume_anomaly -- 2 tabel beda dataset, outlier 10x -> EXPECT alert
  2. reverse_etl_mismatch     -- 1 baris sintetis mismatch_aborted -> EXPECT alert
  3. ml_output_freshness_delay (freshness)      -- lag jauh di atas threshold -> EXPECT alert
  4. ml_output_freshness_delay (sensor duration) -- durasi jauh di atas baseline -> EXPECT alert
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection
from detect_volume_anomaly import run_for_table as run_volume_detection
from detect_parity_mismatch import run as run_parity_detection
from detect_ml_output_issues import run as run_ml_output_detection

SIM_DATASET = "_simulation"
FAKE_FRESHNESS_DATE = datetime.date(2099, 1, 1)
FAKE_SENSOR_RUN_IDS = [999990001, 999990002, 999990003, 999990004]
FAKE_SENSOR_ANOMALOUS_RUN_ID = 999990099


def _cleanup(cur):
    cur.execute("DELETE FROM monitoring.warehouse_volume_snapshot WHERE dataset_name = %s", (SIM_DATASET,))
    cur.execute("DELETE FROM monitoring.reverse_etl_sync_log WHERE is_simulated = TRUE")
    cur.execute("DELETE FROM monitoring.ml_output_freshness_snapshot WHERE snapshot_date = %s", (FAKE_FRESHNESS_DATE,))
    cur.execute(
        "DELETE FROM monitoring.pipeline_run_log WHERE run_id = ANY(%s)",
        (FAKE_SENSOR_RUN_IDS + [FAKE_SENSOR_ANOMALOUS_RUN_ID],),
    )
    cur.execute("DELETE FROM monitoring.alerts WHERE is_simulated = TRUE")


def _seed_volume_history(cur, table, base_count, snapshot_date, dow):
    for weeks_back in (1, 2, 3):
        d = snapshot_date - datetime.timedelta(weeks=weeks_back)
        cur.execute(
            """
            INSERT INTO monitoring.warehouse_volume_snapshot (dataset_name, table_name, snapshot_date, row_count, day_of_week)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (dataset_name, table_name, snapshot_date) DO UPDATE SET row_count = EXCLUDED.row_count
            """,
            (SIM_DATASET, table, d, base_count, dow),
        )
    cur.execute(
        """
        INSERT INTO monitoring.warehouse_volume_snapshot (dataset_name, table_name, snapshot_date, row_count, day_of_week)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (dataset_name, table_name, snapshot_date) DO UPDATE SET row_count = EXCLUDED.row_count
        """,
        (SIM_DATASET, table, snapshot_date, base_count * 10, dow),
    )


def run_simulation():
    conn = get_connection(readonly=False)
    cur = conn.cursor()
    _cleanup(cur)
    conn.commit()

    print("=== Uji Coba Terkontrol Milestone 6.3 ===\n")
    all_passed = True
    today = datetime.date.today()
    dow = today.isoweekday() % 7

    # --- Skenario 1: warehouse_volume_anomaly, 2 tabel beda "dataset" (KK2) ---
    for table, base_count in [("sim_table_a", 755), ("sim_table_b", 3)]:
        _seed_volume_history(cur, table, base_count, today, dow)
    conn.commit()
    for table in ["sim_table_a", "sim_table_b"]:
        result = run_volume_detection(conn, SIM_DATASET, table, today, is_simulated=True)
        got = bool(result["alerts_raised"])
        passed = got is True
        all_passed &= passed
        print(f"[{'PASS' if passed else 'FAIL'}] warehouse_volume_anomaly {table}: expected_alert=True -> got={got}")

    # --- Skenario 2: reverse_etl_mismatch (KK3) ---
    cur.execute(
        """
        INSERT INTO monitoring.reverse_etl_sync_log
            (table_name, bq_row_count, pg_row_count, status, dataset_name, is_simulated)
        VALUES ('sim_mismatch_table', 1000, 990, 'mismatch_aborted', 'mart_cleaned', TRUE)
        """
    )
    conn.commit()
    raised = run_parity_detection(conn, is_simulated=True)
    got = bool(raised)
    passed = got is True
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] reverse_etl_mismatch: expected_alert=True -> got={got}")

    # --- Skenario 3: ml_output_freshness_delay, freshness lag (KK4a) ---
    cur.execute(
        """
        INSERT INTO monitoring.ml_output_freshness_snapshot (snapshot_date, latest_scored_at, lag_hours)
        VALUES (%s, %s, %s)
        ON CONFLICT (snapshot_date) DO UPDATE SET lag_hours = EXCLUDED.lag_hours
        """,
        (FAKE_FRESHNESS_DATE, datetime.datetime(2098, 12, 25, tzinfo=datetime.timezone.utc), 150.0),
    )
    conn.commit()
    result = run_ml_output_detection(conn, snapshot_date=FAKE_FRESHNESS_DATE, is_simulated=True)
    got = any(kind == "freshness" for kind, _, _ in result["alerts_raised"])
    passed = got is True
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] ml_output_freshness_delay (freshness): expected_alert=True -> got={got}")

    # --- Skenario 4: ml_output_freshness_delay, sensor duration (KK4b) ---
    base_time = datetime.datetime(2026, 8, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
    for i, rid in enumerate(FAKE_SENSOR_RUN_IDS):
        started = base_time + datetime.timedelta(days=i)
        cur.execute(
            """
            INSERT INTO monitoring.pipeline_run_log
                (titik_id, titik_label, workflow_name, run_id, step_name, granularity, status, started_at, completed_at, duration_seconds, trigger_event)
            VALUES (5, 'Sensor ml_output (SIM)', 'Transform Mart Aggregated', %s, 'sensor, tunggu ml_output.predictions', 'detailed', 'success', %s, %s, 120, 'simulated')
            """,
            (rid, started, started + datetime.timedelta(seconds=120)),
        )
    started = base_time + datetime.timedelta(days=5)
    cur.execute(
        """
        INSERT INTO monitoring.pipeline_run_log
            (titik_id, titik_label, workflow_name, run_id, step_name, granularity, status, started_at, completed_at, duration_seconds, trigger_event)
        VALUES (5, 'Sensor ml_output (SIM)', 'Transform Mart Aggregated', %s, 'sensor, tunggu ml_output.predictions', 'detailed', 'success', %s, %s, 3600, 'simulated')
        """,
        (FAKE_SENSOR_ANOMALOUS_RUN_ID, started, started + datetime.timedelta(seconds=3600)),
    )
    conn.commit()
    result = run_ml_output_detection(
        conn, snapshot_date=today, sensor_run_id=FAKE_SENSOR_ANOMALOUS_RUN_ID, is_simulated=True
    )
    got = any(kind == "sensor_duration" for kind, _, _ in result["alerts_raised"])
    passed = got is True
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] ml_output_freshness_delay (sensor duration): expected_alert=True -> got={got}")

    cur.close()
    conn.close()
    print(f"\n=== Hasil akhir: {'SEMUA SKENARIO SESUAI EKSPEKTASI' if all_passed else 'ADA SKENARIO YANG TIDAK SESUAI'} ===")
    return all_passed


if __name__ == "__main__":
    ok = run_simulation()
    raise SystemExit(0 if ok else 1)
