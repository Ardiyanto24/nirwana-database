"""
Milestone 6.4 -- Output 2 (KK2): validasi kelengkapan ml_output.predictions
vs populasi entity mart_aggregated.fact_revenue_room_type_daily (BUKAN
mart_cleaned langsung -- decisions.md: entity_id ml_output cuma cocok dengan
room_type_id surrogate key mart_aggregated, bukan room_type string mentah di
mart_cleaned).

Populasi "diharapkan ter-score" = distinct (property_id, room_type_id) di
fact_revenue_room_type_daily pada period_date yang sama dengan
feature_snapshot_at TERBARU di ml_output.predictions. Populasi "sudah
ter-score" = distinct (property_id, room_type_id) di ml_output.predictions
pada feature_snapshot_at yang sama. Selisih = entity hilang, dicatat baris
per baris (bukan cuma angka) -- literal KK2 "teridentifikasi otomatis".

Satu-satunya dari 3 mekanisme M6.4 yang push ke monitoring.alerts -- "ada
entity hilang" adalah temuan biner berbasis evidence, bukan threshold
tebakan (beda dari staleness/drift, lihat decisions.md).

Usage: python check_ml_output_completeness.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bq import PROJECT_ID, get_client
from db import get_connection


def fetch_latest_feature_snapshot_at(client):
    query = f"SELECT MAX(feature_snapshot_at) AS latest FROM `{PROJECT_ID}.ml_output.predictions`"
    rows = list(client.query(query).result())
    return rows[0]["latest"] if rows else None


def fetch_expected_entities(client, feature_snapshot_at):
    query = f"""
        SELECT DISTINCT property_id, room_type_id
        FROM `{PROJECT_ID}.mart_aggregated.fact_revenue_room_type_daily`
        WHERE period_date = DATE(@feature_snapshot_at)
    """
    job_config = _query_config(feature_snapshot_at)
    rows = client.query(query, job_config=job_config).result()
    return {(r["property_id"], r["room_type_id"]) for r in rows}


def fetch_scored_entities(client, feature_snapshot_at):
    # ml_output.predictions tidak punya kolom property_id/room_type_id terpisah --
    # cuma entity_id komposit ("property_id:room_type_id"), sama pola split yang
    # dipakai warehouse/models/mart_aggregated/ml_feedback/fact_ml_occupancy_forecast_property_room_type.sql
    query = f"""
        SELECT DISTINCT
            SPLIT(entity_id, ':')[OFFSET(0)] AS property_id,
            CAST(SPLIT(entity_id, ':')[OFFSET(1)] AS INT64) AS room_type_id
        FROM `{PROJECT_ID}.ml_output.predictions`
        WHERE feature_snapshot_at = @feature_snapshot_at
    """
    job_config = _query_config(feature_snapshot_at)
    rows = client.query(query, job_config=job_config).result()
    return {(r["property_id"], r["room_type_id"]) for r in rows}


def _query_config(feature_snapshot_at):
    from google.cloud import bigquery
    return bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("feature_snapshot_at", "TIMESTAMP", feature_snapshot_at)
        ]
    )


def write_results(conn, snapshot_date, feature_snapshot_at, expected, scored, missing, persist=True, is_simulated=False):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO monitoring.ml_output_completeness_snapshot
            (snapshot_date, feature_snapshot_at, expected_entity_count, scored_entity_count, missing_entity_count)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (snapshot_date, feature_snapshot_at)
        DO UPDATE SET expected_entity_count = EXCLUDED.expected_entity_count,
                       scored_entity_count = EXCLUDED.scored_entity_count,
                       missing_entity_count = EXCLUDED.missing_entity_count,
                       captured_at = now()
        """,
        (snapshot_date, feature_snapshot_at, len(expected), len(scored), len(missing)),
    )
    for property_id, room_type_id in missing:
        cur.execute(
            """
            INSERT INTO monitoring.ml_output_missing_entity
                (feature_snapshot_at, property_id, room_type_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (feature_snapshot_at, property_id, room_type_id) DO NOTHING
            """,
            (feature_snapshot_at, property_id, room_type_id),
        )
    if missing:
        detail = f"{len(missing)} entity gagal ter-score pada feature_snapshot_at={feature_snapshot_at}: " \
                  + ", ".join(f"{p}:{r}" for p, r in sorted(missing)[:20])
        if len(missing) > 20:
            detail += f" (+{len(missing) - 20} lainnya)"
        cur.execute(
            """
            INSERT INTO monitoring.alerts
                (schema_name, table_name, alert_type, severity, detail, snapshot_date, is_simulated)
            VALUES ('ml_output', 'predictions', 'ml_output_incomplete_scoring', 'critical', %s, %s, %s)
            """,
            (detail, snapshot_date, is_simulated),
        )
    if persist:
        conn.commit()
    cur.close()


def run(persist=True, is_simulated=False, feature_snapshot_at_override=None):
    client = get_client()
    snapshot_date = datetime.datetime.now(datetime.timezone.utc).date()

    feature_snapshot_at = feature_snapshot_at_override or fetch_latest_feature_snapshot_at(client)
    if feature_snapshot_at is None:
        print("[ok] ml_output.predictions kosong, tidak ada yang divalidasi.")
        return

    expected = fetch_expected_entities(client, feature_snapshot_at)
    scored = fetch_scored_entities(client, feature_snapshot_at)
    missing = expected - scored

    conn = get_connection(readonly=False)
    try:
        write_results(conn, snapshot_date, feature_snapshot_at, expected, scored, missing,
                       persist=persist, is_simulated=is_simulated)
    finally:
        conn.close()

    print(f"feature_snapshot_at={feature_snapshot_at} expected={len(expected)} scored={len(scored)} missing={len(missing)}")
    if missing:
        print(f"[CRITICAL] {len(missing)} entity gagal ter-score: {sorted(missing)[:20]}")
    else:
        print("[ok] semua entity yang diharapkan sudah ter-score")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-snapshot-at", default=None,
                         help="Cek completeness untuk feature_snapshot_at spesifik (ISO timestamp), bukan yang terbaru. "
                              "Berguna untuk audit snapshot lama atau uji coba terkontrol.")
    parser.add_argument("--simulated", action="store_true",
                         help="Tandai hasil (snapshot + missing entity + alert) sebagai is_simulated=TRUE.")
    args = parser.parse_args()

    override = None
    if args.feature_snapshot_at:
        override = datetime.datetime.fromisoformat(args.feature_snapshot_at)
        if override.tzinfo is None:
            override = override.replace(tzinfo=datetime.timezone.utc)

    run(feature_snapshot_at_override=override, is_simulated=args.simulated)
