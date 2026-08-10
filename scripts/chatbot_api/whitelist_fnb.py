"""
Milestone 4.4 -- fnb domain whitelist. Source: chatbot_views (M4.2) --
8 view agregat + 3 view lookup (fnb_inventory/fnb_transactions/recipe_bom).
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

WHITELIST = {
    "outlet-daily": {"source": "chatbot_views.v_fnb_outlet_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "category-daily": {"source": "chatbot_views.v_fnb_category_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "hourly": {"source": "chatbot_views.v_fnb_hourly", "filters": _PROPERTY_PERIOD_FILTERS},
    "customer-type-daily": {"source": "chatbot_views.v_fnb_customer_type_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "menu-item-daily": {"source": "chatbot_views.v_fnb_menu_item_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "waste-daily": {"source": "chatbot_views.v_fnb_waste_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "inventory-status": {"source": "chatbot_views.v_fnb_inventory_status", "filters": _PROPERTY_PERIOD_FILTERS},
    "ingredient-price-daily": {
        "source": "chatbot_views.v_fnb_ingredient_price_daily",
        "filters": [
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
    "fnb-inventory": {
        "source": "chatbot_views.v_lookup_fnb_inventory",
        "filters": [{"param": "property_id", "column": "property_id", "op": "="}],
    },
    "fnb-transactions": {
        "source": "chatbot_views.v_lookup_fnb_transactions",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "outlet_id", "column": "outlet_id", "op": "="},
        ],
    },
    "recipe-bom": {
        "source": "chatbot_views.v_lookup_recipe_bom",
        "filters": [{"param": "item_name", "column": "item_name", "op": "="}],
    },
}
