"""
Milestone 3.3 -- index design for mart_aggregated (serving PostgreSQL), consumed by
reindex_analyze.py. Replaces the M5.5 provisional example_indexes.py (which existed
only to prove the REINDEX/ANALYZE-after-swap mechanism worked, docstring explicitly
said "Jangan dianggap sebagai desain index M3.3"). Populated per-domain across M3.3's
checkpoints (Revenue, F&B, Facility/Ops, Spa & Event, HR, Corporate/Financial) -- see
docs/08-serving-data-analyst/index-baseline-analyst.md for the full rationale and
EXPLAIN ANALYZE evidence per entry.

Columns chosen from the "Filter Wajib" per role in
docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md (M3.1) and the join columns
in docs/08-serving-data-analyst/view-query-pattern-analyst.md (M3.2) -- entity/property
filter column(s) first, then date range, matching the composite-index convention in
rancangan-arsitektur-data-platform-elt.md Bagian 9.3.2.

Only tables/columns empirically confirmed to be used by the query planner (EXPLAIN
ANALYZE showing Index/Bitmap Index Scan, not Seq Scan) are kept here -- Milestone 3.3
Keputusan #2 (decisions.md): no blanket indexing of small tables. Several mart_aggregated
fact tables are small dimension-style aggregates (hundreds of rows) where Postgres will
sequential-scan regardless of indexing -- those are deliberately left out, documented in
index-baseline-analyst.md rather than indexed "for completeness."
"""

MART_AGGREGATED_INDEXES = [
    # --- Revenue (Checkpoint 2) ---
    {
        "table": "fact_revenue_room_type_daily",
        "index_name": "idx_fact_revenue_room_type_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_channel_daily",
        "index_name": "idx_fact_revenue_channel_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_los_daily",
        "index_name": "idx_fact_revenue_los_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_property_daily",
        "index_name": "idx_fact_revenue_property_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_pricing_deviation",
        "index_name": "idx_fact_revenue_pricing_deviation_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_loyalty_daily",
        "index_name": "idx_fact_revenue_loyalty_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_revenue_nationality_daily",
        "index_name": "idx_fact_revenue_nationality_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    # fact_revenue_gop_impact_monthly (180 rows) deliberately excluded -- too small
    # for Postgres to ever prefer an index scan over seq scan (Keputusan #2).

    # --- F&B (Checkpoint 3) ---
    # Fact tables here are keyed by outlet_id (not property_id directly -- an outlet
    # always belongs to exactly 1 property, resolved via dim_outlet in analyst_views).
    {
        "table": "fact_fnb_outlet_daily",
        "index_name": "idx_fact_fnb_outlet_daily_outlet_period",
        "columns": ["outlet_id", "period_date"],
    },
    {
        "table": "fact_fnb_category_daily",
        "index_name": "idx_fact_fnb_category_daily_outlet_period",
        "columns": ["outlet_id", "period_date"],
    },
    {
        "table": "fact_fnb_hourly",
        "index_name": "idx_fact_fnb_hourly_outlet_period",
        "columns": ["outlet_id", "period_date"],
    },
    {
        "table": "fact_fnb_customer_type_daily",
        "index_name": "idx_fact_fnb_customer_type_daily_outlet_period",
        "columns": ["outlet_id", "period_date"],
    },
    {
        "table": "fact_fnb_menu_item_daily",
        "index_name": "idx_fact_fnb_menu_item_daily_outlet_period",
        "columns": ["outlet_id", "period_date"],
    },
    {
        "table": "fact_fnb_waste_daily",
        "index_name": "idx_fact_fnb_waste_daily_outlet_period",
        "columns": ["outlet_id", "period_date"],
    },
    {
        "table": "fact_fnb_ingredient_price_daily",
        "index_name": "idx_fact_fnb_ingredient_price_daily_ingredient_period",
        "columns": ["ingredient_id", "period_date"],
    },
    # fact_fnb_inventory_status (17 rows -- current-state snapshot) deliberately
    # excluded, same reasoning as fact_revenue_gop_impact_monthly.

    # --- Facility/Ops (Checkpoint 4) ---
    {
        "table": "fact_housekeeping_room_type_daily",
        "index_name": "idx_fact_housekeeping_room_type_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_housekeeping_property_daily",
        "index_name": "idx_fact_housekeeping_property_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_housekeeping_staff_daily",
        "index_name": "idx_fact_housekeeping_staff_daily_staff_period",
        "columns": ["staff_id", "period_date"],
    },
    {
        "table": "fact_maintenance_ticket_daily",
        "index_name": "idx_fact_maintenance_ticket_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_maintenance_cost_daily",
        "index_name": "idx_fact_maintenance_cost_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_maintenance_technician_daily",
        "index_name": "idx_fact_maintenance_technician_daily_staff_period",
        "columns": ["assigned_staff_id", "period_date"],
    },
    {
        "table": "fact_maintenance_room_recurrence_yearly",
        "index_name": "idx_fact_maintenance_room_recurrence_yearly_room_year",
        "columns": ["room_id", "year"],
    },
    # fact_facility_room_status_daily (549 rows, current-state snapshot) and
    # fact_maintenance_property_benchmark_yearly (20 rows) deliberately excluded --
    # too small (Keputusan #2).

    # --- Spa & Event (Checkpoint 5) ---
    {
        "table": "fact_spa_daily",
        "index_name": "idx_fact_spa_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_spa_customer_type_daily",
        "index_name": "idx_fact_spa_customer_type_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_spa_service_daily",
        "index_name": "idx_fact_spa_service_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_event_venue_daily",
        "index_name": "idx_fact_event_venue_daily_venue_period",
        "columns": ["venue_id", "period_date"],
    },
    {
        "table": "fact_event_property_daily",
        "index_name": "idx_fact_event_property_daily_property_period",
        "columns": ["property_id", "period_date"],
    },
    {
        "table": "fact_event_type_daily",
        "index_name": "idx_fact_event_type_daily_property_period",
        "columns": ["property_id", "period_date"],
    },

    # --- HR (Checkpoint 6) ---
    # HR is the only domain with 2 mandatory filters at once (property_id AND
    # department_id, per pemetaan-pola-akses-analyst.md #5).
    {
        "table": "fact_hr_attendance_daily",
        "index_name": "idx_fact_hr_attendance_daily_property_department_period",
        "columns": ["property_id", "department_id", "period_date"],
    },
    {
        "table": "fact_hr_employee_monthly",
        "index_name": "idx_fact_hr_employee_monthly_employee_period",
        "columns": ["employee_id", "period_date"],
    },
    {
        "table": "fact_hr_employee_performance_semester",
        "index_name": "idx_fact_hr_employee_performance_semester_employee_period",
        "columns": ["employee_id", "review_period"],
    },
    {
        "table": "fact_hr_watchlist_monthly",
        "index_name": "idx_fact_hr_watchlist_monthly_employee_period",
        "columns": ["employee_id", "period_date"],
    },
    # dim_employee (755 rows) tested empirically per Keputusan #2 despite being a small
    # dimension table -- 3 large HR views (24k+24k+3.7k rows) join through
    # dim_employee.property_id/department_id (M5.7 retrofit), so the join-side index is
    # worth checking even though the table itself is small.
    {
        "table": "dim_employee",
        "index_name": "idx_dim_employee_property",
        "columns": ["property_id"],
    },
    # fact_hr_turnover_snapshot (43), fact_hr_headcount_status_daily (89),
    # fact_hr_performance_department_semester (258), fact_hr_performance_by_status_semester
    # (90) deliberately excluded -- snapshot/semester-grain tables in the hundreds of rows,
    # far below any table that has empirically benefited from an index so far (Keputusan #2).
]
