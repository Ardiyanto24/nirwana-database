"""
Milestone 4.3 -- role config for reservation_chatbot_reader. GRANT_TARGETS
hand-enumerated from scripts/chatbot_views/views_reservation.sql (Keputusan
#4 -- no whitelist file to derive from, Milestone 4.4/API doesn't exist yet).
All 10 views live in chatbot_views -- no mart_aggregated/mart_cleaned grants
at all (Keputusan #3).
"""

GRANT_TARGETS = [
    "chatbot_views.v_reservation_room_type_daily",
    "chatbot_views.v_reservation_channel_daily",
    "chatbot_views.v_reservation_los_daily",
    "chatbot_views.v_reservation_property_daily",
    "chatbot_views.v_reservation_gop_impact_monthly",
    "chatbot_views.v_reservation_pricing_deviation",
    "chatbot_views.v_reservation_loyalty_daily",
    "chatbot_views.v_reservation_nationality_daily",
    "chatbot_views.v_lookup_bookings",
    "chatbot_views.v_lookup_daily_occupancy",
]

ROLE_CONFIG = {
    "role": "reservation_chatbot_reader",
    "env_var": "RESERVATION_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own aggregate view", "SELECT count(*) FROM chatbot_views.v_reservation_room_type_daily"),
        ("own lookup view", "SELECT count(*) FROM chatbot_views.v_lookup_bookings"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.fact_revenue_room_type_daily"),
        ("base table bypass (mart_cleaned direct)", "SELECT count(*) FROM mart_cleaned.bookings"),
        ("role_permissions (M4.1 Keputusan #7 -- never a target)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        ("cross-domain: fnb view", "SELECT count(*) FROM chatbot_views.v_fnb_outlet_daily"),
        ("cross-domain: guests_pii view", "SELECT count(*) FROM chatbot_views.guests_contact_view"),
        ("cross-domain: payroll lookup", "SELECT count(*) FROM chatbot_views.v_lookup_payroll"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.bookings (booking_id) VALUES ('should-fail')",
}
