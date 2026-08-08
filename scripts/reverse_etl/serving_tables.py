"""
Daftar 23 tabel mart_cleaned untuk Milestone 2.4 (reverse ETL BigQuery -> serving
Postgres). Salinan (schema, table) dari scripts/extract/tables_config.py --
SENGAJA tidak di-import lewat sys.path (bug class M2.1: kolaps nama modul yang
sama di-cache Python, resolve ke file yang salah). cursor_strategy tidak
relevan di sini (M2.4 selalu full refresh + swap, bukan incremental).

BigQuery table id: mart_cleaned.mart_cleaned__<table> (prefix domain TIDAK
dipakai di BigQuery -- lihat `bq ls` M2.3, beda dari raw_production/staging).
PostgreSQL table: schema mart_cleaned, nama tabel BARE <table> (tanpa prefix
domain/mart_cleaned__ -- schema Postgres sudah cukup jadi namespace).
"""

SERVING_TABLES = [
    # schema (dokumentasi asal saja, tidak dipakai di BigQuery/Postgres side), table
    ("corporate_master", "properties"),
    ("corporate_master", "employees"),
    ("corporate_master", "guests"),
    ("corporate_master", "role_permissions"),

    ("reservation_revenue", "bookings"),
    ("reservation_revenue", "daily_occupancy"),
    ("reservation_revenue", "pricing_history"),

    ("fnb_operations", "fnb_outlets"),
    ("fnb_operations", "recipe_bom"),
    ("fnb_operations", "ingredient_price_history"),
    ("fnb_operations", "fnb_transactions"),
    ("fnb_operations", "fnb_waste_log"),
    ("fnb_operations", "fnb_inventory"),

    ("facility_maintenance", "rooms"),
    ("facility_maintenance", "housekeeping_log"),
    ("facility_maintenance", "maintenance_tickets"),

    ("spa_event", "venues"),
    ("spa_event", "spa_bookings"),
    ("spa_event", "event_bookings"),

    ("hr_finance", "staff_shifts"),
    ("hr_finance", "employee_performance"),
    ("hr_finance", "payroll"),
    ("hr_finance", "financial_summary"),
]

assert len(SERVING_TABLES) == 23, f"expected 23 tables, got {len(SERVING_TABLES)}"
