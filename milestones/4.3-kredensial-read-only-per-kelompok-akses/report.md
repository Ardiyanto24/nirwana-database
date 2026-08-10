# Milestone 4.3: Kredensial Read-Only Per Kelompok Akses — Report

**Status:** Completed
**Date completed:** 2026-08-10

## Kriteria Keberhasilan — Hasil

- [x] **Kredensial chatbot terbukti tidak bisa mengakses tabel `mart_cleaned` di luar yang dipetakan Milestone 4.1, `raw_production`, atau sistem production sama sekali saat diuji coba langsung.** — Diuji langsung (connect-as-role, bukan asumsi) untuk seluruh 10 role: setiap role gagal (`InsufficientPrivilege`) saat mencoba `SELECT` ke tabel dasar `mart_aggregated.fact_*`/`dim_*` **dan** `mart_cleaned.<table>` mentah manapun (lebih ketat dari M3.5 yang cuma menguji bypass `mart_aggregated`) — role bahkan tidak punya `USAGE` ke schema `mart_cleaned`/`mart_aggregated` sama sekali, hanya ke `chatbot_views`. `mart_cleaned.role_permissions` diuji eksplisit ditolak di seluruh 10 role (M4.1 Keputusan #7). Tidak ada role manapun yang punya kredensial ke `raw_production`/BigQuery sama sekali — kredensial ini murni PostgreSQL serving project.
- [x] **Kredensial terbukti hanya bisa membaca (`SELECT`), tidak bisa menulis/mengubah data di `mart_aggregated` maupun tabel `mart_cleaned` yang dijangkau.** — `write_check_sql` (`INSERT`) diuji di seluruh 10 role, semua gagal `InsufficientPrivilege`. Karena tidak ada satu pun role dengan `USAGE` ke `mart_cleaned`/`mart_aggregated`, write-denial ini sekaligus membuktikan isolasi schema penuh, bukan cuma table-level.

## Deliverables

- `scripts/chatbot_credentials/{connections.py,verify_role_isolation.py,setup_chatbot_roles.py,role_config_<10 domain>.py}` — 10 role Postgres di serving project, seluruhnya read-only, GRANT eksklusif ke `chatbot_views`.
- `docs/09-serving-ai-chatbot/kredensial-chatbot.md` — dokumentasi kebijakan akses lengkap per role, bukti isolasi, temuan operasional.
- Update `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` — 10 baris inventaris baru + bagian "Siapa Boleh Memegang" untuk `*_chatbot_reader`.
- `.env`/`.env.example` — 10 `*_CHATBOT_READER_DB_URL` baru.

## Deviations from decisions.md

Tidak ada deviasi — seluruh 10 keputusan teknis dieksekusi persis seperti direncanakan (10 role 1:1 `data_domain`, GRANT eksklusif `chatbot_views`, tanpa role union, verifier isolasi copy M3.5, deny-test bypass ganda `mart_aggregated`+`mart_cleaned` di semua role).

## Known Gaps / Follow-ups

- **Belum ada rotasi terjadwal otomatis** untuk 10 password ini — konsisten gap yang sudah dicatat project-wide di `kebijakan-akses-kredensial-scoped.md` §Rotasi dan Pencabutan (tidak ada kredensial manapun di project ini yang punya rotasi otomatis). Rotasi manual lewat re-run `setup_chatbot_roles.py --all`.
- **Belum ada konsumen nyata** yang memakai 10 kredensial ini — Milestone 4.4 (API) yang akan memilih/mengorkestrasi kredensial mana dipakai per request berdasarkan `role_permissions` persona belum dibangun. Kredensial sudah terbukti terisolasi teknis, tapi belum "hidup" dipakai produksi.
- **Tidak ada mekanisme untuk komposisi multi-domain** (mis. General Manager butuh 7+4 domain sekaligus dalam 1 sesi chat) di level kredensial ini — sesuai Keputusan #9, ini sengaja didesain jadi tanggung jawab Milestone 4.4, bukan gap yang terlewat.

## Handoff Notes

- **Untuk Milestone 4.4 (API):** 10 kredensial siap dipakai. API perlu logika pemilihan kredensial per request: baca `role_title` dari identitas user (via Lapis 1), lookup `data_domain` yang diizinkan di `corporate_master.role_permissions`, pilih koneksi database yang sesuai (kemungkinan connection pool per role, bukan 1 koneksi admin universal). Filter `own_property`/`all_properties` (M4.1 Keputusan #5) juga sepenuhnya tanggung jawab API — kredensial ini tidak melakukan filtering properti apa pun.
- **`guests_pii_chatbot_reader`/`guests_profile_chatbot_reader`**: API harus memastikan permintaan domain `guests_pii` tidak pernah salah routing ke kredensial `guests_profile` (atau sebaliknya) — kedua kredensial sengaja saling menolak akses satu sama lain (diverifikasi eksplisit), jadi kesalahan routing akan gagal keras (bukan silang data), tapi tetap perlu logika pemilihan yang benar di sisi API.
- **Dokumentasi kredensial project-wide** (`kebijakan-akses-kredensial-scoped.md`) sudah mencakup 10 kredensial baru ini — pemilik infrastruktur data berikutnya bisa langsung rujuk ke situ untuk gambaran lengkap seluruh kredensial project (sekarang 27 baris: 8 non-analyst + 7 analyst + 1 analyst-readonly + 10 chatbot + 1 baris exception `dbt-transform`... total tepatnya lihat tabel).
