"""
Milestone 1.2 - Task 7: uji coba terkontrol.

Membuktikan logic alert (detect_alerts.py) bekerja benar, terpisah dari
kondisi data production yang memang stale (lihat decisions.md & logs.md).
Memakai entitas sintetis ("_simulation" schema) yang disisipkan langsung ke
tabel monitoring.* -- TIDAK menyentuh data production, dan alert yang
dihasilkan ditandai is_simulated=TRUE supaya tidak tercampur laporan nyata.

5 skenario:
  1. volume_normal_case      -> dalam band normal      -> EXPECT no alert
  2. volume_spike_case       -> lonjakan buatan         -> EXPECT critical alert
  3. volume_drop_case        -> penurunan buatan        -> EXPECT critical alert
  4. freshness_normal_case   -> lag di bawah threshold  -> EXPECT no alert
  5. freshness_delayed_case  -> lag di atas threshold   -> EXPECT critical alert
"""
import datetime
from db import get_connection
from detect_alerts import run_for_table

SIM_SCHEMA = "_simulation"
TEST_DATE = datetime.date(2026, 8, 3)  # Senin, dipilih tetap agar day_of_week konsisten
HISTORY_WEEKS = 8
NORMAL_BASELINE = 1000
NORMAL_NOISE = 20


def _seed_volume_history(cur, table, baseline, test_day_value):
    day_of_week = TEST_DATE.isoweekday() % 7
    # 8 minggu histori di hari yang sama (Senin-Senin), nilai stabil di sekitar baseline
    for i in range(1, HISTORY_WEEKS + 1):
        d = TEST_DATE - datetime.timedelta(weeks=i)
        value = baseline + (i % 3 - 1) * (NORMAL_NOISE // 2)  # variasi kecil, deterministik
        cur.execute(
            """
            INSERT INTO monitoring.volume_daily_snapshot
                (schema_name, table_name, snapshot_date, row_count, day_of_week)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (schema_name, table_name, snapshot_date) DO UPDATE SET row_count = EXCLUDED.row_count;
            """,
            (SIM_SCHEMA, table, d, value, day_of_week),
        )
    # hari yang diuji
    cur.execute(
        """
        INSERT INTO monitoring.volume_daily_snapshot
            (schema_name, table_name, snapshot_date, row_count, day_of_week)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (schema_name, table_name, snapshot_date) DO UPDATE SET row_count = EXCLUDED.row_count;
        """,
        (SIM_SCHEMA, table, TEST_DATE, test_day_value, day_of_week),
    )


def _seed_freshness(cur, table, lag_hours):
    latest_value = datetime.datetime.combine(TEST_DATE, datetime.time.min) - datetime.timedelta(hours=lag_hours)
    cur.execute(
        """
        INSERT INTO monitoring.freshness_snapshot
            (schema_name, table_name, snapshot_date, freshness_column, latest_value, lag_hours)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (schema_name, table_name, snapshot_date)
        DO UPDATE SET latest_value = EXCLUDED.latest_value, lag_hours = EXCLUDED.lag_hours;
        """,
        (SIM_SCHEMA, table, TEST_DATE, "simulated_event_time", latest_value, lag_hours),
    )


def run_simulation():
    conn = get_connection(readonly=False)
    cur = conn.cursor()

    # cleanup run sebelumnya (idempotent re-run)
    cur.execute("DELETE FROM monitoring.alerts WHERE schema_name = %s;", (SIM_SCHEMA,))
    cur.execute("DELETE FROM monitoring.volume_daily_snapshot WHERE schema_name = %s;", (SIM_SCHEMA,))
    cur.execute("DELETE FROM monitoring.freshness_snapshot WHERE schema_name = %s;", (SIM_SCHEMA,))
    conn.commit()

    _seed_volume_history(cur, "volume_normal_case", NORMAL_BASELINE, test_day_value=1005)
    _seed_volume_history(cur, "volume_spike_case", NORMAL_BASELINE, test_day_value=2500)
    _seed_volume_history(cur, "volume_drop_case", NORMAL_BASELINE, test_day_value=100)
    _seed_freshness(cur, "freshness_normal_case", lag_hours=10)
    _seed_freshness(cur, "freshness_delayed_case", lag_hours=150)
    conn.commit()

    scenarios = [
        ("volume_normal_case", None, "no_alert"),
        ("volume_spike_case", None, "critical"),
        ("volume_drop_case", None, "critical"),
        ("freshness_normal_case", "daily", "no_alert"),
        ("freshness_delayed_case", "daily", "critical"),
    ]

    print(f"=== Uji Coba Terkontrol Milestone 1.2 (Task 7) — test_date={TEST_DATE} ===\n")
    all_passed = True
    for table, cadence, expected in scenarios:
        result = run_for_table(conn, SIM_SCHEMA, table, TEST_DATE, cadence, is_simulated=True)
        got_severities = [sev for _, sev, _ in result["alerts_raised"]]
        if expected == "no_alert":
            passed = len(got_severities) == 0
        else:
            passed = expected in got_severities
        all_passed &= passed
        status = "PASS" if passed else "FAIL"
        detail = result["alerts_raised"] if result["alerts_raised"] else "(tidak ada alert terpicu)"
        print(f"[{status}] {table}: expected={expected} -> {detail}")

    cur.close()
    conn.close()
    print(f"\n=== Hasil akhir: {'SEMUA SKENARIO SESUAI EKSPEKTASI' if all_passed else 'ADA SKENARIO YANG TIDAK SESUAI'} ===")
    return all_passed


if __name__ == "__main__":
    ok = run_simulation()
    raise SystemExit(0 if ok else 1)
