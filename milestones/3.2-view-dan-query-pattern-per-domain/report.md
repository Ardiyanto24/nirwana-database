# Milestone 3.2: View dan Query Pattern per Domain — Report

**Status:** Completed
**Date completed:** 2026-08-09

## Kriteria Keberhasilan — Hasil

- [x] **KK1 — Untuk tiap domain, hasil query dari view yang dibangun cocok dengan hasil perhitungan manual/sampel pada beberapa metrik kunci yang representatif.** Terpenuhi untuk seluruh 6 domain, diverifikasi langsung terhadap serving PostgreSQL sungguhan (bukan asumsi):
  - Revenue: `v_revenue_room_type_daily` — row count identik fact vs view (19.746), sampel `occupancy_rate`/`adr`/`revpar` cocok persis.
  - F&B: `v_fnb_menu_item_daily` — row count identik (289.938), sampel `food_cost_ratio_actual`/`food_cost_ratio_target` cocok persis.
  - Facility/Ops: `v_maintenance_ticket_daily` — row count identik (12.840), breach logic teruji (medium/48 jam: avg 120 jam → breach, avg 24 jam → tidak).
  - Spa & Event: `v_event_venue_daily` — row count identik (1.333), sampel `utilization_rate` cocok persis.
  - HR: `v_hr_watchlist_monthly` — row count identik (24.036), `in_watchlist=true` count identik (1.122, cocok dengan angka M5.6).
  - Corporate/Financial: `v_financial_departmental_margin` sampel `margin_pct` (0.72) dan `v_financial_gop_overhead` sampel `gop`/`gop_margin_pct`/`undistributed_expense_total` cocok persis hitung manual dan fact table sumber.
- [x] **KK2 — Percobaan query tanpa filter eksplisit tetap menghasilkan output yang benar karena filter sudah tertanam di view.** Terpenuhi, diuji paling ketat di domain paling berisiko (Corporate/Financial): `SELECT DISTINCT business_line_name FROM v_financial_departmental_margin` tanpa `WHERE` tambahan apa pun menghasilkan tepat 3 nilai (`F&B`, `Room`, `Spa&Event`) — `Overall`/`Corporate Overhead` terbukti tidak pernah muncul, row count (540) cocok persis dengan filter manual yang sama diterapkan ke fact table. Business rule SLA `pending_count`-vs-breach (Facility) juga tertanam permanen dan teruji.

## Deliverables

- `docs/08-serving-data-analyst/view-query-pattern-analyst.md` — inventaris 48 view (nama, fact table sumber, dimension di-join, business rule tertanam).
- `scripts/data_analyst_views/{schema.sql, connections.py, apply_views.py, views_revenue.sql, views_fnb.sql, views_facility.sql, views_spa_event.sql, views_hr.sql, views_corporate_financial.sql}`.
- Schema `analyst_views` di serving PostgreSQL, 48 view aktif (Revenue 8 + F&B 8 + Facility 9 + Spa&Event 6 + HR 8 + Corporate/Financial 9).
- `milestones/3.2-view-dan-query-pattern-per-domain/{decisions,logs}.md`.

## Business Rule Kritis yang Ditanam Permanen (bukti implementasi)

1. **`v_financial_departmental_margin`**: `WHERE bl.line_name NOT IN ('Overall','Corporate Overhead')` — diverifikasi KK2 di atas.
2. **`v_maintenance_ticket_daily`**: `pending_count` kolom terpisah, `sla_threshold_hours`/`avg_exceeds_sla_threshold` dihitung dari threshold resmi (`Metadata.md`, bukan asumsi).
3. **Payroll eksklusif Corporate/Financial**: `views_hr.sql` tidak menyentuh `fact_payroll_*`/`fact_financial_service_charge_monthly`/`fact_financial_labor_cost_monthly`/`fact_payroll_access_level_monthly` sama sekali — bukan cuma tidak digunakan, memang tidak ada view-nya di domain HR.
4. **Basket analysis & repeat-client-event/cross-sell**: sengaja tidak ada view — dicatat eksplisit di dokumen inventaris supaya tidak keliru diasumsikan tersedia sebagai metrik agregat.

## Deviations from decisions.md

Tidak ada deviasi dari 1 keputusan AskUserQuestion (schema `analyst_views`) maupun 6 keputusan teknis. Struktur file, threshold SLA, dan pola koneksi semuanya diikuti persis.

## Known Gaps / Follow-ups

- **`mart_aggregated.dim_employee` tidak punya kolom `property_id`** (ditemukan saat implementasi, tidak tercatat di M3.1) — padahal `employees.property_id` ada di produksi. Akibatnya `v_hr_employee_monthly`, `v_hr_employee_performance_semester`, `v_hr_watchlist_monthly` tidak bisa difilter/join ke properti. Didokumentasikan di `view-query-pattern-analyst.md`. **Perbaikan di luar cakupan M3.2** — sudah diajukan lewat mekanisme resmi Milestone 5.6, lihat `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` §"Kolom `property_id` hilang di `dim_employee`" (status: Diajukan, menunggu evaluasi pemilik `mart_aggregated`).
- **`fact_revenue_pace_booking_snapshot` tetap tidak punya view** — status implementasi append-only vs BigQuery Sandbox belum final (dibawa dari M3.1, belum berubah).
- **GRANT/kredensial belum ada** — seluruh 48 view saat ini hanya bisa diakses lewat koneksi admin `SERVING_DB_URL`. Isolasi akses per peran (termasuk larangan Property/GM Analyst ke 9 view Corporate/Financial) adalah cakupan eksplisit Milestone 3.5, bukan M3.2 — schema `analyst_views` terpisah sengaja disiapkan untuk memudahkan GRANT itu nanti.

## Handoff Notes

- **Milestone 3.3 (Index):** kolom filter di tiap view (`property_id`, `department_id`, `business_line_id`, dst — sudah terdaftar per view di `view-query-pattern-analyst.md`) adalah kandidat index/composite index langsung terhadap tabel dasar (`mart_aggregated.fact_*`) — index di tabel dasar akan terpakai lewat view karena `CREATE OR REPLACE VIEW` bukan materialized view.
- **Milestone 3.4 (API):** 48 view di `analyst_views` adalah basis langsung untuk endpoint agregat per domain — nama view sudah konsisten `v_<domain>_<grain>` sehingga mapping ke endpoint straightforward. Endpoint row-level tetap query `mart_cleaned` langsung (tidak lewat `analyst_views`), sesuai pemisahan M3.1.
- **Milestone 3.5 (Kredensial):** GRANT SELECT per view per kelompok peran memakai daftar di `view-query-pattern-analyst.md` — HR Analyst dapat 8 view HR (tanpa payroll), Property/GM Analyst dapat 39 view domain #1-5 (dengan filter `property_id` di level query/API, bukan GRANT terpisah per properti), Corporate/Financial Analyst satu-satunya yang dapat akses ke 9 view Corporate/Financial termasuk `v_financial_business_line_group_monthly`.
- **Jika Milestone 3.4 butuh filter properti untuk 3 view HR grain-karyawan**, gap `dim_employee.property_id` di atas harus diselesaikan dulu lewat M5.6 sebelum endpoint tersebut bisa dibangun benar.
