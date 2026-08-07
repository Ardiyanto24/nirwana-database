-- Milestone 1.3 — Monitoring Kualitas Data dan Anomali Nilai
-- Perluasan schema `monitoring` (dibuat di Milestone 1.2). Additive only.
-- Rujukan: milestones/1.3-kualitas-data-anomali/decisions.md

CREATE TABLE IF NOT EXISTS monitoring.dq_test_results (
    id               BIGSERIAL PRIMARY KEY,
    schema_name      TEXT NOT NULL,
    table_name       TEXT NOT NULL,
    suite_name       TEXT NOT NULL,
    expectation_type TEXT NOT NULL,
    expectation_detail TEXT,           -- kolom/rule yang diuji, human-readable
    success          BOOLEAN NOT NULL,
    unexpected_count INTEGER,
    unexpected_percent NUMERIC,
    run_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    run_date         DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_dq_test_results_lookup
    ON monitoring.dq_test_results (schema_name, table_name, run_date DESC);

-- Snapshot proporsi "dirty by design" harian per kolom (Task 4 / Decision: tolerance band)
CREATE TABLE IF NOT EXISTS monitoring.dirty_proportion_snapshot (
    id             BIGSERIAL PRIMARY KEY,
    schema_name    TEXT NOT NULL,
    table_name     TEXT NOT NULL,
    column_name    TEXT NOT NULL,
    snapshot_date  DATE NOT NULL,
    total_rows     BIGINT NOT NULL,
    dirty_rows     BIGINT NOT NULL,
    dirty_pct      NUMERIC NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (schema_name, table_name, column_name, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_dirty_proportion_lookup
    ON monitoring.dirty_proportion_snapshot (schema_name, table_name, column_name, snapshot_date DESC);

-- Snapshot statistik nilai (IQR) harian per kolom bisnis kritis (Task 6)
CREATE TABLE IF NOT EXISTS monitoring.value_anomaly_snapshot (
    id             BIGSERIAL PRIMARY KEY,
    schema_name    TEXT NOT NULL,
    table_name     TEXT NOT NULL,
    column_name    TEXT NOT NULL,
    snapshot_date  DATE NOT NULL,
    q1             NUMERIC,
    median         NUMERIC,
    q3             NUMERIC,
    iqr            NUMERIC,
    lower_fence    NUMERIC,   -- q1 - k*iqr
    upper_fence    NUMERIC,   -- q3 + k*iqr
    outlier_count  INTEGER,
    row_count      BIGINT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (schema_name, table_name, column_name, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_value_anomaly_lookup
    ON monitoring.value_anomaly_snapshot (schema_name, table_name, column_name, snapshot_date DESC);

-- Perluas alert_type yang diterima monitoring.alerts (dibuat Milestone 1.2)
ALTER TABLE monitoring.alerts DROP CONSTRAINT IF EXISTS alerts_alert_type_check;
ALTER TABLE monitoring.alerts ADD CONSTRAINT alerts_alert_type_check
    CHECK (alert_type IN ('volume_anomaly', 'freshness_delay', 'dq_test_failure', 'dirty_proportion_drift', 'value_anomaly'));
