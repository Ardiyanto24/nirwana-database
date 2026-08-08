# Milestone 2.3: Layer Intermediate dan Mart Cleaned (Fase 2) — Report

**Status:** Partially Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Seluruh 23 tabel `mart_cleaned` tersedia dan dapat diquery di BigQuery.** — Terpenuhi. Semua 23 tabel `mart_cleaned.<nama_tabel>` ada di BigQuery, row count diverifikasi identik dengan `staging` (23/23 cocok, termasuk tabel terbesar `fnb_transactions` 902.574 dan `staff_shifts` 610.019 baris).
- [x] **Pengujian data quality berjalan, hasil (lolos/gagal) tercatat & bisa ditelusuri.** — Terpenuhi. 36 dbt test (`unique`/`not_null` untuk 15 tabel ber-PK tunggal, 2 `relationships` foreign key ke `properties`, 1 `accepted_values` untuk `department`, 3 custom business rule) — seluruhnya PASS, hasil tercatat di output `dbt test` (dapat dijalankan ulang & ditelusuri kapan saja via `dbt test --select mart_cleaned`).
- [x] **Percobaan memasukkan data melanggar business rule berhasil ditangkap gate, tidak diteruskan ke mart.** — Terpenuhi, diverifikasi dengan pelanggaran business rule **sungguhan** (bukan test buatan): 1 baris `total_amount=-500000` disuntik sementara ke `mart_cleaned__bookings`, test `assert_bookings_total_amount_non_negative` FAIL, `scripts/mart_cleaned/promote.py` berhenti sebelum swap. Dicek langsung: `mart_cleaned` (tabel sungguhan, bukan staging) tetap 217.654 baris, `MIN(total_amount)` tetap positif, `COUNTIF(booking_id='BK_SIMULATION_BAD_ROW')=0` — baris palsu **tidak pernah** terlihat di `mart_cleaned`.
- [~] **Refresh pada hari dengan sedikit perubahan data terbukti lebih murah/cepat dibanding full refresh.** — **TIDAK TERPENUHI.** Ditemukan selama implementasi: BigQuery Sandbox mode (belum ada billing) memblokir **seluruh** operasi DML (`MERGE`/`INSERT`/`UPDATE`/`DELETE`), bukan cuma soal partitioning seperti insiden M2.1 — berarti *tidak ada* strategi incremental dbt (`merge` maupun `append`) yang bisa dijalankan sama sekali tanpa billing. `mart_cleaned` dibangun sebagai full refresh murni (`CREATE OR REPLACE TABLE`, DDL) untuk seluruh 23 tabel. Logic `is_incremental()` tetap ada di kode (dormant), siap diaktifkan begitu billing aktif.

## Row Count Parity (23/23 tabel)

Seluruh 23 tabel `mart_cleaned.<nama_tabel>` identik row count dengan `staging.stg_<schema>__<tabel>` — divalidasi 2x (setelah build awal & setelah uji coba terkontrol Task 13, untuk memastikan proses uji coba tidak meninggalkan sisa apa pun).

## Deliverables

- 23 tabel `mart_cleaned.<nama_tabel>` di BigQuery — full refresh (`table`), passthrough 1:1 dari staging sesuai `pemetaan-kebutuhan-konsumen-data-mart.md`.
- Dataset `mart_cleaned_staging` — tempat dbt selalu membangun dulu sebelum digerbang (gate); `mart_cleaned` tidak pernah ditulis dbt secara langsung.
- `scripts/mart_cleaned/promote.py` — mekanisme build→test→swap, service account terpisah `dbt-transform` (env var `DBT_TRANSFORM_CREDENTIALS`).
- `warehouse/macros/generate_schema_name.sql` — override untuk custom `+schema` literal (mencegah bug penggabungan dataset seperti M2.2).
- `scripts/extract/renew_expiration.py` diperluas jangkauannya (dipakai manual untuk `staging`/`mart_cleaned`/`mart_cleaned_staging`, meski baru terjadwal otomatis untuk `raw_production` — lihat Known Gaps).
- 36 dbt test (`_mart_cleaned_tests.yml` + 3 file `tests/assert_*.sql`).
- Entri baru `docs/keputusan-tertunda.md` ("Aktivasi billing GCP...") mendokumentasikan gap project-wide.
- `milestones/2.3-layer-intermediate-mart-cleaned/{decisions,logs}.md`.

## Deviations from decisions.md

- **Keputusan awal (watermark `is_incremental()` + strategi `merge`) tidak jadi diimplementasikan** — ditemukan blocker DML total di Sandbox mode saat Task 5, bukan cuma soal partitioning yang sudah diantisipasi. Didokumentasikan sebagai Decision baru ("DML diblokir total di Sandbox mode"), bukan penghapusan keputusan lama — rencana `is_incremental()` tetap berlaku untuk nanti.
- **Task 13 tidak pakai schema `_simulation`** seperti direncanakan (pola Fase 1) — DML/INSERT diblokir, jadi injeksi baris uji coba dilakukan lewat `UNION ALL` sementara langsung di SQL model, dihapus setelah diverifikasi.
- Bug teknis ditemukan & diperbaiki saat implementasi (dicatat untuk transparansi, bukan deviasi keputusan): `ref()` staging ikut resolve ke dataset target aktif saat sempat dicoba multi-target dbt (diperbaiki dengan `macros/generate_schema_name.sql` + `+schema` eksplisit); `promote.py` awalnya pakai kredensial salah (`extract-writer` alih-alih `dbt-transform`); duplikasi definisi `mart_cleaned__bookings` di 2 file yml.

## Known Gaps / Follow-ups

- **Kriteria Keberhasilan #4 (incremental lebih murah dari full refresh) tidak terpenuhi** — gap utama, berakar dari constraint billing yang sama dengan gap "full history" M2.1/M2.2. **Wajib direvisit begitu billing GCP aktif**: ubah `+materialized: table` → `incremental` di `dbt_project.yml`, tidak perlu menulis ulang SQL model (logic `is_incremental()` sudah ada, dormant).
- **Renewal `expirationTime` belum terjadwal otomatis untuk `staging`/`mart_cleaned`/`mart_cleaned_staging`** — cuma `raw_production` yang sudah masuk `extract-production.yml`. Untuk saat ini dijalankan manual. Perlu workflow terjadwal baru (`mart-cleaned-refresh.yml`?) yang menjalankan `promote.py` + `renew_expiration.py` untuk ketiga dataset ini, supaya konsisten dengan mitigasi M2.1/M2.3 — **prioritas tinggi**, karena tanpa ini `mart_cleaned` akan expired ~2026-10-02 tanpa peringatan.
- **`promote.py --select <model>` mempromosikan SEMUA tabel di `mart_cleaned_staging`**, bukan cuma yang di-select saat itu (karena langkah promosi list semua tabel di dataset, bukan filter berdasar model yang baru dibangun). Tidak menyebabkan masalah korektnes (tabel lain memang sudah benar), tapi tidak efisien untuk selektif re-promote 1 tabel saja — perlu diperbaiki kalau nanti dipakai lebih sering untuk debugging per-tabel.
- **Data quality test (Task 12) tidak menutupi 8 tabel tanpa PK tunggal** (composite key/tanpa PK) dengan `unique` test — sama seperti gap M2.2, perlu pendekatan custom (composite uniqueness test) kalau mau menutup gap ini nanti.

## Handoff Notes

- **Untuk Milestone 2.4 (Reverse ETL)**: `mart_cleaned` siap dikonsumsi — 23 tabel, full history (untuk saat ini — lihat gap billing), gate DQ sudah terbukti bekerja.
- **Kalau billing GCP diaktifkan**: (1) hapus `defaultTableExpirationMs`/`defaultPartitionExpirationMs` di semua dataset, (2) reset `expirationTime` tabel existing, (3) ubah `+materialized: table` → `incremental` di `warehouse/dbt_project.yml` (blok `mart_cleaned`), (4) hapus langkah `renew_expiration.py` dari workflow terjadwal.
- **Rerun manual**: `python scripts/mart_cleaned/promote.py --select mart_cleaned` (build+test+swap seluruh 23 tabel) — set `DBT_BIN` env var kalau `dbt` tidak ada di PATH (masalah umum di Windows, lihat `scripts/extract/gcp-dbt-transform-key.json` setup).
- **Peringatan**: jangan jalankan `dbt run` langsung ke `mart_cleaned` (dataset asli) — semua model `mart_cleaned/` sengaja di-hardcode `+schema: mart_cleaned_staging`, satu-satunya jalan resmi ke `mart_cleaned` adalah lewat `promote.py` setelah test lolos.
