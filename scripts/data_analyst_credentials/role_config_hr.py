"""
Milestone 3.5 -- role config for hr_analyst_reader. GRANT targets derived
from scripts/data_analyst_api/whitelist_hr.py (Keputusan #4) -- payroll is
NOT in that whitelist at all, so it can't leak into grant_targets here
either. Deny-checks below prove it explicitly (KK1 M3.5's own worked example:
"HR Analyst tidak bisa mengakses payroll").
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_analyst_api"))
from whitelist_hr import AGGREGATE_WHITELIST, ROWLEVEL_WHITELIST  # noqa: E402

from grant_utils import derive_grant_targets  # noqa: E402

ROLE_CONFIG = {
    "role": "hr_analyst_reader",
    "env_var": "HR_ANALYST_READER_DB_URL",
    "grant_targets": derive_grant_targets(AGGREGATE_WHITELIST, ROWLEVEL_WHITELIST),
    "allow_checks": [
        ("own aggregate view", "SELECT count(*) FROM analyst_views.v_hr_watchlist_monthly"),
        ("own row-level table", "SELECT count(*) FROM mart_cleaned.staff_shifts"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.fact_hr_watchlist_monthly"),
        ("payroll row-level (KK1 worked example)", "SELECT count(*) FROM mart_cleaned.payroll"),
        ("payroll-department view", "SELECT count(*) FROM analyst_views.v_payroll_department_monthly"),
        ("payroll-access-level view", "SELECT count(*) FROM analyst_views.v_payroll_access_level_monthly"),
        ("service-charge view", "SELECT count(*) FROM analyst_views.v_financial_service_charge_monthly"),
        ("labor-cost view", "SELECT count(*) FROM analyst_views.v_financial_labor_cost_monthly"),
        ("cross-domain: revenue row-level", "SELECT count(*) FROM mart_cleaned.bookings"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.staff_shifts (shift_id) VALUES ('should-fail')",
}
