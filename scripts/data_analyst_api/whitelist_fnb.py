"""
Milestone 3.4 -- F&B Analyst whitelist.
Aggregate: analyst_views.v_fnb_* (M3.2) -- outlet-keyed fact tables expose
property_id via the dim_outlet join, so both are valid filters. Row-level:
mart_cleaned.fnb_transactions (902k rows, largest table in the project,
indexed on (outlet_id, transaction_datetime) in M3.3).
"""

_OUTLET_PROPERTY_PERIOD_FILTERS = [
    {"param": "outlet_id", "column": "outlet_id", "op": "="},
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

AGGREGATE_WHITELIST = {
    "outlet-daily": {"source": "analyst_views.v_fnb_outlet_daily", "filters": _OUTLET_PROPERTY_PERIOD_FILTERS},
    "category-daily": {"source": "analyst_views.v_fnb_category_daily", "filters": _OUTLET_PROPERTY_PERIOD_FILTERS},
    "hourly": {
        "source": "analyst_views.v_fnb_hourly",
        "filters": _OUTLET_PROPERTY_PERIOD_FILTERS + [{"param": "hour_of_day", "column": "hour_of_day", "op": "="}],
    },
    "customer-type-daily": {"source": "analyst_views.v_fnb_customer_type_daily", "filters": _OUTLET_PROPERTY_PERIOD_FILTERS},
    "menu-item-daily": {"source": "analyst_views.v_fnb_menu_item_daily", "filters": _OUTLET_PROPERTY_PERIOD_FILTERS},
    "waste-daily": {"source": "analyst_views.v_fnb_waste_daily", "filters": _OUTLET_PROPERTY_PERIOD_FILTERS},
    "inventory-status": {"source": "analyst_views.v_fnb_inventory_status", "filters": _OUTLET_PROPERTY_PERIOD_FILTERS},
    "ingredient-price-daily": {
        "source": "analyst_views.v_fnb_ingredient_price_daily",
        "filters": [
            {"param": "ingredient_id", "column": "ingredient_id", "op": "="},
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
}

ROWLEVEL_WHITELIST = {
    "fnb-transactions": {
        "source": "mart_cleaned.fnb_transactions",
        "filters": [
            {"param": "outlet_id", "column": "outlet_id", "op": "="},
            {"param": "date_from", "column": "transaction_datetime", "op": ">="},
            {"param": "date_to", "column": "transaction_datetime", "op": "<"},
            {"param": "customer_type", "column": "customer_type", "op": "="},
            {"param": "item_name", "column": "item_name", "op": "="},
        ],
    },
}
