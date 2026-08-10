"""Milestone 4.4 -- employees_directory domain whitelist. 1 view."""

WHITELIST = {
    "employees": {
        "source": "chatbot_views.v_employees_directory",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "department_name", "column": "department_name", "op": "="},
        ],
    },
}
