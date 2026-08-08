"""
Milestone 5.4 -- sensor: poll ml_output.predictions until the scoring job
(scripts/ml_scoring/mock_score.py, run as its own separate GitHub Actions
workflow -- see .github/workflows/scoring-occupancy-forecast.yml) has
written fresh rows, or give up after a bounded number of attempts.

GitHub Actions has no native sensor -- it only reacts to a workflow's
*completion* (workflow_run), not to arbitrary external state such as "has
another, genuinely external system finished writing this table yet." This
script is the manual polling workaround docs/05-orchestrator/konvensi-job-dependency.md
itself prescribes for exactly this situation (see "Batasan yang Perlu
Diketahui" and docs/keputusan-tertunda.md's "Orchestrator sungguhan" entry,
which flags Milestone 5.4 as the point this gap would need solving).

transform-mart-aggregated.yml triggers off the SAME upstream event as
scoring-occupancy-forecast.yml (workflow_run on "Transform Staging and Mart
Cleaned"), not off the scoring workflow's own completion -- otherwise this
sensor would never really be exercised (see milestones/5.4-.../decisions.md
Keputusan #1). A lookback window (not a fixed "since" timestamp) tolerates
the two workflows starting a few seconds apart.

Exit code 0 = fresh rows found (sensor succeeded). Exit code 1 = timed out
without finding fresh rows -- the CALLING WORKFLOW is responsible for
treating this as "skip the ML step, do not fail the job" (KK3), not this
script.

Usage: python scripts/ml_scoring/wait_for_ml_output.py
       [--model-name occupancy_forecast] [--max-attempts 30]
       [--interval-seconds 120] [--lookback-minutes 90]
"""
import argparse
import os
import sys
import time

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ID = "nirwana-database-elt"
TABLE = f"{PROJECT_ID}.ml_output.predictions"


def get_client():
    # dbt-transform (project-level bigquery.dataEditor, M2.2 pengecualian
    # sadar) -- job ini sudah memakainya untuk seluruh step dbt lain, tidak
    # perlu kredensial ketiga cuma untuk sensor (lihat decisions.md
    # Keputusan #11, "Kenapa bukan reader terpisah untuk sensor").
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    keyfile_env = env.get("DBT_TRANSFORM_CREDENTIALS", "scripts/extract/gcp-dbt-transform-key.json")
    keyfile = keyfile_env if os.path.isabs(keyfile_env) else os.path.join(REPO_ROOT, keyfile_env)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyfile
    return bigquery.Client(project=PROJECT_ID)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default="occupancy_forecast")
    parser.add_argument("--max-attempts", type=int, default=30)
    parser.add_argument("--interval-seconds", type=int, default=120)
    parser.add_argument("--lookback-minutes", type=int, default=90)
    args = parser.parse_args()

    client = get_client()

    try:
        client.get_table(TABLE)
    except NotFound:
        print(f"ml_output.predictions does not exist yet -- scoring job has not run at all.")
        sys.exit(1)

    query = f"""
        SELECT COUNT(*) AS n
        FROM `{TABLE}`
        WHERE model_name = @model_name
          AND scored_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @lookback_minutes MINUTE)
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("model_name", "STRING", args.model_name),
        bigquery.ScalarQueryParameter("lookback_minutes", "INT64", args.lookback_minutes),
    ])

    for attempt in range(1, args.max_attempts + 1):
        row = list(client.query(query, job_config=job_config).result())[0]
        print(f"[attempt {attempt}/{args.max_attempts}] fresh rows (model_name={args.model_name}, "
              f"last {args.lookback_minutes}min): {row.n}")
        if row.n > 0:
            print("Sensor: ml_output is ready.")
            sys.exit(0)
        if attempt < args.max_attempts:
            time.sleep(args.interval_seconds)

    print(f"Sensor TIMED OUT after {args.max_attempts} attempts "
          f"({args.max_attempts * args.interval_seconds}s total) -- ml_output not ready in time.")
    sys.exit(1)


if __name__ == "__main__":
    main()
