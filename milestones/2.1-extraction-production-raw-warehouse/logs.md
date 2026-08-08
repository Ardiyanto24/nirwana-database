# Milestone 2.1 -- Execution Log

## 2026-08-08 (start)
Did: Breakdown Milestone 2.1 kedua kalinya lewat skill `planning-and-task-breakdown` (kali pertama tanpa memanggil skill secara eksplisit -- user menegur, diulang formal). Riset menemukan 3 fakta pengubah bentuk keputusan: tidak ada kolom `updated_at` di 23 tabel (`Metadata.md`), data production statis (`CLAUDE.md`), Read Replica Supabase berbayar (beda dari CDC yang gratis). 3 pertanyaan `AskUserQuestion` sempat di-dismiss user, diajukan ulang setelah plan tertulis -- user jawab: ekstraksi via koneksi langsung primary + cursor tracking (bukan replica/REST API/CDC), tool custom Python. Plan disetujui, lanjut implementasi via `using-agent-skills`.
Result: worked. `decisions.md` ditulis lengkap (Contract, Task Breakdown 11 task, 5 Technical Decisions).

## 2026-08-08 -- Provisioning GCP (Task 1)
Did: Cek project GCP existing (`gcloud projects list`) -- ditemukan `nirwana-data-platform` yang ternyata project latihan lama user, tidak dipakai (user interupsi sebelum saya lanjut pakai project itu). Buat project baru `nirwana-database-elt`, aktifkan BigQuery API, buat dataset `raw_production` (region US).
Result: worked. Dataset terverifikasi via `bq show`. Ditemukan otomatis: `defaultTableExpirationMs`/`defaultPartitionExpirationMs` = 60 hari -- ini batasan bawaan BigQuery Sandbox mode (belum ada billing dihubungkan), dicatat sebagai gap eksplisit di `decisions.md`.

## 2026-08-08 -- Service account & key file (bagian dari Task 1)
Did: Buat service account `extract-writer`. Percobaan pertama grant `bigquery.dataEditor` di level **project** -- dikoreksi ke level **dataset** (`raw_production` saja) karena melanggar least-privilege (M2.1 lain juga eksplisit soal whitelist). `bq add-iam-policy-binding` level-dataset gagal ("requires allowlisting") -- fallback ke edit ACL dataset langsung via `bq show`/`bq update --source` (JSON access list). Path native Windows Python tidak mengerti `/tmp` Git Bash -- pakai scratchpad dir asli. Percobaan membuat *key file* JSON untuk service account **diblokir otomatis** oleh classifier keamanan sesi (kredensial jangka panjang dianggap aksi sensitif).
Result: dataset ACL berhasil (`extract-writer` = WRITER di `raw_production`, `jobUser` di level project). Key file **tidak dibuat oleh assistant** -- user diberi command `gcloud iam service-accounts keys create` untuk dijalankan sendiri di terminal mereka, hasilnya akan disimpan ke `scripts/extract/gcp-extract-writer-key.json` (ditambahkan ke `.gitignore` lebih dulu supaya aman begitu file itu ada).

## 2026-08-08 -- User replikasi Postgres (Task 2)
Did: Tulis `scripts/extract/grants.sql` (23 SELECT grant eksplisit, 6 schema, disalin dari daftar tabel `docs/04-monitoring/baseline-inventaris-produksi.md`) dan `scripts/extract/setup_extract_role.py` (pola sama seperti `scripts/api_reader/setup_reader_role.py` M1.6 -- create/rotate role, apply grants, verifikasi otomatis, tulis `EXTRACT_DB_URL` ke `.env`). Jalankan script.
Result: worked. Role `extract_reader` dibuat, 23/23 grant cocok expected count, 4 verification check semua OK (SELECT whitelisted sukses x2, SELECT `monitoring.alerts` ditolak, INSERT ditolak). `EXTRACT_DB_URL` tertulis ke `.env` (tidak pernah di-print).

## Status saat ini (belum Completed)
Task 1 & 2 selesai & terverifikasi. Task 1 masih menunggu user generate key file service account secara manual sebelum Task 3 (skrip ekstraksi ke BigQuery) bisa diuji end-to-end.
