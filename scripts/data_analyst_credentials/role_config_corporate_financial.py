"""
Milestone 3.5 -- role config for corporate_financial_analyst_reader. GRANT
targets derived from scripts/data_analyst_api/whitelist_corporate_financial.py
(Keputusan #4). This is the one role that DOES get payroll (its exclusive
domain per M3.1).

The base-table-bypass deny-check here is the most critical in the whole
milestone: v_financial_departmental_margin bakes in `WHERE line_name NOT IN
('Overall','Corporate Overhead')` (M3.2 business rule). If this role could
SELECT the underlying fact_financial_business_line_monthly table directly, it
could see the Overall/Corporate Overhead rows the view deliberately hides --
Keputusan #8 exists specifically to make that structurally impossible.
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_analyst_api"))
from whitelist_corporate_financial import AGGREGATE_WHITELIST, ROWLEVEL_WHITELIST  # noqa: E402

from grant_utils import derive_grant_targets  # noqa: E402

ROLE_CONFIG = {
    "role": "corporate_financial_analyst_reader",
    "env_var": "CORPORATE_FINANCIAL_ANALYST_READER_DB_URL",
    "grant_targets": derive_grant_targets(AGGREGATE_WHITELIST, ROWLEVEL_WHITELIST),
    "allow_checks": [
        ("own aggregate view (departmental margin)", "SELECT count(*) FROM analyst_views.v_financial_departmental_margin"),
        ("own row-level table: payroll", "SELECT count(*) FROM mart_cleaned.payroll"),
        ("own row-level table: financial_summary", "SELECT count(*) FROM mart_cleaned.financial_summary"),
    ],
    "deny_checks": [
        (
            "base table bypass -- Overall exclusion circumvention (most critical check in M3.5)",
            "SELECT count(*) FROM mart_aggregated.fact_financial_business_line_monthly",
        ),
        ("cross-domain: revenue row-level", "SELECT count(*) FROM mart_cleaned.bookings"),
        ("cross-domain: fnb row-level", "SELECT count(*) FROM mart_cleaned.fnb_transactions"),
        ("cross-domain: HR watchlist view", "SELECT count(*) FROM analyst_views.v_hr_watchlist_monthly"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.payroll (payroll_id) VALUES ('should-fail')",
}
