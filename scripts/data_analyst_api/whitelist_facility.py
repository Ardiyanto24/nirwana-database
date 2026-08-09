"""
Milestone 3.4 -- Facility/Ops Analyst whitelist.
Aggregate: analyst_views.v_facility_*/v_housekeeping_*/v_maintenance_* (M3.2).
v_maintenance_ticket_daily exposes pending_count separate from
avg_exceeds_sla_threshold as-is (M3.1/M3.2 business rule) -- the API does not
collapse them. Row-level: mart_cleaned.maintenance_tickets.
"""

_PROPERTY_PERIOD_FILTERS = [
    {"param": "property_id", "column": "property_id", "op": "="},
    {"param": "date_from", "column": "period_date", "op": ">="},
    {"param": "date_to", "column": "period_date", "op": "<"},
]

AGGREGATE_WHITELIST = {
    "room-status-daily": {
        "source": "analyst_views.v_facility_room_status_daily",
        "filters": _PROPERTY_PERIOD_FILTERS + [{"param": "room_id", "column": "room_id", "op": "="}],
    },
    "housekeeping-room-type-daily": {"source": "analyst_views.v_housekeeping_room_type_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "housekeeping-property-daily": {"source": "analyst_views.v_housekeeping_property_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "housekeeping-staff-daily": {
        "source": "analyst_views.v_housekeeping_staff_daily",
        "filters": [
            {"param": "staff_id", "column": "staff_id", "op": "="},
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
    "maintenance-ticket-daily": {
        "source": "analyst_views.v_maintenance_ticket_daily",
        "filters": _PROPERTY_PERIOD_FILTERS,
    },
    "maintenance-cost-daily": {"source": "analyst_views.v_maintenance_cost_daily", "filters": _PROPERTY_PERIOD_FILTERS},
    "maintenance-room-recurrence-yearly": {
        "source": "analyst_views.v_maintenance_room_recurrence_yearly",
        "filters": [
            {"param": "room_id", "column": "room_id", "op": "="},
            {"param": "year", "column": "year", "op": "="},
        ],
    },
    "maintenance-property-benchmark-yearly": {
        "source": "analyst_views.v_maintenance_property_benchmark_yearly",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "year", "column": "year", "op": "="},
        ],
    },
    "maintenance-technician-daily": {
        "source": "analyst_views.v_maintenance_technician_daily",
        "filters": [
            {"param": "assigned_staff_id", "column": "assigned_staff_id", "op": "="},
            {"param": "date_from", "column": "period_date", "op": ">="},
            {"param": "date_to", "column": "period_date", "op": "<"},
        ],
    },
}

ROWLEVEL_WHITELIST = {
    "maintenance-tickets": {
        "source": "mart_cleaned.maintenance_tickets",
        "filters": [
            {"param": "property_id", "column": "property_id", "op": "="},
            {"param": "room_id", "column": "room_id", "op": "="},
            {"param": "date_from", "column": "reported_date", "op": ">="},
            {"param": "date_to", "column": "reported_date", "op": "<"},
            {"param": "status", "column": "status", "op": "="},
            {"param": "priority", "column": "priority", "op": "="},
        ],
    },
}
