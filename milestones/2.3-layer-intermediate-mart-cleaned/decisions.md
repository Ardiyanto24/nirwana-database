# Milestone 2.3: Layer Intermediate dan Mart Cleaned (Fase 2)

**Source:** `docs/03-implementation-plans/02-serving-data-scientist.md` (baris 104-121, "Milestone 2.3 — Layer Intermediate dan Mart Cleaned")
**Status:** In Progress
**Date started:** 2026-08-08

## Contract (from source doc)

- **Lingkup:** Membangun layer intermediate (jika ada kebutuhan join struktural antar staging) dan menyelesaikan `mart_cleaned` — 23 tabel `mart_cleaned.<nama_tabel>` siap konsumsi, beserta data quality gate (`not_null`, `unique`, `relationships`, `accepted_values`, custom business rule) sebagai gerbang sebelum data diteruskan. `mart_cleaned` dibangun sebagai tabel dengan refresh **incremental** (overwrite per partition), bukan full refresh.
- **Output:** 23 tabel `mart_cleaned` lengkap, full history, refresh incremental; rangkaian pengujian data quality terpasang.
- **Kriteria keberhasilan:**
  1. Seluruh 23 tabel `mart_cleaned` tersedia dan dapat diquery.
  2. Pengujian data quality berjalan, hasil (lolos/gagal) tercatat & bisa ditelusuri.
  3. Percobaan memasukkan data melanggar business rule berhasil ditangkap gate, tidak diteruskan ke mart.
  4. Refresh pada hari dengan sedikit perubahan data terbukti lebih murah/cepat dibanding full refresh.

## Konteks Kritis: Temuan Sebelum Breakdown

Riset ke dokumentasi resmi GCP (2 `WebFetch`) sebelum breakdown task mengungkap batasan BigQuery Sandbox mode (project `nirwana-database-elt`, masih tanpa billing) jauh lebih keras dari yang diketahui saat insiden M2.1:

> *"all tables, views, and partitions automatically expire after 60 days"* — hard limit sandbox-wide, **tidak bisa di-override per-tabel**.

Ini bukan cuma soal partition (M2.1) — tabel `raw_production` yang unpartitioned pun akan terhapus **seluruhnya** ~60 hari sejak dibuat. Kontradiksi langsung dengan syarat "full history" M2.3. Keputusan billing diajukan ke user (`AskUserQuestion`) — dijawab: **belum bisa diaktifkan** (kendala kartu kredit saat ini, akan diaktifkan di masa depan).

## Task Breakdown

14 task, 4 fase. **Commit + push + log progres di tiap checkpoint** (bukan cuma di akhir milestone).

### Fase 1 — Fondasi
- [ ] Task 1: Tambah langkah perpanjang `expirationTime` (`bq update --expiration`) ke `extract-production.yml` — Acceptance: expirationTime tabel maju tiap job jalan — Verify: `bq show` sebelum/sesudah
- [ ] Task 2: Konfirmasi & dokumentasikan tidak perlu layer intermediate — Acceptance: keputusan sadar tercatat — Verify: review manual
- [ ] Task 3: Setup dataset `mart_cleaned` + `mart_cleaned_staging` — Acceptance: kedua dataset ada — Verify: `bq ls`

**Checkpoint 1** — commit + push, log Task 1-3.

### Fase 2 — Mekanisme Gate + Model Percobaan
- [ ] Task 4: Pola build→test→swap (script Python: `dbt run --target staging` → `dbt test` → swap hanya kalau lolos) — Acceptance: model gagal-test tidak sampai `mart_cleaned` — Verify: uji coba terkontrol
- [ ] Task 5: Model `mart_cleaned` percobaan (`bookings`) — `incremental`, strategi `merge`, TANPA partitioning BigQuery — Acceptance: refresh kedua hanya proses baris baru — Verify: `dbt run` 2x + `bq show --schema` (tidak ada `timePartitioning`)

**Checkpoint 2** — commit + push, log Task 4-5.

### Fase 3 — 23 Model `mart_cleaned`
- [ ] Task 6: `corporate_master` (4 tabel)
- [ ] Task 7: `reservation_revenue` (3 tabel)
- [ ] Task 8: `fnb_operations` (6 tabel)

**Checkpoint 3** — commit + push, log Task 6-8 (13/23 tabel).

- [ ] Task 9: `facility_maintenance` (3 tabel)
- [ ] Task 10: `spa_event` (3 tabel)
- [ ] Task 11: `hr_finance` (4 tabel)

**Checkpoint 4** — commit + push, log Task 9-11 (23/23 tabel).

### Fase 4 — Data Quality Gate + Penutupan
- [ ] Task 12: dbt test lengkap (`not_null`/`unique`/`relationships`/`accepted_values` + ≥1 custom business rule) untuk 23 tabel
- [ ] Task 13: Uji coba terkontrol — suntik baris melanggar business rule (schema `_simulation`), buktikan gate menangkap

**Checkpoint 5** — commit + push, log Task 12-13.

- [ ] Task 14: Verifikasi Kriteria Keberhasilan + `report.md`

**Checkpoint 6 (final)** — commit + push, tutup milestone.

## Technical Decisions

### Decision: Billing GCP belum diaktifkan — `mart_cleaned` tanpa partitioning + mitigasi perpanjangan expirationTime

- **Context:** BigQuery Sandbox mode (tanpa billing) hard-limit 60 hari untuk SEMUA tabel/view/partition, tidak bisa dioverride per-tabel (dikonfirmasi dokumentasi resmi GCP). `mart_cleaned` butuh "full history" + refresh incremental "overwrite per partition" — kombinasi ini di Sandbox mode akan mengulang insiden M2.1 (partisi bertanggal lama otomatis terhapus) kalau dipartisi, atau kehilangan seluruh tabel dalam 60 hari kalau tidak.
- **Decision:** (1) `mart_cleaned` dibangun sebagai tabel `incremental` dbt dengan strategi `merge` (bukan `insert_overwrite`/partition-based) — TANPA time-partitioning BigQuery sama sekali, supaya tidak ada partisi yang bisa "expired" duluan. (2) Tambahkan langkah `bq update --expiration` (~55 hari dari saat itu) ke workflow terjadwal untuk memperpanjang `expirationTime` tabel tiap kali job jalan — mitigasi ringan dalam batas Sandbox mode (reset expirationTime individual boleh, asal tidak melebihi 60 hari dari saat itu; beda dari menghilangkan expirasi sama sekali yang ditolak GCP).
- **Konsekuensi eksplisit:** (a) Deviasi sadar dari Output literal M2.3 ("overwrite per partition") — didokumentasikan di sini, bukan kelalaian, rencana migrasi ke partition-based incremental begitu billing aktif. (b) "Full history" hanya terjamin selama job perpanjangan terus jalan — kalau berhenti (repo tidak aktif >55 hari), **seluruh Fase 2** (`raw_production`, `staging`, `mart_cleaned`) perlu di-rebuild dari Postgres dari nol. Ini gap **project-wide**, bukan cuma M2.3 — dicatat juga di `docs/keputusan-tertunda.md`.
- **Alternatives considered:** Aktifkan billing sekarang (ditolak — kendala kartu kredit user saat ini, bukan keputusan teknis); job drop+recreate berkala (ditolak — lebih berat & lebih berisiko daripada sekadar memperpanjang `expirationTime`).

### Decision: Data quality gate — build ke schema terpisah, test, baru swap

- **Context:** Kriteria Keberhasilan #3 eksplisit minta data yang melanggar business rule **tidak diteruskan** ke mart — dbt test standar (jalan setelah `dbt run`) tidak cukup karena data sudah sempat masuk tabel sebelum test dijalankan.
- **Decision:** Model dibangun dulu ke `mart_cleaned_staging`, `dbt test` dijalankan, swap/rename ke `mart_cleaned` HANYA kalau seluruh test lolos.
- **Alternatives considered:** dbt build+test biasa (pola sama M2.2), alert manual kalau gagal.
- **Rejected because:** tidak memenuhi kriteria keberhasilan sumber secara literal — data yang melanggar rule akan sempat terlihat di `mart_cleaned` sebelum ketahuan gagal.

### Decision: Watermark incremental — dbt native `is_incremental()`, bukan reuse cursor M2.1

- **Context:** Butuh cara mendeteksi baris baru/berubah per tabel untuk refresh incremental `mart_cleaned`. Tabel `monitoring.extract_cursor` (M2.1) sudah ada untuk kebutuhan serupa.
- **Decision:** `WHERE kolom_tanggal > (SELECT MAX(kolom_tanggal) FROM {{ this }})` (pola native dbt `is_incremental()`) per tabel berkolom tanggal bersih. Tabel tanpa kolom tanggal bersih (composite key/no-PK) pakai full-refresh, konsisten pola M2.1.
- **Alternatives considered:** Reuse `monitoring.extract_cursor`.
- **Rejected because:** tabel itu dirancang untuk sinkronisasi Postgres→BigQuery (butuh koneksi lintas sistem), bukan transformasi BigQuery→BigQuery — dbt native lebih sederhana untuk kasus ini, tanpa state tambahan yang perlu dikelola.

### Decision: Tidak perlu layer intermediate

- **Context:** M2.3 lingkup menyebut layer intermediate "kalau ada kebutuhan join struktural".
- **Decision:** Tidak dibangun — `docs/02-requirements/pemetaan-kebutuhan-konsumen-data-mart.md` eksplisit menetapkan `mart_cleaned` 1:1 dengan tabel sumber, "tidak digabung lintas domain, tidak dipecah ulang".
- **Alternatives considered:** N/A — keputusan desain sudah final di dokumen rujukan resmi, bukan pilihan bebas milik milestone ini.

## Open Questions Resolved with User

- Q: Billing GCP? → A: Belum bisa (kendala kartu kredit), akan diaktifkan di masa depan — jalan dulu tanpa billing dengan mitigasi.
- Q: Mekanisme data quality gate blocking? → A: Build ke schema terpisah → test → swap.
- Q: Watermark incremental? → A: dbt native `is_incremental()`, bukan reuse cursor M2.1.
