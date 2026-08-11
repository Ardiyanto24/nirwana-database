-- Milestone 6.5 — Monitoring Performa Query AI Chatbot
-- Perluasan schema monitoring bersama (production Supabase, sudah ada sejak
-- M1.2), additive only. Rujukan: milestones/6.5-monitoring-performa-query-chatbot/decisions.md

CREATE SCHEMA IF NOT EXISTS monitoring;

-- Output 1/2 (KK1): snapshot pg_stat_statements untuk query chatbot_views.*
-- (project serving, dibaca via chatbot_perf_reader). queryid adalah hash
-- normalized-query bawaan pg_stat_statements sendiri -- dipakai sebagai
-- unique key per snapshot, bukan hash query_text sendiri (query_text bisa
-- panjang, tidak cocok untuk index UNIQUE).
CREATE TABLE IF NOT EXISTS monitoring.chatbot_query_perf_snapshot (
    id                  BIGSERIAL PRIMARY KEY,
    snapshot_date       DATE NOT NULL,
    queryid             BIGINT NOT NULL,
    query_text          TEXT NOT NULL,
    calls               BIGINT NOT NULL,
    mean_exec_time_ms   NUMERIC NOT NULL,
    max_exec_time_ms    NUMERIC NOT NULL,
    rows_returned       BIGINT,
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (snapshot_date, queryid)
);

CREATE INDEX IF NOT EXISTS idx_chatbot_query_perf_snapshot_lookup
    ON monitoring.chatbot_query_perf_snapshot (snapshot_date, mean_exec_time_ms DESC);

-- Output 2: EXPLAIN ANALYZE berkala terhadap ~10 query representatif
-- (1 per domain chatbot, Keputusan D -- kurasi manual, bukan ekstrak dinamis
-- dari pg_stat_statements yang cuma simpan teks ternormalisasi berplaceholder).
CREATE TABLE IF NOT EXISTS monitoring.chatbot_explain_analyze_log (
    id                  BIGSERIAL PRIMARY KEY,
    domain              TEXT NOT NULL,
    view_name           TEXT NOT NULL,
    query_text          TEXT NOT NULL,
    execution_time_ms   NUMERIC NOT NULL,
    plan_summary        TEXT NOT NULL,
    snapshot_date       DATE NOT NULL,
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chatbot_explain_analyze_log_lookup
    ON monitoring.chatbot_explain_analyze_log (domain, view_name, snapshot_date DESC);

-- Output 3 (KK3): snapshot jumlah koneksi aktif (pg_stat_activity, project
-- serving, dibaca via chatbot_perf_reader) -- append-only, TANPA UNIQUE
-- constraint (uji coba terkontrol butuh snapshot berulang cepat: sebelum/
-- selama/sesudah burst). Rolling-baseline TANPA filter day-of-week (Keputusan
-- F -- sama alasan sensor duration anomaly M6.3, jumlah koneksi tidak punya
-- pola mingguan berarti).
CREATE TABLE IF NOT EXISTS monitoring.chatbot_connection_snapshot (
    id                        BIGSERIAL PRIMARY KEY,
    snapshot_time             TIMESTAMPTZ NOT NULL DEFAULT now(),
    active_connection_count   INTEGER NOT NULL,
    captured_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chatbot_connection_snapshot_lookup
    ON monitoring.chatbot_connection_snapshot (snapshot_time DESC);

-- Perluas alert_type monitoring.alerts (M1.2, diperluas M1.3/M6.3/M6.4)
-- dengan 1 sumber sinyal baru M6.5.
ALTER TABLE monitoring.alerts DROP CONSTRAINT IF EXISTS alerts_alert_type_check;
ALTER TABLE monitoring.alerts ADD CONSTRAINT alerts_alert_type_check
    CHECK (alert_type IN (
        'volume_anomaly', 'freshness_delay', 'dq_test_failure', 'dirty_proportion_drift', 'value_anomaly',
        'dbt_test_failure', 'warehouse_volume_anomaly', 'reverse_etl_mismatch', 'ml_output_freshness_delay',
        'ml_output_incomplete_scoring', 'chatbot_connection_pool_spike'
    ));

-- KK1: kolom durasi per-request di monitoring.chatbot_query_log (M4.5) --
-- Keputusan A, ditambahkan lewat scripts/chatbot_audit/schema.sql (bukan
-- di sini) karena tabel itu milik M4.5, bukan tabel baru M6.5. Dicatat di
-- sini murni sebagai catatan silang -- lihat scripts/chatbot_audit/schema.sql.
