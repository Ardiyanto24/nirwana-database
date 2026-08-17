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
    # --- Corporate/Financial (Checkpoint 7) ---
    {
        "table": "financial_summary",
        "index_name": "idx_financial_summary_property_period",
        "columns": ["property_id", "period"],
    },
    {
        "table": "payroll",
        "index_name": "idx_payroll_employee_period",
        "columns": ["employee_id", "period"],
    },
    # --- Guests (M6.5 follow-up: fix performa guests_contact_view/guests_profile_view,
    # domain "guests" tidak masuk 6 checkpoint M3.3 di atas -- lihat logs.md M6.5).
    # HANYA guest_id di sini -- guest_id+booking_date pada bookings/spa_bookings dicoba
    # (termasuk varian DESC yang cocok persis arah ORDER BY view) tapi TERBUKTI TIDAK
    # DIPAKAI planner untuk query DISTINCT ON gabungan UNION ALL milik view ini (dites
    # paksa via enable_seqscan=off -- planner tetap re-sort penuh, malah lebih lambat)
    # -- dibuang lagi sesuai Keputusan #2 M3.3: hanya index yang empirically confirmed
    # dipakai planner yang dipertahankan di sini.
    {
        "table": "guests",
        "index_name": "idx_guests_guest_id",
        "columns": ["guest_id"],
    },
]
