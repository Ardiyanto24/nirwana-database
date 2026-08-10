# Milestone 6.3: Monitoring Kesalahan dan Anomali di Pipeline Warehouse — Decisions

**Source:** `docs/03-implementation-plans/06-monitoring-warehouse-serving-fase2.md`, baris 86-105.
**Prasyarat:** Milestone 6.1 (Completed, peta 10 titik) dan 6.2 (Completed, `monitoring.pipeline_run_log`/`pipeline_run_status`).
**Status:** In Progress
**Date started:** 2026-08-11

## Contract (from source doc)

- **Lingkup:** Membangun deteksi untuk tiga jenis kejadian berbeda sifat: kegagalan job (pipeline health), penyimpangan kualitas/nilai data di tiap layer transformasi (`mart_cleaned`, `mart_aggregated`), dan volume/row count tidak wajar dibanding baseline historis — termasuk row count parity BigQuery vs PostgreSQL pasca-reverse-ETL. Termasuk memantau hasil pengujian data (DQ gate) yang sudah dipasang M2.3/M5.3 — mengonsolidasikan hasilnya, bukan membangun ulang. Freshness check `ml_output` jadi titik pengamatan eksplisit (satu-satunya sumber data eksternal di tengah pipeline internal).
- **Output:** (1) Konsolidasi hasil DQ gate `mart_cleaned`+`mart_aggregated`. (2) Volume/row-count anomaly, baseline rolling, tiap tahap transformasi + pasca-reverse-ETL. (3) Row-count parity BigQuery vs PostgreSQL, dikonsolidasikan. (4) Freshness check `ml_output` — kapan terakhir ditulis + apakah sensor menunggu lebih lama dari wajar.
- **Kriteria Keberhasilan:**
  1. Kegagalan pengujian data `mart_cleaned`/`mart_aggregated` (uji coba terkontrol) terlihat di monitoring tanpa buka log mentah.
  2. Penyimpangan volume buatan (uji coba terkontrol) terdeteksi, bisa dibedakan tahap asalnya.
  3. Ketidakcocokan row count BigQuery vs PostgreSQL (uji coba terkontrol) terdeteksi + tabel teridentifikasi.
  4. Keterlambatan `ml_output` (uji coba terkontrol) terdeteksi sebagai freshness issue, bukan cuma kegagalan sensor.

Milestone terbesar di keluarga 6.x sejauh ini, dan pertama yang menyentuh file terkait pipeline (2 workflow YAML M2.3/M5.3, +1 step masing-masing) — lihat Keputusan #1.

## Temuan Riset (3 Explore agent paralel)

- `warehouse/target/run_results.json` (artefak standar dbt) berisi `unique_id`/`status`/`execution_time`/`failures` per test — cukup untuk kebutuhan M6.3, belum pernah diparse di mana pun. Tidak diupload sebagai CI artifact, tidak terekspos GitHub Actions API — satu-satunya akses adalah dari proses di runner yang sama sebelum ditutup.
- Test count re-verifikasi live: `mart_cleaned` 36 (33 schema + 3 singular, cocok M2.3), `mart_aggregated` **190** (189 schema + 1 singular) — beda dari "244+1" di `report.md` M5.3, kemungkinan drift M5.6/M5.7. Tidak ditelusuri akar penyebab (di luar scope).
- `monitoring.reverse_etl_sync_log` (M2.4/M5.5) sudah lengkap untuk Output 3 — 0 mekanisme baru, murni konsolidasi.
- `wait_for_ml_output.py` cuma `print()` — tapi M6.2 sudah menangkap durasi sensor (titik 5, `pipeline_run_log.duration_seconds`) tanpa perlu instrumentasi baru.
- Pola Fase 1 (`detect_alerts.py`, `snapshot_value_anomaly.py`, `dq_alerts.py`) — algoritma rolling-baseline matang, siap direplikasi: mean±sigma per hari-dalam-minggu (volume), `monitoring.alerts` 1 tabel gabungan dengan `alert_type` CHECK extensible (dipakai 3× sebelumnya).
- Staging = VIEW (M2.2), bukan table — tidak ada row-count metadata sendiri, selalu identik `raw_production` — dikecualikan dari volume anomaly (redundan).

## Task Breakdown

6 checkpoint, commit tiap checkpoint.

- [x] **Checkpoint 1** — `decisions.md` + kredensial `warehouse-monitor-reader` + extend `schema.sql` — Acceptance: kredensial isolasi terbukti, schema live — Verify: `verify_dataset_isolation.py` 5/5 OK, `information_schema` — M
- [x] **Checkpoint 2** — Output 1 (KK1): `capture_dbt_test_results.py` + step baru 2 workflow YAML + fault-injection nyata — Verified: run 31436680183, 1/37 fail tertangkap tepat sesuai injeksi — S/M
- [x] **Checkpoint 3** — Output 2 (KK2): `snapshot_warehouse_volume.py` + `detect_volume_anomaly.py` + uji coba terkontrol 2 tabel — Verified: 123 tabel di-snapshot (23+23+77), 2 alert critical benar (mart_cleaned & mart_aggregated, masing-masing tabel teridentifikasi tepat), data sintetis dibersihkan — M
- [x] **Checkpoint 4** — Output 3 (KK3): `detect_parity_mismatch.py` + uji coba terkontrol — Verified: 1 mismatch sintetis terdeteksi tepat, run non-simulasi tetap 0 (isolasi terbukti) — S
- [ ] **Checkpoint 5** — Output 4 (KK4): `snapshot_ml_output_freshness.py` + `detect_ml_output_issues.py` + uji coba terkontrol — M
- [ ] **Checkpoint 6** — Workflow terjadwal + `simulate_test.py` + dokumentasi + `report.md` — M

## Technical Decisions

### 1. Menangkap detail hasil dbt test: step BARU di 2 workflow existing, `promote.py` TIDAK disentuh

**Context:** `run_results.json` tidak terekspos API manapun — satu-satunya akses adalah dari proses di runner yang sama.
**Decision:** Step baru (`if: always()`) tepat setelah step "build->test->swap gate" di `transform-mart-cleaned.yml`/`transform-mart-aggregated.yml`, menjalankan script yang membaca `run_results.json` dan menulis ke Postgres.
**Alternatives considered:** Edit `promote.py` langsung (paling invasif, menyentuh logic pipeline M2.3/M5.3 yang sudah battle-tested); wrapper script menggantikan pemanggilan `promote.py` (indirection tambahan tanpa manfaat lebih). Step baru independen paling tidak invasif — 0 baris `promote.py`/step existing disentuh.

### 2. Skema `monitoring.dbt_test_result`

`layer, unique_id, test_name, resource_type, status, execution_time, failures, github_run_id, captured_at`. `github_run_id` (dari env `GITHUB_RUN_ID`) — cross-reference ke `pipeline_run_log.run_id` (M6.2), menutup celah titik 3/7 (coarse pass/fail → sekarang bisa JOIN ke detail per-test).

### 3. Volume anomaly: cakupan `raw_production`+`mart_cleaned`+`mart_aggregated`, BUKAN `staging`

**Context:** Staging = view (M2.2), row count selalu identik `raw_production`.
**Decision:** Kecualikan staging dari snapshot. **Alasan:** memantau keduanya terpisah murni duplikasi tanpa sinyal baru.

### 4. Row count via `__TABLES__` (legacy metadata pseudo-table), bukan `COUNT(*)` per tabel

**Revisi saat implementasi** (Checkpoint 3): rencana awal `INFORMATION_SCHEMA.TABLE_STORAGE` **ternyata `Access Denied`** di project ini — dicoba dataset-qualified (`Dataset ... INFORMATION_SCHEMA was not found`, indikasi syntax salah) dan region-qualified (`Access Denied: User does not have permission`, syntax benar tapi ditolak) — kemungkinan besar restriksi BigQuery Sandbox mode (view ini terkait storage billing, project ini belum ada billing account). Diganti `SELECT table_id, row_count FROM \`project.dataset.__TABLES__\`` (legacy pseudo-table, beda mekanisme dari `INFORMATION_SCHEMA`, tidak kena restriksi yang sama) — **diverifikasi angka akurat**: `corporate_master__employees`=755, `corporate_master__guests`=24893, `corporate_master__properties`=6, seluruhnya cocok persis angka yang sudah dikonfirmasi M1.1. Manfaat inti keputusan asli tetap dipertahankan: 1 query per dataset (3 total) vs ~122 query individual `COUNT(*)`.

### 5. Discovery tabel dinamis, bukan config statis

`INFORMATION_SCHEMA.TABLE_STORAGE` otomatis mencakup tabel apa pun yang ada saat itu — tidak perlu maintain config manual tiap kali tabel baru ditambah lewat M5.6.

### 6. Rolling baseline: replikasi `detect_alerts.py` persis

`WINDOW_WEEKS=8`, `MIN_HISTORY_POINTS=3`, sigma warning=2/critical=3, same-day-of-week filter, `statistics.pstdev` zero-guarded.

### 7. Row-count parity: murni konsolidasi, 0 mekanisme baru, `sync.py` TIDAK disentuh

View `monitoring.warehouse_parity_status` di atas `reverse_etl_sync_log` existing — **diverifikasi langsung terhadap data real** (query live menunjukkan baris `mart_aggregated` sungguhan, `status='synced'`, `bq_row_count=pg_row_count` cocok).

**Revisi saat implementasi** (Checkpoint 4 Task 11): view ini hardcode `WHERE is_simulated = FALSE` (supaya aman dikonsumsi dashboard/M6.7 tanpa filter tambahan) — tapi ini berarti `detect_parity_mismatch.py` **tidak bisa** memakai view yang sama untuk uji coba terkontrol KK3 (baris mismatch sintetis `is_simulated=TRUE` tidak akan pernah terlihat lewat view). Diperbaiki: detector query LANGSUNG ke `reverse_etl_sync_log` dengan parameter `is_simulated` eksplisit (bukan lewat view) — view tetap jadi cara konsumsi yang benar untuk pemakaian normal, detector butuh akses lebih fleksibel untuk kebutuhan testing.

### 8. `reverse_etl_sync_log` dapat kolom baru `is_simulated`

`ALTER TABLE ... ADD COLUMN IF NOT EXISTS is_simulated BOOLEAN NOT NULL DEFAULT FALSE` — pola identik precedent M5.5 (`dataset_name`). Ditambahkan lewat `schema.sql` **milik M6.3 sendiri** (`scripts/monitoring_warehouse/`), bukan mengedit `scripts/reverse_etl/schema_monitoring.sql` (file M2.4) — menjaga batas kepemilikan file tetap bersih.

### 9. `monitoring.ml_output_freshness_snapshot` — tabel baru, formula dari `snapshot_freshness.py`

`lag_hours = (now - MAX(scored_at)) / 3600`.

### 10. Sensor duration anomaly: REUSE `pipeline_run_log`, 0 instrumentasi baru ke `wait_for_ml_output.py`

Titik 5 (M6.2) sudah punya `duration_seconds` per run — rolling baseline (algoritma #6) dijalankan langsung terhadap data itu.

### 11. Alerts: extend `monitoring.alerts` existing

`ALTER TABLE ... DROP/ADD CONSTRAINT` — 4 `alert_type` baru: `dbt_test_failure`, `warehouse_volume_anomaly`, `reverse_etl_mismatch`, `ml_output_freshness_delay`. **Diterapkan & diverifikasi**: `pg_get_constraintdef` mengonfirmasi seluruh 9 nilai (5 lama + 4 baru) benar.

### 12. Kredensial baru `warehouse-monitor-reader` (BigQuery, READER 4 dataset)

**Context:** M6.3 murni baca row-count/timestamp, tidak pernah menulis ke BigQuery.
**Decision:** Service account baru, dataset ACL READER `raw_production`+`mart_cleaned`+`mart_aggregated`+`ml_output` (bukan `staging` — Keputusan #3) + `roles/bigquery.jobUser` project-level.
**Alasan ditolak reuse `dbt-transform`:** project-level `dataEditor` (WRITE-capable) melanggar least-privilege (M2.6) tanpa alasan kuat untuk kebutuhan read-only.
**Dieksekusi & diverifikasi:** `gcloud iam service-accounts create warehouse-monitor-reader`; ACL 4 dataset via `bq show`/`bq update --source` (workaround `bq add-iam-policy-binding` "requires allowlisting", precedent M2.1/M3.6) — dijalankan lewat **PowerShell**, bukan Git Bash, karena kombinasi `bq.exe` (native Windows) + Python baca-tulis JSON via path Git-Bash-style menghasilkan file kosong/tidak ditemukan secara silent; PowerShell `Out-File -Encoding utf8` sendiri menambah BOM yang bikin `bq update` gagal parse — diperbaiki pakai `[System.IO.File]::WriteAllText` dengan `UTF8Encoding($false)` eksplisit. Key file `scripts/extract/gcp-warehouse-monitor-reader-key.json` (gitignored, dikonfirmasi `git check-ignore`). Verifikasi: `verify_dataset_isolation.py` 5/5 OK (4 allow + 1 deny `staging`), percobaan `CREATE TABLE` ditolak `403 Forbidden`. `.env`/`.env.example` + `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` diperbarui.

### 13. Folder scripts: lanjutkan `scripts/monitoring_warehouse/`, extend `schema.sql` M6.2

Tidak bikin folder/file baru — konsisten "extend, bukan mulai baru".

### 14. `simulate_test.py` — 1 file, 4 skenario, replikasi pola `scripts/dq/simulate_test.py`

Data sintetis langsung ke tabel snapshot Postgres (DML BigQuery blocked lagipula). Kecuali KK1 — butuh fault-injection nyata ke model dbt (pola M2.3/M5.3) karena yang diuji adalah pipa capture-nya sendiri.

### 15. Workflow terjadwal baru `monitoring-warehouse-dq-anomaly.yml`

`workflow_run` listener ke `"Reverse ETL Mart Aggregated to Serving PostgreSQL"` (titik paling akhir 10 titik M6.1).

## Open Questions Resolved with User

Tidak ada `AskUserQuestion` di milestone ini — seluruh fork desain (cara capture dbt test, cakupan volume anomaly, sumber row-count) punya jawaban teknis yang jelas lebih unggul setelah dianalisis (beda dari M6.2 yang punya 3 trade-off genuinely seimbang). User menyetujui plan lengkap via `ExitPlanMode` tanpa revisi.
