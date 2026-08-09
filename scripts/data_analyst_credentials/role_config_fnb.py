"""
Milestone 3.5 -- role config for fnb_analyst_reader. GRANT targets derived
from scripts/data_analyst_api/whitelist_fnb.py (Keputusan #4).
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_analyst_api"))
from whitelist_fnb import AGGREGATE_WHITELIST, ROWLEVEL_WHITELIST  # noqa: E402

from grant_utils import derive_grant_targets  # noqa: E402

ROLE_CONFIG = {
    "role": "fnb_analyst_reader",
    "env_var": "FNB_ANALYST_READER_DB_URL",
    "grant_targets": derive_grant_targets(AGGREGATE_WHITELIST, ROWLEVEL_WHITELIST),
    "allow_checks": [
        ("own aggregate view", "SELECT count(*) FROM analyst_views.v_fnb_outlet_daily"),
        ("own row-level table", "SELECT count(*) FROM mart_cleaned.fnb_transactions"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.fact_fnb_outlet_daily"),
        ("cross-domain: payroll", "SELECT count(*) FROM mart_cleaned.payroll"),
        ("cross-domain: revenue row-level", "SELECT count(*) FROM mart_cleaned.bookings"),
        ("cross-domain: HR watchlist view", "SELECT count(*) FROM analyst_views.v_hr_watchlist_monthly"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.fnb_transactions (transaction_id) VALUES ('should-fail')",
}
