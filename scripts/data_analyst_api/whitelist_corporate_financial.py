"""
Milestone 3.4 -- Corporate/Financial Analyst whitelist.
Aggregate: analyst_views.v_financial_*/v_payroll_* (M3.2). departmental-margin
already excludes Overall/Corporate Overhead at the view level (M3.2 business
rule) -- the API adds no extra filtering logic on top, it just passes through
whatever the view returns. Row-level: mart_cleaned.financial_summary/payroll
-- exclusive to this domain, never exposed via any other domain's whitelist
(see whitelist_hr.py's payroll exclusion note).
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

AGGREGATE_WHITELIST = {
    "departmental-margin": {
        "source": "analyst_views.v_financial_departmental_margin",
        "filters": _PROPERTY_PERIOD_FILTERS + [{"param": "business_line_name", "column": "business_line_name", "op": "="}],
    },
    "gop-overhead": {"source": "analyst_views.v_financial_gop_overhead", "filters": _PROPERTY_PERIOD_FILTERS},
    "revenue-runrate-daily": {"source": "analyst_views.v_financial_revenue_runrate_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "payroll-department-monthly": {
        "source": "analyst_views.v_payroll_department_monthly",
        "filters": _PROPERTY_PERIOD_FILTERS + [{"param": "department_name", "column": "department_name", "op": "="}],
    },
    "service-charge-monthly": {"source": "analyst_views.v_financial_service_charge_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
    "labor-cost-monthly": {"source": "analyst_views.v_financial_labor_cost_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
    "payroll-access-level-monthly": {
        "source": "analyst_views.v_payroll_access_level_monthly",
        "filters": _PROPERTY_PERIOD_FILTERS + [{"param": "access_level_name", "column": "access_level_name", "op": "="}],
    },
    "business-line-group-monthly": {
        "source": "analyst_views.v_financial_business_line_group_monthly",
        "filters": [
            {"param": "business_line_name", "column": "business_line_name", "op": "="},
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
    "property-benchmark-monthly": {"source": "analyst_views.v_financial_property_benchmark_monthly", "filters": _PROPERTY_PERIOD_FILTERS},
}

ROWLEVEL_WHITELIST = {
    "financial-summary": {
        "source": "mart_cleaned.financial_summary",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "period_from", "column": "period", "op": ">="},
            {"param": "period_to", "column": "period", "op": "<"},
            {"param": "department", "column": "department", "op": "="},
        ],
    },
    "payroll": {
        "source": "mart_cleaned.payroll",
        "filters": [
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "period_from", "column": "period", "op": ">="},
            {"param": "period_to", "column": "period", "op": "<"},
        ],
    },
}
