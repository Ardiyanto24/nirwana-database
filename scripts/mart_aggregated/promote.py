"""
Milestone 5.3 -- data quality gate: build -> test -> swap.

Pola identik scripts/mart_cleaned/promote.py (Milestone 2.3) -- copy, bukan
diimpor/diparameterisasi, mengikuti preseden project ("copied rather than
imported across scripts/* subfolders" karena sys.path tricks pernah
menyebabkan bug tabrakan nama modul, lihat milestones/2.1-.../logs.md).

dbt selalu menulis model mart_aggregated ke `mart_aggregated_staging` -- TIDAK
PERNAH langsung ke `mart_aggregated`. Script ini menjalankan `dbt build`
(run + test bersamaan) terhadap dataset staging itu, dan cuma menyalin tiap
tabel ke `mart_aggregated` (via CREATE OR REPLACE TABLE ... AS SELECT, operasi
DDL -- Sandbox mode tidak masalah dengan ini, beda dari strategi incremental
dbt yang sudah ditolak di decisions.md) kalau SEMUA test untuk SEMUA model
mart_aggregated lolos.

Kalau ada test gagal, `mart_aggregated` dibiarkan sepenuhnya tidak tersentuh
-- data apa pun yang melanggar business rule tidak pernah terlihat di sana,
memenuhi KK#2 Milestone 5.3 secara literal (bukan cuma "test gagal setelah
kejadian").

Usage: python scripts/mart_aggregated/promote.py [--select <dbt selector>]
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
STAGING_DATASET = "mart_aggregated_staging"
TARGET_DATASET = "mart_aggregated"
DBT_BIN = os.environ.get("DBT_BIN", "dbt")
PROJECT_ID = "nirwana-database-elt"


def get_dbt_transform_client():
    # dbt-transform (bukan extract-writer/scripts/extract/bq.py) -- kredensial
    # yang sama dipakai dbt sendiri via warehouse/profiles.yml, sudah punya akses
    # project-level ke mart_aggregated_staging/mart_aggregated.
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
    parser.add_argument("--select", default="mart_aggregated", help="dbt node selector")
    args = parser.parse_args()

    print(f"=== dbt run --select {args.select} ===")
    run_rc = run_dbt(["run", "--select", args.select])
    if run_rc != 0:
        print("\ndbt run FAILED -- mart_aggregated not touched.")
        sys.exit(run_rc)

    print(f"\n=== dbt test --select {args.select} ===")
    test_rc = run_dbt(["test", "--select", args.select])
    if test_rc != 0:
        print("\ndbt test FAILED -- mart_aggregated_staging has the data, "
              "but mart_aggregated is left UNTOUCHED (gate blocked promotion).")
        sys.exit(test_rc)

    print("\n=== All tests passed -- promoting mart_aggregated_staging -> mart_aggregated ===")
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
