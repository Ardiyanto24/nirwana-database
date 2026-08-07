"""
CASE expression untuk mengelompokkan tabel berdasarkan prioritas Milestone 1.1
(docs/04-monitoring/baseline-inventaris-produksi.md), dipakai berulang di query
panel Grafana supaya konsisten dgn scripts/monitoring/tables_config.py.
"""

PRIORITY_CASE_SQL = """CASE table_name
    WHEN 'employees' THEN 'Tinggi' WHEN 'guests' THEN 'Tinggi' WHEN 'role_permissions' THEN 'Tinggi'
    WHEN 'bookings' THEN 'Tinggi' WHEN 'fnb_transactions' THEN 'Tinggi' WHEN 'staff_shifts' THEN 'Tinggi'
    WHEN 'payroll' THEN 'Tinggi'
    WHEN 'fnb_outlets' THEN 'Rendah' WHEN 'fnb_inventory' THEN 'Rendah' WHEN 'venues' THEN 'Rendah'
    WHEN 'employee_performance' THEN 'Rendah'
    ELSE 'Sedang'
END"""

PRIORITY_ORDER_SQL = """CASE table_name
    WHEN 'employees' THEN 1 WHEN 'guests' THEN 1 WHEN 'role_permissions' THEN 1
    WHEN 'bookings' THEN 1 WHEN 'fnb_transactions' THEN 1 WHEN 'staff_shifts' THEN 1
    WHEN 'payroll' THEN 1
    WHEN 'fnb_outlets' THEN 3 WHEN 'fnb_inventory' THEN 3 WHEN 'venues' THEN 3
    WHEN 'employee_performance' THEN 3
    ELSE 2
END"""
