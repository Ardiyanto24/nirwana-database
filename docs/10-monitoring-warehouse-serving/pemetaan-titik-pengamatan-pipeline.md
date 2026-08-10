# Peta Titik Pengamatan Pipeline — Fase 2 (Warehouse & Serving)

**Hasil kerja Milestone 6.1** (`docs/03-implementation-plans/06-monitoring-warehouse-serving-fase2.md`)

| | |
|---|---|
| **Dokumen rujukan kanonis** | `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` §9.1 (10 langkah orkestrasi end-to-end) |
| **Sumber verifikasi** | `.github/workflows/*.yml`, `scripts/*/schema.sql`, tabel `monitoring.*` (production Supabase), `report.md` 32 milestone (1.1-5.7) |
| **Metode** | Pembacaan langsung bertahap per 7 layer pengerjaan warehouse, disilang-cek ke kode/config live (bukan cuma narasi dokumen arsitektur) |
| **Status** | Completed. **Update Milestone 6.2 (2026-08-10)**: titik 1-9 sekarang punya sinyal tambahan `monitoring.pipeline_run_log`/`pipeline_run_status` (status+durasi per run, terbukti lewat trigger nyata) — lihat catatan per baris dan `milestones/6.2-monitoring-log-proses-pipeline/report.md`. |

> Dokumen ini rujukan langsung untuk Milestone 6.2 (log proses), 6.3 (kesalahan/anomali), 6.4 (drift ML), 6.5 (performa query chatbot), 6.6 (serving layer), dan 6.7 (dashboard terpadu). Tidak perlu analisis ulang dari nol.

---

## Catatan Penting Sebelum Membaca Peta

### 1. Diskrepansi "10 vs 11 titik"

`rancangan-arsitektur-data-platform-elt.md` §9.1 (sumber kanonis) mendefinisikan **persis 10 langkah**, berakhir di "Post-sync validation (row count parity check)" — tidak menyertakan konsumsi oleh Data Analyst/AI Chatbot. `06-monitoring-warehouse-serving-fase2.md` (baris 35-46) menambahkan butir ke-11 ("Konsumsi oleh Data Analyst dan AI Chatbot") di daftar "Alur yang perlu dipantau"-nya, sementara Kriteria Keberhasilan Milestone 6.1 tetap menyebut literal **"Setiap 10 titik pengamatan"**.

**Keputusan (`milestones/6.1-inventarisasi-titik-pengamatan/decisions.md` #2):** Peta inti di bawah mengikuti 10 titik §9.1 — memenuhi KK secara literal. Titik ke-11 dicatat terpisah di bagian akhir dokumen ini sebagai catatan out-of-scope, bukan didiamkan.

### 2. Dua temuan risiko lintas-titik

Ditemukan saat sintesis peta ini, dicatat lengkap di `docs/keputusan-tertunda.md` (bukan diperbaiki di M6.1 — di luar wewenang milestone observasional ini):

- **Titik 1→2 tidak digate** — dependency-nya cuma buffer waktu (cron 03:00→05:00 UTC), bukan `workflow_run` seperti seluruh dependency lain di pipeline ini. Kalau ekstraksi gagal, transform tetap berjalan tanpa mekanisme apa pun yang menghentikan/memberi tahu. Dampak saat ini rendah (dataset production statis), tapi gap struktural nyata.
- **Titik 3 & 7 (DQ gate `promote.py`) tidak punya sinyal queryable sama sekali** — gate-nya terbukti bekerja benar (2× dibuktikan lewat fault-injection nyata: M2.3, M5.3), tapi hasilnya cuma exit code + `dbt run_results.json` efemeral di dalam run CI. **Prasyarat langsung Milestone 6.3** — wajib direvisit di awal breakdown-nya, lihat entri `docs/keputusan-tertunda.md`.

---

## Peta 10 Titik Pengamatan

| # | Tahap (§9.1) | Sumber Sinyal Tersedia | Sinyal Belum Ada (Gap) | Dependency (menunggu titik apa) | Klasifikasi Prioritas |
|---|---|---|---|---|---|
| 1 | Sinkronisasi ekstraksi (production → `raw_production`) | `monitoring.extract_cursor` (`schema_name`,`table_name`,`last_cursor`,`updated_at`, `scripts/extract/schema.sql`) + log run `extract-production.yml` (cron 03:00 UTC) + **`monitoring.pipeline_run_log`/`pipeline_run_status`** (M6.2, `granularity='detailed'`, run-level, terbukti otomatis via `workflow_run` listener) | Cursor cuma menangkap INSERT, tidak menangkap UPDATE ke baris lama (M2.1, diterima sebagai batasan sadar karena data production statis). Risiko expirasi BigQuery Sandbox untuk `raw_production` sudah dimitigasi (`renew_expiration.py` terjadwal di workflow yang sama). | Root — tidak ada dependency masuk | **Tinggi** |
| 2 | Transformasi: staging → intermediate → `mart_cleaned` | Log run `transform-mart-cleaned.yml` (cron 05:00 UTC) — menjalankan dbt staging build lalu `scripts/mart_cleaned/promote.py` + **`pipeline_run_log`** (M6.2, `granularity='detailed'`, step-level: step "build->test->swap gate ke mart_cleaned") | ⚠️ Dependency ke titik 1 cuma buffer waktu (03:00→05:00 UTC), **bukan** `workflow_run` — lihat `docs/keputusan-tertunda.md`. DML diblokir total di BigQuery Sandbox mode (M2.3) → `mart_cleaned` full refresh permanen sampai billing GCP aktif (`docs/keputusan-tertunda.md` "Aktivasi billing GCP..."). | Titik 1 (tidak digate) | **Kritis** — akar fan-out ke 3 cabang paralel (titik 3/9 lewat workflow sama, titik 4, titik 6 lewat `workflow_run` "Transform Staging and Mart Cleaned") |
| 3 | Pengujian data: validasi `mart_cleaned` | Gate `scripts/mart_cleaned/promote.py` (36 dbt test: `unique`/`not_null`/`relationships`/`accepted_values`/3 custom business rule) — terbukti bekerja lewat fault-injection nyata (M2.3: `total_amount=-500000` disuntik ke `mart_cleaned__bookings`, test FAIL, swap dibatalkan). **M6.2**: `pipeline_run_log` sekarang punya sinyal pass/fail kasar (`granularity='coarse'`, step sama dengan titik 2), terbukti otomatis via trigger nyata. | ❌ Sinyal M6.2 cuma pass/fail keseluruhan step — **hasil per-test (36 dbt test mana yang gagal) masih tidak ditulis ke tabel manapun**, cuma exit code + `dbt run_results.json` efemeral di run CI. `monitoring.dq_test_results` yang sudah ada adalah hasil `scripts/dq/build_and_run.py` (Great Expectations, data production Fase 1) — mekanisme dan tabel berbeda sepenuhnya. Gap detail ini tetap prasyarat Milestone 6.3, TIDAK tertutup oleh M6.2 — lihat `docs/keputusan-tertunda.md`. | Titik 2 (gate sebelum swap, workflow sama) | **Tinggi** |
| 4 | Trigger scoring job eksternal (pipeline Data Scientist) | `workflow_run` listener `scoring-occupancy-forecast.yml`, menulis `ml_output.predictions` (`scripts/ml_scoring/mock_score.py`, mock/provisional — M5.4) + **`pipeline_run_log`** (M6.2, `granularity='detailed'`, run-level) | Tidak ada tabel log khusus proses scoring — cuma status run GitHub Actions | Titik 2 (paralel dengan titik 6 & 9, sama-sama listener `workflow_run` "Transform Staging and Mart Cleaned") | Sedang — desain isolated-failure, dibuktikan M5.4 |
| 5 | Sensor: menunggu `ml_output` selesai ditulis | `scripts/ml_scoring/wait_for_ml_output.py` (polling `COUNT(*)` `ml_output.predictions`), terbukti isolated-failure lewat fault-injection nyata (M5.4: model dipaksa tidak ada, sensor timeout, job tetap `success`, 76 tabel non-ML tetap ter-promote). **M6.2**: `pipeline_run_log` sekarang punya sinyal pass/fail+durasi sensor (`granularity='detailed'`, step sendiri, terbukti otomatis via trigger nyata). | ❌ Hasil sensor detail (percobaan ke berapa baru sukses, dst) masih cuma di log run GitHub Actions mentah — M6.2 cuma mencatat hasil akhir step, bukan isi log polling-nya. Timeout realistis (~30 percobaan × 120 detik ≈ 60 menit) **belum pernah diuji habis** — cuma versi dipersingkat (`sensor_max_attempts`/`sensor_interval_seconds` input) dipakai di uji coba terkontrol CI. | Titik 4 | Sedang — tapi **fokus eksplisit Milestone 6.3** per dokumen sumber (freshness `ml_output` sebagai titik pengamatan tersendiri) |
| 6 | Transformasi: `mart_aggregated` (join ke `ml_output`) | Log run `transform-mart-aggregated.yml`; `renew_expiration.py mart_aggregated mart_aggregated_staging` terkonfirmasi terjadwal (diverifikasi langsung lewat `grep` ke workflow file, baris 114) + **`pipeline_run_log`** (M6.2, `granularity='detailed'`, step-level) | Sama seperti titik 3 — hasil per-test gate `promote.py` tidak queryable (M6.2 cuma nambah sinyal pass/fail kasar, lihat titik 7). | Titik 2 (`workflow_run` "Transform Staging and Mart Cleaned") + titik 5 (best-effort, `continue-on-error`, tidak blocking — Keputusan M5.4) | **Tinggi** |
| 7 | Pengujian data: validasi `mart_aggregated` | Gate `scripts/mart_aggregated/promote.py` (244 dbt test + 1 singular test `assert_gop_no_double_counting.sql`) — terbukti bekerja lewat fault-injection nyata (M5.3: filter `department` sengaja dihapus dari `fact_financial_overall_monthly`, 180 baris FAIL, swap dibatalkan). **M6.2**: `pipeline_run_log` sekarang punya sinyal pass/fail kasar (`granularity='coarse'`, step sama dengan titik 6), terbukti otomatis via trigger nyata. | ❌ Sama seperti titik 3 (per-test detail tidak queryable — M6.2 cuma nambah sinyal kasar, gap ini TETAP prasyarat M6.3). **Plus kelas gap berbeda**: aturan wajib "`property_id` di seluruh tabel" (M5.2 KK#2) dilanggar `dim_employee` selama 2 milestone (M5.2, M5.3) tanpa terdeteksi gate — DQ test tidak bisa menangkap "kolom hilang", cuma "nilai salah" (baru ketahuan konsumen M3.2, ditutup M5.7). | Titik 6 | **Tinggi** |
| 8 | Reverse ETL: `mart_aggregated` → PostgreSQL | `monitoring.reverse_etl_sync_log` (`dataset_name='mart_aggregated'`, `status` CHECK synced/mismatch_aborted), `scripts/reverse_etl_mart_aggregated/reindex_analyze.py` pasca-swap + **`pipeline_run_log`** (M6.2, `granularity='detailed'`, run-level) | Cakupan cuma **76/77 tabel** — `fact_ml_occupancy_forecast_property_room_type` (provisional, M5.4) sengaja dikecualikan (keputusan sadar M5.5, bukan gap). ⚠️ **WARNING "expected" berulang** (M5.7: swap RENAME-based crash-turned-warning karena `analyst_views` M3.2 terikat OID ke tabel lama) akan muncul di hampir tiap run terjadwal untuk sebagian besar dari 76 tabel — perlu dibedakan dari alert kegagalan sungguhan di M6.2/6.7. **Dikonfirmasi ulang saat verifikasi M6.2 (2026-08-10)**: 1 run nyata gagal `psycopg2.errors.DuplicateTable: relation "dim_property__old" already exists` — bukan sekadar WARNING lagi, kali ini job-nya sendiri gagal (`titik_id=8` tercatat `status='failure'` di `pipeline_run_log`), mengonfirmasi risiko orphan-table M5.7 nyata terjadi, bukan cuma hipotetis. | Titik 6 (`workflow_run` "Transform Mart Aggregated") | **Tinggi** |
| 9 | Reverse ETL: `mart_cleaned` → PostgreSQL | `monitoring.reverse_etl_sync_log` (`dataset_name='mart_cleaned'`), `scripts/reverse_etl/reindex_analyze.py` pasca-swap + **`pipeline_run_log`** (M6.2, `granularity='detailed'`, run-level) | Tidak ada gap sinyal — zero-downtime swap paling teruji di seluruh project (M2.4: 274 query konkuren, 0 error; M5.5 pola sama untuk `mart_aggregated`: 250 query konkuren, 0 error). **Catatan operasional dari verifikasi M6.2 (2026-08-10)**: 1 run nyata gagal `psycopg2.errors.DuplicateTable: relation "employees__old" already exists` (`titik_id=9` tercatat `status='failure'`) — orphan table sama seperti pola M5.7, kali ini di schema `mart_cleaned`, bukan `mart_aggregated`. `pipeline_run_log` terbukti menangkap kegagalan nyata ini otomatis (bukti KK1/KK2 M6.2), bukan cuma skenario success. | Titik 2 (`workflow_run` "Transform Staging and Mart Cleaned", paralel dengan titik 4 & 6) | **Tinggi** |
| 10 | Post-sync validation (row count parity check) | **Identik dengan titik 8/9** — kolom `status` di `reverse_etl_sync_log` ADALAH hasil parity check, built-in sebelum swap (gate di `sync.py`), bukan langkah terpisah | Tidak ada — 0 mismatch di 70+ baris log historis gabungan M2.4+M5.5 | Titik 8 & 9 (mekanisme yang sama) | **Tinggi** (risiko rendah — mekanisme paling terbukti di seluruh pipeline) |

---

## Klasifikasi Prioritas (Ringkasan)

- **Kritis** (blast-radius tertinggi, tidak digate dari upstream): **Titik 2** — satu-satunya akar fan-out ke 3 cabang paralel sekaligus (titik 3/9, titik 4, titik 6), dan dependency-nya sendiri ke titik 1 tidak ditegakkan (lihat "Catatan Penting" #2 dan `docs/keputusan-tertunda.md`).
- **Tinggi** (gerbang penting, sebagian besar sudah punya sinyal solid): Titik 1, 3, 6, 7, 8, 9, 10.
- **Sedang** (terbukti isolated-by-design lewat fault-injection nyata M5.4, kegagalannya tidak menjatuhkan pipeline utama): Titik 4, 5.

Dasar klasifikasi ini menjawab langsung Kriteria Keberhasilan #2 Milestone 6.1 — begitu Milestone 6.7 menyusun alerting, kegagalan di titik Kritis (titik 2) semestinya menghasilkan **satu** alert akar yang menjelaskan seluruh downstream terdampak, bukan alert terpisah dari tiap titik 3/4/6/7/8/9/10 yang ikut gagal sebagai akibatnya.

---

## Titik 11 (Out of Scope) — Konsumsi Data Analyst / AI Chatbot

Tidak termasuk peta 10 titik inti (lihat "Catatan Penting" #1), dicatat sebagai referensi:

| Konsumen | Sumber Sinyal | Gap |
|---|---|---|
| AI Chatbot | `monitoring.chatbot_query_log` (M4.5) — `role_title`, `domain`, `view_name`, `employee_id`, `access_scope`, `resolved_property_id`, `status`, `denial_reason`, `row_count`, `requested_at` | ❌ **Tidak ada kolom latency/durasi** — untuk performa query (fokus M6.5), perlu join terpisah ke `pg_stat_statements`. Juga best-effort (bukan guaranteed delivery) — baris bisa hilang kalau proses API mati di antara response terkirim dan background task selesai menulis log (M4.5). |
| Data Analyst | Tidak ada | ❌ API Data Analyst (M3.4, internal-only, tidak pernah dideploy) **tidak punya audit log sama sekali** — asimetri dengan AI Chatbot yang sudah punya `chatbot_query_log` sejak M4.5. |

---

## Cross-check terhadap Kriteria Keberhasilan Milestone 6.1

- ✅ **Setiap 10 titik pengamatan punya sumber sinyal yang jelas dan bisa dirujuk langsung Milestone 6.2 tanpa re-eksplorasi.** — 8/10 titik (1,2,4,6,8,9,10, dan titik 5 dengan catatan fokus M6.3) punya sinyal existing yang bisa langsung dipakai; titik 3 dan 7 gap-nya dicatat eksplisit dengan rujukan langsung ke prasyarat Milestone 6.3 (`docs/keputusan-tertunda.md`) — bukan sekadar "belum ada", tapi jelas siapa yang perlu menutupnya dan kenapa.
- ✅ **Dependency antar titik terdokumentasi sehingga satu kegagalan akar tidak memicu banjir alert.** — Kolom Dependency tiap titik merujuk mekanisme YAML nyata (`workflow_run` vs buffer waktu), fan-out 3-cabang-paralel dari titik 2 didokumentasikan eksplisit, klasifikasi prioritas 3 level memberi dasar konkret untuk desain dedup alert Milestone 6.7.

Detail keputusan & metode di balik peta ini ada di `milestones/6.1-inventarisasi-titik-pengamatan/decisions.md`. Jurnal eksplorasi 7 layer ada di `milestones/6.1-inventarisasi-titik-pengamatan/logs.md`.
