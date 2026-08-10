"""
Milestone 4.3 -- role config for facility_chatbot_reader. GRANT_TARGETS
hand-enumerated from scripts/chatbot_views/views_facility.sql (Keputusan #4).
"""

GRANT_TARGETS = [
    "chatbot_views.v_facility_room_status_daily",
    "chatbot_views.v_housekeeping_room_type_daily",
    "chatbot_views.v_housekeeping_property_daily",
    "chatbot_views.v_housekeeping_staff_daily",
    "chatbot_views.v_maintenance_ticket_daily",
    "chatbot_views.v_maintenance_cost_daily",
    "chatbot_views.v_maintenance_room_recurrence_yearly",
    "chatbot_views.v_maintenance_property_benchmark_yearly",
    "chatbot_views.v_maintenance_technician_daily",
    "chatbot_views.v_lookup_rooms",
    "chatbot_views.v_lookup_housekeeping_log",
    "chatbot_views.v_lookup_maintenance_tickets",
]

ROLE_CONFIG = {
    "role": "facility_chatbot_reader",
    "env_var": "FACILITY_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own aggregate view", "SELECT count(*) FROM chatbot_views.v_maintenance_ticket_daily"),
        ("own lookup view", "SELECT count(*) FROM chatbot_views.v_lookup_rooms"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.fact_maintenance_ticket_daily"),
        ("base table bypass (mart_cleaned direct)", "SELECT count(*) FROM mart_cleaned.maintenance_tickets"),
        ("role_permissions (M4.1 Keputusan #7)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        ("cross-domain: spa_event lookup", "SELECT count(*) FROM chatbot_views.v_lookup_spa_bookings"),
        ("cross-domain: financial lookup", "SELECT count(*) FROM chatbot_views.v_lookup_financial_summary"),
        ("cross-domain: guests_pii view", "SELECT count(*) FROM chatbot_views.guests_contact_view"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.maintenance_tickets (ticket_id) VALUES ('should-fail')",
}
