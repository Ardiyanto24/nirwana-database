"""
Milestone 4.3 -- role config for properties_ref_chatbot_reader. GRANT_TARGETS
hand-enumerated from scripts/chatbot_views/views_properties_ref.sql
(Keputusan #4). Simplest domain -- 1 view, low sensitivity (M4.1 §2.7).
"""

GRANT_TARGETS = [
    "chatbot_views.v_properties_ref",
]

ROLE_CONFIG = {
    "role": "properties_ref_chatbot_reader",
    "env_var": "PROPERTIES_REF_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own view", "SELECT count(*) FROM chatbot_views.v_properties_ref"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.dim_property"),
        ("role_permissions (M4.1 Keputusan #7)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        ("cross-domain: employees_directory view", "SELECT count(*) FROM chatbot_views.v_employees_directory"),
        ("cross-domain: guests_pii view", "SELECT count(*) FROM chatbot_views.guests_contact_view"),
        ("cross-domain: reservation lookup", "SELECT count(*) FROM chatbot_views.v_lookup_bookings"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.properties (property_id) VALUES ('should-fail')",
}
