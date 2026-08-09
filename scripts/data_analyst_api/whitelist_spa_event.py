"""
Milestone 3.4 -- Spa & Event Analyst whitelist.
Aggregate: analyst_views.v_spa_*/v_event_* (M3.2). Row-level:
mart_cleaned.event_bookings. Repeat-client-event and spa x event cross-sell
are intentionally NOT exposed here -- M3.1/M3.2 business rule: client_name is
free text with no structured ID, not reliable enough for an automated metric.
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

AGGREGATE_WHITELIST = {
    "spa-daily": {"source": "analyst_views.v_spa_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "spa-customer-type-daily": {"source": "analyst_views.v_spa_customer_type_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "spa-service-daily": {"source": "analyst_views.v_spa_service_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "event-venue-daily": {
        "source": "analyst_views.v_event_venue_daily",
        "filters": [
            {"param": "venue_id", "column": "venue_id", "op": "="},
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
    "event-property-daily": {"source": "analyst_views.v_event_property_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "event-type-daily": {"source": "analyst_views.v_event_type_daily", "filters": _PROPERTY_PERIOD_FILTERS},
}

ROWLEVEL_WHITELIST = {
    "event-bookings": {
        "source": "mart_cleaned.event_bookings",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "venue_id", "column": "venue_id", "op": "="},
            {"param": "date_from", "column": "event_date", "op": ">="},
            {"param": "date_to", "column": "event_date", "op": "<"},
            {"param": "event_type", "column": "event_type", "op": "="},
            {"param": "status", "column": "status", "op": "="},
        ],
    },
}
