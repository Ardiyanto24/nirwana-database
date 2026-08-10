"""
Milestone 6.3 -- Output 4 (KK4): freshness ml_output.predictions. Query
MAX(scored_at) via BigQuery (kredensial warehouse-monitor-reader), hitung
lag_hours (formula direplikasi dari scripts/monitoring/snapshot_freshness.py,
Fase 1), upsert monitoring.ml_output_freshness_snapshot.

Usage: python snapshot_ml_output_freshness.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bq import PROJECT_ID, get_client
from db import get_connection


def fetch_latest_scored_at(client):
    query = f"SELECT MAX(scored_at) AS latest FROM `{PROJECT_ID}.ml_output.predictions`"
    rows = list(client.query(query).result())
    return rows[0]["latest"] if rows else None


def compute_lag_hours(latest_scored_at, reference_now):
    if latest_scored_at is None:
        return None
    latest_utc = latest_scored_at
    if latest_utc.tzinfo is None:
        latest_utc = latest_utc.replace(tzinfo=datetime.timezone.utc)
    return round((reference_now - latest_utc).total_seconds() / 3600, 1)


def upsert_snapshot(conn, snapshot_date, latest_scored_at, lag_hours):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO monitoring.ml_output_freshness_snapshot
            (snapshot_date, latest_scored_at, lag_hours)
        VALUES (%s, %s, %s)
        ON CONFLICT (snapshot_date)
        DO UPDATE SET latest_scored_at = EXCLUDED.latest_scored_at, lag_hours = EXCLUDED.lag_hours, created_at = now()
        """,
        (snapshot_date, latest_scored_at, lag_hours),
    )
    conn.commit()
    cur.close()


def main():
    client = get_client()
    reference_now = datetime.datetime.now(datetime.timezone.utc)
    snapshot_date = reference_now.date()

    latest_scored_at = fetch_latest_scored_at(client)
    lag_hours = compute_lag_hours(latest_scored_at, reference_now)

    conn = get_connection()
    try:
        upsert_snapshot(conn, snapshot_date, latest_scored_at, lag_hours)
    finally:
        conn.close()

    print(f"snapshot_date={snapshot_date} latest_scored_at={latest_scored_at} lag_hours={lag_hours}")


if __name__ == "__main__":
    main()
