"""
Konfigurasi 23 tabel production untuk Milestone 1.2.

Sumber: docs/04-monitoring/baseline-inventaris-produksi.md (prioritas Milestone 1.1)
        + milestones/1.2-monitoring-volume-freshness/decisions.md (pemetaan freshness, dikoreksi saat implementasi)

freshness_column_type:
  "date"                  -> kolom Postgres bertipe date/timestamp, MAX() langsung valid
  "text_ddmmyyyy_mixed"   -> kolom text, ~2% baris DD/MM/YYYY, sisanya YYYY-MM-DD (dirty data) -> parse di Python
  "text_period_month"     -> kolom text format YYYY-MM, zero-padded (MAX() SQL leksikografis valid)
  "text_period_semester"  -> kolom text format YYYY-S1/YYYY-S2, zero-padded (MAX() SQL leksikografis valid)
  None                    -> tabel tanpa sinyal freshness (volume-only)

cadence_class menentukan threshold alert freshness (lihat detect_alerts.py):
  "daily" | "monthly" | "semesterly" | None (volume-only, tidak dicek freshness)
"""

TABLES = [
    # schema, table, priority, freshness_column, freshness_column_type, cadence_class
    ("corporate_master", "properties", "Sedang", None, None, None),
    ("corporate_master", "employees", "Tinggi", "hire_date", "text_ddmmyyyy_mixed", "daily"),
    ("corporate_master", "guests", "Tinggi", "registered_date", "date", "daily"),
    ("corporate_master", "role_permissions", "Tinggi", None, None, None),

    ("reservation_revenue", "bookings", "Tinggi", "booking_date", "date", "daily"),
    ("reservation_revenue", "daily_occupancy", "Sedang", "date", "date", "daily"),
    ("reservation_revenue", "pricing_history", "Sedang", "date", "date", "daily"),

    ("fnb_operations", "fnb_outlets", "Rendah", None, None, None),
    ("fnb_operations", "recipe_bom", "Sedang", None, None, None),
    ("fnb_operations", "ingredient_price_history", "Sedang", "date", "date", "daily"),
    ("fnb_operations", "fnb_transactions", "Tinggi", "transaction_datetime", "date", "daily"),
    ("fnb_operations", "fnb_waste_log", "Sedang", "date", "date", "daily"),
    ("fnb_operations", "fnb_inventory", "Rendah", None, None, None),

    ("facility_maintenance", "rooms", "Sedang", None, None, None),
    ("facility_maintenance", "housekeeping_log", "Sedang", "date", "date", "daily"),
    ("facility_maintenance", "maintenance_tickets", "Sedang", "reported_date", "date", "daily"),

    ("spa_event", "venues", "Rendah", None, None, None),
    ("spa_event", "spa_bookings", "Sedang", "booking_date", "date", "daily"),
    ("spa_event", "event_bookings", "Sedang", None, None, None),  # gap diketahui, lihat decisions.md

    ("hr_finance", "staff_shifts", "Tinggi", "date", "date", "daily"),
    ("hr_finance", "employee_performance", "Rendah", "review_period", "text_period_semester", "semesterly"),
    ("hr_finance", "payroll", "Tinggi", "period", "text_period_month", "monthly"),
    ("hr_finance", "financial_summary", "Sedang", "period", "text_period_month", "monthly"),
]

# Threshold lag per cadence_class, dipakai detect_alerts.py.
# (warning_hours, critical_hours)
FRESHNESS_THRESHOLDS_HOURS = {
    "daily": (48, 96),
    "monthly": (45 * 24, 60 * 24),
    "semesterly": (200 * 24, 220 * 24),
}

HIGH_PRIORITY_TABLES = [(s, t) for s, t, p, *_ in TABLES if p == "Tinggi"]
