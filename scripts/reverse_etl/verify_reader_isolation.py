"""
Milestone 2.4 Task 3 -- verify reverse-etl-reader is isolated to mart_cleaned
only (can read mart_cleaned, cannot read raw_production or staging).

Usage: python scripts/reverse_etl/verify_reader_isolation.py
"""
import os

from google.api_core.exceptions import Forbidden
from google.cloud import bigquery

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYFILE = os.path.join(REPO_ROOT, "scripts", "extract", "gcp-reverse-etl-reader-key.json")
PROJECT_ID = "nirwana-database-elt"


def main():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEYFILE
    client = bigquery.Client(project=PROJECT_ID)

    checks = []

    try:
        rows = list(client.query("SELECT COUNT(*) AS c FROM `mart_cleaned.mart_cleaned__properties`").result())
        checks.append(("SELECT mart_cleaned.* (whitelisted)", True, rows[0]["c"] > 0))
    except Forbidden:
        checks.append(("SELECT mart_cleaned.* (whitelisted)", True, False))

    try:
        list(client.query("SELECT COUNT(*) FROM `raw_production.corporate_master__properties`").result())
        checks.append(("SELECT raw_production.* (NOT whitelisted)", False, False))
    except Forbidden:
        checks.append(("SELECT raw_production.* (NOT whitelisted)", False, True))

    try:
        list(client.query("SELECT COUNT(*) FROM `staging.stg_corporate_master__employees`").result())
        checks.append(("SELECT staging.* (NOT whitelisted)", False, False))
    except Forbidden:
        checks.append(("SELECT staging.* (NOT whitelisted)", False, True))

    print("Verification:")
    all_ok = True
    for label, should_succeed, ok in checks:
        status = "OK" if ok else "FAIL"
        if not ok:
            all_ok = False
        expect = "should succeed" if should_succeed else "should be denied"
        print(f"  [{status}] {label} ({expect})")

    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
