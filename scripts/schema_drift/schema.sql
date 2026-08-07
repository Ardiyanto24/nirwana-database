-- Milestone 1.4 — Monitoring Perubahan Struktur (Schema Drift)
-- Perluasan schema `monitoring`. Additive only.
-- Rujukan: milestones/1.4-monitoring-schema-drift/decisions.md

-- Baseline "disetujui" -- acuan tetap, bukan snapshot hari-ke-hari.
-- Diperbarui HANYA lewat acknowledge.py, tidak pernah ditimpa otomatis oleh snapshot_and_diff.py.
CREATE TABLE IF NOT EXISTS monitoring.schema_column_baseline (
    id             BIGSERIAL PRIMARY KEY,
    schema_name    TEXT NOT NULL,
    table_name     TEXT NOT NULL,
    column_name    TEXT NOT NULL,
    data_type      TEXT NOT NULL,
    is_nullable    BOOLEAN NOT NULL,
    ordinal_position INTEGER NOT NULL,
    approved_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (schema_name, table_name, column_name)
);

CREATE TABLE IF NOT EXISTS monitoring.schema_drift_events (
    id             BIGSERIAL PRIMARY KEY,
    schema_name    TEXT NOT NULL,
    table_name     TEXT NOT NULL,
    column_name    TEXT NOT NULL,
    drift_type     TEXT NOT NULL CHECK (drift_type IN ('column_added', 'column_removed', 'type_changed')),
    detail         TEXT NOT NULL,          -- deskripsi human-readable perubahan
    severity       TEXT NOT NULL CHECK (severity IN ('normal', 'high')),
    status         TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'acknowledged')),
    detected_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_schema_drift_events_pending
    ON monitoring.schema_drift_events (status, detected_at DESC);
