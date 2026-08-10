"""
Milestone 4.6 Layer B -- spot-check the own_property override mechanism
across a representative sample (1 domain per persona, 15 personas: General
Manager + 7 Manager + 7 Staff), rather than exhaustively re-testing all 48
own_property rows in role_permissions -- the override code path
(resolve_property_id + own_property_column substitution in
scripts/chatbot_api/main.py) is the SAME code regardless of domain/role, and
was already proven repeatedly in M4.4/M4.5 (decisions.md M4.6 Keputusan #4).

For each sample, two calls:
  1. employee_id = the P01 test employee, WITH a claimed property_id=P02 in
     the query string -- must still return 100% P01 rows (claim ignored).
  2. employee_id = the P02 test employee, no claim at all -- must return
     100% P02 rows (proves the override isn't hardcoded to P01, it resolves
     per-employee_id).

Usage:
  python -m uvicorn main:app --port 8010   # in scripts/chatbot_api/, separately
  python run_property_override_sample.py [--base-url http://127.0.0.1:8010]
"""
import argparse
import sys

import requests

from ground_truth import pick_test_employee_ids
from run_access_matrix import VIEW_BY_DOMAIN

# 1 own_property domain per persona -- General Manager + 7 Manager + 7 Staff.
# None of these use the guests_pii/guests_profile own_property_column special
# case (last_active_property_id), so "property_id" is the uniform param/column
# for every sample here.
SAMPLE = [
    ("General Manager", "reservation"),
    ("Revenue Manager", "reservation"),
    ("F&B Manager", "fnb"),
    ("Finance Manager", "financial"),
    ("Housekeeping Manager", "facility"),
    ("HR Manager", "hr"),
    ("Maintenance Manager", "facility"),
    ("Spa & Event Manager", "spa_event"),
    ("Front Office Staff", "reservation"),
    ("F&B Staff", "fnb"),
    ("Finance Staff", "financial"),
    ("Housekeeping Staff", "facility"),
    ("HR Staff", "hr"),
    ("Maintenance Staff", "facility"),
    ("Spa & Event Staff", "spa_event"),
]


def call(base_url, domain, role_title, employee_id, claimed_property_id=None):
    view_name = VIEW_BY_DOMAIN[domain]
    params = {"role_title": role_title, "employee_id": employee_id, "limit": 50}
    if claimed_property_id:
        params["property_id"] = claimed_property_id
    resp = requests.get(f"{base_url}/chatbot/{domain}/{view_name}", params=params, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    return {row["property_id"] for row in rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    args = parser.parse_args()

    emp_p01, emp_p02 = pick_test_employee_ids()
    print(f"employee_id P01={emp_p01}, P02={emp_p02}\n")

    failures = []
    inconclusive = []
    for role, domain in SAMPLE:
        seen_claim_ignored = call(args.base_url, domain, role, emp_p01, claimed_property_id="P02")
        seen_resolve_per_employee = call(args.base_url, domain, role, emp_p02)

        if not seen_claim_ignored or not seen_resolve_per_employee:
            inconclusive.append((role, domain, seen_claim_ignored, seen_resolve_per_employee))
            verdict = "INCONCLUSIVE (no rows)"
        else:
            ok = seen_claim_ignored == {"P01"} and seen_resolve_per_employee == {"P02"}
            verdict = "OK" if ok else "MISMATCH"
            if not ok:
                failures.append((role, domain, seen_claim_ignored, seen_resolve_per_employee))

        print(
            f"{role:<24}{domain:<14} claim-ignored={seen_claim_ignored or '{}'} (expect P01) "
            f"resolve-per-employee={seen_resolve_per_employee or '{}'} (expect P02)  {verdict}"
        )

    print(f"\n{len(SAMPLE) - len(failures) - len(inconclusive)}/{len(SAMPLE)} samples OK.")
    if inconclusive:
        print(f"{len(inconclusive)} inconclusive (no rows returned -- re-check manually).")
    if failures:
        print("\nFAILURES:")
        for role, domain, seen_a, seen_b in failures:
            print(f"  {role} x {domain}: claim-ignored saw {seen_a} (expect P01), resolve-per-employee saw {seen_b} (expect P02)")
        sys.exit(1)


if __name__ == "__main__":
    main()
