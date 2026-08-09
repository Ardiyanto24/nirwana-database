"""
Milestone 3.4 -- Revenue Analyst whitelist.
Aggregate: analyst_views.v_revenue_* (M3.2). Row-level: mart_cleaned.bookings/
pricing_history (M3.1 mapping). Filter columns/date-range mirror the indexes
built in M3.3 (property_id, period_date/check_in_date/date) so these queries
hit the indexed path, not a sequential scan.
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

AGGREGATE_WHITELIST = {
    "room-type-daily": {"source": "analyst_views.v_revenue_room_type_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "channel-daily": {"source": "analyst_views.v_revenue_channel_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "los-daily": {"source": "analyst_views.v_revenue_los_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "property-daily": {"source": "analyst_views.v_revenue_property_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "gop-impact-monthly": {"source": "analyst_views.v_revenue_gop_impact_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
    "pricing-deviation": {"source": "analyst_views.v_revenue_pricing_deviation", "filters": _PROPERTY_PERIOD_FILTERS},
    "loyalty-daily": {"source": "analyst_views.v_revenue_loyalty_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "nationality-daily": {"source": "analyst_views.v_revenue_nationality_daily", "filters": _PROPERTY_PERIOD_FILTERS},
}

ROWLEVEL_WHITELIST = {
    "bookings": {
        "source": "mart_cleaned.bookings",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "date_from", "column": "check_in_date", "op": ">="},
            {"param": "date_to", "column": "check_in_date", "op": "<"},
            {"param": "status", "column": "status", "op": "="},
        ],
    },
    "pricing-history": {
        "source": "mart_cleaned.pricing_history",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "date_from", "column": "date", "op": ">="},
            {"param": "date_to", "column": "date", "op": "<"},
        ],
    },
}
