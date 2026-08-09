# Milestone 3.5: Isolasi Akses dan Kredensial Read-Only — Decisions

**Sumber:** `docs/03-implementation-plans/04-serving-data-analyst.md`, baris 122-137.
**Prasyarat:** Milestone 3.1 (pemetaan akses), 3.2 (48 view `analyst_views`), 3.3 (50 index), 3.4 (12 endpoint API + whitelist per domain) — semua Completed.
**Status:** In Progress
**Date started:** 2026-08-09

## Lingkup Sumber / Contract

- **Lingkup:** Mengonfigurasi kredensial/akses read-only khusus untuk kebutuhan Data Analyst, mempertimbangkan tidak semua peran punya cakupan akses sama (mis. HR Analyst tidak mencakup payroll; Property/GM Analyst tidak mencakup `financial_summary` tingkat grup). Memakai mekanisme role read-only yang disediakan pemilik infrastruktur Postgres serving layer.
- **Output:**
  1. Kredensial/role read-only per kelompok peran analyst, terpisah dari kredensial Data Scientist/AI Chatbot.
  2. Dokumentasi kebijakan akses per peran.
- **Kriteria Keberhasilan:**
  1. Kredensial yang diberikan ke suatu peran analyst terbukti **tidak bisa** mengakses data di luar cakupannya saat diuji coba (mis. HR Analyst tidak bisa mengakses `payroll`).
  2. Seluruh kredensial analyst bersifat read-only, tidak bisa menulis/mengubah data di `mart_aggregated` maupun `mart_cleaned`.

## Temuan Eksplorasi (sebelum breakdown)

- **RLS tidak pernah dipakai di project ini** — nol referensi "Row Level Security"/"CREATE POLICY" di 377 file tracked (dicek lewat eksplorasi mendalam). Seluruh 9 kredensial existing di `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` (termasuk `data-scientist-reader` yang menyentuh PII/payroll) memakai GRANT/REVOKE schema/table-level, bukan row-level.
- **KK M3.5 sendiri memakai contoh table-level** ("HR Analyst tidak bisa mengakses `payroll`"), bukan row-level. Catatan Handoff M3.2 (`report.md` baris 45) eksplisit: isolasi `property_id` untuk Property/GM Analyst ada "di level query/API, **bukan** GRANT terpisah per properti" — tanggung jawab M3.4 (API), bukan M3.5.
- **Kesimpulan dikunci tanpa AskUserQuestion**: M3.5 fokus isolasi table/schema-level (GRANT/REVOKE) per domain, konsisten satu-satunya pola akses yang pernah dipakai project ini.
- **Pola pembuatan role**: `scripts/api_reader/setup_reader_role.py` (M1.6) dan `scripts/extract/setup_extract_role.py` — `NOSUPERUSER NOCREATEDB NOCREATEROLE`, password `secrets.token_urlsafe(24)`, idempoten (`ALTER ROLE` kalau sudah ada), verifikasi live sebelum menulis `.env`, password tidak pernah dicetak penuh.
- **Tidak ada verifier isolasi Postgres generik existing** — `verify_reader_isolation.py`/`verify_dataset_isolation.py` khusus BigQuery. Setiap `setup_*_role.py` Postgres punya verifikasi inline sendiri-sendiri (connect-as-role, `psycopg2.errors.InsufficientPrivilege`).
- **Konvensi GRANT per-objek**: `scripts/extract/grants.sql` — 1 baris `GRANT SELECT ON <schema>.<table>` per objek, bukan `ALL TABLES IN SCHEMA` (yang cuma dipakai kalau role memang menguasai seluruh schema, tidak relevan di sini karena tiap role analyst cuma boleh subset view/tabel).
- **Postgres view berjalan dengan privilege pemilik view** (bukan privilege pemanggil) secara default — kalau terbukti benar, role analyst cukup di-GRANT `SELECT` ke `analyst_views.<view>` saja, tidak perlu GRANT apa pun ke `mart_aggregated` (schema yang jadi basis view). Ini juga berarti bypass langsung ke `mart_aggregated.fact_*` (melewati filter business rule yang ditanam di view, mis. `Overall` exclusion) harus otomatis gagal kalau tidak ada GRANT eksplisit ke schema itu — diverifikasi empiris sebelum jadi asumsi desain final (Fase 0).

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 1. Cakupan isolasi: table/schema-level (GRANT/REVOKE), bukan RLS

Lihat Temuan Eksplorasi.

### 2. 7 role

6 role domain (`revenue_analyst_reader`, `fnb_analyst_reader`, `facility_analyst_reader`, `spa_event_analyst_reader`, `hr_analyst_reader`, `corporate_financial_analyst_reader`) + 1 role union (`property_gm_analyst_reader`).

### 3. Property/GM role: role inheritance, bukan re-grant

`GRANT revenue_analyst_reader, fnb_analyst_reader, facility_analyst_reader, spa_event_analyst_reader, hr_analyst_reader TO property_gm_analyst_reader` — Postgres role membership mewarisi privilege otomatis.

### 4. Sumber kebenaran daftar akses = whitelist M3.4

GRANT per role diturunkan program-atis dari `AGGREGATE_WHITELIST`/`ROWLEVEL_WHITELIST` di `scripts/data_analyst_api/whitelist_<domain>.py` (field `source`) — mencegah drift antara API dan kredensial.

### 5. 1 file config per domain

`role_config_<domain>.py` di `scripts/data_analyst_credentials/`, mengimpor whitelist domain terkait.

### 6. Pola pembuatan role & password

Direplikasi dari `setup_reader_role.py`/`setup_extract_role.py`. Connection string ditulis ke `.env` root (pola M2.4/M5.5). Password tidak pernah dicetak penuh.

### 7. Verifier isolasi Postgres baru, dipakai ulang 7×

`scripts/data_analyst_credentials/verify_role_isolation.py` — generalisasi pola inline `setup_*_role.py`, semangat sama `verify_dataset_isolation.py` (M2.5).

### 8. Deny-test krusial tambahan: bypass ke tabel dasar `mart_aggregated`

Tiap role diuji tidak bisa SELECT langsung ke `mart_aggregated.fact_*` — membuktikan business rule M3.2 (mis. filter `Overall`) tidak bisa dilewati.

### 9. Row-level tetap GRANT langsung ke `mart_cleaned.<table>`

Konsisten desain M3.2 (row-level query `mart_cleaned` langsung, bukan lewat view).

### 10. Dokumentasi kebijakan

Update `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` (7 baris + bagian "Siapa Boleh Memegang") + dokumen baru `docs/08-serving-data-analyst/kredensial-analyst.md`.

## Task Breakdown

**Kenapa 9 task / 9 checkpoint:** 6 role domain + 1 role union adalah 7 unit kerja independen, tiap role py config file sendiri diturunkan dari whitelist domain M3.4 yang juga terpisah per file — pola sama M3.2/M3.4. Ditambah 1 fondasi + 1 finalisasi = 9.

### Fase 0 — Fondasi
1. Verifikasi empiris Keputusan #8 (view privilege pemilik). Bangun `scripts/data_analyst_credentials/{connections.py,verify_role_isolation.py,setup_analyst_roles.py}` skeleton. Update `.env.example` — Acceptance: asumsi terbukti — Verify: query langsung serving PostgreSQL — S

**✅ Checkpoint 1** — commit + log.

### Fase 1 — Revenue role
2. `role_config_revenue.py`, role `revenue_analyst_reader`, grant, verifikasi isolasi (allow/deny/write) — M

**✅ Checkpoint 2** — commit + log.

### Fase 2 — F&B role
3. `role_config_fnb.py`, role `fnb_analyst_reader` — M

**✅ Checkpoint 3** — commit + log.

### Fase 3 — Facility/Ops role
4. `role_config_facility.py`, role `facility_analyst_reader` — M

**✅ Checkpoint 4** — commit + log.

### Fase 4 — Spa & Event role
5. `role_config_spa_event.py`, role `spa_event_analyst_reader` — S

**✅ Checkpoint 5** — commit + log.

### Fase 5 — HR role
6. `role_config_hr.py`, role `hr_analyst_reader`, deny-test `payroll` — M

**✅ Checkpoint 6** — commit + log.

### Fase 6 — Corporate/Financial role
7. `role_config_corporate_financial.py`, role `corporate_financial_analyst_reader`, deny-test bypass `mart_aggregated.fact_financial_business_line_monthly` — M

**✅ Checkpoint 7** — commit + log.

### Fase 7 — Property/GM role
8. `property_gm_analyst_reader` via role inheritance, verifikasi allow 5 domain + deny Corporate/Financial — M

**✅ Checkpoint 8** — commit + log.

### Fase 8 — Finalisasi
9. Update kebijakan kredensial, tulis `kredensial-analyst.md`, verifikasi KK1+KK2 lintas 7 role, `report.md` — M

**✅ Checkpoint 9 (final)** — commit; tanya user sebelum push.
