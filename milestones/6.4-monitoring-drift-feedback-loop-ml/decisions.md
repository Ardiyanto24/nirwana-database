# Milestone 6.4: Monitoring Data Drift Feedback Loop ML — Decisions

**Source:** `docs/03-implementation-plans/06-monitoring-warehouse-serving-fase2.md` (baris 108-127)
**Status:** Done
**Date started:** 2026-08-11

## Contract (from source doc)

- **Lingkup:** Memantau kesehatan feedback loop ML — model staleness per `model_version`, validasi kelengkapan `ml_output` vs populasi entity `mart_cleaned`, dan tren feature/prediction drift (kalau datanya sudah diekspos pipeline scoring, bukan dihitung ulang di sini).
- **Output:** (1) Mekanisme pemantauan model staleness per `model_version`. (2) Validasi kelengkapan `ml_output` terhadap populasi entity. (3) Dashboard/tampilan tren feature drift dan prediction drift, bersumber dari data pipeline scoring.
- **Kriteria Keberhasilan:**
  - KK1: Tim bisa melihat kapan model terakhir di-retrain untuk tiap `model_version` yang aktif tanpa bertanya langsung ke tim Data Scientist.
  - KK2: Entity yang gagal ter-score (ada di populasi tapi tidak muncul di `ml_output`) teridentifikasi otomatis.
  - KK3: Tren drift (jika data drift sudah diekspos oleh pipeline scoring) tervisualisasi dan bisa dipantau dari waktu ke waktu.
  - Catatan ketergantungan eksplisit dari dokumen sumber: threshold "signifikan" untuk drift dan bentuk tabel drift itu sendiri bergantung kesepakatan dengan tim Data Scientist — milestone ini menyediakan **kapasitas** pemantauan begitu data tersedia, bukan menentukan threshold-nya.

## Temuan Riset

Riset dilakukan lewat Explore agent (baca `milestones/5.4-*`, `scripts/ml_scoring/`, `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` §9.4.2/§9.7/Bagian 10, `docs/keputusan-tertunda.md`, workflow YAML terkait) + pembacaan langsung `scripts/ml_scoring/mock_score.py`.

1. **`model_version` adalah string konstan hardcoded** — `mock_score.py:48`, `MODEL_VERSION = "occupancy_forecast_mock_v1"`, diinjeksikan ke SETIAP baris lewat SQL template (baris 81). Tidak ada logic retrain, tidak pernah berubah sejak M5.4 pertama jalan (dikonfirmasi `logs.md` M5.4 Checkpoint 2: 252→504→756 baris, `model_version` selalu sama). Tidak ada cadence retrain sungguhan untuk dikalibrasi jadi threshold "wajar".

2. **Tidak ada tabel/dataset drift apa pun di seluruh repo.** `ml_monitoring.feature_drift` cuma teks ilustratif di dokumen arsitektur §9.4.2 (baris 476), dalam paragraf yang eksplisit menyebut "dapat dilakukan" (deskripsi mekanisme, bukan spesifikasi bangun). Bagian 10 dokumen yang sama ("Area yang Masih Memerlukan Validasi"), item #3: threshold drift "belum ditentukan, perlu didiskusikan bersama Data Scientist". Checklist akhir dokumen (baris 589-590) kedua item drift masih `[ ]` belum dicentang. Grep repo-wide untuk "drift" (55 file) hampir seluruhnya `schema_drift` (M1.4, konsep production schema berbeda total) — cuma dokumen arsitektur & dokumen sumber M6.4 sendiri yang memakai "drift" dalam pengertian ML.

3. **Populasi entity yang benar untuk completeness check BUKAN `mart_cleaned` langsung**, meski itu kata literal dokumen sumber (baris 118). `mock_score.py` (`SOURCE_TABLE`, baris 44) sebenarnya membaca dari `mart_aggregated.fact_revenue_room_type_daily`, dan `entity_id` (`property_id:room_type_id`, baris 79) memakai `room_type_id` — surrogate key `mart_aggregated.dim_room_type` (`row_number() over (order by room_type)`), BUKAN `room_type` string mentah yang ada di `mart_cleaned__daily_occupancy`. Grain scoring per run: distinct `(property_id, room_type_id)` di `base_stats` (window `lookback_days=30` dari `last_date = MAX(period_date)`), di-cross-join `horizon_days=14` (`target_date`), seluruhnya berbagi `feature_snapshot_at = TIMESTAMP(last_date)` yang sama dalam 1 run. Ini pola revisi teknis yang sama seperti M4.1 (dokumen sumber ternyata under-spesifikasi dibanding realita implementasi) — dipaksa temuan, bukan pilihan gaya.

4. **`warehouse-monitor-reader` (M6.3) sudah READER di `ml_output` + `mart_aggregated`** (dan `raw_production`, `mart_cleaned`) — cukup untuk query staleness & completeness tanpa kredensial baru. TAPI `list_datasets()` (dibutuhkan canary drift) butuh **enumerasi dataset project-wide**, secara IAM beda dari dataset-ACL per-dataset yang sudah dipegang kredensial ini (dataset ACL cuma memberi visibilitas ke dataset yang secara eksplisit di-grant, tidak otomatis bisa `list_datasets()` project-wide).

5. **`monitoring.alerts.severity` CHECK cuma `('warning', 'critical')`** (`scripts/monitoring/schema.sql:41`) — tidak ada level "info". Konsekuensi: mekanisme yang murni informational (staleness, canary drift) tidak menulis ke `monitoring.alerts` sama sekali, cukup ke tabel dedicated masing-masing.

## Diskusi dengan User (2 keputusan material, dikunci lewat AskUserQuestion)

### Q1 — Pendekatan staleness, mengingat `model_version` tidak pernah berubah
Diajukan 3 opsi: (A) threshold alert arbitrer, (B) informational-only tanpa threshold, (C) skip/Known Gap. **User memilih (B)**, plus eksplisit minta ditambahkan catatan di `docs/keputusan-tertunda.md` untuk didiskusikan dengan tim Data Scientist.

### Q2 — Penanganan KK3 (drift), mengingat tidak ada data drift apa pun
User awalnya minta penjelasan lebih detail sebelum memutuskan (diberikan penjelasan panjang soal 3 opsi: canary check / Known Gap murni / placeholder skema spekulatif, termasuk trade-off masing-masing). Setelah penjelasan, **user memilih Opsi A (canary check)**.

## Technical Decisions

### Decision: Model staleness — informational only, TANPA alert threshold
- **Context:** `model_version` cuma 1 nilai statis, tidak ada cadence retrain sungguhan untuk dikalibrasi jadi angka ambang batas yang defensible.
- **Decision:** Snapshot per `model_version` (`first_scored_at`, `last_scored_at`, `row_count_total`) + view yang melaporkan "sudah berapa hari model_version aktif tidak berganti" — TIDAK push ke `monitoring.alerts`, TIDAK ada klaim ambang batas "wajar".
- **Alternatives considered:** Threshold arbitrer ala freshness-lag Fase 1 (mis. 30 hari) — ditolak user karena angkanya sendiri tidak berdasar evidence apa pun (beda dari freshness-lag yang punya precedent nyata Fase 1); skip total — ditolak karena KK1 tetap bisa dipenuhi tanpa perlu alert.
- **Rejected because:** User secara eksplisit memilih B setelah diberi 3 opsi.

### Decision: KK3 drift — Canary check (deteksi eksistensi dataset, nol asumsi skema)
- **Context:** Tidak ada tabel/dataset drift apa pun untuk dipantau; menebak skema kolom berisiko salah total (dokumen arsitektur sendiri bilang ini "area validasi terbuka").
- **Decision:** 1 script harian, `list_datasets()` via `warehouse-monitor-reader`, cocokkan pola nama (`%drift%`, `%ml_monitoring%`, case-insensitive) — TIDAK menebak kolom apa pun. Kalau ditemukan, catat 1 baris ke tabel dedicated. TIDAK push ke `monitoring.alerts` (bukan warning/critical, murni informational).
- **Alternatives considered:** Known Gap murni tanpa kode (paling defensif, tapi pasif — butuh manusia ingat cek ulang); placeholder skema spekulatif (nilai lebih tinggi kalau tebakan benar, tapi risiko kerja terbuang kalau salah, pola anti-pattern berulang di project ini — M2.1, M5.2).
- **Rejected because:** User memilih canary check setelah penjelasan detail trade-off ketiganya.

### Decision: Completeness pakai `mart_aggregated.fact_revenue_room_type_daily`, bukan `mart_cleaned` langsung
- **Context:** Dokumen sumber literal bilang "populasi entity di `mart_cleaned`", tapi `mock_score.py` sendiri membaca dari `mart_aggregated.fact_revenue_room_type_daily` dan `entity_id` cuma cocok dengan `room_type_id` surrogate key di situ.
- **Decision:** Populasi "diharapkan ter-score" = distinct `(property_id, room_type_id)` di `fact_revenue_room_type_daily` pada `period_date` yang sama dengan `feature_snapshot_at` terbaru di `ml_output.predictions`. Populasi "sudah ter-score" = distinct `(property_id, room_type_id)` di `ml_output.predictions` pada `feature_snapshot_at` yang sama. Selisih = entity hilang, dicatat baris per baris (bukan cuma angka) sesuai literal KK2 "teridentifikasi otomatis". Ini satu-satunya dari 3 mekanisme M6.4 yang push ke `monitoring.alerts` (`alert_type='ml_output_incomplete_scoring'`) — beda dari staleness/drift karena "ada entity hilang" adalah temuan biner berbasis evidence, bukan threshold tebakan.
- **Alternatives considered:** Ikuti literal dokumen sumber (`mart_cleaned__daily_occupancy`) — ditolak karena grain-nya (`room_type` string) tidak match `entity_id` yang sebenarnya dipakai `ml_output`, akan menghasilkan false-positive "missing" untuk SELURUH entity (karena join key tidak pernah cocok).
- **Derived, tidak ditanyakan ke user** — dipaksa oleh temuan teknis, pola sama M4.1.

### Decision: Kredensial — reuse `warehouse-monitor-reader`, tambah 1 IAM role project-level
- **Context:** Kebutuhan M6.4 (baca `ml_output`+`mart_aggregated`, plus `list_datasets()`) adalah subset dari yang sudah dipegang M6.3, kecuali kemampuan enumerasi dataset project-wide.
- **Decision:** Tidak bikin kredensial baru. Tambah `roles/bigquery.metadataViewer` project-level ke `warehouse-monitor-reader` via `gcloud projects add-iam-policy-binding` — beda mekanisme dari dataset-ACL (`bq update --source`) yang dipakai untuk 4 grant sebelumnya, karena ini kebutuhan project-wide bukan per-dataset.
- **Dieksekusi:** Diblokir classifier auto-mode (pola sama M2.1-2.3) — dijalankan manual oleh user.
- **Alternatives considered:** Kredensial baru khusus canary — ditolak, over-provisioning untuk kebutuhan sekecil "list nama dataset".

### Decision: Uji coba terkontrol KK2 pakai fault-injection nyata ke `mock_score.py`, BUKAN data sintetis Postgres
- **Context:** Data BigQuery statis & bersih — tiap entity di `base_stats` pasti ter-score by construction (tidak ada filter yang bisa exclude entity secara alami). DML diblokir Sandbox mode, jadi tidak bisa menyuntik baris BigQuery langsung seperti M6.3 lakukan untuk Postgres.
- **Decision:** Modifikasi sementara `mock_score.py` (exclude 1 `property_id` dari query `base_stats`), trigger `scoring-occupancy-forecast.yml` manual, verifikasi detector menangkap entity yang di-exclude, revert `mock_score.py`. Pola identik M2.3/M5.3/M6.3-Task6 (fault-injection nyata ke pipeline, diverifikasi, direvert).
- **Alternatives considered:** Data sintetis langsung ke `ml_output_missing_entity` Postgres (pola `is_simulated` M6.3) — ditolak karena tidak menguji QUERY completeness-nya sendiri (bagian yang sebenarnya perlu dibuktikan benar), cuma menguji jalur tulis/alert setelah hasil sudah ada.

### Decision: Continue `scripts/monitoring_warehouse/`, extend file existing
- Konsisten pola "extend, bukan mulai baru" — `schema.sql`, `simulate_test.py`, `monitoring-warehouse-dq-anomaly.yml` (ketiganya sudah ada dari M6.2/M6.3) di-extend, bukan dibuat file/folder/workflow paralel baru.

## Open Questions Resolved with User

- Q: Bagaimana staleness ditangani kalau `model_version` tidak pernah berubah? → A: Informational only, tanpa threshold, plus catatan `keputusan-tertunda.md` untuk didiskusikan dengan tim Data Scientist.
- Q: Bagaimana KK3 (drift) ditangani kalau tidak ada data drift sama sekali? → A: Canary check (deteksi eksistensi dataset, nol asumsi skema kolom).

## Task Breakdown

### Checkpoint 1 — Fondasi: decisions.md + kredensial + schema
- [x] Task 1: `decisions.md` — dokumen ini.
- [x] Task 2: Update kredensial `warehouse-monitor-reader` — tambah `roles/bigquery.metadataViewer` project-level. Acceptance: `list_datasets()` mengembalikan seluruh dataset existing tanpa exception. Verify: jalankan `list_datasets()` manual. **Selesai** — diblokir classifier, dieksekusi manual oleh user, diverifikasi 7/7 dataset terlihat setelah propagasi IAM.
- [x] Task 3: Extend `scripts/monitoring_warehouse/schema.sql` — 5 tabel/view baru + extend `alerts.alert_type` CHECK. Acceptance: seluruh objek baru live. Verify: query `information_schema`. **Selesai**.

### Checkpoint 2 — Output 1: Model staleness (KK1)
- [x] Task 4: `scripts/monitoring_warehouse/snapshot_ml_model_version.py`. **Selesai**.
- [x] Task 5: Entri baru `docs/keputusan-tertunda.md`. **Selesai**.
- [x] Task 6: Verifikasi terhadap data live. **Selesai**.

### Checkpoint 3 — Output 2: Completeness validation (KK2)
- [x] Task 7: `scripts/monitoring_warehouse/check_ml_output_completeness.py`. **Selesai** — 1 bug ditemukan+diperbaiki (entity_id komposit, lihat logs.md).
- [x] Task 8: Baseline live (harus 0 missing). **Selesai** — expected=18 scored=18 missing=0.
- [x] Task 9: Uji coba terkontrol — fault-injection nyata `mock_score.py`, revert. **Selesai** — 3 entity P03 terdeteksi tepat.

### Checkpoint 4 — Output 3: Drift canary (KK3)
- [x] Task 10: `scripts/monitoring_warehouse/check_drift_data_availability.py`. **Selesai**.
- [x] Task 11: Verifikasi 2 jalur (found=false state sekarang; found=true via dataset throwaway `bq mk`/`bq rm`). **Selesai**.

### Checkpoint 5 (final) — Konsolidasi
- [x] Task 12: Extend `monitoring-warehouse-dq-anomaly.yml` — 3 step baru. **Selesai** — run 31443361931 sukses penuh.
- [x] Task 13: Extend `simulate_test.py` — staleness + drift canary (KK2 sengaja tidak masuk, sama alasan KK1 M6.3). **Selesai** — 6/6 skenario PASS.
- [x] Task 14: Update `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md`. **Selesai**.
- [x] Task 15: `logs.md` + `report.md`. **Selesai**.
