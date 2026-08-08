# Milestone 2.4: Reverse ETL Mart Cleaned ke PostgreSQL — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Seluruh 23 tabel `mart_cleaned` tersedia di PostgreSQL dengan jumlah baris yang cocok dengan versi BigQuery pasca-sync.** — Terpenuhi. 23/23 tabel ter-sync ke serving Postgres (`mart_cleaned.<nama_tabel>`), row count cocok persis BigQuery untuk seluruh tabel, termasuk yang terbesar: `fnb_transactions` 902.574, `staff_shifts` 610.019, `housekeeping_log` 425.172, `bookings` 217.654. Diverifikasi berulang kali — run lokal per-domain (Task 8-13), run CI manual (`workflow_dispatch`, 23/23 `status=synced`), dan run CI otomatis lewat rantai `workflow_run` (23/23 `status=synced` lagi) — total 47+23 baris di `monitoring.reverse_etl_sync_log`, **nol mismatch** di seluruhnya.
- [x] **Swap table berjalan tanpa downtime yang mengganggu akses berjalan (query yang sedang berlangsung tidak gagal akibat proses swap).** — Terpenuhi, diverifikasi empiris lewat `scripts/reverse_etl/test_no_downtime_swap.py`: thread polling `SELECT COUNT(*)` konkuren (interval 20ms) terhadap tabel live selagi 8 siklus swap (fetch->COPY->gate->RENAME) berjalan berturut-turut di foreground. Hasil: **274 query konkuren, 0 error**. RENAME Postgres cuma memegang ACCESS EXCLUSIVE lock sesaat — query yang sedang berjalan menunggu beberapa milidetik, tidak pernah gagal.

## Deliverables

- Project Supabase **baru**, terpisah dari production, sebagai serving layer — schema `mart_cleaned` berisi 23 tabel hasil reverse ETL.
- Role least-privilege `reverse_etl_writer` (scoped ke schema `mart_cleaned` saja, bukan superuser) dan service account BigQuery `reverse-etl-reader` (read-only, dataset-scoped ke `mart_cleaned` saja) — keduanya diverifikasi terisolasi lewat uji coba terkontrol.
- `.github/workflows/transform-mart-cleaned.yml` — menutup 2 known gap Milestone 2.3 (dbt staging + `promote.py` tidak terjadwal, renewal `staging`/`mart_cleaned`/`mart_cleaned_staging` tidak terjadwal). Dijadwalkan 05:00 UTC.
- `.github/workflows/reverse-etl-mart-cleaned.yml` — trigger `workflow_run` menunggu `transform-mart-cleaned.yml` sukses, konvensi orchestrator M2.0. Diverifikasi 2x: `workflow_dispatch` manual dan rantai otomatis sungguhan (transform selesai -> reverse-etl auto-trigger -> sukses).
- `scripts/reverse_etl/sync.py` — mekanisme reverse ETL generik per tabel: baca BigQuery paginated, bulk load Postgres via `psycopg2.copy_expert` (text-format COPY, bukan row-by-row INSERT), gate row-count-parity SEBELUM swap, RENAME-based swap (matching pola arsitektur dokumen Bagian 7.2).
- `scripts/reverse_etl/test_no_downtime_swap.py` — bukti empiris KK#2.
- `monitoring.reverse_etl_sync_log` (schema `monitoring`, production Supabase) — log tiap sync (row count kedua sisi, status, timestamp), tetap terpusat meski serving layer di project berbeda.
- `milestones/2.4-reverse-etl-postgresql/{decisions,logs}.md`.

## Deviations from decisions.md

- **Koneksi serving DB: Session Pooler, bukan direct connection.** `decisions.md` tidak eksplisit mengunci mode koneksi -- rekomendasi awal (di `.env.example`) adalah direct connection, ternyata gagal (`nslookup` mengonfirmasi host direct-connection project Supabase baru IPv6-only, tidak reachable dari environment ini). Dikoreksi ke Session Pooler (IPv4-compatible, tetap dedicated per koneksi jadi aman untuk `copy_expert`). Dicatat sebagai temuan implementasi, bukan perubahan keputusan strategis.
- **Kredensial GCP (grant `bigquery.jobUser`, pembuatan key file) tidak diblokir classifier sesi ini** -- berbeda dari precedent M2.1/M2.2/M2.3 yang selalu butuh user jalankan manual. Assistant berhasil menjalankan langsung. Dicatat sebagai observasi (perilaku classifier tidak konsisten antar sesi), bukan perubahan proses yang disengaja -- kalau sesi mendatang kembali diblokir, pola "user jalankan manual" tetap berlaku sebagai fallback.
- **Penamaan tabel Postgres**: `decisions.md` tidak eksplisit mengunci konvensi penamaan -- diputuskan saat implementasi (`scripts/reverse_etl/serving_tables.py`) untuk pakai nama BARE (`mart_cleaned.bookings`, bukan `mart_cleaned.mart_cleaned__bookings`) karena schema Postgres sudah cukup jadi namespace, beda dari BigQuery yang flat (perlu prefix `mart_cleaned__`). Bukan deviasi dari keputusan yang sudah dikunci, murni detail teknis yang diisi saat implementasi.

## Known Gaps / Follow-ups

- **Role read-only untuk konsumen (Data Analyst) di serving project belum dibangun** -- sesuai catatan out-of-scope di `decisions.md`, M2.4 hanya membangun role WRITER untuk job reverse-etl sendiri. Tidak ada milestone eksplisit di `02-serving-data-scientist.md` yang menaungi ini (M2.5/2.6 fokus ke akses BigQuery Data Scientist, bukan akses Postgres Data Analyst) -- kandidat entri baru `docs/keputusan-tertunda.md`, direkomendasikan diangkat sebelum Data Analyst benar-benar butuh akses.
- **`sync.py --domain`/`--table` tidak dipakai di workflow terjadwal** -- `reverse-etl-mart-cleaned.yml` selalu `--all` (23 tabel setiap run, ~7-8 menit di CI). Untuk skala project ini tidak masalah (data statis/sintetis, waktu proses stabil), tapi kalau volume bertambah signifikan, opsi sync selektif per domain sudah tersedia dan bisa dipakai untuk debugging/parsial refresh tanpa kerja tambahan.
- **8 tabel tanpa PK tunggal** (composite key/tanpa PK, sama seperti gap M2.2/M2.3) tidak diberi constraint UNIQUE eksplisit di sisi Postgres -- konsisten dengan `mart_cleaned` BigQuery yang juga tidak menutup gap ini, bukan regresi baru.
- **Gap billing GCP (`docs/keputusan-tertunda.md`) tetap berlaku** -- `mart_cleaned` sisi BigQuery masih full refresh (M2.3 KK#4 belum terpenuhi), jadi M2.4 mem-push ulang seluruh data tiap run (bukan cuma delta) -- konsisten dengan keputusan sumber M2.4 sendiri (full refresh + swap, bukan incremental), jadi ini bukan gap baru di M2.4, hanya konsekuensi lanjutan dari batasan yang sama.

## Handoff Notes

- **Untuk Milestone 2.5 (API Akses Data Scientist)**: serving Postgres (`mart_cleaned`, 23 tabel) sudah siap dikonsumsi Data Analyst — tapi role read-only untuk mereka belum ada (lihat Known Gaps di atas), perlu dibangun sebelum akses sungguhan diberikan.
- **Kalau volume data bertambah signifikan**: `scripts/reverse_etl/sync.py` sudah punya opsi `--domain <schema>` untuk sync parsial per domain, tidak perlu selalu `--all`.
- **Rerun manual**: `python scripts/reverse_etl/sync.py --all` (dari direktori `scripts/reverse_etl/`, butuh `.env` terisi `REVERSE_ETL_READER_CREDENTIALS`/`REVERSE_ETL_WRITER_DB_URL`/`SUPABASE_DB_URL`).
- **Peringatan**: role `reverse_etl_writer` di serving project cuma bisa CREATE/DROP/RENAME table di schema `mart_cleaned` -- jangan pakai kredensial admin (`SERVING_DB_URL`) untuk operasi rutin, itu cuma untuk setup satu kali (`setup_serving_schema.py`, `setup_writer_role.py`).
