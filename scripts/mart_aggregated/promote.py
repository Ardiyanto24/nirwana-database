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

Milestone 5.4 -- tambah `--exclude` (dbt tidak punya sintaks inline
"exclude:" di dalam --select, cuma flag terpisah) supaya bisa dipanggil 2x
dengan scope terpisah: 76 tabel existing (wajib) vs tag:ml_feedback_loop
(best-effort) -- lihat .github/workflows/transform-mart-aggregated.yml dan
milestones/5.4-.../decisions.md Keputusan #10. Promosi juga di-scope ke
model yang benar-benar match selector (`dbt ls`), bukan lagi "copy semua
tabel di staging", supaya invocation kedua tidak diam-diam ikut menyalin
ulang 76 tabel yang sudah dipromosikan invocation pertama.

Usage: python scripts/mart_aggregated/promote.py [--select <dbt selector>] [--exclude <dbt selector>]
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


def get_selected_model_names(select, exclude):
    # Milestone 5.4 -- dbt has no "exclude:" inline selector syntax (only a
    # separate --exclude flag), and the promotion loop below used to copy
    # EVERY table found in mart_aggregated_staging regardless of --select
    # scope (harmless when the whole dataset is one selector, but would
    # silently re-promote tag:ml_feedback_loop's table on every "76 tables
    # only" run and vice versa once two scoped selectors are used in the
    # same job -- see milestones/5.4-.../decisions.md Keputusan #10). This
    # resolves the selector to the exact model name list so promotion only
    # touches tables actually in scope for this invocation.
    # --quiet is load-bearing, not cosmetic: without it dbt's INFO banner
    # ("Running with dbt=...", "Found N models...") lands on stdout right
    # alongside the actual node names and would get parsed as if they were
    # model names below.
    cmd = ["--quiet", "ls", "--select", select, "--resource-type", "model", "--output", "name"]
    if exclude:
        cmd += ["--exclude", exclude]
    result = subprocess.run(
        [DBT_BIN] + cmd + ["--profiles-dir", "."],
        cwd=WAREHOUSE_DIR, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("dbt ls failed while resolving --select/--exclude scope")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--select", default="mart_aggregated", help="dbt node selector")
    parser.add_argument("--exclude", default=None, help="dbt node selector to exclude")
    args = parser.parse_args()

    run_args = ["run", "--select", args.select]
    test_args = ["test", "--select", args.select]
    if args.exclude:
        run_args += ["--exclude", args.exclude]
        test_args += ["--exclude", args.exclude]

    print(f"=== dbt run --select {args.select}" + (f" --exclude {args.exclude}" if args.exclude else "") + " ===")
    run_rc = run_dbt(run_args)
    if run_rc != 0:
        print("\ndbt run FAILED -- mart_aggregated not touched.")
        sys.exit(run_rc)

    print(f"\n=== dbt test --select {args.select}" + (f" --exclude {args.exclude}" if args.exclude else "") + " ===")
    test_rc = run_dbt(test_args)
    if test_rc != 0:
        print("\ndbt test FAILED -- mart_aggregated_staging has the data, "
              "but mart_aggregated is left UNTOUCHED (gate blocked promotion).")
        sys.exit(test_rc)

    print("\n=== All tests passed -- promoting mart_aggregated_staging -> mart_aggregated ===")
    in_scope = get_selected_model_names(args.select, args.exclude)
    client = get_dbt_transform_client()
    tables = list(client.list_tables(f"{client.project}.{STAGING_DATASET}"))
    promoted = 0
    for table_ref in tables:
        table_id = table_ref.table_id
        if table_id not in in_scope:
            continue
        src = f"`{client.project}.{STAGING_DATASET}.{table_id}`"
        dst = f"`{client.project}.{TARGET_DATASET}.{table_id}`"
        client.query(f"CREATE OR REPLACE TABLE {dst} AS SELECT * FROM {src}").result()
        print(f"  promoted {table_id}")
        promoted += 1

    print(f"\n{promoted} table(s) promoted to {TARGET_DATASET} (scope: {len(in_scope)} model(s) selected).")


if __name__ == "__main__":
    main()
