"""
Milestone 2.4 Task 3 -- verify reverse-etl-reader is isolated to mart_cleaned
only (can read mart_cleaned, cannot read raw_production or staging).

Thin wrapper around scripts/bigquery_common/verify_dataset_isolation.py
(generalized in Milestone 2.5 Task 2 so a 3rd service account doesn't need a
3rd copy-pasted script) -- kept as its own file since M2.4's decisions.md/
report.md reference this exact path as a deliverable.

Usage: python scripts/reverse_etl/verify_reader_isolation.py
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(REPO_ROOT, "scripts", "bigquery_common"))
from verify_dataset_isolation import verify_isolation  # noqa: E402

KEYFILE = os.path.join(REPO_ROOT, "scripts", "extract", "gcp-reverse-etl-reader-key.json")
PROJECT_ID = "nirwana-database-elt"

CHECKS = [
    ("SELECT mart_cleaned.* (whitelisted)",
     "SELECT COUNT(*) AS c FROM `mart_cleaned.mart_cleaned__properties`", True),
    ("SELECT raw_production.* (NOT whitelisted)",
     "SELECT COUNT(*) FROM `raw_production.corporate_master__properties`", False),
    ("SELECT staging.* (NOT whitelisted)",
     "SELECT COUNT(*) FROM `staging.stg_corporate_master__employees`", False),
]


def main():
    if not verify_isolation(KEYFILE, PROJECT_ID, CHECKS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
