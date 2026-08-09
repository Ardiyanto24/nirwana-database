"""
Milestone 3.5 -- role config for property_gm_analyst_reader. Unlike the 6
domain roles, this one has NO grant_targets of its own -- Keputusan #3:
it's built via Postgres role inheritance (GRANT <5 domain roles> TO
property_gm_analyst_reader), reusing whatever those 5 roles already have
instead of re-listing 39 view/table names. member_of drives a different
code path in setup_analyst_roles.py's setup_role().

Explicitly excludes corporate_financial_analyst_reader -- M3.1 business rule
#3: Property/GM Analyst must never reach financial_summary/payroll or the
group-level fact_financial_business_line_group_monthly.
"""

ROLE_CONFIG = {
    "role": "property_gm_analyst_reader",
    "env_var": "PROPERTY_GM_ANALYST_READER_DB_URL",
    "member_of": [
        "revenue_analyst_reader",
        "fnb_analyst_reader",
        "facility_analyst_reader",
        "spa_event_analyst_reader",
        "hr_analyst_reader",
    ],
    "allow_checks": [
        ("inherited: revenue view", "SELECT count(*) FROM analyst_views.v_revenue_room_type_daily"),
        ("inherited: fnb row-level", "SELECT count(*) FROM mart_cleaned.fnb_transactions"),
        ("inherited: facility view", "SELECT count(*) FROM analyst_views.v_maintenance_ticket_daily"),
        ("inherited: spa-event row-level", "SELECT count(*) FROM mart_cleaned.event_bookings"),
        ("inherited: hr view", "SELECT count(*) FROM analyst_views.v_hr_watchlist_monthly"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.fact_revenue_room_type_daily"),
        ("corporate-financial: departmental margin view", "SELECT count(*) FROM analyst_views.v_financial_departmental_margin"),
        ("corporate-financial: group-level view (M3.1 business rule #3)", "SELECT count(*) FROM analyst_views.v_financial_business_line_group_monthly"),
        ("corporate-financial: payroll row-level", "SELECT count(*) FROM mart_cleaned.payroll"),
        ("corporate-financial: financial_summary row-level", "SELECT count(*) FROM mart_cleaned.financial_summary"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.bookings (booking_id) VALUES ('should-fail')",
}
