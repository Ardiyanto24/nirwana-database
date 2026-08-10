"""
Milestone 4.3 -- role config for financial_chatbot_reader. GRANT_TARGETS
hand-enumerated from scripts/chatbot_views/views_financial.sql (Keputusan #4).
"""

GRANT_TARGETS = [
    "chatbot_views.v_financial_departmental_margin",
    "chatbot_views.v_financial_gop_overhead",
    "chatbot_views.v_financial_revenue_runrate_daily",
    "chatbot_views.v_payroll_department_monthly",
    "chatbot_views.v_financial_service_charge_monthly",
    "chatbot_views.v_financial_labor_cost_monthly",
    "chatbot_views.v_payroll_access_level_monthly",
    "chatbot_views.v_financial_business_line_group_monthly",
    "chatbot_views.v_financial_property_benchmark_monthly",
    "chatbot_views.v_lookup_financial_summary",
    "chatbot_views.v_lookup_payroll",
]

ROLE_CONFIG = {
    "role": "financial_chatbot_reader",
    "env_var": "FINANCIAL_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own aggregate view", "SELECT count(*) FROM chatbot_views.v_financial_departmental_margin"),
        ("own lookup view", "SELECT count(*) FROM chatbot_views.v_lookup_payroll"),
    ],
    "deny_checks": [
        (
            "base table bypass -- business rule Overall exclusion (paling kritis)",
            "SELECT count(*) FROM mart_aggregated.fact_financial_business_line_monthly",
        ),
        ("base table bypass (mart_cleaned direct)", "SELECT count(*) FROM mart_cleaned.financial_summary"),
        ("role_permissions (M4.1 Keputusan #7)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        ("cross-domain: hr lookup", "SELECT count(*) FROM chatbot_views.v_lookup_staff_shifts"),
        ("cross-domain: guests_pii view", "SELECT count(*) FROM chatbot_views.guests_contact_view"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.payroll (payroll_id) VALUES ('should-fail')",
}
