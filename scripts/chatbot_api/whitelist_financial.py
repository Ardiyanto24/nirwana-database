"""
Milestone 4.4 -- financial domain whitelist. Source: chatbot_views (M4.2) --
9 view agregat + 2 view lookup (financial_summary/payroll). Business rule
kritis carry-over M3.1 #1: v_financial_departmental_margin sudah exclude
'Overall'/'Corporate Overhead' permanen di level view (M4.2) -- tidak perlu
diulang di sini.
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

WHITELIST = {
    "departmental-margin": {"source": "chatbot_views.v_financial_departmental_margin", "filters": _PROPERTY_PERIOD_FILTERS},
    "gop-overhead": {"source": "chatbot_views.v_financial_gop_overhead", "filters": _PROPERTY_PERIOD_FILTERS},
    "revenue-runrate-daily": {"source": "chatbot_views.v_financial_revenue_runrate_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "payroll-department-monthly": {"source": "chatbot_views.v_payroll_department_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
    "service-charge-monthly": {"source": "chatbot_views.v_financial_service_charge_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
    "labor-cost-monthly": {"source": "chatbot_views.v_financial_labor_cost_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
    "payroll-access-level-monthly": {"source": "chatbot_views.v_payroll_access_level_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
    "business-line-group-monthly": {
        "source": "chatbot_views.v_financial_business_line_group_monthly",
        "filters": [
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
    "property-benchmark-monthly": {"source": "chatbot_views.v_financial_property_benchmark_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
    "financial-summary": {
        "source": "chatbot_views.v_lookup_financial_summary",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "period", "column": "period", "op": "="},
            {"param": "department", "column": "department", "op": "="},
        ],
    },
    "payroll": {
        "source": "chatbot_views.v_lookup_payroll",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "period", "column": "period", "op": "="},
        ],
    },
}
