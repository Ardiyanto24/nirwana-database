"""
Milestone 6.4 -- Output 1 (KK1): model staleness, INFORMATIONAL ONLY (tidak
ada alert -- decisions.md, model_version cuma 1 nilai statis di data mock,
tidak ada cadence retrain sungguhan untuk dikalibrasi jadi threshold).

Snapshot per (model_name, model_version): kapan pertama & terakhir muncul di
ml_output.predictions, berapa baris total. Diulang tiap hari job jalan --
upsert idempotent per (model_name, model_version, snapshot_date).

Usage: python snapshot_ml_model_version.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bq import PROJECT_ID, get_client
from db import get_connection


def fetch_model_versions(client):
    query = f"""
        SELECT
            model_name,
            model_version,
            MIN(scored_at) AS first_scored_at,
            MAX(scored_at) AS last_scored_at,
            COUNT(*) AS row_count_total
        FROM `{PROJECT_ID}.ml_output.predictions`
        GROUP BY model_name, model_version
    """
    return list(client.query(query).result())


def upsert_snapshot(conn, snapshot_date, row):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO monitoring.ml_model_version_snapshot
            (model_name, model_version, snapshot_date, first_scored_at, last_scored_at, row_count_total)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (model_name, model_version, snapshot_date)
        DO UPDATE SET first_scored_at = EXCLUDED.first_scored_at,
                       last_scored_at = EXCLUDED.last_scored_at,
                       row_count_total = EXCLUDED.row_count_total,
                       captured_at = now()
        """,
        (row["model_name"], row["model_version"], snapshot_date,
         row["first_scored_at"], row["last_scored_at"], row["row_count_total"]),
    )
    cur.close()


def main():
    client = get_client()
    snapshot_date = datetime.datetime.now(datetime.timezone.utc).date()

    rows = fetch_model_versions(client)

    conn = get_connection(readonly=False)
    try:
        for row in rows:
            upsert_snapshot(conn, snapshot_date, row)
        conn.commit()
    finally:
        conn.close()

    for row in rows:
        print(f"model_name={row['model_name']} model_version={row['model_version']} "
              f"first_scored_at={row['first_scored_at']} last_scored_at={row['last_scored_at']} "
              f"row_count_total={row['row_count_total']}")


if __name__ == "__main__":
    main()
