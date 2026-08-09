# Milestone 3.3: Index dan Optimasi Performa untuk Pola Akses Analyst — Logs

## 2026-08-09 — Mulai kerja

- Plan disetujui via Plan Mode (setelah revisi task breakdown dari template 9/5 M3.1-M3.2 menjadi 8/8 yang diturunkan ulang dari bentuk kerja M3.3 sebenarnya — 6 domain independen menulis ke 2 file bersama, bukan file terpisah per domain seperti M3.2).
- `decisions.md` ditulis: 1 keputusan AskUserQuestion (cakupan mart_aggregated + mart_cleaned) + 7 keputusan teknis.
- Folder dibuat: `milestones/3.3-index-optimasi-performa-analyst/`.
- Mulai Task 1 (Fase 0 — bangun mekanisme reindex kedua schema).

## 2026-08-09 — Checkpoint 1

- `scripts/reverse_etl/{mart_cleaned_indexes.py,reindex_analyze.py}` dibuat (clone persis pola `reverse_etl_mart_aggregated`, target schema `mart_cleaned`, 23 tabel dari `serving_tables.py`).
- `scripts/reverse_etl_mart_aggregated/example_indexes.py` dihapus, diganti `mart_aggregated_indexes.py` (docstring PROVISIONAL dihapus, sekarang menyatakan diri sebagai desain M3.3). `reindex_analyze.py` (mart_aggregated) diupdate importnya.
- Step baru ditambahkan ke `.github/workflows/reverse-etl-mart-cleaned.yml`: "Milestone 3.3 -- REINDEX/ANALYZE pasca-swap" setelah `sync.py --all`, mengikuti persis pola step 2 di `reverse-etl-mart-aggregated.yml`.
- Verifikasi: `reindex_analyze.py --all` dijalankan langsung terhadap serving PostgreSQL sungguhan untuk kedua schema — 76 tabel `mart_aggregated` dan 23 tabel `mart_cleaned` semuanya sukses (no-op reindex karena daftar index masih kosong, `ANALYZE` tetap jalan). Tidak ada error privilege pada `reverse_etl_writer`/`reverse_etl_mart_aggregated_writer` untuk `CREATE INDEX`/`REINDEX`/`ANALYZE`.

## 2026-08-09 — Checkpoint 2: Index Revenue

- Row count live sisa tabel Revenue: `fact_revenue_channel_daily` 26.697, `fact_revenue_gop_impact_monthly` 180 (dikeluarkan — terlalu kecil, Keputusan #2), `fact_revenue_pricing_deviation` 5.490, `fact_revenue_loyalty_daily` 21.413, `fact_revenue_nationality_daily` 10.970, `fact_revenue_property_daily` 5.485.
- **Baseline (sebelum index)**, query "laporan bulanan P01" (filter `property_id`+`period_date` 1 bulan): `fact_revenue_room_type_daily` Seq Scan 88.2ms (19.622/19.746 baris dibuang filter); `fact_revenue_channel_daily` Seq Scan 130.7ms; `fact_revenue_los_daily` Seq Scan 276.6ms; `mart_cleaned.bookings` (investigasi cancellation) Parallel Seq Scan 82.1ms; `mart_cleaned.pricing_history` Seq Scan 2.7ms (sudah cepat, tabel kecil).
- Index dipasang: 7 tabel `mart_aggregated` (`fact_revenue_room_type_daily`, `channel_daily`, `los_daily`, `property_daily`, `pricing_deviation`, `loyalty_daily`, `nationality_daily`, semua composite `(property_id, period_date)`) + 2 tabel `mart_cleaned` (`bookings` → `(property_id, check_in_date)`, `pricing_history` → `(property_id, date)`).
- **Verifikasi setelah index**: seluruh 9 query `EXPLAIN ANALYZE` beralih ke Index Scan/Bitmap Index Scan (tidak ada Seq Scan tersisa). Waktu eksekusi: room_type_daily 88.2ms→2.2ms, channel_daily 130.7ms→1.8ms, los_daily 276.6ms→0.48ms, bookings 82.1ms→3.3ms. `pg_stat_user_indexes.idx_scan` dikonfirmasi ≥1 untuk seluruh 9 index — KK2 terbukti dua arah (query plan + runtime usage), bukan cuma index ada di skema.

**✅ Checkpoint 2 selesai.**

## 2026-08-09 — Checkpoint 3: Index F&B

- Row count live sisa tabel F&B: `fact_fnb_outlet_daily` 18.649, `fact_fnb_category_daily` 53.121, `fact_fnb_customer_type_daily` 31.812, `fact_fnb_waste_daily` 45.889, `fact_fnb_inventory_status` 17 (dikeluarkan — snapshot state terkini, terlalu kecil), `fact_fnb_ingredient_price_daily` 32.910.
- **Baseline (sebelum index)**, filter `outlet_id`+`period_date` 1 bulan (`OUT001`): `fact_fnb_outlet_daily` Seq Scan 111.1ms; `fact_fnb_menu_item_daily` Parallel Seq Scan 793.2ms (144.579 baris dibuang filter); `fact_fnb_hourly` Parallel Seq Scan 299.7ms; `mart_cleaned.fnb_transactions` (902rb baris, tabel terbesar project) Parallel Seq Scan **1004.4ms** (449.440 baris dibuang filter per worker) — paling lambat dari seluruh domain, bukti kuat kenapa `mart_cleaned` wajib masuk cakupan M3.3.
- Index dipasang: 7 tabel `mart_aggregated` (composite `(outlet_id, period_date)`, kecuali `fact_fnb_ingredient_price_daily` pakai `(ingredient_id, period_date)` — tabel ini tidak terikat 1 outlet) + `mart_cleaned.fnb_transactions` → `(outlet_id, transaction_datetime)`.
- **Verifikasi setelah index**: seluruh 8 query beralih ke Index/Bitmap Index Scan. Waktu eksekusi: outlet_daily 111.1ms→3.0ms, menu_item_daily 793.2ms→7.6ms, hourly 299.7ms→9.6ms. `fnb_transactions` sempat terukur 1473.5ms pada run pertama pasca-`REINDEX` (anomali cache-dingin, buffer belum warm) — diverifikasi ulang 3x run berikutnya: 64.7ms → 5.6ms → 4.9ms, stabil cepat begitu cache warm. Dicatat jujur sebagai karakteristik operasional (baseline pertama pasca-swap/reindex bisa lebih lambat sampai cache warm), bukan disembunyikan. `pg_stat_user_indexes.idx_scan` ≥1 untuk seluruh 8 index (fnb_transactions idx_scan=5 dari beberapa kali run verifikasi).

**✅ Checkpoint 3 selesai.**

## 2026-08-09 — Checkpoint 4: Index Facility/Ops

- Row count live sisa tabel: `fact_facility_room_status_daily` 549 (dikeluarkan — snapshot state terkini), `fact_housekeeping_room_type_daily` 19.746, `fact_housekeeping_property_daily` 5.485, `fact_maintenance_cost_daily` 10.317, `fact_maintenance_room_recurrence_yearly` 2.115, `fact_maintenance_property_benchmark_yearly` 20 (dikeluarkan — terlalu kecil).
- **Baseline (sebelum index)**: `fact_housekeeping_room_type_daily` Seq Scan 74.5ms; `fact_housekeeping_property_daily` Seq Scan 17.6ms; `fact_housekeeping_staff_daily` (164.707 baris) Parallel Seq Scan 348.7ms; `fact_maintenance_ticket_daily` Seq Scan 50.3ms; `fact_maintenance_cost_daily` Seq Scan 21.4ms; `fact_maintenance_technician_daily` Seq Scan 36.4ms; `fact_maintenance_room_recurrence_yearly` (2.115 baris) Seq Scan 4.2ms (sudah relatif cepat, tetap diuji index sesuai Keputusan #2); `mart_cleaned.maintenance_tickets` Seq Scan 84.8ms.
- Index dipasang: 7 tabel `mart_aggregated` (`property_id`/`staff_id`/`assigned_staff_id`/`room_id` + `period_date`/`year`) + `mart_cleaned.maintenance_tickets` → `(property_id, reported_date)`.
- **Verifikasi setelah index**: seluruh 8 query beralih ke Index Scan, termasuk `fact_maintenance_room_recurrence_yearly` yang tadinya sudah cepat (4.2ms→2.6ms, tetap dipertahankan karena terbukti terpakai planner, bukan diasumsikan). Waktu eksekusi: housekeeping_room_type_daily 74.5ms→0.96ms, housekeeping_staff_daily 348.7ms→3.3ms, maintenance_ticket_daily 50.3ms→1.7ms, maintenance_tickets (mart_cleaned) 84.8ms→1.6ms. `pg_stat_user_indexes.idx_scan` ≥1 untuk seluruh 8 index.

**✅ Checkpoint 4 selesai.**

## 2026-08-09 — Checkpoint 5: Index Spa & Event

- Row count live sisa tabel: `fact_spa_daily` 5.485, `fact_spa_customer_type_daily` 10.900, `fact_event_property_daily` 1.177, `fact_event_type_daily` 1.300.
- **Baseline (sebelum index)**: `fact_spa_daily` 17.5ms; `fact_spa_customer_type_daily` 16.1ms; `fact_spa_service_daily` 115.9ms (41.718 baris); `fact_event_venue_daily` 8.1ms; `fact_event_property_daily` 3.8ms; `fact_event_type_daily` 1.5ms; `mart_cleaned.event_bookings` 14.6ms.
- Index dipasang: 6 tabel `mart_aggregated` (`property_id`+`period_date`, kecuali `fact_event_venue_daily` pakai `venue_id`+`period_date`) + `mart_cleaned.event_bookings` → `(property_id, event_date)`.
- **Verifikasi setelah index**: seluruh 7 query beralih ke Index Scan, termasuk 2 tabel terkecil domain ini (`fact_event_property_daily` 1.177 baris, `fact_event_type_daily` 1.300 baris) yang tetap terbukti terpakai planner — dipertahankan sesuai bukti empiris, bukan dikeluarkan berdasar ukuran semata. Waktu eksekusi: spa_service_daily 115.9ms→1.2ms, spa_daily 17.5ms→1.1ms, event_bookings 14.6ms→0.13ms. `pg_stat_user_indexes.idx_scan` ≥1 untuk seluruh 7 index.

**✅ Checkpoint 5 selesai.**

## 2026-08-09 — Checkpoint 6: Index HR

- Row count live sisa tabel: `fact_hr_turnover_snapshot` 43, `fact_hr_headcount_status_daily` 89, `fact_hr_performance_department_semester` 258, `fact_hr_performance_by_status_semester` 90 — keempatnya dikeluarkan tanpa perlu uji empiris, jauh di bawah tabel terkecil manapun yang pernah terbukti diuntungkan index sejauh ini (Keputusan #2).
- **Baseline (sebelum index)**: `fact_hr_attendance_daily` 183.9ms; `fact_hr_employee_monthly` 102.8ms; `fact_hr_employee_performance_semester` 12.9ms; `fact_hr_watchlist_monthly` 66.8ms; `dim_employee` (filter `property_id`) 1.7ms; `mart_cleaned.staff_shifts` (610rb baris) **1702.8ms** — baseline terlambat di seluruh milestone ini, lebih lambat dari `fnb_transactions`; `mart_cleaned.employee_performance` 16.6ms.
- Index dipasang: 5 tabel `mart_aggregated` (`fact_hr_attendance_daily` composite `(property_id, department_id, period_date)` — 2 filter wajib sekaligus, satu-satunya domain begitu; `fact_hr_employee_monthly`/`fact_hr_watchlist_monthly` `(employee_id, period_date)`; `fact_hr_employee_performance_semester` `(employee_id, review_period)`; `dim_employee` `(property_id)` — diuji empiris meski tabel kecil karena 3 view besar join lewat situ) + 2 tabel `mart_cleaned` (`staff_shifts` `(employee_id, date)`, `employee_performance` `(employee_id, review_period)`).
- **Verifikasi setelah index**: seluruh 7 query beralih ke Index Scan, termasuk `dim_employee` yang cuma 755 baris — terbukti terpakai planner meski tabelnya kecil. Waktu eksekusi: `staff_shifts` 1702.8ms→2.5ms (680x lebih cepat, penurunan terbesar di seluruh milestone), `fact_hr_attendance_daily` 183.9ms→7.4ms, `fact_hr_employee_monthly` 102.8ms→3.9ms. `pg_stat_user_indexes.idx_scan` ≥1 untuk seluruh 7 index.

**✅ Checkpoint 6 selesai.**

## 2026-08-09 — Checkpoint 7: Index Corporate/Financial

- Row count live sisa tabel: mayoritas kecil (`fact_financial_overall_monthly` 216, `fact_financial_service_charge_monthly` 216, `fact_financial_labor_cost_monthly` 216, `fact_payroll_access_level_monthly` 468, `fact_financial_business_line_group_monthly` 180, `fact_financial_property_benchmark_monthly` 216) — hanya `fact_financial_revenue_runrate_daily` (5.485) dan `fact_payroll_department_monthly` (1.548) yang lebih besar. `mart_cleaned.payroll` 23.383.
- **Temuan empiris penting yang mengoreksi asumsi awal**: spot-check index di `fact_financial_business_line_group_monthly` (180 baris — seukuran `fact_revenue_gop_impact_monthly` yang dikeluarkan di Checkpoint 2) ternyata **tetap terpakai planner** (Index Scan, 1.4ms) begitu filter cukup selektif (2 kolom: `business_line_id`+rentang tanggal). Ini mengoreksi asumsi "tabel kecil pasti seq-scan" dari Keputusan #2 — selektivitas filter, bukan cuma ukuran tabel mentah, yang menentukan pilihan planner. Seluruh 9 tabel `mart_aggregated` + 2 tabel `mart_cleaned` domain ini diuji, bukan diasumsikan dari ukurannya.
- **Baseline (sebelum index)**: mayoritas tabel kecil sudah sub-milidetik (0.05-0.5ms) karena baris sedikit; `fact_financial_business_line_monthly` 5.3ms; `mart_cleaned.financial_summary` 6.9ms; `mart_cleaned.payroll` **145.2ms** (23rb baris, satu-satunya yang genuinely lambat di domain ini).
- Index dipasang: 9 tabel `mart_aggregated` (`property_id`/`business_line_id` + `period_date`) + 2 tabel `mart_cleaned` (`financial_summary` → `(property_id, period)`, `payroll` → `(employee_id, period)`).
- **Verifikasi setelah index**: seluruh 11 query beralih ke Index Scan. **Catatan jujur**: untuk tabel terkecil (`fact_financial_overall_monthly`, `fact_financial_labor_cost_monthly`, dll), waktu eksekusi sebenarnya sedikit naik dibanding baseline (0.05ms→~1.3ms) — index dipakai planner (memenuhi KK2 literal) tapi tidak memberi percepatan nyata pada tabel seukuran itu (overhead traversal B-tree vs seq scan trivial pada <500 baris); tetap dalam batas wajar analisis interaktif (KK1, keduanya <3ms). `mart_cleaned.payroll` 145.2ms→2.4ms adalah perbaikan nyata di domain ini. `pg_stat_user_indexes.idx_scan` ≥1 untuk seluruh 11 index.
- **Validasi business rule kritis M3.1/M3.2**: `SELECT DISTINCT business_line_name FROM v_financial_departmental_margin` tetap tepat 3 nilai (`F&B`, `Room`, `Spa&Event`) setelah index dipasang — `EXPLAIN ANALYZE` view mengonfirmasi index baru (`idx_fact_financial_business_line_monthly_property_period`) terpakai DAN filter `line_name <> ALL ('{Overall,"Corporate Overhead"}')` tetap diterapkan di `dim_business_line` — index cuma memengaruhi kecepatan, tidak mengubah hasil filter.

**✅ Checkpoint 7 selesai.**

## 2026-08-09 — Checkpoint 8 (final) — Tutup milestone

- Verifikasi total: `pg_indexes` mengonfirmasi 41 index `idx_*` di `mart_aggregated` + 9 di `mart_cleaned` = 50 index. `pg_stat_user_indexes` dicek untuk seluruh index milik project (bukan sistem Supabase `auth`/`storage`) — tidak ada satu pun dengan `idx_scan=0`.
- `docs/08-serving-data-analyst/index-baseline-analyst.md` ditulis — baseline lengkap per tabel, ringkasan verifikasi KK1/KK2, dan koreksi asumsi Keputusan #2 (selektivitas filter > ukuran tabel mentah).
- `report.md` ditulis, mendokumentasikan koreksi Keputusan #2 sebagai deviation eksplisit dan Known Gap (tabel kecil domain awal belum diuji ulang dengan pemahaman baru).
- Milestone ditutup. Handoff eksplisit: mekanisme reindex sudah otomatis (tidak perlu intervensi manual), baseline query jadi basis M3.4, dan pengingat index perlu direvisit kalau skema `mart_aggregated`/`mart_cleaned` berubah lewat M5.6.
