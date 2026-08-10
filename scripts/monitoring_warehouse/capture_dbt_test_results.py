"""
Milestone 6.3 -- baca warehouse/target/run_results.json (artefak dbt standar,
ditulis ulang tiap kali `dbt run`/`dbt test` dijalankan) SETELAH step gate
promote.py (mart_cleaned/mart_aggregated) selesai, tulis detail per-test ke
monitoring.dbt_test_result. promote.py sendiri TIDAK disentuh -- lihat
milestones/6.3-monitoring-kesalahan-anomali-warehouse/decisions.md Keputusan #1.

Dipanggil sebagai step BARU (if: always()) di
.github/workflows/{transform-mart-cleaned,transform-mart-aggregated}.yml,
tepat setelah step "build->test->swap gate" -- run_results.json pada titik
itu berisi hasil `dbt test` (invocation TERAKHIR promote.py, bukan `dbt run`).

Usage:
    python capture_dbt_test_results.py --layer mart_cleaned
    python capture_dbt_test_results.py --layer mart_aggregated --run-results-path <path lain>
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_RUN_RESULTS_PATH = os.path.join(REPO_ROOT, "warehouse", "target", "run_results.json")


def parse_test_name(unique_id):
    """dbt unique_id format: <resource_type>.<project_name>.<test_name>.<hash>
    Best-effort: fallback ke unique_id penuh kalau formatnya tidak sesuai dugaan."""
    parts = unique_id.split(".")
    if len(parts) >= 4:
        return parts[2]
    return unique_id


def load_results(run_results_path):
    with open(run_results_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("results", [])


def insert_results(conn, layer, results, github_run_id):
    cur = conn.cursor()
    for r in results:
        unique_id = r["unique_id"]
        resource_type = unique_id.split(".")[0] if "." in unique_id else None
        cur.execute(
            """
            INSERT INTO monitoring.dbt_test_result
                (layer, unique_id, test_name, resource_type, status, execution_time, failures, github_run_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                layer,
                unique_id,
                parse_test_name(unique_id),
                resource_type,
                r.get("status"),
                r.get("execution_time"),
                r.get("failures"),
                github_run_id,
            ),
        )
    conn.commit()
    cur.close()


def main(layer, run_results_path):
    results = load_results(run_results_path)
    github_run_id = os.environ.get("GITHUB_RUN_ID")
    github_run_id = int(github_run_id) if github_run_id else None

    conn = get_connection()
    try:
        insert_results(conn, layer, results, github_run_id)
    finally:
        conn.close()

    n_fail = sum(1 for r in results if r.get("status") == "fail")
    n_error = sum(1 for r in results if r.get("status") == "error")
    print(f"Captured {len(results)} test result(s) for layer={layer}: {n_fail} fail, {n_error} error.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layer", required=True, choices=["mart_cleaned", "mart_aggregated"])
    parser.add_argument("--run-results-path", default=DEFAULT_RUN_RESULTS_PATH)
    args = parser.parse_args()
    main(args.layer, args.run_results_path)
