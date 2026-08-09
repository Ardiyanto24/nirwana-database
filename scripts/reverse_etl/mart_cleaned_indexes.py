"""
Milestone 3.3 -- index design for mart_cleaned (serving PostgreSQL), consumed by
reindex_analyze.py. Populated per-domain across M3.3's checkpoints (Revenue, F&B,
Facility/Ops, Spa & Event, HR, Corporate/Financial) -- see
docs/08-serving-data-analyst/index-baseline-analyst.md for the full rationale and
EXPLAIN ANALYZE evidence per entry.

Columns chosen from the "Filter Wajib" per role in
docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md (M3.1) -- entity/property
filter column(s) first, then date range, matching the composite-index convention in
rancangan-arsitektur-data-platform-elt.md Bagian 9.3.2.

Only tables/columns empirically confirmed to be used by the query planner (EXPLAIN
ANALYZE showing Index/Bitmap Index Scan, not Seq Scan) are kept here -- Milestone 3.3
Keputusan #2 (decisions.md): no blanket indexing of small tables.
"""

MART_CLEANED_INDEXES = [
    # --- Revenue (Checkpoint 2) ---
    {
        "table": "bookings",
        "index_name": "idx_bookings_property_checkin",
        "columns": ["property_id", "check_in_date"],
    },
    {
        "table": "pricing_history",
        "index_name": "idx_pricing_history_property_date",
        "columns": ["property_id", "date"],
    },
    # --- F&B (Checkpoint 3) ---
    {
        "table": "fnb_transactions",
        "index_name": "idx_fnb_transactions_outlet_datetime",
        "columns": ["outlet_id", "transaction_datetime"],
    },
    # --- Facility/Ops (Checkpoint 4) ---
    {
        "table": "maintenance_tickets",
        "index_name": "idx_maintenance_tickets_property_reported",
        "columns": ["property_id", "reported_date"],
    },
    # --- Spa & Event (Checkpoint 5) ---
    {
        "table": "event_bookings",
        "index_name": "idx_event_bookings_property_eventdate",
        "columns": ["property_id", "event_date"],
    },
    # --- HR (Checkpoint 6) ---
    {
        "table": "staff_shifts",
        "index_name": "idx_staff_shifts_employee_date",
        "columns": ["employee_id", "date"],
    },
    {
        "table": "employee_performance",
        "index_name": "idx_employee_performance_employee_period",
        "columns": ["employee_id", "review_period"],
    },
]
