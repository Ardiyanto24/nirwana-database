"""
Milestone 4.3 -- role config for guests_pii_chatbot_reader. GRANT_TARGETS =
guests_contact_view only (scripts/chatbot_views/views_guests.sql). Most
sensitive of the 10 domains (PII: email, phone) -- deny_checks include the
crucial same-table-different-view test: this role must NOT be able to read
guests_profile_view, even though both views sit on top of the same physical
mart_cleaned.guests table (M4.1 Keputusan #3/§3, rancangan-rbac-ai-chatbot.md
Bagian 4).
"""

GRANT_TARGETS = [
    "chatbot_views.guests_contact_view",
]

ROLE_CONFIG = {
    "role": "guests_pii_chatbot_reader",
    "env_var": "GUESTS_PII_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own view", "SELECT count(*) FROM chatbot_views.guests_contact_view"),
    ],
    "deny_checks": [
        ("base table bypass (mart_cleaned.guests direct)", "SELECT count(*) FROM mart_cleaned.guests"),
        ("role_permissions (M4.1 Keputusan #7)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        (
            "same-table sibling view: guests_profile_view (KRUSIAL -- kolom beda di atas tabel fisik sama)",
            "SELECT count(*) FROM chatbot_views.guests_profile_view",
        ),
        ("cross-domain: reservation lookup", "SELECT count(*) FROM chatbot_views.v_lookup_bookings"),
        ("cross-domain: spa_event lookup", "SELECT count(*) FROM chatbot_views.v_lookup_spa_bookings"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.guests (guest_id) VALUES ('should-fail')",
}
