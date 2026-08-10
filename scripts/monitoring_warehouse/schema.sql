-- Milestone 6.2 — Monitoring Log Proses Pipeline (Fase 2)
-- Perluasan schema monitoring bersama (sudah ada sejak M1.2), additive only.
-- Rujukan: milestones/6.2-monitoring-log-proses-pipeline/decisions.md

CREATE SCHEMA IF NOT EXISTS monitoring;

CREATE TABLE IF NOT EXISTS monitoring.pipeline_run_log (
    id                BIGSERIAL PRIMARY KEY,
    titik_id          SMALLINT NOT NULL CHECK (titik_id BETWEEN 1 AND 10),
    titik_label       TEXT NOT NULL,
    workflow_name     TEXT NOT NULL,
    run_id            BIGINT NOT NULL,
    step_name         TEXT,       -- NULL = granularitas run-level (titik 1,4,8,9); terisi = step-level (titik 2,3,5,6,7)
    granularity       TEXT NOT NULL CHECK (granularity IN ('coarse', 'detailed')),
    status            TEXT NOT NULL CHECK (status IN ('success', 'failure', 'cancelled', 'skipped', 'timed_out')),
    started_at        TIMESTAMPTZ NOT NULL,
    completed_at      TIMESTAMPTZ NOT NULL,
    duration_seconds  INTEGER NOT NULL,
    trigger_event     TEXT,       -- schedule / workflow_dispatch / workflow_run, dari github.event.workflow_run
    logged_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- UNIQUE index pakai COALESCE(step_name, '') -- bukan UNIQUE constraint biasa di kolom nullable,
-- karena Postgres menganggap tiap NULL berbeda satu sama lain (2 baris titik run-level dengan
-- titik_id+run_id sama tapi step_name NULL keduanya TIDAK akan dianggap duplikat oleh UNIQUE constraint biasa).
CREATE UNIQUE INDEX IF NOT EXISTS uq_pipeline_run_log_titik_run_step
    ON monitoring.pipeline_run_log (titik_id, run_id, COALESCE(step_name, ''));

CREATE INDEX IF NOT EXISTS idx_pipeline_run_log_lookup
    ON monitoring.pipeline_run_log (titik_id, completed_at DESC);

CREATE OR REPLACE VIEW monitoring.pipeline_run_status AS
SELECT DISTINCT ON (titik_id)
    titik_id,
    titik_label,
    workflow_name,
    step_name,
    granularity,
    status,
    started_at,
    completed_at,
    duration_seconds,
    (started_at::date = CURRENT_DATE) AS ran_today
FROM monitoring.pipeline_run_log
ORDER BY titik_id, completed_at DESC;

-- Milestone 6.3 — Monitoring Kesalahan dan Anomali di Pipeline Warehouse
-- Perluasan lanjutan schema monitoring bersama, additive only.
-- Rujukan: milestones/6.3-monitoring-kesalahan-anomali-warehouse/decisions.md

-- Output 1 (KK1): detail per-test hasil dbt test mart_cleaned/mart_aggregated,
-- diparse dari warehouse/target/run_results.json setelah step gate promote.py
-- selesai (promote.py sendiri TIDAK disentuh -- Keputusan #1). Append-only,
-- tidak ada UNIQUE constraint, sama pola scripts/dq/schema.sql's dq_test_results.
CREATE TABLE IF NOT EXISTS monitoring.dbt_test_result (
    id              BIGSERIAL PRIMARY KEY,
    layer           TEXT NOT NULL CHECK (layer IN ('mart_cleaned', 'mart_aggregated')),
    unique_id       TEXT NOT NULL,
    test_name       TEXT,
    resource_type   TEXT,
    status          TEXT NOT NULL,
    execution_time  NUMERIC,
    failures        INTEGER,
    github_run_id   BIGINT,   -- cross-reference ke monitoring.pipeline_run_log.run_id (M6.2)
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dbt_test_result_lookup
    ON monitoring.dbt_test_result (layer, captured_at DESC);

-- Output 2 (KK2): snapshot row-count harian BigQuery, 3 dataset
-- (raw_production, mart_cleaned, mart_aggregated -- staging sengaja
-- dikecualikan, lihat decisions.md Keputusan #3). Diisi via
-- INFORMATION_SCHEMA.TABLE_STORAGE, bukan COUNT(*) per tabel (Keputusan #4).
CREATE TABLE IF NOT EXISTS monitoring.warehouse_volume_snapshot (
    id             BIGSERIAL PRIMARY KEY,
    dataset_name   TEXT NOT NULL,
    table_name     TEXT NOT NULL,
    snapshot_date  DATE NOT NULL,
    row_count      BIGINT NOT NULL,
    day_of_week    SMALLINT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (dataset_name, table_name, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_warehouse_volume_snapshot_lookup
    ON monitoring.warehouse_volume_snapshot (dataset_name, table_name, day_of_week, snapshot_date DESC);

-- Output 4 (KK4): freshness ml_output.predictions -- MAX(scored_at) vs now(),
-- formula lag_hours direplikasi dari scripts/monitoring/snapshot_freshness.py.
CREATE TABLE IF NOT EXISTS monitoring.ml_output_freshness_snapshot (
    id                 BIGSERIAL PRIMARY KEY,
    snapshot_date      DATE NOT NULL,
    latest_scored_at   TIMESTAMPTZ,
    lag_hours          NUMERIC,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (snapshot_date)
);

-- Output 3 (KK3): row-count parity BigQuery vs PostgreSQL -- murni konsolidasi,
-- monitoring.reverse_etl_sync_log (M2.4/M5.5) sudah punya seluruh data yang
-- dibutuhkan. sync.py TIDAK disentuh -- kolom is_simulated ditambah lewat ALTER
-- additive (pola identik precedent M5.5 dataset_name), default FALSE untuk
-- seluruh baris existing dan baris baru dari sync.py (yang tidak tahu-menahu
-- soal kolom ini), dibutuhkan supaya KK3 bisa diuji coba terkontrol tanpa
-- mengotori riwayat sync nyata.
ALTER TABLE monitoring.reverse_etl_sync_log
    ADD COLUMN IF NOT EXISTS is_simulated BOOLEAN NOT NULL DEFAULT FALSE;

CREATE OR REPLACE VIEW monitoring.warehouse_parity_status AS
SELECT DISTINCT ON (dataset_name, table_name)
    dataset_name,
    table_name,
    bq_row_count,
    pg_row_count,
    status,
    synced_at
FROM monitoring.reverse_etl_sync_log
WHERE is_simulated = FALSE
ORDER BY dataset_name, table_name, synced_at DESC;

-- Perluas alert_type monitoring.alerts (dibuat M1.2, diperluas M1.3) dengan
-- 4 sumber sinyal baru Milestone 6.3 -- pola extensibility identik
-- scripts/dq/schema.sql, sudah dipakai 3x sebelumnya.
ALTER TABLE monitoring.alerts DROP CONSTRAINT IF EXISTS alerts_alert_type_check;
ALTER TABLE monitoring.alerts ADD CONSTRAINT alerts_alert_type_check
    CHECK (alert_type IN (
        'volume_anomaly', 'freshness_delay', 'dq_test_failure', 'dirty_proportion_drift', 'value_anomaly',
        'dbt_test_failure', 'warehouse_volume_anomaly', 'reverse_etl_mismatch', 'ml_output_freshness_delay',
        'ml_output_incomplete_scoring'
    ));

-- Milestone 6.4 — Monitoring Data Drift Feedback Loop ML
-- Perluasan lanjutan schema monitoring bersama, additive only.
-- Rujukan: milestones/6.4-monitoring-drift-feedback-loop-ml/decisions.md

-- Output 1 (KK1): model staleness -- INFORMATIONAL ONLY, TIDAK ada alert
-- (Keputusan: model_version cuma 1 nilai statis di data mock, tidak ada
-- cadence retrain sungguhan untuk dikalibrasi jadi threshold defensible).
-- Snapshot per (model_name, model_version): kapan pertama & terakhir muncul,
-- berapa baris total -- diulang tiap hari job jalan (idempotent per hari).
CREATE TABLE IF NOT EXISTS monitoring.ml_model_version_snapshot (
    id                BIGSERIAL PRIMARY KEY,
    model_name        TEXT NOT NULL,
    model_version     TEXT NOT NULL,
    snapshot_date     DATE NOT NULL,
    first_scored_at   TIMESTAMPTZ NOT NULL,
    last_scored_at    TIMESTAMPTZ NOT NULL,
    row_count_total   INTEGER NOT NULL,
    captured_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (model_name, model_version, snapshot_date)
);

CREATE OR REPLACE VIEW monitoring.ml_model_staleness_status AS
SELECT DISTINCT ON (model_name, model_version)
    model_name,
    model_version,
    snapshot_date,
    first_scored_at,
    last_scored_at,
    row_count_total,
    EXTRACT(DAY FROM (now() - first_scored_at))::INTEGER AS days_since_first_scored,
    (last_scored_at = MAX(last_scored_at) OVER (PARTITION BY model_name)) AS is_most_recently_active
FROM monitoring.ml_model_version_snapshot
ORDER BY model_name, model_version, snapshot_date DESC;

-- Output 2 (KK2): validasi kelengkapan ml_output vs populasi entity
-- mart_aggregated.fact_revenue_room_type_daily (BUKAN mart_cleaned langsung
-- -- lihat decisions.md, entity_id ml_output cuma cocok dengan room_type_id
-- surrogate key mart_aggregated). Satu-satunya dari 3 mekanisme M6.4 yang
-- push ke monitoring.alerts -- "ada entity hilang" adalah temuan biner
-- berbasis evidence, bukan threshold tebakan.
CREATE TABLE IF NOT EXISTS monitoring.ml_output_completeness_snapshot (
    id                     BIGSERIAL PRIMARY KEY,
    snapshot_date          DATE NOT NULL,
    feature_snapshot_at    TIMESTAMPTZ NOT NULL,
    expected_entity_count  INTEGER NOT NULL,
    scored_entity_count    INTEGER NOT NULL,
    missing_entity_count   INTEGER NOT NULL,
    captured_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (snapshot_date, feature_snapshot_at)
);

CREATE TABLE IF NOT EXISTS monitoring.ml_output_missing_entity (
    id                   BIGSERIAL PRIMARY KEY,
    feature_snapshot_at  TIMESTAMPTZ NOT NULL,
    property_id          TEXT NOT NULL,
    room_type_id         INTEGER NOT NULL,
    detected_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (feature_snapshot_at, property_id, room_type_id)
);

-- Output 3 (KK3): canary drift -- deteksi EKSISTENSI dataset drift, nol
-- asumsi skema kolom (Keputusan: tidak ada data drift apa pun tersedia,
-- menebak skema berisiko salah total). Murni informational, tidak push ke
-- monitoring.alerts (severity CHECK cuma warning/critical, tidak ada level
-- info -- lihat decisions.md).
CREATE TABLE IF NOT EXISTS monitoring.ml_drift_data_availability_check (
    id             BIGSERIAL PRIMARY KEY,
    checked_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    dataset_found  BOOLEAN NOT NULL,
    dataset_name   TEXT,
    project_id     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ml_drift_check_lookup
    ON monitoring.ml_drift_data_availability_check (checked_at DESC);
