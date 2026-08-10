"""
Milestone 4.4 -- spa_event domain whitelist. Source: chatbot_views (M4.2) --
6 view agregat + 3 view lookup (spa_bookings/event_bookings/venues).
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

WHITELIST = {
    "spa-daily": {"source": "chatbot_views.v_spa_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "spa-customer-type-daily": {"source": "chatbot_views.v_spa_customer_type_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "spa-service-daily": {"source": "chatbot_views.v_spa_service_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "event-venue-daily": {"source": "chatbot_views.v_event_venue_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "event-property-daily": {"source": "chatbot_views.v_event_property_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "event-type-daily": {"source": "chatbot_views.v_event_type_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "spa-bookings": {
        "source": "chatbot_views.v_lookup_spa_bookings",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "date_from", "column": "service_date", "op": ">="},
            {"param": "date_to", "column": "service_date", "op": "<"},
            {"param": "status", "column": "status", "op": "="},
        ],
    },
    "event-bookings": {
        "source": "chatbot_views.v_lookup_event_bookings",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "date_from", "column": "event_date", "op": ">="},
            {"param": "date_to", "column": "event_date", "op": "<"},
            {"param": "status", "column": "status", "op": "="},
        ],
    },
    "venues": {
        "source": "chatbot_views.v_lookup_venues",
        "filters": [{"param": "property_id", "column": "property_id", "op": "="}],
    },
}
