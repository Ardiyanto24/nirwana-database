# Milestone 2.1: Extraction Production ke Raw Warehouse (Fase 2) — Report

**Status:** Partially Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Seluruh 23 tabel berhasil tersinkronisasi ke `raw_production` dengan jumlah baris yang cocok dengan sumber pada snapshot yang sama.** — Terpenuhi penuh. Validasi `COUNT(*)` Postgres vs BigQuery per tabel: **23/23 OK**, total ~2.529.584 baris (cocok "~2.53M rows" di `CLAUDE.md`). Sempat ada insiden kehilangan data di 11 tabel akibat percobaan partitioning (lihat Known Gaps) — dipulihkan penuh sebelum verifikasi akhir ini, dibuktikan lewat query count kedua sisi, bukan diasumsikan.
- [~] **Sinkronisasi berjalan terjadwal secara incremental tanpa membebani database primary (tervalidasi lewat read replica).** — **Terpenuhi sebagian.** Bagian "berjalan terjadwal secara incremental": terpenuhi dan terbukti — `.github/workflows/extract-production.yml` (cron harian) dipicu manual untuk verifikasi, run [31232217473](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31232217473) sukses, log membuktikan cursor tracking bekerja benar di CI (0 baris baru untuk 19 tabel yang sudah tersinkron, 4 tabel `full_refresh` re-sync seperti didesain). Bagian "tervalidasi lewat read replica": **tidak terpenuhi** — ekstraksi memakai koneksi langsung ke primary (`extract_reader` via `EXTRACT_DB_URL`), bukan read replica sungguhan, karena fitur itu berbayar di Supabase (plan Pro+). Keputusan sadar user, dicatat di `decisions.md`.
- [x] **User replikasi terbukti tidak bisa mengakses tabel di luar whitelist saat diuji coba.** — Terpenuhi. `scripts/extract/setup_extract_role.py` — 23/23 grant SELECT cocok whitelist, uji coba `SELECT monitoring.alerts` (di luar whitelist) **ditolak** (`InsufficientPrivilege`), uji coba `INSERT` **ditolak**. Diverifikasi lewat percobaan langsung, bukan diasumsikan.

## Deliverables

- GCP project baru `nirwana-database-elt` (BigQuery Sandbox mode, tanpa billing), dataset `raw_production` (region US).
- Service account `extract-writer` — `WRITER` di dataset ACL `raw_production` saja (bukan project-level), `roles/bigquery.jobUser` di project. Key file dibuat manual oleh user (bukan assistant), disimpan lokal + GitHub Secret (`GCP_EXTRACT_WRITER_KEY_JSON`), tidak pernah di-commit.
- Role Postgres `extract_reader` — read-only, whitelist 23 tabel eksplisit (`scripts/extract/grants.sql`), password di `EXTRACT_DB_URL` (lokal `.env` + GitHub Secret).
- `scripts/extract/` — `tables_config.py` (cursor strategy per tabel, dicek langsung ke `information_schema`), `bq.py` (BigQuery client helper), `extract.py` (fungsi ekstraksi generik dipakai 23 tabel), `schema.sql` (`monitoring.extract_cursor`), `partition_tables.py` (ditulis & terbukti bekerja secara mekanis, hasilnya di-revert — lihat Known Gaps).
- `.github/workflows/extract-production.yml` — jadwal harian, terverifikasi jalan sukses.
- 23 tabel `raw_production.<schema>__<table>` di BigQuery, skema autodetect 1:1 dengan sumber + kolom metadata `_synced_at`.
- `docs/05-orchestrator/konvensi-job-dependency.md` diikuti untuk penamaan workflow.
- `.env.example`, `.gitignore` diperbarui (kredensial GCP/extract baru).
- `milestones/2.1-extraction-production-raw-warehouse/{decisions,logs}.md`.

## Deviations from decisions.md

- **Task 6 (partitioning) direncanakan selesai, ternyata dihentikan di tengah jalan** setelah insiden kehilangan data — bukan deviasi dari rencana breakdown (yang memang mengantisipasi "checkpoint" verifikasi), tapi hasil akhirnya berbeda dari rencana awal (partitioning selesai) menjadi gap terdokumentasi. Root cause dan recovery lengkap ada di `decisions.md` & `logs.md`.
- **`monitoring.extract_cursor` ditulis lewat koneksi ADMIN (`SUPABASE_DB_URL`), bukan `extract_reader`** — tidak eksplisit direncanakan di breakdown awal, tapi konsisten dengan keputusan `extract_reader` read-only (Task 2) yang sudah ditetapkan sebelum Task 3 ditulis. Bukan deviasi, hanya detail implementasi yang belum tertulis eksplisit di breakdown.
- Bug kecil ditemukan & diperbaiki saat implementasi (bukan deviasi keputusan, hanya dicatat untuk transparansi): tipe kolom `TIME` Postgres tidak ter-handle di `_json_safe` (Task 5/7), collision `sys.path.insert` menyebabkan modul `tables_config.py` salah ambil punya `scripts/monitoring/` (Task 3).

## Known Gaps / Follow-ups

- **Read Replica belum dipakai** — ekstraksi dari primary langsung. Revisit kalau plan Supabase di-upgrade ke Pro+, atau kalau beban primary dari ekstraksi harian terbukti jadi masalah nyata (belum terjadi — 23 tabel, ~2.53M baris, ekstraksi harian selesai dalam hitungan menit).
- **CDC tidak dipakai** — cursor tracking custom hanya menangkap baris baru (INSERT), tidak menangkap UPDATE ke baris lama. Diterima sebagai batasan sadar karena data production di sini statis (lihat `CLAUDE.md`). Kalau nanti data production jadi live/berubah, ini perlu direvisit ke CDC sungguhan.
- **Partitioning tidak diterapkan** — gap paling signifikan secara teknis. `scripts/extract/partition_tables.py` sudah ditulis & terbukti benar secara mekanis (CTAS memproses byte penuh sesuai row count), tapi diblokir batasan keras BigQuery Sandbox mode (60 hari expirasi wajib, dihitung dari nilai tanggal partisi untuk kolom non-ingestion-time — menyebabkan hampir seluruh data historis langsung "kedaluwarsa" begitu tabel dibuat). **Wajib direvisit sebelum milestone ini dianggap selesai penuh secara operasional** — begitu billing GCP diaktifkan, jalankan ulang `partition_tables.py` tanpa modifikasi.
- **BigQuery Sandbox mode juga menolak DML** (`UPDATE`/`DELETE`) — tidak menghalangi jalur produksi normal (`extract.py` cuma pakai load job), tapi menghalangi operasi maintenance ad-hoc. Dicatat untuk siapa pun yang nanti perlu operasi row-level di BigQuery tanpa reload seluruh tabel.
- **`scripts/extract/gcp-extract-writer-key.json` ada di mesin lokal user** — sudah di-`.gitignore`, tapi perlu rotasi manual (`setup_extract_role.py`-style key rotation belum ada untuk GCP, cuma untuk Postgres) kalau pernah bocor.

## Handoff Notes

- **Untuk Milestone 2.2 (Layer Staging)**: `raw_production` sudah siap dikonsumsi — 23 tabel, skema 1:1, sinkron harian. Ingat data raw di sini **tidak dibersihkan sama sekali** (dirty data dipertahankan by design, sesuai prinsip kunci di `02-serving-data-scientist.md`).
- **Kalau billing GCP diaktifkan**: jalankan `python scripts/extract/partition_tables.py` untuk menuntaskan Task 6 tanpa modifikasi kode.
- **Rerun manual ekstraksi**: `gh workflow run extract-production.yml --repo Ardiyanto24/nirwana-database`, atau lokal `python scripts/extract/extract.py [schema.table opsional]`.
- **Rotasi kredensial**: `python scripts/extract/setup_extract_role.py` untuk rotate password Postgres `extract_reader` (otomatis update `.env`, GitHub Secret `EXTRACT_DB_URL` perlu diupdate manual setelahnya via `gh secret set`). Key GCP tidak punya mekanisme rotasi otomatis — perlu `gcloud iam service-accounts keys create` manual lagi + update secret.
- **Peringatan**: jangan jalankan `partition_tables.py` di project GCP manapun yang masih Sandbox mode (tanpa billing) tanpa memahami insiden di `decisions.md`/`logs.md` — bisa mengulang kehilangan data di tabel manapun dengan kolom tanggal historis.
