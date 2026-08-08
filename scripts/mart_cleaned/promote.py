"""
Milestone 2.3 -- data quality gate: build -> test -> swap.

dbt always writes mart_cleaned models to `mart_cleaned_staging` (see
warehouse/dbt_project.yml +schema override) -- NEVER directly to
`mart_cleaned`. This script runs `dbt build` (run + test together) against
that staging dataset, and only copies each table over to `mart_cleaned`
(via CREATE OR REPLACE TABLE ... AS SELECT, a DDL op -- Sandbox mode has no
issue with this, unlike the DML incremental strategies ruled out in
decisions.md) if EVERY test for EVERY mart_cleaned model passes.

If any test fails, `mart_cleaned` is left completely untouched -- whatever
violated a business rule never becomes visible there, satisfying Milestone
2.3's Kriteria Keberhasilan #3 literally (not just "test failed after the
fact").

Usage: python scripts/mart_cleaned/promote.py [--select <dbt selector>]
"""
import argparse
import os
import subprocess
import sys

from google.cloud import bigquery

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monitoring"))
from db import _load_env  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WAREHOUSE_DIR = os.path.join(REPO_ROOT, "warehouse")
STAGING_DATASET = "mart_cleaned_staging"
TARGET_DATASET = "mart_cleaned"
DBT_BIN = os.environ.get("DBT_BIN", "dbt")
PROJECT_ID = "nirwana-database-elt"


def get_dbt_transform_client():
    # dbt-transform (not extract-writer/scripts/extract/bq.py) -- it's the
    # one with project-level access covering mart_cleaned_staging/mart_cleaned,
    # same credential dbt itself uses via warehouse/profiles.yml.
    env = _load_env(os.path.join(REPO_ROOT, ".env"))
    keyfile_env = env.get("DBT_TRANSFORM_CREDENTIALS", "scripts/extract/gcp-dbt-transform-key.json")
    keyfile = keyfile_env if os.path.isabs(keyfile_env) else os.path.join(REPO_ROOT, keyfile_env)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyfile
    return bigquery.Client(project=PROJECT_ID)


def run_dbt(args):
    cmd = [DBT_BIN] + args + ["--profiles-dir", "."]
    result = subprocess.run(cmd, cwd=WAREHOUSE_DIR)
    return result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--select", default="mart_cleaned", help="dbt node selector")
    args = parser.parse_args()

    print(f"=== dbt run --select {args.select} ===")
    run_rc = run_dbt(["run", "--select", args.select])
    if run_rc != 0:
        print("\ndbt run FAILED -- mart_cleaned not touched.")
        sys.exit(run_rc)

    print(f"\n=== dbt test --select {args.select} ===")
    test_rc = run_dbt(["test", "--select", args.select])
    if test_rc != 0:
        print("\ndbt test FAILED -- mart_cleaned_staging has the data, "
              "but mart_cleaned is left UNTOUCHED (gate blocked promotion).")
        sys.exit(test_rc)

    print("\n=== All tests passed -- promoting mart_cleaned_staging -> mart_cleaned ===")
    client = get_dbt_transform_client()
    tables = list(client.list_tables(f"{client.project}.{STAGING_DATASET}"))
    for table_ref in tables:
        table_id = table_ref.table_id
        src = f"`{client.project}.{STAGING_DATASET}.{table_id}`"
        dst = f"`{client.project}.{TARGET_DATASET}.{table_id}`"
        client.query(f"CREATE OR REPLACE TABLE {dst} AS SELECT * FROM {src}").result()
        print(f"  promoted {table_id}")

    print(f"\n{len(tables)} table(s) promoted to {TARGET_DATASET}.")


if __name__ == "__main__":
    main()
