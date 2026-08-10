"""
Milestone 4.4 -- guests_profile domain whitelist. 1 view (guests_profile_view).
Mirror of whitelist_guests_pii.py's own_property_column handling.
"""

WHITELIST = {
    "guests-profile": {
        "source": "chatbot_views.guests_profile_view",
        "filters": [
            {"param": "guest_id", "column": "guest_id", "op": "="},
            {"param": "property_id", "column": "last_active_property_id", "op": "="},
        ],
        "own_property_column": "last_active_property_id",
    },
}
