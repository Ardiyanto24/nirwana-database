"""
Milestone 3.4 -- HR Analyst whitelist.
Aggregate: analyst_views.v_hr_* (M3.2, property_id/department_id are the 2
mandatory filters per M3.1 -- the only domain with both at once). Row-level:
mart_cleaned.staff_shifts/employee_performance. Payroll is NOT included here
in any form -- exclusive to Corporate/Financial (whitelist_corporate_financial.py).
"""

_PROPERTY_DEPARTMENT_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "department_name", "column": "department_name", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

_EMPLOYEE_PERIOD_FILTERS = [
    {"param": "employee_id", "column": "employee_id", "op": "="},
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

AGGREGATE_WHITELIST = {
    "attendance-daily": {"source": "analyst_views.v_hr_attendance_daily", "filters": _PROPERTY_DEPARTMENT_PERIOD_FILTERS},
    "employee-monthly": {"source": "analyst_views.v_hr_employee_monthly", "filters": _EMPLOYEE_PERIOD_FILTERS},
    "employee-performance-semester": {
        "source": "analyst_views.v_hr_employee_performance_semester",
        "filters": [
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "review_period", "column": "review_period", "op": "="},
        ],
    },
    "turnover-snapshot": {"source": "analyst_views.v_hr_turnover_snapshot", "filters": _PROPERTY_DEPARTMENT_PERIOD_FILTERS},
    "headcount-status-daily": {
        "source": "analyst_views.v_hr_headcount_status_daily",
        "filters": _PROPERTY_DEPARTMENT_PERIOD_FILTERS + [{"param": "status_name", "column": "status_name", "op": "="}],
    },
    "performance-department-semester": {
        "source": "analyst_views.v_hr_performance_department_semester",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "department_name", "column": "department_name", "op": "="},
            {"param": "review_period", "column": "review_period", "op": "="},
        ],
    },
    "performance-by-status-semester": {
        "source": "analyst_views.v_hr_performance_by_status_semester",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "status_name", "column": "status_name", "op": "="},
            {"param": "review_period", "column": "review_period", "op": "="},
        ],
    },
    "watchlist-monthly": {"source": "analyst_views.v_hr_watchlist_monthly", "filters": _EMPLOYEE_PERIOD_FILTERS},
}

ROWLEVEL_WHITELIST = {
    "staff-shifts": {
        "source": "mart_cleaned.staff_shifts",
        "filters": [
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "date_from", "column": "date", "op": ">="},
            {"param": "date_to", "column": "date", "op": "<"},
            {"param": "status", "column": "status", "op": "="},
        ],
    },
    "employee-performance": {
        "source": "mart_cleaned.employee_performance",
        "filters": [
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "review_period", "column": "review_period", "op": "="},
        ],
    },
}
