"""
Milestone 1.4 - Task 6: uji coba terkontrol.

Buat tabel staging terpisah di schema `_simulation` (BUKAN salah satu dari 23 tabel
production), jalankan ALTER TABLE beneran di tabel itu, buktikan:
  1. Kolom baru biasa -> terdeteksi, severity normal
  2. Kolom baru bernama sensitif -> terdeteksi, severity high
  3. Kolom dihapus -> terdeteksi
  4. Tipe data berubah -> terdeteksi
  5. Drift yang TIDAK di-acknowledge tetap 'pending' di run kedua (bukti model baseline
     tetap, bukan day-over-day yang bisa "lupa")
  6. Setelah di-acknowledge, drift itu tidak muncul lagi & baseline ter-update
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import get_connection  # noqa: E402

from baseline_columns import fetch_current_columns
from snapshot_and_diff import run_diff
from acknowledge import acknowledge_event

SIM_SCHEMA = "_simulation"
SIM_TABLE = "staging_table"


def _setup(cur):
    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{SIM_SCHEMA}";')
    cur.execute(f'DROP TABLE IF EXISTS "{SIM_SCHEMA}"."{SIM_TABLE}";')
    cur.execute(f"""
        CREATE TABLE "{SIM_SCHEMA}"."{SIM_TABLE}" (
            id INTEGER PRIMARY KEY,
            name TEXT,
            amount INTEGER
        );
    """)
    # bersihkan sisa baseline/drift event dari run sebelumnya (idempotent re-run)
    cur.execute(
        "DELETE FROM monitoring.schema_drift_events WHERE schema_name=%s AND table_name=%s;",
        (SIM_SCHEMA, SIM_TABLE),
    )
    cur.execute(
        "DELETE FROM monitoring.schema_column_baseline WHERE schema_name=%s AND table_name=%s;",
        (SIM_SCHEMA, SIM_TABLE),
    )


def _take_baseline_for_sim_table(cur):
    for column_name, data_type, is_nullable, ordinal_position in fetch_current_columns(cur, SIM_SCHEMA, SIM_TABLE):
        cur.execute(
            """
            INSERT INTO monitoring.schema_column_baseline
                (schema_name, table_name, column_name, data_type, is_nullable, ordinal_position)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (SIM_SCHEMA, SIM_TABLE, column_name, data_type, is_nullable == "YES", ordinal_position),
        )


def _apply_ddl_changes(cur):
    cur.execute(f'ALTER TABLE "{SIM_SCHEMA}"."{SIM_TABLE}" ADD COLUMN notes TEXT;')                 # normal
    cur.execute(f'ALTER TABLE "{SIM_SCHEMA}"."{SIM_TABLE}" ADD COLUMN password_hash TEXT;')          # sensitive
    cur.execute(f'ALTER TABLE "{SIM_SCHEMA}"."{SIM_TABLE}" DROP COLUMN name;')                       # removed
    cur.execute(f'ALTER TABLE "{SIM_SCHEMA}"."{SIM_TABLE}" ALTER COLUMN amount TYPE NUMERIC;')       # type changed


def _get_pending_events(cur):
    cur.execute(
        """
        SELECT id, column_name, drift_type, severity FROM monitoring.schema_drift_events
        WHERE schema_name=%s AND table_name=%s AND status='pending'
        ORDER BY column_name, drift_type;
        """,
        (SIM_SCHEMA, SIM_TABLE),
    )
    return cur.fetchall()


def run_simulation():
    conn = get_connection(readonly=False)
    cur = conn.cursor()
    all_passed = True

    print(f"=== Uji Coba Terkontrol Milestone 1.4 (Task 6) ===\n")

    print("Setup: buat tabel staging _simulation.staging_table, ambil baseline awal...")
    _setup(cur)
    conn.commit()
    _take_baseline_for_sim_table(cur)
    conn.commit()

    print("Terapkan 4 perubahan DDL (ADD normal, ADD sensitif, DROP, ALTER TYPE)...")
    _apply_ddl_changes(cur)
    conn.commit()

    print("\n--- Run diff #1 (setelah DDL, sebelum acknowledge) ---")
    run_diff(conn, tables=[(SIM_SCHEMA, SIM_TABLE)])
    events_run1 = _get_pending_events(cur)
    expected = {
        ("notes", "column_added", "normal"),
        ("password_hash", "column_added", "high"),
        ("name", "column_removed", "normal"),
        ("amount", "type_changed", "normal"),
    }
    got = {(col, dtype, sev) for _id, col, dtype, sev in events_run1}
    passed = got == expected
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] 4 drift terdeteksi dengan severity benar: {got}")

    print("\n--- Run diff #2 (tanpa acknowledge apa pun -- buktikan tidak 'lupa' & tidak duplikat) ---")
    run_diff(conn, tables=[(SIM_SCHEMA, SIM_TABLE)])
    events_run2 = _get_pending_events(cur)
    got2 = {(col, dtype, sev) for _id, col, dtype, sev in events_run2}
    passed = (got2 == expected) and (len(events_run2) == len(events_run1))
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] Masih 4 event pending yang sama (bukan 8 -- tidak duplikat, "
          f"bukan 0 -- tidak 'lupa'): {len(events_run2)} event")

    print("\n--- Acknowledge 1 event ('notes') ---")
    notes_event_id = next(eid for eid, col, dtype, sev in events_run1 if col == "notes")
    acknowledge_event(conn, notes_event_id, note="simulasi: kolom biasa, disetujui")
    events_after_ack = _get_pending_events(cur)
    got3 = {(col, dtype, sev) for _id, col, dtype, sev in events_after_ack}
    expected_after_ack = expected - {("notes", "column_added", "normal")}
    passed = got3 == expected_after_ack
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] 'notes' hilang dari pending, 3 sisanya tetap: {got3}")

    print("\n--- Run diff #3 (setelah acknowledge -- 'notes' tidak boleh muncul lagi sbg drift baru) ---")
    run_diff(conn, tables=[(SIM_SCHEMA, SIM_TABLE)])
    events_run3 = _get_pending_events(cur)
    got4 = {(col, dtype, sev) for _id, col, dtype, sev in events_run3}
    passed = got4 == expected_after_ack
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] 'notes' permanen tidak muncul lagi (baseline ter-update): {got4}")

    cur.close()
    conn.close()
    print(f"\n=== Hasil akhir: {'SEMUA SKENARIO SESUAI EKSPEKTASI' if all_passed else 'ADA SKENARIO YANG TIDAK SESUAI'} ===")
    return all_passed


if __name__ == "__main__":
    ok = run_simulation()
    raise SystemExit(0 if ok else 1)
