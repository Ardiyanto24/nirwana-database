"""Kolom numerik bisnis kritis yang dipantau lewat IQR (Milestone 1.3, Task 6)."""

VALUE_COLUMNS = [
    # (schema, table, column, filter_sql_or_None)
    ("reservation_revenue", "bookings", "total_amount", "status IN ('completed','confirmed')"),
    ("fnb_operations", "fnb_transactions", "total_price", None),
    ("facility_maintenance", "maintenance_tickets", "cost", None),
    ("hr_finance", "payroll", "net_salary", None),
    ("spa_event", "spa_bookings", "price", "status IN ('completed','confirmed')"),
    ("spa_event", "event_bookings", "total_revenue", "status IN ('completed','confirmed')"),
]

IQR_K = 1.5  # Tukey's fence standar
