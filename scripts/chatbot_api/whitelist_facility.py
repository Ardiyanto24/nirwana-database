"""
Milestone 4.4 -- facility domain whitelist. Source: chatbot_views (M4.2) --
9 view agregat + 3 view lookup (rooms/housekeeping_log/maintenance_tickets).

v_housekeeping_staff_daily/v_maintenance_technician_daily punya property_id
hasil koreksi M4.4 (lihat scripts/chatbot_views/views_facility.sql) --
sebelumnya cuma staff_id/period_date, tidak bisa difilter own_property sama
sekali.
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

WHITELIST = {
    "room-status-daily": {"source": "chatbot_views.v_facility_room_status_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "housekeeping-room-type-daily": {"source": "chatbot_views.v_housekeeping_room_type_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "housekeeping-property-daily": {"source": "chatbot_views.v_housekeeping_property_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "housekeeping-staff-daily": {
        "source": "chatbot_views.v_housekeeping_staff_daily",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "staff_id", "op": "="},
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
    "maintenance-ticket-daily": {"source": "chatbot_views.v_maintenance_ticket_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "maintenance-cost-daily": {"source": "chatbot_views.v_maintenance_cost_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "maintenance-room-recurrence-yearly": {
        "source": "chatbot_views.v_maintenance_room_recurrence_yearly",
        "filters": [{"param": "property_id", "column": "property_id", "op": "="}, {"param": "year", "column": "year", "op": "="}],
    },
    "maintenance-property-benchmark-yearly": {
        "source": "chatbot_views.v_maintenance_property_benchmark_yearly",
        "filters": [{"param": "property_id", "column": "property_id", "op": "="}, {"param": "year", "column": "year", "op": "="}],
    },
    "maintenance-technician-daily": {
        "source": "chatbot_views.v_maintenance_technician_daily",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "assigned_staff_id", "op": "="},
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
    "rooms": {
        "source": "chatbot_views.v_lookup_rooms",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "status", "column": "status", "op": "="},
        ],
    },
    "housekeeping-log": {
        "source": "chatbot_views.v_lookup_housekeeping_log",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "staff_id", "op": "="},
            {"param": "date_from", "column": "date", "op": ">="},
            {"param": "date_to", "column": "date", "op": "<"},
        ],
    },
    "maintenance-tickets": {
        "source": "chatbot_views.v_lookup_maintenance_tickets",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "employee_id", "column": "assigned_staff_id", "op": "="},
            {"param": "status", "column": "status", "op": "="},
            {"param": "priority", "column": "priority", "op": "="},
        ],
    },
}
