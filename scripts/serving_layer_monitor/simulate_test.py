"""
Milestone 6.6 -- uji coba terkontrol re-runnable, pola sama
scripts/monitoring_warehouse/simulate_test.py (M6.3/M6.4) dan
scripts/chatbot_perf_monitor/simulate_test.py (M6.5): seed data sintetis
bertanda jelas, jalankan detection logic PRODUCTION yang sama persis,
verifikasi alert sesuai ekspektasi, cleanup di AWAL run berikutnya.

BEDA dari M6.3-6.5: kedua mekanisme KK2 M6.6 (orphan detection, swap
duration anomaly) SAMA-SAMA murni deteksi SQL di atas tabel snapshot/log --
tidak butuh fault-injection nyata ke pipeline seperti KK1 M6.3/KK2 M6.4/KK1
M6.5 -- jadi KEDUANYA masuk di sini, meski keduanya JUGA sudah dibuktikan
terpisah dengan bukti nyata (73 orphan sungguhan, lock ACCESS EXCLUSIVE
sungguhan -- lihat logs.md Checkpoint 4/5). simulate_test.py di sini murni
untuk regresi ke depan, bukan pengganti bukti nyata itu.

Marker: schema_name/dataset_name/table_name '_simulation' (pola sama Fase 1)
+ snapshot_date/synced_at di 2099-01-01 (pola sama FAKE_FRESHNESS_DATE M6.3).
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection
from detect_orphan_tables import run as run_orphan_detection
from detect_swap_duration_anomaly import run as run_swap_duration_detection

SIM_MARKER_DATE = datetime.date(2099, 1, 1)
SIM_SCHEMA = "_simulation"
SIM_TABLE = "fake_table__old"
SIM_SWAP_TABLE = "fake_swap_table"


def _cleanup(cur):
    cur.execute("DELETE FROM monitoring.serving_storage_snapshot WHERE schema_name = %s", (SIM_SCHEMA,))
    cur.execute("DELETE FROM monitoring.reverse_etl_sync_log WHERE dataset_name = %s", (SIM_SCHEMA,))
    cur.execute(
        "DELETE FROM monitoring.alerts WHERE is_simulated = TRUE AND alert_type IN "
        "('serving_swap_orphan_table', 'serving_swap_slow')"
    )


def _seed_orphan_snapshot(cur):
    cur.execute(
        """
        INSERT INTO monitoring.serving_storage_snapshot
            (schema_name, table_name, snapshot_date, total_size_bytes, live_row_count,
             dead_row_count, dead_pct, is_orphan)
        VALUES (%s, %s, %s, 1048576, 100, 0, 0.0, TRUE)
        ON CONFLICT (schema_name, table_name, snapshot_date) DO NOTHING
        """,
        (SIM_SCHEMA, SIM_TABLE, SIM_MARKER_DATE),
    )


def _seed_swap_duration_history_and_spike(cur):
    base_time = datetime.datetime(2099, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    for i, duration in enumerate([800, 850, 790, 820, 810, 830, 795, 805]):  # 8 baseline points
        cur.execute(
            """
            INSERT INTO monitoring.reverse_etl_sync_log
                (table_name, bq_row_count, pg_row_count, status, dataset_name, swap_duration_ms, synced_at)
            VALUES (%s, 10, 10, 'synced', %s, %s, %s)
            """,
            (SIM_SWAP_TABLE, SIM_SCHEMA, duration, base_time + datetime.timedelta(minutes=i)),
        )
    spike_time = base_time + datetime.timedelta(minutes=100)
    cur.execute(
        """
        INSERT INTO monitoring.reverse_etl_sync_log
            (table_name, bq_row_count, pg_row_count, status, dataset_name, swap_duration_ms, synced_at)
        VALUES (%s, 10, 10, 'synced', %s, 25000, %s)
        RETURNING id
        """,
        (SIM_SWAP_TABLE, SIM_SCHEMA, spike_time),
    )
    return cur.fetchone()[0]


def run_simulation():
    conn = get_connection(readonly=False)
    cur = conn.cursor()
    _cleanup(cur)
    conn.commit()

    print("=== Uji Coba Terkontrol Milestone 6.6 ===\n")
    all_passed = True

    # --- Skenario 1: orphan table detection ---
    _seed_orphan_snapshot(cur)
    conn.commit()
    outcome = run_orphan_detection(conn, snapshot_date=SIM_MARKER_DATE, is_simulated=True)
    got = outcome["alert_raised"] is not None
    passed = got is True
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] serving_swap_orphan_table: expected_alert=True -> got={got}")

    # --- Skenario 2: swap duration anomaly ---
    spike_id = _seed_swap_duration_history_and_spike(cur)
    conn.commit()
    outcome = run_swap_duration_detection(conn, SIM_SCHEMA, SIM_SWAP_TABLE, as_of_id=spike_id, is_simulated=True)
    got = outcome["alert_raised"] is not None
    passed = got is True
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] serving_swap_slow: expected_alert=True -> got={got}"
          + (f" ({outcome['alert_raised'][1]})" if outcome["alert_raised"] else ""))

    cur.close()
    conn.close()
    print(f"\n=== Hasil akhir: {'SEMUA SKENARIO SESUAI EKSPEKTASI' if all_passed else 'ADA SKENARIO YANG TIDAK SESUAI'} ===")
    return all_passed


if __name__ == "__main__":
    ok = run_simulation()
    raise SystemExit(0 if ok else 1)
