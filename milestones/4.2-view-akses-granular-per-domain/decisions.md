# Milestone 4.2: View Akses Granular per Domain — Decisions

**Sumber:** `docs/03-implementation-plans/05-serving-ai-chatbot.md`, Milestone 4.2 (baris 68-84).
**Prasyarat:** Milestone 4.1 (`docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md`, Completed) — pemetaan 10 `data_domain` → tabel `mart_aggregated`/`mart_cleaned`, mekanisme filter, kontrak 2 view PII sudah tersedia sebagai acuan langsung.
**Status:** In Progress
**Date started:** 2026-08-10

## Lingkup Sumber / Contract

- **Lingkup:** Membangun view di atas `mart_aggregated` sesuai pemetaan Milestone 4.1 — termasuk view terpisah `guests_contact_view`/`guests_profile_view` di atas tabel `guests` yang sama, dan penerapan filter `own_property`/`all_properties` secara konsisten di seluruh view domain lainnya.
- **Output:** View akses per domain data, termasuk pemisahan kolom PII vs profile pada `guests`. Validasi bahwa tidak ada view yang secara tidak sengaja mengekspos kolom di luar cakupan domain yang dimaksud.
- **Kriteria Keberhasilan:**
  1. Setiap domain data punya view yang mengembalikan hanya kolom yang relevan dengan domain tersebut.
  2. Percobaan mengakses kolom PII lewat `guests_profile_view` (atau sebaliknya) gagal karena kolom tersebut memang tidak ada di view itu.
  3. Filter `own_property`/`all_properties` terbukti bekerja benar pada uji coba dengan beberapa `property_id` berbeda.

## Temuan Eksplorasi (sebelum breakdown)

- Preseden terdekat: `milestones/3.2-view-dan-query-pattern-per-domain/` (Data Analyst) — 48 view agregat di schema `analyst_views`, pola: 1 file SQL per domain, `CREATE OR REPLACE VIEW`, runner Python (`apply_views.py`/`connections.py`), dimension di-resolve ke nama, business rule kritis ditanam di view.
- **Beda penting dari M3.2:** M3.2 hanya membangun view agregat — akses row-level Data Analyst ke `mart_cleaned` lewat GRANT langsung ke tabel mentah (Data Analyst memang butuh row-level penuh tanpa kurasi kolom). Chatbot **tidak** boleh diberi GRANT langsung ke `mart_cleaned` mentah — kebutuhan `guests_pii`/`guests_profile` sendiri sudah memaksa kurasi kolom lewat view. Supaya defense-in-depth seragam di seluruh 10 domain (bukan cuma domain guest), **seluruh** akses `mart_cleaned` row-level untuk chatbot lewat view yang mengkurasi kolom — keputusan turunan dari kebutuhan M4.1, bukan pertanyaan baru.
- Serving PostgreSQL schema sudah dikonfirmasi M3.2: `mart_aggregated` — 1:1 nama tabel BigQuery (`fact_*`/`dim_*` bare). `mart_cleaned` — prefix `mart_cleaned__` di BigQuery di-strip jadi nama tabel produksi asli di Postgres (mis. `mart_cleaned.bookings`).
- `guests` (`mart_cleaned.guests`) tidak punya kolom `property_id` (dikonfirmasi M4.1 terhadap `Metadata.md`) — `guests_contact_view`/`guests_profile_view` butuh `last_active_property_id` turunan dari join `bookings`/`spa_bookings`/`event_bookings`.
- SLA breach threshold Facility (`critical`=8j, `high`=24j, `medium`=48j, `low`=72j) sudah dikonfirmasi M3.2 di `Metadata.md` baris 706-715 — reuse logic yang sama, tidak perlu verifikasi ulang.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti preseden M3.2 + turunan kontrak M4.1)

### 1. Schema baru `chatbot_views`

Terpisah dari `mart_aggregated`/`mart_cleaned`/`analyst_views` di serving PostgreSQL — alasan identik M3.2: memudahkan Milestone 4.3 (kredensial) GRANT SELECT per view/per kelompok akses tanpa menyentuh GRANT di schema mart mentah tempat writer role reverse ETL beroperasi.

### 2. Dua lapis view per domain operasional

View agregat (`v_<domain>_<metric>`, 1 per fact table relevan, pola identik M3.2 — dimension di-resolve ke nama) + view row-level baru (`v_lookup_<table>`, kolom dikurasi sesuai kebutuhan lookup Staff di `pemetaan-akses-teknis-chatbot.md` §2). Tidak ada GRANT langsung ke tabel `mart_cleaned` mentah untuk kredensial chatbot manapun (beda dari M3.2, lihat Temuan Eksplorasi).

### 3. Nama `guests_contact_view`/`guests_profile_view` dikunci dari M4.1

Bukan pola `v_lookup_*` — kontrak nama sudah ditulis di `pemetaan-akses-teknis-chatbot.md` §3, dipakai persis sama supaya tidak ada drift antara dokumen kontrak dan implementasi. Termasuk kolom `last_active_property_id`.

### 4. `property_id` selalu kolom mentah, tidak difilter di view

Konsisten M4.1 Keputusan #5 (filter own_property/all_properties di API, bukan di database) — setiap view yang scope-nya properti wajib mengekspos `property_id` apa adanya. View **tidak pernah** melakukan `WHERE property_id = ...` hardcoded.

### 5. Deployment: plain SQL DDL + Python runner

`scripts/chatbot_views/{schema.sql,connections.py,apply_views.py}` — copy pola `scripts/data_analyst_views/` (konvensi copy-bukan-import lintas `scripts/*`, sejak M2.1, menghindari collision `sys.path`).

### 6. Koneksi: `SERVING_DB_URL` (admin)

Sama alasan M3.2 — murni authoring/apply DDL sekali jalan, bukan operasi harian. GRANT scoped-role menyusul di Milestone 4.3.

### 7. Struktur file: 1 file SQL per domain (9 file)

`views_reservation.sql`, `views_fnb.sql`, `views_facility.sql`, `views_spa_event.sql`, `views_hr.sql`, `views_financial.sql`, `views_properties_ref.sql`, `views_employees_directory.sql`, `views_guests.sql` (2 domain PII digabung 1 file karena sama-sama di atas `guests`).

## Task Breakdown

10 task, 6 fase, 6 checkpoint (commit tiap checkpoint; checkpoint final commit + tanya user dulu sebelum push, ikuti pola M3.2/M4.1).

### Fase 0 — Fondasi
1. `scripts/chatbot_views/{schema.sql,connections.py,apply_views.py}`. Uji konektivitas `SERVING_DB_URL`, jalankan `schema.sql` — Acceptance: schema `chatbot_views` ada — Verify: `information_schema.schemata` — S

**✅ Checkpoint 0** — commit + log.

### Fase 1 — Reservation + F&B
2. `views_reservation.sql` (8 view agregat + `v_lookup_bookings`, `v_lookup_daily_occupancy`) + apply + verifikasi kolom sesuai domain — M — **Selesai**
3. `views_fnb.sql` (8 view agregat + `v_lookup_fnb_inventory`, `v_lookup_fnb_transactions`, `v_lookup_recipe_bom`) + apply + verifikasi — M — **Selesai**

**✅ Checkpoint 1** — commit + log.

### Fase 2 — Facility + Spa & Event
4. `views_facility.sql` (9 view agregat, termasuk `sla_status` reuse logic M3.2 + `v_lookup_rooms`, `v_lookup_housekeeping_log`, `v_lookup_maintenance_tickets`) + apply + verifikasi — M — **Selesai**
5. `views_spa_event.sql` (6 view agregat + `v_lookup_spa_bookings`, `v_lookup_event_bookings`, `v_lookup_venues`) + apply + verifikasi — M — **Selesai**

**✅ Checkpoint 2** — commit + log.

### Fase 3 — HR + Financial
6. `views_hr.sql` (8 view agregat, tanpa payroll + `v_lookup_staff_shifts`, `v_lookup_employee_performance`) + apply + verifikasi larangan payroll — M — **Selesai**
7. `views_financial.sql` (9 view agregat + `v_lookup_financial_summary`, `v_lookup_payroll`) + apply + verifikasi business rule `business_line_id` (`v_financial_departmental_margin` exclude `Overall`/`Corporate Overhead`) — M — **Selesai**. Fix tambahan: `property_id` yang terlewat di 3 lookup view Fase 1-2 (`v_lookup_fnb_inventory`, `v_lookup_fnb_transactions`, `v_lookup_housekeeping_log`) ditambahkan via join ke `fnb_outlets`/`rooms`.

**✅ Checkpoint 3** — commit + log.

### Fase 4 — 4 Domain Granular
8. `views_properties_ref.sql` (`v_properties_ref`) + `views_employees_directory.sql` (`v_employees_directory`) + apply — S
9. `views_guests.sql` (`guests_contact_view`, `guests_profile_view`, `last_active_property_id`) + apply + **uji eksplisit KK2**: `guests_profile_view` tidak punya kolom `email`/`phone`, `guests_contact_view` tidak punya kolom `loyalty_tier`/`nationality` — M

**✅ Checkpoint 4** — commit + log.

### Fase 5 — Finalisasi
10. Uji KK3: `SELECT property_id, count(*) FROM <view> WHERE property_id IN ('P01','P02') GROUP BY property_id` pada beberapa view representatif, buktikan hasil berbeda benar per properti. Tulis `docs/09-serving-ai-chatbot/view-query-pattern-chatbot.md` (inventaris seluruh view, pola sama `view-query-pattern-analyst.md`). Verifikasi ulang KK1-KK3, tulis `report.md`. — M

**✅ Checkpoint 5 (final)** — commit; tanya user sebelum push.
