"""
Milestone 4.3 -- role config for employees_directory_chatbot_reader.
GRANT_TARGETS hand-enumerated from
scripts/chatbot_views/views_employees_directory.sql (Keputusan #4).
"""

GRANT_TARGETS = [
    "chatbot_views.v_employees_directory",
]

ROLE_CONFIG = {
    "role": "employees_directory_chatbot_reader",
    "env_var": "EMPLOYEES_DIRECTORY_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own view", "SELECT count(*) FROM chatbot_views.v_employees_directory"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.dim_employee"),
        ("base table bypass (mart_cleaned direct)", "SELECT count(*) FROM mart_cleaned.employees"),
        ("role_permissions (M4.1 Keputusan #7)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        ("cross-domain: hr lookup (payroll-adjacent)", "SELECT count(*) FROM chatbot_views.v_lookup_staff_shifts"),
        ("cross-domain: guests_profile view", "SELECT count(*) FROM chatbot_views.guests_profile_view"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.employees (employee_id) VALUES ('should-fail')",
}
