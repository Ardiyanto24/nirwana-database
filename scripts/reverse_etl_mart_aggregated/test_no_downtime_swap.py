"""
Milestone 5.5 -- controlled test proving RENAME-based swap doesn't cause
query failures against the live mart_aggregated table (Kriteria
Keberhasilan #2). Copy of scripts/reverse_etl/test_no_downtime_swap.py
(M2.4), adapted -- table dim_property (small, cheap to sync repeatedly).

Runs a tight polling loop (SELECT COUNT(*) against mart_aggregated.dim_property)
in a background thread while sync.py performs several back-to-back syncs
(each one a full fetch -> COPY -> gate -> RENAME swap) in the foreground.
Postgres RENAME takes a brief ACCESS EXCLUSIVE lock -- a concurrent SELECT
issued at that exact moment simply waits a few milliseconds for the lock,
it does not error. This test proves that empirically rather than asserting
it from Postgres locking theory alone.

Usage: python scripts/reverse_etl_mart_aggregated/test_no_downtime_swap.py
"""
import threading
import time

from connections import get_serving_connection, get_serving_writer_connection
from sync import get_reverse_etl_reader_client, sync_table

POLL_INTERVAL_SECONDS = 0.02
SYNC_CYCLES = 8

results = {"queries": 0, "errors": []}
stop_event = threading.Event()


def poll_loop():
    conn = get_serving_connection(readonly=True)
    try:
        while not stop_event.is_set():
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM mart_aggregated.dim_property")
                    cur.fetchone()
                results["queries"] += 1
            except Exception as e:  # noqa: BLE001 -- deliberately broad, this IS the check
                results["errors"].append(str(e))
            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        conn.close()


def main():
    poller = threading.Thread(target=poll_loop, daemon=True)
    poller.start()
    time.sleep(0.2)  # let a few queries land before swaps start

    bq_client = get_reverse_etl_reader_client()
    pg_conn = get_serving_writer_connection()
    try:
        for i in range(SYNC_CYCLES):
            sync_table(bq_client, pg_conn, "dim_property")
            print(f"  sync cycle {i + 1}/{SYNC_CYCLES} done")
    finally:
        pg_conn.close()

    time.sleep(0.2)  # let a few more queries land after the last swap
    stop_event.set()
    poller.join(timeout=5)

    print(f"\n{results['queries']} concurrent queries executed during {SYNC_CYCLES} swap cycles.")
    if results["errors"]:
        print(f"FAILED -- {len(results['errors'])} concurrent query error(s):")
        for err in results["errors"][:5]:
            print(f"  {err}")
        raise SystemExit(1)
    print("PASSED -- zero concurrent query errors during swap.")


if __name__ == "__main__":
    main()
