# Milestone 4.3: Kredensial Read-Only Per Kelompok Akses — Decisions

**Sumber:** `docs/03-implementation-plans/05-serving-ai-chatbot.md`, Milestone 4.3 (baris 89-103).
**Prasyarat:** Milestone 4.1 (pemetaan RBAC, Completed), Milestone 4.2 (67 view `chatbot_views`, Completed).
**Status:** In Progress
**Date started:** 2026-08-10

## Lingkup Sumber / Contract

- **Lingkup:** Mengonfigurasi kredensial database read-only untuk chatbot, dengan privilese `SELECT` yang secara teknis terbatas hanya ke `mart_aggregated` dan tabel `mart_cleaned` yang dipetakan eksplisit di Milestone 4.1 (lihat catatan revisi boundary Lapis 2 di `05-serving-ai-chatbot.md`).
- **Output:** Kredensial/service account `chatbot-readonly` (atau setara, kemungkinan 1 kelompok akses per `data_domain` per hasil Milestone 4.1) dengan privilese `SELECT` yang terbukti terbatas hanya ke `mart_aggregated` dan tabel `mart_cleaned` yang dipetakan Milestone 4.1. Dokumentasi eksplisit batasan kredensial ini sebagai referensi audit keamanan.
- **Kriteria Keberhasilan:**
  1. Kredensial chatbot terbukti **tidak bisa** mengakses tabel `mart_cleaned` di luar yang dipetakan Milestone 4.1, `raw_production`, atau sistem production sama sekali saat diuji coba langsung (bukan diasumsikan aman).
  2. Kredensial terbukti hanya bisa membaca (`SELECT`), tidak bisa menulis/mengubah data di `mart_aggregated` maupun tabel `mart_cleaned` yang dijangkau.

## Temuan Eksplorasi (sebelum breakdown)

- Preseden terdekat: `milestones/3.5-isolasi-akses-kredensial-analyst/` (7 role Postgres Data Analyst). Pola pembuatan role (`NOSUPERUSER NOCREATEDB NOCREATEROLE`, password `secrets.token_urlsafe(24)`, idempoten), verifier isolasi generik `verify_role_isolation.py` (allow/deny/write checks, dengan retry-with-backoff untuk Supavisor pooler cache staleness — temuan operasional M3.5), dan bukti empiris kunci: **Postgres view berjalan dengan privilege pemilik view**, bukan pemanggil — role cukup di-`GRANT SELECT` ke view, tidak perlu grant apa pun ke tabel dasarnya.
- **Beda struktural dari M3.5**: M3.5 grant campuran — `analyst_views.<view>` (agregat) **dan** `mart_cleaned.<table>` langsung (row-level, karena `analyst_views` cuma cakupan agregat). M4.2 sudah mengunci **seluruh** akses chatbot (agregat maupun row-level) lewat `chatbot_views` — jadi M4.3 **hanya** grant ke `chatbot_views.<view>`, tidak pernah ke `mart_aggregated`/`mart_cleaned` langsung. Ini menghilangkan seluruh kerumitan owner-routing M3.5 (`get_mart_cleaned_owner_connection()` — admin `SERVING_DB_URL` bukan superuser dan silently no-op kalau GRANT ke tabel yang bukan dimilikinya): karena semua 67 view `chatbot_views` dibuat lewat `apply_views.py` (M4.2, koneksi admin), semuanya dimiliki admin — GRANT selalu lewat 1 koneksi admin saja, tidak perlu koneksi owner terpisah sama sekali.
- **Sumber grant target**: M3.5 menurunkan dari whitelist API M3.4 (sudah ada duluan). Urutan chatbot terbalik — M4.4 (API) belum dibangun. Sumber kebenaran daftar grant M4.3 adalah inventaris view M4.2 (`docs/09-serving-ai-chatbot/view-query-pattern-chatbot.md` + file `scripts/chatbot_views/views_<domain>.sql`), sudah 1:1 dengan 10 `data_domain`. Dihitung ulang langsung dari isi file SQL (bukan disalin dari dokumentasi) — total 67 view cocok hasil `information_schema.views` M4.2 Checkpoint 5.
- M4.1 Keputusan #6 sudah mengunci **10 role, 1 per `data_domain`** — tidak ada role union setara Property/GM M3.5, karena komposisi multi-domain per persona (mis. GM butuh 7+4 domain) adalah tanggung jawab API (M4.4), bukan credential layer.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti preseden M3.5, turunan M4.1/M4.2)

### 1. Cakupan isolasi: table/schema-level (GRANT/REVOKE)

Bukan Row Level Security — konsisten satu-satunya pola akses yang pernah dipakai project ini (M3.5 Keputusan #1).

### 2. 10 role, 1 per `data_domain`

`reservation_chatbot_reader`, `fnb_chatbot_reader`, `facility_chatbot_reader`, `spa_event_chatbot_reader`, `hr_chatbot_reader`, `financial_chatbot_reader`, `properties_ref_chatbot_reader`, `employees_directory_chatbot_reader`, `guests_pii_chatbot_reader`, `guests_profile_chatbot_reader`.

### 3. GRANT hanya ke `chatbot_views.<view>`, tidak pernah ke `mart_aggregated`/`mart_cleaned` langsung

Beda dari M3.5 Keputusan #9. Karena seluruh 67 view (agregat + row-level) sudah mengkurasi kolom, tidak ada alasan legitimate bagi kredensial chatbot menyentuh tabel dasar sama sekali — lebih ketat dari M3.5, dan menghilangkan kebutuhan owner-routing (lihat Temuan Eksplorasi).

### 4. Sumber kebenaran daftar grant = inventaris view M4.2

Tidak ada whitelist file untuk di-import (beda M3.5 Keputusan #4) — daftar nama view langsung dienumerasi per domain di `role_config_<domain>.py`, dikomentari referensi ke `views_<domain>.sql` sebagai sumbernya.

### 5. 1 file config per domain

`role_config_<domain>.py` di `scripts/chatbot_credentials/` — 10 file, isi: nama role, env var, daftar `GRANT_TARGETS` (`chatbot_views.<view>`), `allow_checks`, `deny_checks`, `write_check_sql`.

### 6. Pola pembuatan role & password

Replikasi `scripts/data_analyst_credentials/setup_analyst_roles.py` — `NOSUPERUSER NOCREATEDB NOCREATEROLE`, password `secrets.token_urlsafe(24)`, idempoten (`ALTER ROLE` kalau sudah ada), connection string ke `.env` root, password tidak pernah dicetak penuh.

### 7. Verifier isolasi: copy `verify_role_isolation.py` (M3.5)

Ke `scripts/chatbot_credentials/verify_role_isolation.py` (pola copy-bukan-import lintas `scripts/*`, sejak M2.1) — termasuk retry-with-backoff untuk Supavisor pooler cache staleness (temuan M3.5, berlaku sama di sini).

### 8. Deny-test krusial: seluruh 10 role dites bypass ke tabel dasar

Tiap role dites tidak bisa `SELECT` langsung ke `mart_aggregated.fact_*`/`dim_*` maupun `mart_cleaned.<table>` mentah manapun — **lebih ketat dari M3.5 Keputusan #8** (yang cuma menguji bypass `mart_aggregated`, karena row-level access ke `mart_cleaned` memang legitimate di M3.5). Di sini, kedua bypass diuji untuk semua role karena Keputusan #3 melarang keduanya tanpa kecuali.

### 9. Tidak ada role union

10 role domain berdiri sendiri (beda M3.5 Keputusan #3, `property_gm_analyst_reader` via role inheritance) — komposisi multi-domain per persona murni tanggung jawab Milestone 4.4.

### 10. Dokumentasi

Update `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` (10 baris baru, pola tabel existing) + dokumen baru `docs/09-serving-ai-chatbot/kredensial-chatbot.md`.

## Task Breakdown

11 task, 6 fase, 6 checkpoint (commit tiap checkpoint; checkpoint final commit + tanya user dulu sebelum push, ikuti pola M4.1/M4.2).

### Fase 0 — Fondasi
1. Verifikasi empiris view-owner-privilege khusus schema `chatbot_views` (re-cek asumsi M3.5 berlaku juga di sini — cek `pg_class.relowner` seluruh 67 view = role admin). `scripts/chatbot_credentials/{connections.py,verify_role_isolation.py,setup_chatbot_roles.py}` skeleton (connections.py TANPA `get_mart_cleaned_owner_connection` — tidak dibutuhkan, lihat Keputusan #3). Update `.env.example` — Acceptance: asumsi terbukti — Verify: query langsung serving PostgreSQL — S

**✅ Checkpoint 0** — commit + log.

### Fase 1 — Reservation + F&B roles
2. `role_config_reservation.py` (10 `GRANT_TARGETS`), role `reservation_chatbot_reader`, grant, verifikasi isolasi (allow view sendiri, deny bypass `mart_aggregated`+`mart_cleaned` langsung, deny cross-domain, deny write) — M
3. `role_config_fnb.py` (11 `GRANT_TARGETS`), role `fnb_chatbot_reader` — M

**✅ Checkpoint 1** — commit + log.

### Fase 2 — Facility + Spa & Event roles
4. `role_config_facility.py` (12 `GRANT_TARGETS`), role `facility_chatbot_reader` — M
5. `role_config_spa_event.py` (9 `GRANT_TARGETS`), role `spa_event_chatbot_reader` — M

**✅ Checkpoint 2** — commit + log.

### Fase 3 — HR + Financial roles
6. `role_config_hr.py` (10 `GRANT_TARGETS`, tanpa payroll), role `hr_chatbot_reader`, deny-test tambahan: `v_lookup_payroll`/`v_payroll_department_monthly`/dst — M
7. `role_config_financial.py` (11 `GRANT_TARGETS`), role `financial_chatbot_reader`, deny-test bypass `mart_aggregated.fact_financial_business_line_monthly` (business rule `Overall` exclusion) — M

**✅ Checkpoint 3** — commit + log.

### Fase 4 — 4 Domain Granular
8. `role_config_properties_ref.py`/`role_config_employees_directory.py` (1 `GRANT_TARGETS` masing-masing), 2 role — S
9. `role_config_guests_pii.py`/`role_config_guests_profile.py` (1 `GRANT_TARGETS` masing-masing: `guests_contact_view`/`guests_profile_view`), 2 role, **deny-test krusial**: role `guests_pii_chatbot_reader` tidak bisa baca `guests_profile_view` (dan sebaliknya) — M

**✅ Checkpoint 4** — commit + log.

### Fase 5 — Finalisasi
10. `setup_chatbot_roles.py --all` dijalankan end-to-end, verifikasi ulang 10 role sekaligus.
11. Update `kebijakan-akses-kredensial-scoped.md`, tulis `docs/09-serving-ai-chatbot/kredensial-chatbot.md`, verifikasi ulang KK1-KK2, tulis `report.md` — M

**✅ Checkpoint 5 (final)** — commit; tanya user sebelum push.
