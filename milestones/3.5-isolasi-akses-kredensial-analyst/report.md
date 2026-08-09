# Milestone 3.5: Isolasi Akses dan Kredensial Read-Only — Report

**Status:** Completed
**Date completed:** 2026-08-09

## Kriteria Keberhasilan — Hasil

- [x] **KK1 — Kredensial yang diberikan ke suatu peran analyst terbukti tidak bisa mengakses data di luar cakupannya saat diuji coba (mis. HR Analyst tidak bisa mengakses `payroll`).** Terpenuhi untuk seluruh 7 role, diverifikasi lewat `scripts/data_analyst_credentials/verify_role_isolation.py` (connect-as-role sungguhan terhadap serving PostgreSQL, bukan asumsi). Bukti paling ketat: (a) **HR Analyst** — 5 target payroll-adjacent diuji sekaligus (`mart_cleaned.payroll` + 4 view finansial), semua gagal `InsufficientPrivilege`, persis contoh literal KK1 dokumen sumber. (b) **Corporate/Financial Analyst** — SELECT langsung ke `mart_aggregated.fact_financial_business_line_monthly` (bypass filter `Overall` exclusion M3.2) gagal — business-rule-integrity check paling kritis di seluruh milestone. (c) **Property/GM Analyst** — union 5 domain, gagal total ke Corporate/Financial termasuk `v_financial_business_line_group_monthly` (larangan tabel level-grup, M3.1 business rule #3).
- [x] **KK2 — Seluruh kredensial analyst bersifat read-only, tidak bisa menulis/mengubah data di `mart_aggregated` maupun `mart_cleaned`.** Terpenuhi. Tiap role diuji `INSERT` ke tabel row-level miliknya sendiri (kondisi paling menguntungkan penyerang) — seluruhnya gagal `InsufficientPrivilege`. Diverifikasi ulang di penutupan lewat `pg_roles` (`rolsuper=false`, `rolcreatedb=false`, `rolcreaterole=false` untuk seluruh 7 role) dan `pg_class.relacl` (tidak ada satu pun grant selain `r`/SELECT tercatat di `analyst_views`/`mart_cleaned` untuk role manapun).

## Deliverables

- `docs/08-serving-data-analyst/kredensial-analyst.md` — Output resmi #2 (kebijakan akses per peran + bukti isolasi lengkap).
- `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` — diupdate, 7 baris inventaris baru + bagian "Siapa Boleh Memegang" + referensi verifier Postgres generik baru.
- `scripts/data_analyst_credentials/{connections.py, grant_utils.py, verify_role_isolation.py, setup_analyst_roles.py, role_config_revenue.py, role_config_fnb.py, role_config_facility.py, role_config_spa_event.py, role_config_hr.py, role_config_corporate_financial.py, role_config_property_gm.py}`.
- `.env.example` — 7 placeholder baru. `.env` — 7 connection string sungguhan (gitignored).
- `milestones/3.5-isolasi-akses-kredensial-analyst/{decisions,logs}.md`.

## Cakupan Final

7 role read-only live di serving PostgreSQL: 6 role domain (grant objek langsung dari whitelist M3.4) + 1 role union Property/GM (role inheritance, 0 grant objek langsung).

## Business Rule Kritis Diverifikasi End-to-End (whitelist M3.4 → GRANT → koneksi sungguhan)

1. **Payroll eksklusif Corporate/Financial** — HR Analyst dan Property/GM Analyst gagal total ke `payroll` dan seluruh view finansial terkait.
2. **Filter `Overall`/`Corporate Overhead` tidak bisa dilewati** — bahkan Corporate/Financial Analyst sendiri (role dengan akses terluas) tidak bisa SELECT langsung ke tabel dasar di balik `v_financial_departmental_margin`.
3. **Tabel level-grup terlarang untuk Property/GM** — `v_financial_business_line_group_monthly` gagal diakses meski secara teknis tidak mengandung data 1 properti pun (murni agregat lintas grup).
4. **Tidak ada grant apa pun ke `mart_aggregated`** — seluruh 7 role, 0 pengecualian (dikonfirmasi Keputusan #8 Checkpoint 1 dan diverifikasi ulang tiap role berikutnya).

## Deviations from decisions.md

**2 temuan teknis signifikan, ditemukan saat implementasi Checkpoint 2, didokumentasikan eksplisit (bukan disembunyikan) dan diperbaiki dalam scope milestone yang sama:**

1. **Ownership schema vs objek berbeda** — admin (`SERVING_DB_URL`, role `postgres`) ternyata **bukan superuser** di project serving ini dan tidak punya otoritas GRANT atas objek yang tidak dimilikinya. `mart_cleaned.*` dimiliki `reverse_etl_writer` (bukan admin) — `GRANT SELECT` yang dijalankan admin ke tabel itu sukses tanpa error tapi **tidak benar-benar berlaku** (silent no-op, dikonfirmasi lewat `pg_class.relacl`). Diperbaiki: `apply_grants()` merutekan GRANT ke koneksi pemilik sebenarnya per schema (`connections.get_mart_cleaned_owner_connection()`, baru).
2. **Supavisor pooler cache tidak instan** — koneksi sebagai role yang baru dibuat/di-grant bisa gagal auth atau "permission denied" sesaat meski grant sudah benar di katalog. Diperbaiki: `verify_role_isolation.py` menambah retry warm-up (maks 6×, jeda 5 detik) sebelum suite verifikasi sungguhan.

Kedua temuan ini **tidak mengurangi keputusan desain di `decisions.md`** — murni detail implementasi operasional yang tidak bisa diketahui sebelum mencoba terhadap infrastruktur sungguhan. Dampaknya: Checkpoint 2 (Revenue) butuh 1 iterasi debugging tambahan; 5 checkpoint berikutnya (F&B, Facility, Spa&Event, HR, Corporate/Financial) semuanya lolos bersih tanpa retry sejak fix diterapkan, membuktikan akar masalah benar-benar terselesaikan.

**1 gangguan operasional dicatat**: sesi sempat terputus (komputer mati) tepat setelah Checkpoint 2 selesai tapi sebelum commit — dicek ulang saat resume: state role/`.env` di database sungguhan tidak terpengaruh (persisten di server, bukan lokal), lanjut tanpa mengulang kerja.

## Known Gaps / Follow-ups

- **Tidak ada rotasi password terjadwal** — konsisten gap yang sudah dicatat untuk seluruh kredensial project ini (`kebijakan-akses-kredensial-scoped.md` "Rotasi dan Pencabutan"). Re-run `setup_analyst_roles.py --role <x>` merotasi password kapan saja dibutuhkan, tapi tidak otomatis terjadwal.
- **`information_schema.role_table_grants` tidak selalu menunjukkan grant lengkap** ketika query dijalankan oleh admin non-superuser untuk objek yang tidak digrant langsung olehnya (mis. tabel `mart_cleaned` yang di-grant lewat `reverse_etl_writer`) — ditemukan saat verifikasi akhir. `pg_class.relacl`/`pg_namespace.nspacl` adalah sumber kebenaran yang lebih andal untuk audit lintas-pemilik di masa depan; dicatat sebagai catatan operasional, bukan dianggap bug.
- **Belum ada mekanisme pencabutan otomatis** kalau seorang analyst keluar tim — mengikuti pola manual `gcloud iam ... keys delete` yang sudah dipakai kredensial BigQuery lain, tapi untuk role Postgres prosesnya adalah `ALTER ROLE <role> WITH PASSWORD <random-baru>` (invalidate password lama) — belum didokumentasikan sebagai langkah eksplisit terpisah.

## Handoff Notes

- **Milestone 3.4 (API) berikutnya, kalau butuh diperbarui:** 7 kredensial ini siap dipakai FastAPI app (`scripts/data_analyst_api/`) untuk menggantikan koneksi admin `SERVING_DB_URL` yang masih dipakai sekarang — cukup pilih env var sesuai domain/role pemanggil per endpoint, tidak perlu perubahan skema kredensial.
- **Pemilik `mart_aggregated`/`mart_cleaned` berikutnya:** kalau ada tabel/view baru ditambahkan (lewat mekanisme M5.6), ingat GRANT di 6 `role_config_<domain>.py` perlu direvisit — GRANT tidak otomatis mengikuti perubahan whitelist M3.4 (perlu re-run `setup_analyst_roles.py` setelah `whitelist_<domain>.py` diupdate).
- **Kalau menambah kredensial Postgres baru di masa depan** (bukan cuma analyst): pakai `scripts/data_analyst_credentials/verify_role_isolation.py` sebagai verifier generik (bukan pola inline `setup_*_role.py` lama) — sudah terbukti reusable 7×, dan kedua temuan operasional di atas (ownership routing, pooler warm-up) relevan untuk kredensial Postgres apa pun di project ini ke depannya, tidak spesifik ke Data Analyst.
