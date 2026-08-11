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
--
-- CATATAN M6.7: blok DROP+ADD CONSTRAINT yang tadinya di sini (hanya 10 nilai,
-- versi M6.3) DIHAPUS -- re-run apply_schema.py file ini gagal CheckViolation
-- terhadap data live sekarang karena 3 folder LAIN (chatbot_perf_monitor M6.5,
-- serving_layer_monitor M6.6) sudah menambah alert_type baru via file schema.sql
-- mereka sendiri sejak blok ini ditulis -- constraint yang sama dipakai bersama
-- 4 file terpisah, tiap file cuma re-apply versi historisnya sendiri kalau
-- di-run ulang. Definisi final (union seluruh alert_type sampai M6.7) tetap
-- satu, dipindah ke blok Milestone 6.7 di akhir file ini -- lihat di bawah.

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

-- Milestone 6.7 — Dashboard dan Alerting Terpadu (Fase 2)
-- Perluasan lanjutan schema monitoring bersama, additive only.
-- Rujukan: milestones/6.7-dashboard-alerting-terpadu/decisions.md

-- Checkpoint 1 (Keputusan A): graph dependency statis 10 titik pengamatan
-- (docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md,
-- kolom Dependency + Klasifikasi Prioritas), dasar view root-cause Checkpoint 2.
-- 1 baris per (titik_id, depends_on_titik_id); titik_id=1 (root, tanpa
-- dependency) direpresentasikan depends_on_titik_id=NULL. titik_label/
-- priority_class didenormalisasi (redundan di tiap baris titik yang sama) --
-- diterima karena tabel ini statis, 12 baris total, tidak pernah di-update.
CREATE TABLE IF NOT EXISTS monitoring.titik_dependency (
    id                   BIGSERIAL PRIMARY KEY,
    titik_id             SMALLINT NOT NULL CHECK (titik_id BETWEEN 1 AND 10),
    depends_on_titik_id  SMALLINT CHECK (depends_on_titik_id BETWEEN 1 AND 10),
    titik_label          TEXT NOT NULL,
    priority_class       TEXT NOT NULL CHECK (priority_class IN ('kritis', 'tinggi', 'sedang'))
);

-- NULL depends_on_titik_id (titik 1, root) tidak bisa diandalkan UNIQUE biasa
-- (Postgres menganggap tiap NULL berbeda) -- pola sama COALESCE yang sudah
-- dipakai monitoring.pipeline_run_log (M6.2) untuk step_name nullable.
CREATE UNIQUE INDEX IF NOT EXISTS uq_titik_dependency_edge
    ON monitoring.titik_dependency (titik_id, COALESCE(depends_on_titik_id, 0));

INSERT INTO monitoring.titik_dependency (titik_id, depends_on_titik_id, titik_label, priority_class) VALUES
    (1,  NULL, 'Sinkronisasi ekstraksi (production -> raw_production)', 'tinggi'),
    (2,  1,    'Transformasi staging -> mart_cleaned', 'kritis'),
    (3,  2,    'Pengujian data: validasi mart_cleaned', 'tinggi'),
    (4,  2,    'Trigger scoring eksternal (mock)', 'sedang'),
    (5,  4,    'Sensor: menunggu ml_output selesai ditulis', 'sedang'),
    (6,  2,    'Transformasi mart_aggregated (+ join ml_output)', 'tinggi'),
    (6,  5,    'Transformasi mart_aggregated (+ join ml_output)', 'tinggi'),
    (7,  6,    'Pengujian data: validasi mart_aggregated', 'tinggi'),
    (8,  6,    'Reverse ETL: mart_aggregated -> PostgreSQL', 'tinggi'),
    (9,  2,    'Reverse ETL: mart_cleaned -> PostgreSQL', 'tinggi'),
    (10, 8,    'Post-sync validation (row count parity check)', 'tinggi'),
    (10, 9,    'Post-sync validation (row count parity check)', 'tinggi')
ON CONFLICT (titik_id, COALESCE(depends_on_titik_id, 0)) DO NOTHING;

-- Alert_type baru (Keputusan B, Checkpoint 2): sinyal turunan gap dependency
-- Titik 1 -> 2 yang belum digate lewat workflow_run (docs/keputusan-tertunda.md).
ALTER TABLE monitoring.alerts DROP CONSTRAINT IF EXISTS alerts_alert_type_check;
ALTER TABLE monitoring.alerts ADD CONSTRAINT alerts_alert_type_check
    CHECK (alert_type IN (
        'volume_anomaly', 'freshness_delay', 'dq_test_failure', 'dirty_proportion_drift', 'value_anomaly',
        'dbt_test_failure', 'warehouse_volume_anomaly', 'reverse_etl_mismatch', 'ml_output_freshness_delay',
        'ml_output_incomplete_scoring', 'chatbot_connection_pool_spike',
        'serving_swap_orphan_table', 'serving_swap_slow', 'pipeline_dependency_gap'
    ));

-- Checkpoint 2 (Keputusan A): 2 view root-cause correlation, real-time,
-- tanpa job/tabel snapshot baru -- logic deteksi TETAP di 8 detect_*.py/
-- check_*.py existing, view ini murni menyusun ulang hasilnya. 5 alert_type
-- Fase 1 (volume_anomaly, freshness_delay, dq_test_failure,
-- dirty_proportion_drift, value_anomaly -- production, sebelum raw_production)
-- dan chatbot_connection_pool_spike (Titik 11, out of scope peta M6.1) SENGAJA
-- tidak dipetakan ke titik manapun -- baris itu tersaring keluar (titik_id
-- NULL) dari view ini, bukan bug.
--
-- dbt_test_failure dipetakan juga meski TIDAK PERNAH diinsert skrip manapun
-- (temuan M6.7 decisions.md -- reserved-tapi-mati sejak M6.3) -- future-proof,
-- tidak berpengaruh selama tidak ada baris.
--
-- is_simulated DIEKSPOS (bukan difilter di sini) -- pola sama
-- detect_parity_mismatch.py vs monitoring.warehouse_parity_status (view aman
-- default, detector butuh akses is_simulated eksplisit): karena view ini
-- gabungan 3 tabel (bukan 1 tabel sederhana), "bypass view" tidak praktis
-- untuk Checkpoint 5 (uji coba terkontrol butuh mem-verifikasi VIEW ini
-- sendiri, bukan logic Python terpisah) -- jadi filter "aman untuk
-- konsumsi dashboard" (is_simulated=false) dipindah ke titik KONSUMSI
-- (panel Grafana Checkpoint 3, alert rule Checkpoint 4), bukan dibakukan di
-- view. pipeline_run_log tidak punya kolom is_simulated -- diturunkan dari
-- trigger_event='simulated' (marker M6.2/M6.3). dbt_test_result juga tidak
-- punya kolom ini DAN tidak ada konvensi injeksi sintetis untuk tabel itu
-- (M6.3 decisions.md -- butuh fault-injection dbt nyata, bukan snapshot) --
-- is_simulated di-hardcode FALSE (akurat, tidak ada baris sintetis yang
-- pernah masuk ke tabel ini).
-- DROP+CREATE (bukan CREATE OR REPLACE) -- Postgres menolak REPLACE kalau urutan/nama
-- kolom berubah dari versi sebelumnya (terjadi nyata saat Checkpoint 5 menambah
-- is_simulated di tengah daftar kolom), re-runnable lewat DROP IF EXISTS dulu.
DROP VIEW IF EXISTS monitoring.alerts_with_root_cause;
DROP VIEW IF EXISTS monitoring.titik_event_today;

CREATE VIEW monitoring.titik_event_today AS
WITH alerts_mapped AS (
    SELECT
        CASE
            WHEN alert_type = 'warehouse_volume_anomaly' AND schema_name = 'raw_production' THEN 1
            WHEN alert_type = 'warehouse_volume_anomaly' AND schema_name = 'mart_cleaned' THEN 2
            WHEN alert_type = 'warehouse_volume_anomaly' AND schema_name = 'mart_aggregated' THEN 6
            WHEN alert_type = 'dbt_test_failure' AND schema_name = 'mart_cleaned' THEN 3
            WHEN alert_type = 'dbt_test_failure' AND schema_name = 'mart_aggregated' THEN 7
            WHEN alert_type = 'ml_output_incomplete_scoring' THEN 4
            WHEN alert_type = 'ml_output_freshness_delay' THEN 5
            WHEN alert_type = 'serving_swap_slow' AND schema_name = 'mart_aggregated' THEN 8
            WHEN alert_type = 'serving_swap_slow' AND schema_name = 'mart_cleaned' THEN 9
            WHEN alert_type = 'reverse_etl_mismatch' THEN 10
            WHEN alert_type = 'serving_swap_orphan_table' THEN 10
            WHEN alert_type = 'pipeline_dependency_gap' THEN 1
            ELSE NULL
        END AS titik_id,
        'alerts' AS event_source,
        severity,
        (alert_type || ': ' || detail) AS detail,
        triggered_at AS event_at,
        is_simulated
    FROM monitoring.alerts
    WHERE triggered_at::date = CURRENT_DATE
)
SELECT titik_id, event_source, severity, detail, event_at, is_simulated
FROM alerts_mapped
WHERE titik_id IS NOT NULL

UNION ALL

SELECT
    titik_id,
    'pipeline_run_log' AS event_source,
    'critical' AS severity,
    ('Titik ' || titik_id || ' gagal: ' || workflow_name || COALESCE(' / step ' || step_name, '')) AS detail,
    completed_at AS event_at,
    (trigger_event = 'simulated') AS is_simulated
FROM monitoring.pipeline_run_log
WHERE status = 'failure'
  AND started_at::date = CURRENT_DATE

UNION ALL

SELECT
    CASE layer WHEN 'mart_cleaned' THEN 3 WHEN 'mart_aggregated' THEN 7 END AS titik_id,
    'dbt_test_result' AS event_source,
    'critical' AS severity,
    ('DQ gate ' || layer || ' gagal: ' || COALESCE(test_name, unique_id)) AS detail,
    captured_at AS event_at,
    FALSE AS is_simulated
FROM monitoring.dbt_test_result
WHERE status = 'fail'
  AND captured_at::date = CURRENT_DATE;

-- Recursive CTE menaiki monitoring.titik_dependency dari tiap event hari ini;
-- root_titik_id = leluhur TERTINGGI yang juga punya event hari ini (kalau
-- tidak ada leluhur gagal, event itu sendiri adalah root -- is_root=true).
-- depth<10 sekadar guard defensif (graph 10 titik adalah DAG, tidak mungkin
-- siklus, tapi tetap dibatasi). is_simulated diteruskan dari event LEAF
-- (bukan leluhurnya) -- konsumen (dashboard/alert rule) filter di sini.
CREATE VIEW monitoring.alerts_with_root_cause AS
WITH RECURSIVE ancestry AS (
    SELECT
        e.titik_id AS event_titik_id, e.event_source, e.severity, e.detail, e.event_at, e.is_simulated,
        e.titik_id AS current_titik_id, 0 AS depth
    FROM monitoring.titik_event_today e

    UNION ALL

    SELECT
        a.event_titik_id, a.event_source, a.severity, a.detail, a.event_at, a.is_simulated,
        td.depends_on_titik_id, a.depth + 1
    FROM ancestry a
    JOIN monitoring.titik_dependency td ON td.titik_id = a.current_titik_id
    WHERE td.depends_on_titik_id IS NOT NULL
      AND a.depth < 10
      AND EXISTS (
          SELECT 1 FROM monitoring.titik_event_today e2
          WHERE e2.titik_id = td.depends_on_titik_id
      )
),
root_per_event AS (
    SELECT DISTINCT ON (event_titik_id, event_source, detail, event_at)
        event_titik_id, event_source, severity, detail, event_at, is_simulated, current_titik_id AS root_titik_id
    FROM ancestry
    ORDER BY event_titik_id, event_source, detail, event_at, depth DESC
)
SELECT
    event_titik_id AS titik_id,
    event_source,
    severity,
    detail,
    event_at,
    is_simulated,
    root_titik_id,
    (root_titik_id = event_titik_id) AS is_root
FROM root_per_event;
