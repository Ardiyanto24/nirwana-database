# Milestone 3.2: View dan Query Pattern per Domain — Logs

## 2026-08-09 — Mulai kerja

- Plan disetujui via Plan Mode. `decisions.md` ditulis, mengunci 1 keputusan via AskUserQuestion (schema `analyst_views`) + 6 keputusan teknis (cakupan view, dimension resolved ke nama, deployment plain SQL, koneksi admin, SLA threshold, struktur file per domain).
- Folder dibuat: `milestones/3.2-view-dan-query-pattern-per-domain/`, `scripts/data_analyst_views/`.
- Dikonfirmasi `SERVING_DB_URL` tersedia di `.env`.
- Mulai Task 1 (Fase 0 — setup infrastruktur view).

## 2026-08-09 — Checkpoint 1

- `scripts/data_analyst_views/{connections.py,schema.sql,apply_views.py}` dibuat, meniru pola `scripts/monitoring/db.py`+`apply_schema.py` (runner psycopg2, autocommit=False, commit/rollback eksplisit) dan `get_serving_connection` dari `scripts/reverse_etl/connections.py`.
- `apply_views.py schema.sql` dijalankan sukses terhadap `SERVING_DB_URL` sungguhan.
- Verifikasi: `information_schema.schemata` mengonfirmasi `analyst_views` ada berdampingan dengan `mart_aggregated`/`mart_cleaned`.

## 2026-08-09 — Checkpoint 2

- `views_revenue.sql` (8 view: room_type_daily, channel_daily, los_daily, property_daily, gop_impact_monthly, pricing_deviation, loyalty_daily, nationality_daily) dan `views_fnb.sql` (8 view: outlet_daily, category_daily, hourly, customer_type_daily, menu_item_daily, waste_daily, inventory_status, ingredient_price_daily) ditulis dan di-apply ke `analyst_views` sungguhan.
- Kolom fact/dim diambil langsung dari `information_schema.columns` live (bukan asumsi dari dokumen desain) untuk memastikan akurasi.
- Verifikasi KK1: (a) `v_revenue_room_type_daily` — row count identik fact vs view (19.746), sampel `occupancy_rate`/`adr`/`revpar` cocok persis, dimensi ter-resolve benar (P01 → "Nirwana Beach Resort Bali", room_type_id 1 → "Deluxe"). (b) `v_fnb_menu_item_daily` — row count identik (289.938), sampel `food_cost_ratio_actual`/`food_cost_ratio_target` cocok persis, outlet ter-resolve ke property lewat `dim_outlet` (OUT001 → P01/"Sunset Restaurant").

## 2026-08-09 — Checkpoint 3

- `views_facility.sql` (9 view) dan `views_spa_event.sql` (6 view) ditulis dan di-apply.
- `v_maintenance_ticket_daily` mengimplementasikan business rule kritis #5/#6 M3.1: `pending_count` tetap kolom terpisah, `sla_threshold_hours` (CASE per `priority_name`: critical=8, high=24, medium=48, low=72, sesuai `Metadata.md`) dan `avg_exceeds_sla_threshold` (boolean turunan) ditanam permanen di view.
- Verifikasi: (a) row count `fact_maintenance_ticket_daily` vs view identik (12.840); breach logic diuji manual — priority medium (threshold 48 jam) dengan `avg_sla_duration_hours=120` menghasilkan `avg_exceeds_sla_threshold=True`, sedangkan `avg_sla_duration_hours=24` menghasilkan `False`; threshold mapping 4 priority dikonfirmasi persis (8/24/48/72). (b) `v_event_venue_daily` — row count identik (1.333), sampel `utilization_rate` cocok persis, venue ter-resolve ke property (VN001 → P01/"Nirwana Grand Ballroom").

## 2026-08-09 — Checkpoint 4

- **Temuan gap baru** (tidak tercatat di M3.1): `mart_aggregated.dim_employee` cuma punya `employee_id`, `full_name`, `department_id`, `access_level_id` — **tidak ada `property_id`**, padahal `employees.property_id` ada di produksi (`Metadata.md` baris 134). Akibatnya `fact_hr_employee_monthly`, `fact_hr_employee_performance_semester`, `fact_hr_watchlist_monthly` (grain karyawan) tidak bisa difilter/join ke properti lewat `mart_aggregated`. Didokumentasikan eksplisit sebagai komentar di `views_hr.sql` dan akan dicatat sebagai Known Gap di `report.md` — perbaikan (nambah kolom ke `dim_employee`) di luar cakupan M3.2, perlu lewat mekanisme pengajuan M5.6 kalau memang dibutuhkan.
- `views_hr.sql` (8 view, tanpa payroll — business rule #2 M3.1) dan `views_corporate_financial.sql` (9 view) ditulis dan di-apply.
- `v_financial_departmental_margin` mengimplementasikan business rule kritis #1 M3.1: `WHERE bl.line_name NOT IN ('Overall','Corporate Overhead')` ditanam permanen di definisi view.
- Verifikasi HR: `v_hr_watchlist_monthly` row count identik (24.036), `in_watchlist=true` count identik (1.122) — cocok persis dengan angka yang didokumentasikan Milestone 5.6.
- **Verifikasi KK1+KK2 Corporate/Financial (domain paling berisiko)**: KK2 — `SELECT DISTINCT business_line_name FROM v_financial_departmental_margin` menghasilkan tepat 3 nilai (`F&B`, `Room`, `Spa&Event`), `Overall`/`Corporate Overhead` terbukti tidak pernah muncul tanpa filter eksplisit apa pun; row count (540) cocok persis dengan filter manual yang sama diterapkan langsung ke fact table. KK1 — sampel `margin_pct` (0.72), `gop`/`gop_margin_pct`/`undistributed_expense_total` di `v_financial_gop_overhead` cocok persis hitung manual dan fact table sumber.

## 2026-08-09 — Checkpoint 5 (final) — Tutup milestone

- Verifikasi jumlah view: `information_schema.views` schema `analyst_views` = 48 (Revenue 8 + F&B 8 + Facility 9 + Spa&Event 6 + HR 8 + Corporate/Financial 9), cocok dengan target.
- Property/GM Analyst dikonfirmasi terlayani dari 39 view domain #1-5 tanpa view baru — didokumentasikan di `docs/08-serving-data-analyst/view-query-pattern-analyst.md`, termasuk larangan eksplisit akses 9 view Corporate/Financial (penegakan teknis GRANT menyusul M3.5).
- `docs/08-serving-data-analyst/view-query-pattern-analyst.md` ditulis sebagai Output resmi (inventaris 48 view).
- KK1 dan KK2 diverifikasi ulang lintas 6 domain, `report.md` ditulis.
- Milestone ditutup. Handoff eksplisit ke M3.3 (kolom filter view = kandidat index di tabel dasar), M3.4 (48 view = basis endpoint agregat, gap `dim_employee.property_id` perlu diselesaikan dulu kalau dibutuhkan), M3.5 (GRANT per view per peran, daftar lengkap di dokumen inventaris).

## 2026-08-09 — Pengajuan perubahan cakupan `dim_employee.property_id`

- Atas permintaan user, gap `dim_employee` tanpa `property_id` diajukan resmi lewat mekanisme Milestone 5.6: entri baru ditambahkan di `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` §"Kolom `property_id` hilang di `dim_employee`", status "Diajukan" (menunggu evaluasi pemilik `mart_aggregated`). Ditandai eksplisit **bukan simulasi** — beda dari pengajuan watchlist HR M5.6 yang ditulis ala persona, ini temuan nyata dari implementasi M3.2.
- Cross-reference diperbarui di `report.md` (Known Gaps) dan `docs/08-serving-data-analyst/view-query-pattern-analyst.md` (§HR) supaya jejak keputusan tidak terputus.
