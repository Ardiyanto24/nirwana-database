"""
Milestone 5.4 -- mock scoring pipeline (STAND-IN for a real external ML
scoring pipeline that does not exist in this repo -- see
milestones/5.4-integrasi-feedback-loop-ml/decisions.md, Keputusan #1 and the
provisional-status note at the top of that file).

This script deliberately lives OUTSIDE warehouse/ (not a dbt model) and is
run as its own GitHub Actions job (.github/workflows/scoring-occupancy-forecast.yml)
-- consistent with the architecture doc's framing of scoring as happening
"di luar warehouse". It reads occupancy history from mart_aggregated (already
built by M5.3), computes a naive moving-average occupancy forecast per
property x room_type, and writes the result to ml_output.predictions.

Use-case (occupancy forecast), the ml_output.predictions schema (including
the target_date column, which is NOT part of the architecture doc's Bagian
6.3 schema -- an explicit, documented deviation), and the entity_id format
("property_id:room_type_id") are all PROVISIONAL -- placeholders to prove
the trigger->sensor->join->test mechanism works end-to-end, not a real ML
model or a schema agreed with the ML Engineering team.

Sandbox mode (no billing on nirwana-database-elt) blocks all DML, so this
writes via CREATE OR REPLACE TABLE ... AS SELECT (self-union with the
existing table to behave like an append) -- identical pattern to
fact_revenue_pace_booking_snapshot (M5.3). Target dates are computed
relative to MAX(period_date) found in the source data, NOT CURRENT_DATE() --
the dataset is a static synthetic snapshot, and CURRENT_DATE() has already
passed its end, which is exactly why fact_revenue_pace_booking_snapshot came
up empty in M5.3.

Usage: python scripts/ml_scoring/mock_score.py [--horizon-days 14] [--lookback-days 30]
"""
import argparse
import os
import sys

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ID = "nirwana-database-elt"
SOURCE_TABLE = f"{PROJECT_ID}.mart_aggregated.fact_revenue_room_type_daily"
DATASET = "ml_output"
TABLE = "predictions"
MODEL_NAME = "occupancy_forecast"
MODEL_VERSION = "occupancy_forecast_mock_v1"


def get_client():
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    keyfile_env = env.get("ML_SCORING_WRITER_CREDENTIALS", "scripts/extract/gcp-ml-scoring-writer-key.json")
    keyfile = keyfile_env if os.path.isabs(keyfile_env) else os.path.join(REPO_ROOT, keyfile_env)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyfile
    return bigquery.Client(project=PROJECT_ID)


def build_sql(target_table, table_exists, horizon_days, lookback_days):
    union_existing = f"UNION ALL\nSELECT * FROM `{target_table}`" if table_exists else ""
    return f"""
DECLARE last_date DATE;
SET last_date = (SELECT MAX(period_date) FROM `{SOURCE_TABLE}`);

CREATE OR REPLACE TABLE `{target_table}` AS
WITH base_stats AS (
  SELECT
    property_id,
    room_type_id,
    AVG(occupancy_rate) AS avg_occupancy,
    STDDEV(occupancy_rate) AS stddev_occupancy
  FROM `{SOURCE_TABLE}`
  WHERE period_date BETWEEN DATE_SUB(last_date, INTERVAL {lookback_days} DAY) AND last_date
  GROUP BY property_id, room_type_id
),
new_predictions AS (
  SELECT
    GENERATE_UUID() AS prediction_id,
    CONCAT(b.property_id, ':', CAST(b.room_type_id AS STRING)) AS entity_id,
    '{MODEL_NAME}' AS model_name,
    '{MODEL_VERSION}' AS model_version,
    'regression' AS prediction_type,
    CAST(ROUND(LEAST(GREATEST(b.avg_occupancy, 0), 1), 4) AS STRING) AS predicted_value,
    LEAST(GREATEST(
      1 - IFNULL(SAFE_DIVIDE(b.stddev_occupancy, NULLIF(b.avg_occupancy, 0)), 0.5),
      0.05), 0.99) AS confidence_score,
    CURRENT_TIMESTAMP() AS scored_at,
    TIMESTAMP(last_date) AS feature_snapshot_at,
    DATE_ADD(last_date, INTERVAL day_offset DAY) AS target_date
  FROM base_stats b
  CROSS JOIN UNNEST(GENERATE_ARRAY(1, {horizon_days})) AS day_offset
)
SELECT * FROM new_predictions
{union_existing}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-days", type=int, default=14, help="how many days ahead to forecast")
    parser.add_argument("--lookback-days", type=int, default=30, help="history window used for the moving average")
    args = parser.parse_args()

    client = get_client()

    try:
        client.get_dataset(f"{PROJECT_ID}.{DATASET}")
    except NotFound:
        print(f"ERROR: dataset {DATASET} does not exist. It must be created by the infra "
              f"owner first (ml-scoring-writer is least-privilege and cannot create datasets) "
              f"-- see milestones/5.4-integrasi-feedback-loop-ml/logs.md Checkpoint 1.")
        sys.exit(1)

    target_table = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    try:
        client.get_table(target_table)
        table_exists = True
    except NotFound:
        table_exists = False

    sql = build_sql(target_table, table_exists, args.horizon_days, args.lookback_days)
    print(f"=== Running mock scoring ({'append to existing' if table_exists else 'first run, new table'}) ===")
    client.query(sql).result()

    stats = client.query(
        f"SELECT COUNT(*) AS n, MIN(target_date) AS min_d, MAX(target_date) AS max_d, "
        f"MAX(scored_at) AS last_scored FROM `{target_table}`"
    ).result()
    row = list(stats)[0]
    print(f"ml_output.predictions now has {row.n} row(s) total. "
          f"target_date range: {row.min_d} .. {row.max_d}. last scored_at: {row.last_scored}.")


if __name__ == "__main__":
    main()
