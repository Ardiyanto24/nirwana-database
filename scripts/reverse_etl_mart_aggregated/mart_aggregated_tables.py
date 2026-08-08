"""
Daftar 76 tabel mart_aggregated untuk Milestone 5.5 (reverse ETL BigQuery ->
serving Postgres). Hardcoded (bukan dynamic discovery dari
INFORMATION_SCHEMA) -- decisions.md Keputusan #1: konsisten preseden M2.4
(serving_tables.py) dan filosofi eksplisit project ini; dynamic discovery
bisa ikut menyinkronkan tabel yang kebetulan ada di BigQuery tapi belum
sengaja stabil (mis. promote.py gagal sebagian).

Domain di sini mengikuti struktur folder dbt
warehouse/models/mart_aggregated/ (M5.3 Keputusan #2 -- hybrid: 5 folder
align 1:1 dengan skema produksi, hr_finance/ dipecah jadi 2 subfolder
hr/corporate_financial). Dihitung ulang langsung dari isi folder (bukan dari
dokumentasi) saat breakdown M5.5 -- persis 76 (27 dimension + 49 fact).

TIDAK termasuk fact_ml_occupancy_forecast_property_room_type (folder
ml_feedback/, tag dbt ml_feedback_loop, M5.4) -- decisions.md Keputusan #2:
skema tabel itu belum final (provisional, menunggu tim ML Engineer), sengaja
ditunda dari sync M5.5.

BigQuery table id: mart_aggregated.<table> (TANPA prefix domain -- beda dari
mart_cleaned yang di-prefix mart_cleaned__, lihat sync.py). PostgreSQL table:
schema mart_aggregated, nama tabel BARE <table> (sama seperti BigQuery,
tidak perlu strip prefix apa pun).
"""

MART_AGGREGATED_TABLES = [
    # domain (dokumentasi asal, folder dbt -- tidak dipakai di BigQuery/Postgres side), table
    ("corporate_master", "dim_property"),
    ("corporate_master", "dim_employee"),
    ("corporate_master", "dim_department"),
    ("corporate_master", "dim_customer_type"),

    ("reservation_revenue", "dim_room_type"),
    ("reservation_revenue", "dim_room"),
    ("reservation_revenue", "dim_channel"),
    ("reservation_revenue", "dim_loyalty_tier"),
    ("reservation_revenue", "dim_nationality_group"),
    ("reservation_revenue", "dim_pricing_reason"),
    ("reservation_revenue", "fact_revenue_room_type_daily"),
    ("reservation_revenue", "fact_revenue_channel_daily"),
    ("reservation_revenue", "fact_revenue_los_daily"),
    ("reservation_revenue", "fact_revenue_property_daily"),
    ("reservation_revenue", "fact_revenue_gop_impact_monthly"),
    ("reservation_revenue", "fact_revenue_pricing_deviation"),
    ("reservation_revenue", "fact_revenue_loyalty_daily"),
    ("reservation_revenue", "fact_revenue_nationality_daily"),
    ("reservation_revenue", "fact_revenue_pace_booking_snapshot"),

    ("fnb_operations", "dim_outlet_type"),
    ("fnb_operations", "dim_outlet"),
    ("fnb_operations", "dim_fnb_category"),
    ("fnb_operations", "dim_menu_item"),
    ("fnb_operations", "dim_waste_reason"),
    ("fnb_operations", "dim_ingredient"),
    ("fnb_operations", "fact_fnb_outlet_daily"),
    ("fnb_operations", "fact_fnb_category_daily"),
    ("fnb_operations", "fact_fnb_hourly"),
    ("fnb_operations", "fact_fnb_customer_type_daily"),
    ("fnb_operations", "fact_fnb_menu_item_daily"),
    ("fnb_operations", "fact_fnb_waste_daily"),
    ("fnb_operations", "fact_fnb_inventory_status"),
    ("fnb_operations", "fact_fnb_ingredient_price_daily"),

    ("facility_maintenance", "dim_facility_area"),
    ("facility_maintenance", "dim_issue_type"),
    ("facility_maintenance", "dim_priority"),
    ("facility_maintenance", "fact_facility_room_status_daily"),
    ("facility_maintenance", "fact_housekeeping_room_type_daily"),
    ("facility_maintenance", "fact_housekeeping_property_daily"),
    ("facility_maintenance", "fact_housekeeping_staff_daily"),
    ("facility_maintenance", "fact_maintenance_ticket_daily"),
    ("facility_maintenance", "fact_maintenance_cost_daily"),
    ("facility_maintenance", "fact_maintenance_room_recurrence_yearly"),
    ("facility_maintenance", "fact_maintenance_property_benchmark_yearly"),
    ("facility_maintenance", "fact_maintenance_technician_daily"),

    ("spa_event", "dim_spa_service"),
    ("spa_event", "dim_venue_type"),
    ("spa_event", "dim_venue"),
    ("spa_event", "dim_event_type"),
    ("spa_event", "fact_spa_daily"),
    ("spa_event", "fact_spa_customer_type_daily"),
    ("spa_event", "fact_spa_service_daily"),
    ("spa_event", "fact_event_venue_daily"),
    ("spa_event", "fact_event_property_daily"),
    ("spa_event", "fact_event_type_daily"),

    ("hr", "dim_shift_type"),
    ("hr", "dim_employee_status"),
    ("hr", "fact_hr_attendance_daily"),
    ("hr", "fact_hr_employee_monthly"),
    ("hr", "fact_hr_employee_performance_semester"),
    ("hr", "fact_hr_turnover_snapshot"),
    ("hr", "fact_hr_headcount_status_daily"),
    ("hr", "fact_hr_performance_department_semester"),
    ("hr", "fact_hr_performance_by_status_semester"),
    ("hr", "fact_hr_watchlist_monthly"),

    ("corporate_financial", "dim_business_line"),
    ("corporate_financial", "dim_access_level"),
    ("corporate_financial", "fact_financial_business_line_monthly"),
    ("corporate_financial", "fact_financial_overall_monthly"),
    ("corporate_financial", "fact_financial_revenue_runrate_daily"),
    ("corporate_financial", "fact_payroll_department_monthly"),
    ("corporate_financial", "fact_financial_service_charge_monthly"),
    ("corporate_financial", "fact_financial_labor_cost_monthly"),
    ("corporate_financial", "fact_payroll_access_level_monthly"),
    ("corporate_financial", "fact_financial_business_line_group_monthly"),
    ("corporate_financial", "fact_financial_property_benchmark_monthly"),
]

assert len(MART_AGGREGATED_TABLES) == 76, f"expected 76 tables, got {len(MART_AGGREGATED_TABLES)}"
