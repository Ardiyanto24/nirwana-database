-- Milestone 6.6 — Monitoring Reverse ETL dan Serving Layer PostgreSQL
-- Perluasan schema monitoring bersama (production Supabase, sudah ada sejak
-- M1.2), additive only. Rujukan: milestones/6.6-monitoring-reverse-etl-serving-layer/decisions.md

CREATE SCHEMA IF NOT EXISTS monitoring;

-- Output 1 (KK1): storage growth + table bloat/vacuum status -- murni
-- dashboard/snapshot, TIDAK ada alert (Keputusan D -- KK1 minta "tren
-- terlihat", beda dari KK2 yang eksplisit "terdeteksi"). is_orphan dihitung
-- saat insert (table_name LIKE '%__old') -- sumber kebenaran tunggal untuk
-- detect_orphan_tables.py (Keputusan C), robust terhadap kapan pun orphan
-- itu muncul (termasuk 73 yang sudah ada SEBELUM milestone ini).
CREATE TABLE IF NOT EXISTS monitoring.serving_storage_snapshot (
    id                BIGSERIAL PRIMARY KEY,
    schema_name       TEXT NOT NULL,
    table_name        TEXT NOT NULL,
    snapshot_date     DATE NOT NULL,
    total_size_bytes  BIGINT NOT NULL,
    live_row_count    BIGINT NOT NULL,
    dead_row_count    BIGINT NOT NULL,
    dead_pct          NUMERIC,
    last_vacuum       TIMESTAMPTZ,
    last_autovacuum   TIMESTAMPTZ,
    is_orphan         BOOLEAN NOT NULL,
    captured_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (schema_name, table_name, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_serving_storage_snapshot_lookup
    ON monitoring.serving_storage_snapshot (schema_name, table_name, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_serving_storage_snapshot_orphan
    ON monitoring.serving_storage_snapshot (snapshot_date, is_orphan) WHERE is_orphan = TRUE;

-- Output 2 (KK2): swap health -- 2 kolom baru ke monitoring.reverse_etl_sync_log
-- (dimiliki M2.4, sudah diperluas M5.5 dengan dataset_name dan M6.3 dengan
-- is_simulated -- pola extend-lewat-schema.sql-milestone-lain yang sama
-- persis, bukan edit scripts/reverse_etl/schema.sql). old_table_status
-- adalah nilai yang SUDAH DIHITUNG scripts/reverse_etl_mart_aggregated/sync.py
-- sejak M5.7 tapi tidak pernah ditulis (Keputusan A) -- kolom ini menampung
-- nilai itu ke depan, BUKAN mekanisme deteksi utama (lihat Keputusan C,
-- yang query pg_stat_user_tables langsung supaya 73 orphan pra-existing
-- tetap terdeteksi).
ALTER TABLE monitoring.reverse_etl_sync_log
    ADD COLUMN IF NOT EXISTS old_table_status TEXT;
ALTER TABLE monitoring.reverse_etl_sync_log
    ADD COLUMN IF NOT EXISTS swap_duration_ms NUMERIC;

-- Perluas alert_type monitoring.alerts (M1.2, diperluas M1.3/M6.3/M6.4/M6.5)
-- dengan 2 sumber sinyal baru M6.6 -- 2 alert_type TERPISAH (bukan 1
-- generik) karena KK2 eksplisit minta "dibedakan dari masalah query biasa"
-- -- orphan table dan swap lambat adalah 2 signature berbeda yang perlu
-- tetap terlihat berbeda satu sama lain juga.
ALTER TABLE monitoring.alerts DROP CONSTRAINT IF EXISTS alerts_alert_type_check;
ALTER TABLE monitoring.alerts ADD CONSTRAINT alerts_alert_type_check
    CHECK (alert_type IN (
        'volume_anomaly', 'freshness_delay', 'dq_test_failure', 'dirty_proportion_drift', 'value_anomaly',
        'dbt_test_failure', 'warehouse_volume_anomaly', 'reverse_etl_mismatch', 'ml_output_freshness_delay',
        'ml_output_incomplete_scoring', 'chatbot_connection_pool_spike',
        'serving_swap_orphan_table', 'serving_swap_slow'
    ));
