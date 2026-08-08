# Milestone 5.3: Implementasi Transformasi Mart Aggregated — Decisions

**Source:** `docs/03-implementation-plans/03-mart-aggregated-owner.md`, baris 84-101.
**Status:** In Progress
**Date started:** 2026-08-08

## Contract (from source doc)

- **Lingkup:** Membangun transformasi SQL dari `mart_cleaned` ke `mart_aggregated` sesuai skema Milestone 5.2 — business logic penuh (agregasi, kalkulasi metrik, join lintas domain), dan data quality gate (data yang tidak lolos pengujian tidak diteruskan ke mart).
- **Output:**
  1. Transformasi SQL berjalan untuk seluruh tabel `mart_aggregated` sesuai skema.
  2. Pengujian data quality (business rule spesifik) terpasang sebagai bagian dari transformasi.
- **Kriteria Keberhasilan:**
  1. Seluruh tabel `mart_aggregated` terisi dan dapat diquery di BigQuery, hasil tervalidasi cocok terhadap perhitungan manual/sampel dari `mart_cleaned` untuk beberapa metrik kunci.
  2. Data quality gate berhasil menangkap pelanggaran business rule pada uji coba terkontrol.
  3. Kolom yang sudah diputuskan untuk di-mask/dianonimkan pada Milestone 5.2 terbukti benar-benar termask di hasil akhir — bukan diteruskan apa adanya karena terlewat saat implementasi.

## Input Utama

`docs/07-mart-aggregated/DataSchema-mart-aggregated.md` (Milestone 5.2, Completed) — 27 dimension table + 45 fact table (star schema), termasuk 2 fact table kasus khusus dan Audit PII (kesimpulan: tidak ada kolom `guests_pii` mentah di skema manapun).

## Temuan Eksplorasi

- `scripts/mart_cleaned/promote.py`, `warehouse/dbt_project.yml`, `warehouse/macros/generate_schema_name.sql`: pola build→test→swap sudah terbukti jalan untuk `mart_cleaned` — dbt selalu menulis ke dataset staging (`+schema` literal, tidak digabung dengan target schema berkat override `generate_schema_name`), promote hanya lewat `CREATE OR REPLACE TABLE ... AS SELECT` per tabel kalau seluruh `dbt test` lolos.
- Materialization `table` (bukan `incremental`) — BigQuery Sandbox mode blokir semua DML, jadi seluruh strategi incremental dbt tidak bisa jalan; pola ini diwariskan penuh ke `mart_aggregated`.
- `warehouse/models/mart_cleaned/_mart_cleaned_tests.yml`: pola test `unique`/`not_null`/`relationships`/`accepted_values`. Nilai riil `employees.department` (8 departemen): `['Corporate','F&B','Facility','Finance','Housekeeping','HR','Revenue','Spa&Event']` — dipakai sebagai referensi nilai `dim_department`.
- Folder `staging`/`mart_cleaned` mengikuti skema produksi (`corporate_master`, `reservation_revenue`, `fnb_operations`, `facility_maintenance`, `spa_event`, `hr_finance`), bukan domain bisnis M5.1/M5.2.
- `docs/01-architecture/DataSchema.md`/`Metadata.md`: gaya dokumentasi produksi — `DataSchema.md` = struktur tabel per skema (kolom, PK/FK), `Metadata.md` = konteks bisnis + relasi antar tabel + definisi/cara hitung per kolom + peringatan data quality.

## Keputusan (via AskUserQuestion + diskusi, 2 putaran)

### 1. `fact_revenue_pace_booking_snapshot`: self-union `CREATE OR REPLACE`, full history (tanpa retention window)

**Keputusan:** Tiap run, tabel dibangun ulang penuh: `CREATE OR REPLACE TABLE x AS SELECT * FROM x UNION ALL SELECT <snapshot hari ini>` — murni DDL (CTAS), kompatibel Sandbox mode, efeknya seperti append. **Tanpa klausa pruning/retention** — histori disimpan penuh.

**Kenapa:** Draf awal mengusulkan retention 90 hari untuk membatasi biaya rebuild — setelah dihitung ulang, skala data pace booking (5 properti × ~10 tipe kamar × 1 snapshot/hari × ~14 hari lookahead) cuma ~766.000 baris setelah 3 tahun, negligible untuk BigQuery. User menegaskan Data Analyst butuh rentang tahunan dan AI Chatbot butuh seluruh tanggal sejak awal dataset — retention window bertentangan dengan itu tanpa manfaat nyata di skala ini.

**Ditolak:** Retention window 90 hari; menunda implementasi ke sesi terpisah.

### 2. Struktur folder dbt: hybrid — skema produksi untuk 5 folder yang align, `hr_finance/` dipecah 2 subfolder

**Keputusan:** `warehouse/models/mart_aggregated/{corporate_master,reservation_revenue,fnb_operations,facility_maintenance,spa_event,hr_finance/{hr,corporate_financial}}/`.

**Kenapa:** Hanya `hr_finance` bermasalah kalau murni ikut skema produksi (mencampur fact table HR dan Corporate/Financial — 2 domain bisnis berbeda, termasuk disambiguasi `dim_department` vs `dim_business_line` M5.2). 5 folder lain align 1:1 dengan domain bisnis M5.2. Hybrid menjaga konsistensi lineage `ref()` dengan `staging`/`mart_cleaned` di 5/6 folder, sekaligus mempertahankan pemisahan HR vs Corporate/Financial.

**Ditolak:** Murni per domain bisnis M5.2 (menyimpang konvensi di semua 6 folder); murni per skema produksi tanpa pemecahan (mencampur HR+Corporate/Financial).

## Keputusan Teknis Lain (dikunci tanpa AskUserQuestion — mengikuti preseden project)

### 3. `scripts/mart_aggregated/promote.py` — file baru, copy pola `scripts/mart_cleaned/promote.py`

Konsisten preseden "copied rather than imported across `scripts/*` subfolders". `STAGING_DATASET`/`TARGET_DATASET` diganti `mart_aggregated_staging`/`mart_aggregated`.

### 4. Dataset config `dbt_project.yml`: blok `mart_aggregated` persis pola `mart_cleaned`

`+schema: mart_aggregated_staging`, `+materialized: table`, komentar constraint Sandbox mode diwariskan.

### 5. DQ gate: dbt test (schema + singular), bukan Great Expectations

Great Expectations adalah scope Fase 2 Monitoring (belum dikerjakan). Pola gate M5.3: dbt `not_null`/`unique`/`relationships`/`accepted_values`, plus 1 singular test kunci — rekomputasi GOP dari `mart_cleaned__financial_summary` (filter `department='Overall'` murni) dibandingkan ke `fact_financial_overall_monthly`.

### 6. Validasi KK#1: 1 metrik representatif per domain (6 total), manual via query SQL, dicatat di `logs.md`

Tidak perlu script Python reusable terpisah — skala kerja lebih ringan dari kredensial/isolasi.

## Keputusan Tambahan (permintaan user, revisi plan setelah draf pertama ditolak untuk didiskusikan)

### 7. `desain-skema-mart-aggregated.md` di-rename jadi `DataSchema-mart-aggregated.md`

Isi tetap sama, cuma nama disesuaikan pola `docs/01-architecture/DataSchema.md` produksi — dokumen ini sejak M5.2 Keputusan #10 sudah berperan sama seperti `DataSchema.md`. Seluruh referensi nama lama diperbarui.

### 8. `Metadata-mart-aggregated.md` baru — data dictionary penuh, ditulis di Fase 8 (setelah implementasi)

Menuntaskan keputusan tertunda M5.2 (`docs/keputusan-tertunda.md`). Cara hitung, unit, contoh nilai aktual per kolom, gaya `docs/01-architecture/Metadata.md`.

### 9. Diagram Mermaid ERD — 1 diagram tunggal, seluruh 72 tabel

Permintaan eksplisit user (opsi split per domain ditawarkan untuk keterbacaan, ditolak). Risiko: diagram padat, butuh scroll/zoom signifikan saat dirender — dieksekusi apa adanya sesuai preferensi user.

## Task Breakdown

10 fase, 10 checkpoint (commit + log tiap checkpoint).

### Fase 0 — Setup + 27 Dimension Table
1. Tambah blok `mart_aggregated` di `dbt_project.yml`; scaffold folder hybrid; implementasi 27 model dimension table + `_tests.yml` — Acceptance: 27/27 dimension table ter-build — Verify: `dbt run --select mart_aggregated,tag:dimension` — M

**Checkpoint 1**

### Fase 1 — Fact Table Revenue
2. Implementasi 5 fact table Revenue + `fact_revenue_pace_booking_snapshot` — S

**Checkpoint 2**

### Fase 2 — Fact Table F&B
3. Implementasi 8 fact table F&B, termasuk `capture_rate` cross-domain — M

**Checkpoint 3**

### Fase 3 — Fact Table Facility/Ops
4. Implementasi 9 fact table Facility/Ops, termasuk `delayed_rate_vs_occupancy` cross-domain, SLA mentah — M

**Checkpoint 4**

### Fase 4 — Fact Table Spa & Event
5. Implementasi 6 fact table Spa & Event — S

**Checkpoint 5**

### Fase 5 — Fact Table HR
6. Implementasi 6 fact table HR + `fact_hr_watchlist_monthly` — S

**Checkpoint 6**

### Fase 6 — Fact Table Corporate/Financial
7. Implementasi 9 fact table Corporate/Financial, termasuk `service_charge_pool` cross-domain — M

**Checkpoint 7**

### Fase 7 — DQ Gate + Validasi
8. Singular test GOP-Overall + uji coba terkontrol — S
9. `scripts/mart_aggregated/promote.py` + jalankan build→test→swap — S
10. Validasi manual 6 metrik representatif + re-verifikasi Audit PII — S

**Checkpoint 8**

### Fase 8 — Dokumentasi Pendamping
11. Rename `DataSchema-mart-aggregated.md` → `DataSchema-mart-aggregated.md` + update referensi — XS
12. Tulis `Metadata-mart-aggregated.md` — M
13. Tulis `ERD-mart-aggregated.md` (1 Mermaid `erDiagram`, 72 tabel) — M

**Checkpoint 9**

### Fase 9 — Finalisasi
14. Verifikasi 3 KK sumber + tulis `report.md` — S

**Checkpoint 10 (final)**
