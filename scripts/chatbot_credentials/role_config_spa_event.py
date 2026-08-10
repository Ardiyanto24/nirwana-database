"""
Milestone 4.3 -- role config for spa_event_chatbot_reader. GRANT_TARGETS
hand-enumerated from scripts/chatbot_views/views_spa_event.sql (Keputusan #4).
"""

GRANT_TARGETS = [
    "chatbot_views.v_spa_daily",
    "chatbot_views.v_spa_customer_type_daily",
    "chatbot_views.v_spa_service_daily",
    "chatbot_views.v_event_venue_daily",
    "chatbot_views.v_event_property_daily",
    "chatbot_views.v_event_type_daily",
    "chatbot_views.v_lookup_spa_bookings",
    "chatbot_views.v_lookup_event_bookings",
    "chatbot_views.v_lookup_venues",
]

ROLE_CONFIG = {
    "role": "spa_event_chatbot_reader",
    "env_var": "SPA_EVENT_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own aggregate view", "SELECT count(*) FROM chatbot_views.v_spa_daily"),
        ("own lookup view", "SELECT count(*) FROM chatbot_views.v_lookup_spa_bookings"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.fact_spa_daily"),
        ("base table bypass (mart_cleaned direct)", "SELECT count(*) FROM mart_cleaned.spa_bookings"),
        ("role_permissions (M4.1 Keputusan #7)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        ("cross-domain: facility lookup", "SELECT count(*) FROM chatbot_views.v_lookup_rooms"),
        ("cross-domain: guests_profile view", "SELECT count(*) FROM chatbot_views.guests_profile_view"),
        ("cross-domain: employees_directory view", "SELECT count(*) FROM chatbot_views.v_employees_directory"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.spa_bookings (spa_booking_id) VALUES ('should-fail')",
}
