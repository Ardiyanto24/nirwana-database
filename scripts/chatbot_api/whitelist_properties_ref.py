"""Milestone 4.4 -- properties_ref domain whitelist. 1 view, low sensitivity."""

WHITELIST = {
    "properties": {
        "source": "chatbot_views.v_properties_ref",
        "filters": [{"param": "property_id", "column": "property_id", "op": "="}],
    },
}
