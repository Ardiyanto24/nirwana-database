"""
Milestone 4.4 -- reservation domain whitelist. Source: chatbot_views (M4.2) --
8 view agregat (fact_revenue_*) + 2 view lookup (bookings/daily_occupancy).
property_id sengaja tidak dikecualikan dari filters di sini meski
own_property akan meng-override-nya di runtime (main.py) -- filter tetap
berguna untuk role all_properties yang ingin mempersempit ke 1 properti.
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

WHITELIST = {
    "room-type-daily": {"source": "chatbot_views.v_reservation_room_type_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "channel-daily": {"source": "chatbot_views.v_reservation_channel_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "los-daily": {"source": "chatbot_views.v_reservation_los_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "property-daily": {"source": "chatbot_views.v_reservation_property_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "gop-impact-monthly": {"source": "chatbot_views.v_reservation_gop_impact_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
    "pricing-deviation": {"source": "chatbot_views.v_reservation_pricing_deviation", "filters": _PROPERTY_PERIOD_FILTERS},
    "loyalty-daily": {"source": "chatbot_views.v_reservation_loyalty_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "nationality-daily": {"source": "chatbot_views.v_reservation_nationality_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "bookings": {
        "source": "chatbot_views.v_lookup_bookings",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "date_from", "column": "check_in_date", "op": ">="},
            {"param": "date_to", "column": "check_in_date", "op": "<"},
            {"param": "status", "column": "status", "op": "="},
        ],
    },
    "daily-occupancy": {
        "source": "chatbot_views.v_lookup_daily_occupancy",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "date_from", "column": "date", "op": ">="},
            {"param": "date_to", "column": "date", "op": "<"},
        ],
    },
}
