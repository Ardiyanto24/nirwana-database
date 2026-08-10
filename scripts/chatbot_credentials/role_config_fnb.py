"""
Milestone 4.3 -- role config for fnb_chatbot_reader. GRANT_TARGETS
hand-enumerated from scripts/chatbot_views/views_fnb.sql (Keputusan #4).
"""

GRANT_TARGETS = [
    "chatbot_views.v_fnb_outlet_daily",
    "chatbot_views.v_fnb_category_daily",
    "chatbot_views.v_fnb_hourly",
    "chatbot_views.v_fnb_customer_type_daily",
    "chatbot_views.v_fnb_menu_item_daily",
    "chatbot_views.v_fnb_waste_daily",
    "chatbot_views.v_fnb_inventory_status",
    "chatbot_views.v_fnb_ingredient_price_daily",
    "chatbot_views.v_lookup_fnb_inventory",
    "chatbot_views.v_lookup_fnb_transactions",
    "chatbot_views.v_lookup_recipe_bom",
]

ROLE_CONFIG = {
    "role": "fnb_chatbot_reader",
    "env_var": "FNB_CHATBOT_READER_DB_URL",
    "grant_targets": GRANT_TARGETS,
    "allow_checks": [
        ("own aggregate view", "SELECT count(*) FROM chatbot_views.v_fnb_outlet_daily"),
        ("own lookup view", "SELECT count(*) FROM chatbot_views.v_lookup_fnb_transactions"),
    ],
    "deny_checks": [
        ("base table bypass (mart_aggregated direct)", "SELECT count(*) FROM mart_aggregated.fact_fnb_outlet_daily"),
        ("base table bypass (mart_cleaned direct)", "SELECT count(*) FROM mart_cleaned.fnb_transactions"),
        ("role_permissions (M4.1 Keputusan #7)", "SELECT count(*) FROM mart_cleaned.role_permissions"),
        ("cross-domain: reservation lookup", "SELECT count(*) FROM chatbot_views.v_lookup_bookings"),
        ("cross-domain: guests_profile view", "SELECT count(*) FROM chatbot_views.guests_profile_view"),
        ("cross-domain: hr lookup", "SELECT count(*) FROM chatbot_views.v_lookup_staff_shifts"),
    ],
    "write_check_sql": "INSERT INTO mart_cleaned.fnb_transactions (transaction_id) VALUES ('should-fail')",
}
