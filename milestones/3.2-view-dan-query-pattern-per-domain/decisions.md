# Milestone 3.2: View dan Query Pattern per Domain — Decisions

**Sumber:** `docs/03-implementation-plans/04-serving-data-analyst.md`, baris 66-81.
**Prasyarat:** Milestone 3.1 (`pemetaan-pola-akses-analyst.md`, Completed) — pemetaan peran → tabel → filter wajib → business rule kritis sudah tersedia sebagai acuan langsung.
**Status:** In Progress
**Date started:** 2026-08-09

## Lingkup Sumber / Contract

- **Lingkup:** Membangun view/query pattern di atas `mart_aggregated` dan `mart_cleaned` (PostgreSQL) sesuai hasil pemetaan Milestone 3.1 — satu kelompok view per pola domain, dengan filter wajib sudah tertanam.
- **Output:** View/query pattern per domain, mencakup kebutuhan agregat maupun row-level; validasi business rule kritis tertanam.
- **Kriteria Keberhasilan:**
  1. Untuk tiap domain, hasil query dari view yang dibangun cocok dengan hasil perhitungan manual/sampel pada beberapa metrik kunci yang representatif.
  2. Percobaan query tanpa filter eksplisit (mis. lupa filter properti) tetap menghasilkan output yang benar karena filter sudah tertanam di view, bukan bergantung pada pemakai selalu ingat menambahkannya.

## Temuan Eksplorasi (sebelum breakdown)

- Serving PostgreSQL: `mart_aggregated` schema — 1:1 nama tabel dengan BigQuery (`fact_*`/`dim_*` bare), 76 tabel (27 dim + 49 fact, minus `fact_ml_occupancy_forecast_property_room_type` yang sengaja belum di-sync M5.5). `mart_cleaned` schema — prefix `mart_cleaned__` di BigQuery di-strip jadi nama tabel produksi asli di Postgres (mis. `mart_cleaned.bookings`).
- Tidak ada role read-only khusus Data Analyst di serving Postgres (dikonfirmasi juga di `decisions.md` M3.1) — hanya `SERVING_DB_URL` (admin) dan writer role yang scoped ke masing-masing 1 schema. M3.2 pakai admin karena murni authoring DDL.
- `warehouse/profiles.yml` cuma target BigQuery — dbt tidak pernah menyentuh serving PostgreSQL. Satu-satunya preseden view PostgreSQL di project ini adalah `scripts/monitoring/views.sql` (`monitoring.current_status`, M1.2 Task 8) dan `scripts/monitoring/db.py`/`apply_schema.py` untuk pola runner DDL.
- SLA breach threshold per `priority` (dibutuhkan untuk business rule Facility) dikonfirmasi eksplisit di `docs/01-architecture/Metadata.md` baris 706-715: `critical`=8 jam, `high`=24 jam, `medium`=48 jam, `low`=72 jam — dokumen itu sendiri menandai "Ini use case 3.1".

## Keputusan (via AskUserQuestion, dikonfirmasi user)

### 1. Skema penempatan view: `analyst_views` (schema baru)

**Keputusan:** View ditaruh di schema baru `analyst_views` di serving PostgreSQL project, terpisah dari `mart_aggregated`/`mart_cleaned`.

**Kenapa:** Memudahkan Milestone 3.5 (isolasi kredensial) memberi GRANT SELECT per view/per peran tanpa menyentuh GRANT di schema mart mentah (tempat `reverse_etl_writer`/`reverse_etl_mart_aggregated_writer` beroperasi). Konsisten dengan alasan dokumen sumber M3.2 dipisah dari M3.4 (API): "lapisan logis antara mart mentah dan API".

**Ditolak:** Menaruh view langsung di schema `mart_aggregated`/`mart_cleaned` — lebih sederhana tapi mencampur view turunan dengan tabel mart mentah, dan M3.5 harus grant per-tabel di schema yang sama dengan writer role reverse ETL beroperasi (risiko scope creep grant).

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 2. Cakupan view: 1 view per fact table relevan

Mengikuti grain presisi yang sudah didesain M5.2/M5.3 per fact table dan struktur dokumen M3.1 sendiri (1 baris pemetaan = daftar tabel per peran) — tidak ada desain alternatif view gabungan lintas-tabel yang bersaing. **Dikecualikan:** `fact_revenue_pace_booking_snapshot` (status implementasi belum final, ditandai Known Gap M3.1).

### 3. Dimension resolved ke nama, bukan surrogate ID

Tiap view `LEFT JOIN` ke dimension table terkait, mengekspos kolom `*_name`. Praktik standar view analitik, tidak ada alternatif desain yang bersaing.

### 4. Deployment: plain SQL DDL + Python runner (bukan dbt)

`warehouse/profiles.yml` cuma target BigQuery — dbt tidak bisa dipakai untuk serving PostgreSQL. Pola direplikasi dari `scripts/monitoring/views.sql` + `apply_schema.py`: `CREATE OR REPLACE VIEW` per file `.sql`, runner psycopg2 (`autocommit=False`, commit/rollback eksplisit).

### 5. Koneksi: `SERVING_DB_URL` (admin), copy pola `connections.py`

`scripts/data_analyst_views/connections.py` adalah copy pola `get_serving_connection` dari `scripts/reverse_etl/connections.py` (konvensi copy-bukan-import lintas `scripts/*` subfolder sejak M2.1, menghindari collision `sys.path`). Admin dipakai karena M3.2 murni authoring/apply DDL sekali jalan, bukan operasi harian — GRANT scoped-role menyusul di M3.5.

### 6. SLA breach logic Facility

`CASE WHEN resolved_date IS NULL THEN 'pending' WHEN (resolved_date - reported_date) > interval per priority THEN 'breach' ELSE 'ok' END`. Threshold: `critical`=8 jam, `high`=24 jam, `medium`=48 jam, `low`=72 jam (`Metadata.md` baris 706-715, sumber resmi bukan asumsi).

### 7. Struktur file: 1 file SQL per domain

`views_revenue.sql`, `views_fnb.sql`, `views_facility.sql`, `views_spa_event.sql`, `views_hr.sql`, `views_corporate_financial.sql` di `scripts/data_analyst_views/` — selaras 6 checkpoint per-domain yang sudah dipakai M3.1. `apply_views.py` menerima daftar file sebagai argumen.

## Task Breakdown

9 task, 5 fase, 5 checkpoint (commit tiap checkpoint; checkpoint final commit + tanya user dulu sebelum push, ikuti pola M3.1).

### Fase 0 — Fondasi
1. Setup `scripts/data_analyst_views/{schema.sql,connections.py,apply_views.py}`. Uji konektivitas `SERVING_DB_URL`, jalankan `schema.sql` — Acceptance: schema `analyst_views` ada — Verify: `information_schema.schemata` — S

**✅ Checkpoint 1** — commit + log.

### Fase 1 — Revenue + F&B
2. `views_revenue.sql` (7 view) + apply + verifikasi metrik representatif vs hitung manual — M
3. `views_fnb.sql` (8 view) + apply + verifikasi — M

**✅ Checkpoint 2** — commit + log.

### Fase 2 — Facility/Ops + Spa & Event
4. `views_facility.sql` (9 view, termasuk `sla_status` breach/ok/pending) + apply + verifikasi — M
5. `views_spa_event.sql` (6 view) + apply + verifikasi — M

**✅ Checkpoint 3** — commit + log.

### Fase 3 — HR + Corporate/Financial
6. `views_hr.sql` (8 view, tanpa payroll) + apply + verifikasi — M
7. `views_corporate_financial.sql` (9 view, filter `business_line_id` tertanam di `v_financial_departmental_margin`) + apply + verifikasi KK1 dan KK2 sekaligus (query tanpa filter tambahan tidak pernah menampilkan `Overall`) — M

**✅ Checkpoint 4** — commit + log.

### Fase 4 — Property/GM Analyst + Finalisasi
8. Validasi Property/GM Analyst terlayani dari view domain #1-5 tanpa view baru; dokumentasikan larangan akses view Corporate — S
9. Tulis `docs/08-serving-data-analyst/view-query-pattern-analyst.md` (inventaris seluruh view), verifikasi ulang KK1+KK2 lintas domain, tulis `report.md` — M

**✅ Checkpoint 5 (final)** — commit; tanya user sebelum push.
