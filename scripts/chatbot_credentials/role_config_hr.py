"""
Milestone 4.3 -- role config for hr_chatbot_reader. GRANT_TARGETS
hand-enumerated from scripts/chatbot_views/views_hr.sql (Keputusan #4) --
payroll is NOT in this list at all, so it can't leak into grant_targets
either. Deny-checks below prove it explicitly across every payroll-adjacent
view (business rule kritis M3.1 #2, berlaku sama untuk chatbot).
"""

GRANT_TARGETS = [
    "chatbot_views.v_hr_attendance_daily",
    "chatbot_views.v_hr_employee_monthly",
    "chatbot_views.v_hr_employee_performance_semester",
    "chatbot_views.v_hr_turnover_snapshot",
    "chatbot_views.v_hr_headcount_status_daily",
    "chatbot_views.v_hr_performance_department_semester",
    "chatbot_views.v_hr_performance_by_status_semester",
    "chatbot_views.v_hr_watchlist_monthly",
    "chatbot_views.v_lookup_staff_shifts",
    "chatbot_views.v_lookup_employee_performance",
]

ROLE_CONFIG = {
    "role": "hr_chatbot_reader",
    "env_var": "HR_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own aggregate view", "SELECT count(*) FROM chatbot_views.v_hr_watchlist_monthly"),
        ("own lookup view", "SELECT count(*) FROM chatbot_views.v_lookup_staff_shifts"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.fact_hr_watchlist_monthly"),
        ("base table bypass (mart_cleaned direct)", "SELECT count(*) FROM mart_cleaned.staff_shifts"),
        ("role_permissions (M4.1 Keputusan #7)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        ("payroll row-level (KK1 worked example)", "SELECT count(*) FROM mart_cleaned.payroll"),
        ("payroll lookup view", "SELECT count(*) FROM chatbot_views.v_lookup_payroll"),
        ("payroll-department view", "SELECT count(*) FROM chatbot_views.v_payroll_department_monthly"),
        ("payroll-access-level view", "SELECT count(*) FROM chatbot_views.v_payroll_access_level_monthly"),
        ("service-charge view", "SELECT count(*) FROM chatbot_views.v_financial_service_charge_monthly"),
        ("labor-cost view", "SELECT count(*) FROM chatbot_views.v_financial_labor_cost_monthly"),
        ("cross-domain: reservation lookup", "SELECT count(*) FROM chatbot_views.v_lookup_bookings"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.staff_shifts (shift_id) VALUES ('should-fail')",
}
