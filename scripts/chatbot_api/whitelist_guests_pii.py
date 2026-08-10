"""
Milestone 4.4 -- guests_pii domain whitelist. 1 view (guests_contact_view).
own_property_column = "last_active_property_id" -- guests aren't natively
property-scoped (Metadata.md: guests is a cross-property master), M4.2
derives it from the guest's most recent booking/spa_booking.
"""

WHITELIST = {
    "guests-contact": {
        "source": "chatbot_views.guests_contact_view",
        "filters": [
            {"param": "guest_id", "column": "guest_id", "op": "="},
            {"param": "property_id", "column": "last_active_property_id", "op": "="},
        ],
        "own_property_column": "last_active_property_id",
    },
}
