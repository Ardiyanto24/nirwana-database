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
