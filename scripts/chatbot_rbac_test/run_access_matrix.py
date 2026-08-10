"""
Milestone 4.6 Layer A -- exhaustive 20 role x 10 domain (200-cell) access
matrix test against the live chatbot API (scripts/chatbot_api/, must already
be running via `python -m uvicorn main:app`). Compares actual HTTP status
against ground truth pulled fresh from mart_cleaned.role_permissions
(ground_truth.py) -- not the design doc's table, a human-readable snapshot,
not the oracle itself (decisions.md M4.6 Keputusan #2).

One view per domain is enough: authorize(role_title, domain) is a domain-
level decision, made before the whitelist/view_name lookup even happens
(scripts/chatbot_api/main.py) -- so the view itself doesn't affect the
allow/deny outcome being tested here (design doc "Pemetaan 1 View
Representatif per Domain").

employee_id is always sent (harmless for all_properties roles, which ignore
it) using ONE fixed employee_id at P01 for every own_property cell --
authorize() never reads employee_id at all (design doc "Data Uji
own_property").

Usage:
  python -m uvicorn main:app --port 8010   # in scripts/chatbot_api/, separately
  python run_access_matrix.py [--base-url http://127.0.0.1:8010]
"""
import argparse
import sys

import requests

from ground_truth import DOMAINS, ROLES, load_role_permissions, pick_test_employee_ids

VIEW_BY_DOMAIN = {
    "reservation": "room-type-daily",
    "fnb": "outlet-daily",
    "facility": "room-status-daily",
    "spa_event": "spa-daily",
    "hr": "attendance-daily",
    "financial": "departmental-margin",
    "properties_ref": "properties",
    "employees_directory": "employees",
    "guests_pii": "guests-contact",
    "guests_profile": "guests-profile",
}


def call(base_url, domain, role_title, employee_id):
    view_name = VIEW_BY_DOMAIN[domain]
    resp = requests.get(
        f"{base_url}/chatbot/{domain}/{view_name}",
        params={"role_title": role_title, "employee_id": employee_id, "limit": 1},
        timeout=10,
    )
    return resp.status_code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    args = parser.parse_args()

    perms = load_role_permissions()
    employee_id_p01, _ = pick_test_employee_ids()
    print(f"Ground truth: {len(perms)} role_permissions rows loaded. Test employee_id (P01): {employee_id_p01}\n")

    results = []
    for role in ROLES:
        for domain in DOMAINS:
            expected_scope = perms.get((role, domain))
            expected_allow = expected_scope is not None
            status = call(args.base_url, domain, role, employee_id_p01)
            actual_allow = status == 200
            ok = actual_allow == expected_allow
            results.append(
                {
                    "role": role,
                    "domain": domain,
                    "expected": expected_scope or "DENY",
                    "status": status,
                    "ok": ok,
                }
            )

    mismatches = [r for r in results if not r["ok"]]

    header = f"{'role':<32}{'domain':<22}{'expected':<18}{'status':<8}result"
    print(header)
    print("-" * len(header))
    for r in results:
        verdict = "OK" if r["ok"] else "MISMATCH"
        print(f"{r['role']:<32}{r['domain']:<22}{r['expected']:<18}{r['status']:<8}{verdict}")

    print(f"\n{len(results) - len(mismatches)}/{len(results)} cells matched expectation.")

    if mismatches:
        print("\nMISMATCHES:")
        for r in mismatches:
            print(f"  {r['role']} x {r['domain']}: expected {r['expected']}, got HTTP {r['status']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
