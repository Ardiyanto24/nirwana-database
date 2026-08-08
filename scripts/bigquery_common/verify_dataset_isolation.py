"""
Milestone 2.5 Task 2 -- generic BigQuery dataset-isolation verifier, extracted
from scripts/reverse_etl/verify_reader_isolation.py (Milestone 2.4) so a
3rd service account (data-scientist-reader) doesn't need a 3rd copy-pasted
script. Any future dataset-scoped credential in this project can reuse this
CLI directly instead of writing a new one-off verify_*.py file.

Connects to BigQuery AS the credential being tested, runs one query per
check, and asserts whether it should succeed (whitelisted dataset) or raise
google.api_core.exceptions.Forbidden (everything else).

Usage (CLI):
  python verify_dataset_isolation.py --keyfile <path> --project <id> \
      --allow "mart_cleaned.mart_cleaned__properties" \
      --deny "raw_production.corporate_master__properties" \
      --deny "staging.stg_corporate_master__employees"

Usage (as a library):
  from verify_dataset_isolation import verify_isolation
  verify_isolation(keyfile, project_id, [("label", sql, should_succeed), ...])
"""
import argparse
import os

from google.api_core.exceptions import Forbidden
from google.cloud import bigquery


def verify_isolation(keyfile_path, project_id, checks):
    """checks: list of (label, sql, should_succeed) tuples.
    Returns True if every check matched its expectation, False otherwise."""
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyfile_path
    client = bigquery.Client(project=project_id)

    results = []
    for label, sql, should_succeed in checks:
        try:
            list(client.query(sql).result())
            results.append((label, should_succeed, should_succeed))
        except Forbidden:
            results.append((label, should_succeed, not should_succeed))

    print("Verification:")
    all_ok = True
    for label, should_succeed, ok in results:
        status = "OK" if ok else "FAIL"
        if not ok:
            all_ok = False
        expect = "should succeed" if should_succeed else "should be denied"
        print(f"  [{status}] {label} ({expect})")

    return all_ok


def _table_check(table_ref, should_succeed):
    label = f"SELECT {table_ref} ({'whitelisted' if should_succeed else 'NOT whitelisted'})"
    sql = f"SELECT COUNT(*) FROM `{table_ref}`"
    return (label, sql, should_succeed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyfile", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--allow", action="append", default=[], help="dataset.table expected to succeed")
    parser.add_argument("--deny", action="append", default=[], help="dataset.table expected to be denied")
    args = parser.parse_args()

    checks = [_table_check(t, True) for t in args.allow] + [_table_check(t, False) for t in args.deny]
    if not checks:
        parser.error("need at least one --allow or --deny")

    ok = verify_isolation(args.keyfile, args.project, checks)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
