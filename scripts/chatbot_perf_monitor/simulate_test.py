"""
Milestone 6.5 -- uji coba terkontrol re-runnable, pola sama
scripts/monitoring_warehouse/simulate_test.py (M6.3/M6.4): seed data
sintetis bertanda jelas, jalankan detection logic PRODUCTION yang sama
persis, verifikasi alert sesuai ekspektasi, cleanup di AWAL run berikutnya
(bukan di akhir -- hasil run terakhir sengaja dibiarkan sebagai bukti kerja).

HANYA KK3 (connection pool spike) yang masuk di sini. KK1 (latency
percentile) dan KK2 (volume/denied trend) SENGAJA TIDAK -- keduanya butuh
data per-request NYATA dari traffic HTTP sungguhan (duration_ms tidak bisa
disintesis secara bermakna, beda dari angka koneksi yang murni agregat),
sudah dibuktikan terpisah dengan HTTP request nyata: Checkpoint 2 Task 6
(uvicorn lokal, 3 request) dan Checkpoint 4 Task 11 (burst 20 request
paralel) -- sama filosofi KK1 M6.3/KK2 M6.4.

monitoring.chatbot_connection_snapshot tidak punya kolom is_simulated (beda
dari monitoring.alerts/reverse_etl_sync_log) -- ditandai lewat snapshot_time
di tanggal jauh ke depan (2099-01-01, pola sama FAKE_FRESHNESS_DATE M6.3),
dibersihkan lewat range tanggal itu, bukan flag boolean.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection
from detect_connection_pool_spike import run as run_pool_spike_detection

SIM_MARKER_DATE = datetime.date(2099, 1, 1)


def _cleanup(cur):
    cur.execute(
        "DELETE FROM monitoring.chatbot_connection_snapshot WHERE snapshot_time::date = %s",
        (SIM_MARKER_DATE,),
    )
    cur.execute("DELETE FROM monitoring.alerts WHERE is_simulated = TRUE AND alert_type = 'chatbot_connection_pool_spike'")


def _seed_history_and_spike(cur):
    base_time = datetime.datetime(2099, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    for i, count in enumerate([1, 2, 1, 2, 1, 1, 2, 1]):  # 8 baseline points, low variance
        cur.execute(
            "INSERT INTO monitoring.chatbot_connection_snapshot (snapshot_time, active_connection_count) VALUES (%s, %s)",
            (base_time + datetime.timedelta(minutes=i), count),
        )
    spike_time = base_time + datetime.timedelta(minutes=100)
    cur.execute(
        "INSERT INTO monitoring.chatbot_connection_snapshot (snapshot_time, active_connection_count) "
        "VALUES (%s, %s) RETURNING id",
        (spike_time, 45),
    )
    return cur.fetchone()[0]


def run_simulation():
    conn = get_connection(readonly=False)
    cur = conn.cursor()
    _cleanup(cur)
    conn.commit()

    print("=== Uji Coba Terkontrol Milestone 6.5 ===\n")
    all_passed = True

    spike_id = _seed_history_and_spike(cur)
    conn.commit()

    outcome = run_pool_spike_detection(conn, as_of_id=spike_id, is_simulated=True)
    got = outcome["alert_raised"] is not None
    passed = got is True
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] chatbot_connection_pool_spike: expected_alert=True -> got={got}"
          + (f" ({outcome['alert_raised'][1]})" if outcome["alert_raised"] else ""))

    cur.close()
    conn.close()
    print(f"\n=== Hasil akhir: {'SEMUA SKENARIO SESUAI EKSPEKTASI' if all_passed else 'ADA SKENARIO YANG TIDAK SESUAI'} ===")
    return all_passed


if __name__ == "__main__":
    ok = run_simulation()
    raise SystemExit(0 if ok else 1)
