-- Milestone 1.2 — Monitoring Volume dan Freshness Data Production
-- Schema baru, additive only. Tidak menyentuh tabel production manapun.
-- Rujukan: milestones/1.2-monitoring-volume-freshness/decisions.md

CREATE SCHEMA IF NOT EXISTS monitoring;

CREATE TABLE IF NOT EXISTS monitoring.volume_daily_snapshot (
    id             BIGSERIAL PRIMARY KEY,
    schema_name    TEXT NOT NULL,
    table_name     TEXT NOT NULL,
    snapshot_date  DATE NOT NULL,
    row_count      BIGINT NOT NULL,
    day_of_week    SMALLINT NOT NULL, -- 0=Sunday .. 6=Saturday (Postgres EXTRACT(DOW))
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (schema_name, table_name, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_volume_snapshot_lookup
    ON monitoring.volume_daily_snapshot (schema_name, table_name, day_of_week, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS monitoring.freshness_snapshot (
    id                 BIGSERIAL PRIMARY KEY,
    schema_name        TEXT NOT NULL,
    table_name         TEXT NOT NULL,
    snapshot_date      DATE NOT NULL,
    freshness_column   TEXT,            -- NULL = tabel tanpa sinyal freshness (volume-only, lihat decisions.md)
    latest_value       TIMESTAMPTZ,     -- nilai MAX(freshness_column) pada saat snapshot, dinormalisasi ke timestamp
    lag_hours          NUMERIC,         -- jam sejak latest_value hingga saat snapshot diambil
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (schema_name, table_name, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_freshness_snapshot_lookup
    ON monitoring.freshness_snapshot (schema_name, table_name, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS monitoring.alerts (
    id             BIGSERIAL PRIMARY KEY,
    schema_name    TEXT NOT NULL,
    table_name     TEXT NOT NULL,
    alert_type     TEXT NOT NULL CHECK (alert_type IN ('volume_anomaly', 'freshness_delay')),
    severity       TEXT NOT NULL CHECK (severity IN ('warning', 'critical')),
    detail         TEXT NOT NULL,
    snapshot_date  DATE NOT NULL,
    triggered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_simulated   BOOLEAN NOT NULL DEFAULT FALSE  -- TRUE untuk alert hasil uji coba terkontrol (Task 7), bukan alert dari data production nyata
);

CREATE INDEX IF NOT EXISTS idx_alerts_lookup
    ON monitoring.alerts (schema_name, table_name, triggered_at DESC);
