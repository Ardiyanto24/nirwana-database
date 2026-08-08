# Milestone 2.2: Layer Staging — Cleaning per Tabel (Fase 2) — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Untuk tabel dengan aturan normalisasi, hasil staging menunjukkan nilai yang sudah dinormalisasi.** — Terpenuhi.
  - `employees.department`: 19 nilai mentah → **tepat 8** nilai baku (`Corporate`, `F&B`, `Facility`, `Finance`, `Housekeeping`, `HR`, `Revenue`, `Spa&Event`), diverifikasi `COUNT(DISTINCT department)` + dbt test `accepted_values`.
  - `employees.hire_date`: dari kolom `text` campuran ISO/`DD/MM/YYYY` → kolom `DATE` asli, diverifikasi `bq show --schema`.
  - `employees.full_name`: whitespace ter-trim.
  - `guests.phone`: 4 variasi format domestik → 1 format standar (`0xxxxxxxxxx`), nomor asing tidak tersentuh — diverifikasi sampling manual sebelum/sesudah.
  - `guests.nationality`: 466 nilai distinct → 243 (case/whitespace ternormalisasi via `INITCAP(TRIM())`).
- [x] **Untuk kolom/baris yang harus dipertahankan apa adanya, hasil staging identik dengan raw.** — Terpenuhi. Seluruh 11 pola missing-value-bermakna dan dirty-data-disengaja (daftar lengkap di `warehouse/README.md`) diverifikasi identik raw: `role_title` null=15, `guests.email`/`phone` null=989/750, 367 baris duplikat `guests` tidak di-dedup, `guest_id` null di `fnb_transactions`(31%)/`spa_bookings`(21%), `maintenance_tickets.room_id`/`parts_replaced`/`resolved_date`, `staff_shifts.clock_in`/`clock_out`, `properties.star_rating` (P06).
- [x] **Tidak ada kolom turunan/fitur hasil kalkulasi yang muncul di layer ini.** — Terpenuhi. Seluruh 23 model staging hanya berisi kolom yang ada di `raw_production` (plus `_synced_at` yang sudah ada sejak M2.1) — tidak ada kolom baru hasil kalkulasi/agregasi/feature engineering.

## Row Count Parity (23/23 tabel)

Divalidasi ulang dari nol (bukan trust hasil M2.1): seluruh 23 tabel `staging.stg_<schema>__<table>` punya row count **identik** dengan `raw_production` yang sesuai — termasuk tabel dengan cleaning (`employees` 755, `guests` 24.893) maupun passthrough murni.

## Deliverables

- `warehouse/` — project dbt-core baru (`dbt_project.yml`, `profiles.yml.example`, `seeds/department_mapping.csv`, 23 model SQL di `models/staging/`, `_sources.yml`, `_staging_tests.yml`, `README.md`).
- Dataset `staging` di BigQuery (`nirwana-database-elt`), 23 view.
- Service account baru `dbt-transform` (project-level `bigquery.dataEditor`+`jobUser`, terpisah dari `extract-writer`).
- 31 dbt test (`unique`/`not_null` untuk 15 tabel ber-PK tunggal, `accepted_values` untuk `department`) — seluruhnya PASS.
- `milestones/2.2-layer-staging-cleaning-per-tabel/{decisions,logs,data-profiling-findings}.md`.

## Deviations from decisions.md

- **Mapping `department` ternyata lebih sederhana dari dugaan awal** — breakdown awal (berdasar profiling) mengasumsikan sebagian dari 19 variasi bukan cuma beda kapitalisasi (butuh mapping non-mekanis). Query langsung ke data mentah saat Task 3 membuktikan seluruh 19 variasi murni kapitalisasi/whitespace — mapping tetap dibuat eksplisit (bukan `INITCAP()` mekanis, karena "F&B"/"HR" butuh casing khusus) tapi lebih sederhana dari yang direncanakan.
- **Service account `dbt-transform` tidak direncanakan di breakdown awal** — ditemukan saat implementasi (Task 1) bahwa `extract-writer` M2.1 tidak cukup karena scope dataset-nya sengaja dibatasi. Ditangani segera, didokumentasikan sebagai Technical Decision baru.
- Bug `+schema` dbt (dataset `staging_staging` salah) dan bug CTE-naming BigQuery (STRUCT bukan kolom) ditemukan & diperbaiki saat implementasi — tidak direncanakan di breakdown, konsisten pola project ini ("temuan saat implementasi dicatat & diperbaiki, bukan disembunyikan").
- Tidak ada deviasi lain dari 13 task yang direncanakan.

## Known Gaps / Follow-ups

- **dbt test Task 12 bukan gerbang data quality penuh** — hanya bukti awal (`unique`/`not_null`/`accepted_values` terbatas). Gerbang penuh (`relationships`, custom business rule, seluruh 23 tabel) adalah tanggung jawab eksplisit Milestone 2.3.
- **8 tabel tanpa PK tunggal** (`role_permissions`, `daily_occupancy`, `pricing_history`, `recipe_bom`, `ingredient_price_history`, `fnb_inventory`, `financial_summary` — composite key; `fnb_transactions` — tanpa PK sama sekali) tidak punya test `unique` di M2.2 — perlu pendekatan berbeda (composite key test atau terima non-unique) di M2.3.
- **Materialisasi view berarti setiap query staging = query live ke `raw_production`** — cukup untuk volume 23 tabel ini sekarang, tapi kalau `mart_cleaned` (M2.3) atau konsumsi downstream lain butuh performa lebih, perlu revisit ke materialized table (dengan strategi partitioning yang aman Sandbox mode, bukan mengulang insiden M2.1).
- **`nationality` masih py 243 nilai distinct** (dari 466) — sisa variasi (kemungkinan typo/singkatan/bahasa campuran) sengaja tidak dibersihkan lebih lanjut sesuai keputusan scope M2.2.

## Handoff Notes

- **Untuk Milestone 2.3**: `staging.*` (23 view) siap dikonsumsi untuk layer intermediate + `mart_cleaned` final + data quality gate penuh. dbt project sudah ada di `warehouse/` — tinggal tambah `models/intermediate/` dan `models/marts/` di project yang sama, jangan bikin project dbt baru.
- **Kredensial `dbt-transform`**: key file `scripts/extract/gcp-dbt-transform-key.json` (gitignored). Kalau perlu dataset baru (`intermediate`, `mart_cleaned` di M2.3), service account ini sudah punya `bigquery.dataEditor` project-level, tidak perlu request izin baru.
- **Department mapping**: `warehouse/seeds/department_mapping.csv` adalah sumber kebenaran untuk normalisasi department — kalau ada departemen baru muncul di production nanti, tambah baris di seed ini, jangan hardcode di SQL model.
- **Kolom yang sengaja tidak dibersihkan**: rujuk `warehouse/README.md` sebelum mengubah model staging manapun — beberapa null/duplikat/typo di sana **wajib** tetap ada, bukan bug.
