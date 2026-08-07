-- Milestone 1.6: read-only Postgres role for the public monitoring API.
-- Scoped strictly to monitoring.* (all current + future tables/views) plus a
-- small whitelist of non-sensitive production tables (see decisions.md for
-- the rationale behind each table). No write privileges anywhere, no access
-- to any other schema/table by default (Postgres denies unless granted).

-- Role itself is created/password-rotated by scripts/api_reader/setup_reader_role.py
-- (password must never be hardcoded here). This file only manages privileges,
-- safe to re-run (idempotent GRANTs).

GRANT USAGE ON SCHEMA monitoring TO monitoring_api_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA monitoring TO monitoring_api_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring GRANT SELECT ON TABLES TO monitoring_api_reader;

GRANT USAGE ON SCHEMA corporate_master TO monitoring_api_reader;
GRANT SELECT ON corporate_master.properties TO monitoring_api_reader;

GRANT USAGE ON SCHEMA fnb_operations TO monitoring_api_reader;
GRANT SELECT ON fnb_operations.fnb_outlets TO monitoring_api_reader;

GRANT USAGE ON SCHEMA facility_maintenance TO monitoring_api_reader;
GRANT SELECT ON facility_maintenance.rooms TO monitoring_api_reader;
