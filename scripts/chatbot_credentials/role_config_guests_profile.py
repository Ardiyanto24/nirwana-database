"""
Milestone 4.3 -- role config for guests_profile_chatbot_reader. GRANT_TARGETS
= guests_profile_view only. Mirror of role_config_guests_pii.py's crucial
same-table-different-view deny test, in the opposite direction.
"""

GRANT_TARGETS = [
    "chatbot_views.guests_profile_view",
]

ROLE_CONFIG = {
    "role": "guests_profile_chatbot_reader",
    "env_var": "GUESTS_PROFILE_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own view", "SELECT count(*) FROM chatbot_views.guests_profile_view"),
    ],
    "deny_checks": [
        ("base table bypass (mart_cleaned.guests direct)", "SELECT count(*) FROM mart_cleaned.guests"),
        ("role_permissions (M4.1 Keputusan #7)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        (
            "same-table sibling view: guests_contact_view (KRUSIAL -- kolom kontak PII)",
            "SELECT count(*) FROM chatbot_views.guests_contact_view",
        ),
        ("cross-domain: financial lookup", "SELECT count(*) FROM chatbot_views.v_lookup_financial_summary"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.guests (guest_id) VALUES ('should-fail')",
}
