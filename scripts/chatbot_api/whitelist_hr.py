"""
Milestone 4.4 -- hr domain whitelist. Source: chatbot_views (M4.2) --
8 view agregat + 2 view lookup (staff_shifts/employee_performance). TIDAK ADA
payroll di sini sama sekali -- business rule kritis carry-over M3.1 #2,
berlaku sama untuk chatbot (M4.3 sudah membuktikan hr_chatbot_reader tidak
bisa akses payroll dalam bentuk apa pun).
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

_PROPERTY_REVIEW_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "review_period", "column": "review_period", "op": "="},
]

WHITELIST = {
    "attendance-daily": {"source": "chatbot_views.v_hr_attendance_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "employee-monthly": {
        "source": "chatbot_views.v_hr_employee_monthly",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
    "employee-performance-semester": {
        "source": "chatbot_views.v_hr_employee_performance_semester",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "review_period", "column": "review_period", "op": "="},
        ],
    },
    "turnover-snapshot": {
        "source": "chatbot_views.v_hr_turnover_snapshot",
        "filters": [{"param": "property_id", "column": "property_id", "op": "="}],
    },
    "headcount-status-daily": {"source": "chatbot_views.v_hr_headcount_status_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "performance-department-semester": {"source": "chatbot_views.v_hr_performance_department_semester", "filters": _PROPERTY_REVIEW_PERIOD_FILTERS},
    "performance-by-status-semester": {"source": "chatbot_views.v_hr_performance_by_status_semester", "filters": _PROPERTY_REVIEW_PERIOD_FILTERS},
    "watchlist-monthly": {
        "source": "chatbot_views.v_hr_watchlist_monthly",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
    "staff-shifts": {
        "source": "chatbot_views.v_lookup_staff_shifts",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "date_from", "column": "date", "op": ">="},
            {"param": "date_to", "column": "date", "op": "<"},
            {"param": "status", "column": "status", "op": "="},
        ],
    },
    "employee-performance": {
        "source": "chatbot_views.v_lookup_employee_performance",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "employee_id", "op": "="},
            {"param": "review_period", "column": "review_period", "op": "="},
        ],
    },
}
