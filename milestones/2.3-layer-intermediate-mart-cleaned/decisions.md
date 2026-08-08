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
- [x] Task 1: Tambah langkah perpanjang `expirationTime` (`bq update --expiration`) ke `extract-production.yml` — Acceptance: expirationTime tabel maju tiap job jalan — Verify: `scripts/extract/renew_expiration.py`, diuji lokal (raw_production 23 + staging 24 berhasil) dan di CI sungguhan ([run 31239354131](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31239354131), sukses)
- [x] Task 2: Konfirmasi & dokumentasikan tidak perlu layer intermediate — Acceptance: keputusan sadar tercatat — Verify: lihat Technical Decision "Tidak perlu layer intermediate" di bawah
- [x] Task 3: Setup dataset `mart_cleaned` + `mart_cleaned_staging` — Acceptance: kedua dataset ada — Verify: `bq ls` menampilkan keduanya (region US)

**Checkpoint 1** — commit + push, log Task 1-3.

### Fase 2 — Mekanisme Gate + Model Percobaan
- [x] Task 4: Pola build→test→swap (`scripts/mart_cleaned/promote.py`: `dbt run` → `dbt test` → `CREATE OR REPLACE TABLE ... AS SELECT` per tabel HANYA kalau semua test lolos) — Acceptance: model gagal-test tidak sampai `mart_cleaned` — Verify: uji coba terkontrol 2 skenario — (1) data bersih: 3 test PASS, `mart_cleaned__bookings` ter-promote (217.654 baris cocok staging); (2) test sengaja gagal ditambahkan: dbt test FAIL, script berhenti sebelum promote, `mart_cleaned` **tetap 217.654 baris tidak berubah sama sekali** (dicek `COUNT(*)` sebelum & sesudah) — gate benar-benar blocking, bukan cuma laporan
- [x] Task 5: Model `mart_cleaned` percobaan (`bookings`) — **diubah dari rencana awal jadi `table` biasa (full refresh), bukan `incremental`** — lihat Technical Decision "DML diblokir total di Sandbox mode" — Acceptance (revisi): tabel berhasil dibangun 2x berturutan tanpa error DML — Verify: `dbt run` 2x sukses, `bq show --schema` konfirmasi tidak ada `timePartitioning`

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

### Decision: DML diblokir total di Sandbox mode — `mart_cleaned` full refresh murni, bukan incremental sama sekali

- **Context:** Percobaan Task 5 (model `mart_cleaned__bookings`, strategi `merge` dbt) full load pertama berhasil (DDL `CREATE TABLE`), tapi run kedua (yang seharusnya cuma proses delta lewat `MERGE`) gagal eksplisit: *"DML queries are not allowed in the free tier. Set up a billing account to remove this restriction."* Ini bukan cuma soal partitioning (masalah yang sudah diantisipasi di Decision di bawah) — **seluruh DML** (`MERGE`/`INSERT`/`UPDATE`/`DELETE`) diblokir BigQuery Sandbox mode, termasuk strategi `append` dbt (`INSERT INTO ... SELECT`) yang sebelumnya dikira jadi fallback aman.
- **Decision:** `mart_cleaned` dibangun sebagai **full refresh murni** (`CREATE OR REPLACE TABLE ... AS SELECT`, materialisasi `table` dbt biasa, bukan `incremental`) untuk seluruh 23 tabel — konsisten pola `WRITE_TRUNCATE` M2.1. Tidak ada refresh incremental sama sekali sampai billing aktif.
- **Konsekuensi eksplisit:** **Kriteria Keberhasilan #4 M2.3 ("refresh pada hari dengan sedikit perubahan data terbukti lebih murah/cepat dibanding full refresh") TIDAK TERPENUHI** — karena tidak ada mekanisme incremental sama sekali untuk dibandingkan. Ini gap tambahan di atas gap "full history" yang sudah dicatat di Decision berikutnya, sama-sama berakar dari constraint billing yang sama. Model percobaan `mart_cleaned__bookings.sql` (sudah ditulis dengan `is_incremental()`) diubah jadi model full-refresh biasa — logic incremental TIDAK dihapus dari histori (ada di git), tinggal diaktifkan kembali begitu billing aktif.
- **Alternatives considered:** Custom Python-driven upsert di luar dbt (baca staging, hitung delta manual, tulis lewat load job WRITE_APPEND seperti M2.1) — secara teknis mungkin (load job BUKAN DML, jadi tidak kena blokir ini), tapi menambah kerumitan besar (keluar dari framework dbt sepenuhnya untuk mart_cleaned, kehilangan test/lineage bawaan dbt) untuk manfaat yang tidak akan terlihat penuh sampai billing aktif dan partitioning asli bisa dipakai.
- **Rejected because:** effort custom Python-upsert tidak sepadan mengingat solusinya sendiri (full refresh) sudah cukup untuk memenuhi 3 dari 4 Kriteria Keberhasilan, dan gap-nya sudah didokumentasikan jelas sebagai konsekuensi billing yang sama.

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

### Decision (SUPERSEDED oleh temuan DML di atas): Watermark incremental — dbt native `is_incremental()`, bukan reuse cursor M2.1

- **Context:** Butuh cara mendeteksi baris baru/berubah per tabel untuk refresh incremental `mart_cleaned`. Tabel `monitoring.extract_cursor` (M2.1) sudah ada untuk kebutuhan serupa.
- **Decision (saat diambil):** `WHERE kolom_tanggal > (SELECT MAX(kolom_tanggal) FROM {{ this }})` (pola native dbt `is_incremental()`) per tabel berkolom tanggal bersih. Tabel tanpa kolom tanggal bersih (composite key/no-PK) pakai full-refresh, konsisten pola M2.1.
- **Status setelah Task 5:** **Tidak jadi dipakai untuk implementasi saat ini** — ditemukan bahwa mekanisme incremental dbt manapun (termasuk `is_incremental()` + strategi `merge`/`append`) butuh DML, yang diblokir total di Sandbox mode (lihat Decision "DML diblokir total..." di atas). Keputusan desain ini (dbt native, bukan reuse cursor M2.1) **tetap berlaku sebagai rencana** begitu billing aktif — tidak perlu didesain ulang, tinggal diaktifkan.
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
