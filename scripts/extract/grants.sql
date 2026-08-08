-- Milestone 2.1: read-only Postgres role for production extraction (raw_production sync).
-- Explicit whitelist of exactly the 23 production tables across 6 schemas
-- (see docs/04-monitoring/baseline-inventaris-produksi.md "Pemetaan 23 Tabel"
-- for the full inventory this list is drawn from). No write privileges
-- anywhere, no access to any other schema/table by default (Postgres denies
-- unless granted) -- including monitoring.* itself, which this role has no
-- need to read.

-- Role itself is created/password-rotated by scripts/extract/setup_extract_role.py
-- (password must never be hardcoded here). This file only manages privileges,
-- safe to re-run (idempotent GRANTs).

GRANT USAGE ON SCHEMA corporate_master TO extract_reader;
GRANT SELECT ON corporate_master.properties TO extract_reader;
GRANT SELECT ON corporate_master.employees TO extract_reader;
GRANT SELECT ON corporate_master.guests TO extract_reader;
GRANT SELECT ON corporate_master.role_permissions TO extract_reader;

GRANT USAGE ON SCHEMA reservation_revenue TO extract_reader;
GRANT SELECT ON reservation_revenue.bookings TO extract_reader;
GRANT SELECT ON reservation_revenue.daily_occupancy TO extract_reader;
GRANT SELECT ON reservation_revenue.pricing_history TO extract_reader;

GRANT USAGE ON SCHEMA fnb_operations TO extract_reader;
GRANT SELECT ON fnb_operations.fnb_outlets TO extract_reader;
GRANT SELECT ON fnb_operations.recipe_bom TO extract_reader;
GRANT SELECT ON fnb_operations.ingredient_price_history TO extract_reader;
GRANT SELECT ON fnb_operations.fnb_transactions TO extract_reader;
GRANT SELECT ON fnb_operations.fnb_waste_log TO extract_reader;
GRANT SELECT ON fnb_operations.fnb_inventory TO extract_reader;

GRANT USAGE ON SCHEMA facility_maintenance TO extract_reader;
GRANT SELECT ON facility_maintenance.rooms TO extract_reader;
GRANT SELECT ON facility_maintenance.housekeeping_log TO extract_reader;
GRANT SELECT ON facility_maintenance.maintenance_tickets TO extract_reader;

GRANT USAGE ON SCHEMA spa_event TO extract_reader;
GRANT SELECT ON spa_event.venues TO extract_reader;
GRANT SELECT ON spa_event.spa_bookings TO extract_reader;
GRANT SELECT ON spa_event.event_bookings TO extract_reader;

GRANT USAGE ON SCHEMA hr_finance TO extract_reader;
GRANT SELECT ON hr_finance.staff_shifts TO extract_reader;
GRANT SELECT ON hr_finance.employee_performance TO extract_reader;
GRANT SELECT ON hr_finance.payroll TO extract_reader;
GRANT SELECT ON hr_finance.financial_summary TO extract_reader;
