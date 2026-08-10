"""
Milestone 6.3 -- snapshot row-count harian BigQuery untuk 3 dataset
(raw_production, mart_cleaned, mart_aggregated -- staging sengaja dikecualikan,
lihat decisions.md Keputusan #3). Tulis ke monitoring.warehouse_volume_snapshot.

Row count diambil dari `__TABLES__` (legacy metadata pseudo-table), BUKAN
INFORMATION_SCHEMA.TABLE_STORAGE -- yang terakhir Access Denied di project ini
(kemungkinan restriksi BigQuery Sandbox mode, lihat decisions.md Keputusan #4
untuk detail). __TABLES__ tetap 1 query per dataset (bukan per tabel), row
count terverifikasi akurat terhadap angka yang sudah dikonfirmasi M1.1.

Usage: python snapshot_warehouse_volume.py [--dataset raw_production ...]
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bq import PROJECT_ID, get_client
from db import get_connection

DATASETS = ["raw_production", "mart_cleaned", "mart_aggregated"]


def fetch_row_counts(client, dataset):
    query = f"SELECT table_id, row_count FROM `{PROJECT_ID}.{dataset}.__TABLES__`"
    return [(row["table_id"], row["row_count"]) for row in client.query(query).result()]


def upsert_snapshot(conn, dataset, table_id, row_count, snapshot_date, day_of_week):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO monitoring.warehouse_volume_snapshot
            (dataset_name, table_name, snapshot_date, row_count, day_of_week)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (dataset_name, table_name, snapshot_date)
        DO UPDATE SET row_count = EXCLUDED.row_count, created_at = now()
        """,
        (dataset, table_id, snapshot_date, row_count, day_of_week),
    )
    cur.close()


def main(datasets):
    client = get_client()
    conn = get_connection()
    snapshot_date = datetime.date.today()
    day_of_week = snapshot_date.isoweekday() % 7  # Postgres EXTRACT(DOW): 0=Sunday..6=Saturday

    total = 0
    try:
        for dataset in datasets:
            rows = fetch_row_counts(client, dataset)
            for table_id, row_count in rows:
                upsert_snapshot(conn, dataset, table_id, row_count, snapshot_date, day_of_week)
                total += 1
            conn.commit()
            print(f"{dataset}: {len(rows)} table(s) snapshotted.")
    finally:
        conn.close()

    print(f"Total: {total} table snapshot(s) written for {snapshot_date}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", action="append", dest="datasets", choices=DATASETS)
    args = parser.parse_args()
    main(args.datasets or DATASETS)
