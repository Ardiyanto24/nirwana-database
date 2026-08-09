# View dan Query Pattern per Domain — Data Analyst

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 3.2 (`milestones/3.2-view-dan-query-pattern-per-domain/`) |
| **Input utama** | `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md` (Milestone 3.1) |
| **Lokasi teknis** | Schema `analyst_views` di serving PostgreSQL project (terpisah dari `mart_aggregated`/`mart_cleaned`) |
| **Dipakai oleh** | Milestone 3.3 (index), 3.4 (API), 3.5 (kredensial) |
| **Status** | Selesai — 48 view, 6 domain |

---

## Cara Membaca Dokumen Ini

Dokumen ini adalah inventaris seluruh view yang dibangun di schema `analyst_views`, sumber SQL-nya ada di `scripts/data_analyst_views/views_*.sql` (1 file per domain). Tiap view di-`LEFT JOIN` ke dimension table terkait supaya kolom `*_name` langsung terpakai analyst tanpa join manual. Business rule kritis dari Milestone 3.1 ditanam permanen di definisi view (bukan diserahkan ke pemakai) — lihat kolom "Business Rule Tertanam".

## Revenue (8 view)

| View | Fact Table Sumber | Dimension Di-join | Business Rule Tertanam |
|---|---|---|---|
| `v_revenue_room_type_daily` | `fact_revenue_room_type_daily` | `dim_property`, `dim_room_type` | — |
| `v_revenue_channel_daily` | `fact_revenue_channel_daily` | `dim_property`, `dim_channel` | — |
| `v_revenue_los_daily` | `fact_revenue_los_daily` | `dim_property`, `dim_room_type`, `dim_channel` | — |
| `v_revenue_property_daily` | `fact_revenue_property_daily` | `dim_property` | — |
| `v_revenue_gop_impact_monthly` | `fact_revenue_gop_impact_monthly` | `dim_property` | `gop_margin` bersumber dari baris `Overall`-equivalent (konsisten dengan `v_financial_gop_overhead`) |
| `v_revenue_pricing_deviation` | `fact_revenue_pricing_deviation` | `dim_property`, `dim_pricing_reason` | — |
| `v_revenue_loyalty_daily` | `fact_revenue_loyalty_daily` | `dim_property`, `dim_loyalty_tier` | — |
| `v_revenue_nationality_daily` | `fact_revenue_nationality_daily` | `dim_property`, `dim_nationality_group` | — |

**Dikecualikan:** `fact_revenue_pace_booking_snapshot` — status implementasi append-only vs BigQuery Sandbox DML block belum final (Known Gap M3.1, dikonfirmasi ulang berlaku di M3.2).

## F&B (8 view)

| View | Fact Table Sumber | Dimension Di-join | Business Rule Tertanam |
|---|---|---|---|
| `v_fnb_outlet_daily` | `fact_fnb_outlet_daily` | `dim_outlet`→`dim_property`, `dim_outlet_type` | `property_id` diturunkan lewat `dim_outlet.property_id` |
| `v_fnb_category_daily` | `fact_fnb_category_daily` | `dim_outlet`→`dim_property`, `dim_fnb_category` | sama |
| `v_fnb_hourly` | `fact_fnb_hourly` | `dim_outlet`→`dim_property` | sama |
| `v_fnb_customer_type_daily` | `fact_fnb_customer_type_daily` | `dim_outlet`→`dim_property`, `dim_customer_type` | sama |
| `v_fnb_menu_item_daily` | `fact_fnb_menu_item_daily` | `dim_outlet`→`dim_property` | sama |
| `v_fnb_waste_daily` | `fact_fnb_waste_daily` | `dim_outlet`→`dim_property`, `dim_waste_reason` | sama |
| `v_fnb_inventory_status` | `fact_fnb_inventory_status` | `dim_outlet`→`dim_property` | sama |
| `v_fnb_ingredient_price_daily` | `fact_fnb_ingredient_price_daily` | — | Tidak ada `property_id` (grain harga bahan baku bersifat global, bukan per-outlet) |

**Tidak ada view untuk basket analysis** — business rule kritis M3.1: harus row-level `mart_cleaned.fnb_transactions`, tidak bisa direkonstruksi dari fact table manapun.

## Facility/Ops (9 view)

| View | Fact Table Sumber | Dimension Di-join | Business Rule Tertanam |
|---|---|---|---|
| `v_facility_room_status_daily` | `fact_facility_room_status_daily` | `dim_room`→`dim_property`, `dim_room_type` | — |
| `v_housekeeping_room_type_daily` | `fact_housekeeping_room_type_daily` | `dim_property`, `dim_room_type` | — |
| `v_housekeeping_property_daily` | `fact_housekeeping_property_daily` | `dim_property` | — |
| `v_housekeeping_staff_daily` | `fact_housekeeping_staff_daily` | `dim_employee` | Performa individu — sensitivitas lebih tinggi dari label RBAC "Rendah", filtering akses granular didelegasikan ke M3.4/3.5 |
| `v_maintenance_ticket_daily` | `fact_maintenance_ticket_daily` | `dim_property`, `dim_facility_area`, `dim_issue_type`, `dim_priority` | **`pending_count` terpisah eksplisit dari breach**; `sla_threshold_hours` (CASE per priority: critical=8, high=24, medium=48, low=72 jam, sumber `Metadata.md`) dan `avg_exceeds_sla_threshold` ditanam permanen |
| `v_maintenance_cost_daily` | `fact_maintenance_cost_daily` | `dim_property`, `dim_issue_type` | — |
| `v_maintenance_room_recurrence_yearly` | `fact_maintenance_room_recurrence_yearly` | `dim_room`→`dim_property`, `dim_room_type` | — |
| `v_maintenance_property_benchmark_yearly` | `fact_maintenance_property_benchmark_yearly` | `dim_property` | — |
| `v_maintenance_technician_daily` | `fact_maintenance_technician_daily` | `dim_employee` | Performa individu — sama catatan `v_housekeeping_staff_daily` |

## Spa & Event (6 view)

| View | Fact Table Sumber | Dimension Di-join | Business Rule Tertanam |
|---|---|---|---|
| `v_spa_daily` | `fact_spa_daily` | `dim_property` | — |
| `v_spa_customer_type_daily` | `fact_spa_customer_type_daily` | `dim_property`, `dim_customer_type` | — |
| `v_spa_service_daily` | `fact_spa_service_daily` | `dim_property`, `dim_spa_service` | — |
| `v_event_venue_daily` | `fact_event_venue_daily` | `dim_venue`→`dim_property`, `dim_venue_type` | — |
| `v_event_property_daily` | `fact_event_property_daily` | `dim_property` | — |
| `v_event_type_daily` | `fact_event_type_daily` | `dim_property`, `dim_event_type` | — |

**Tidak ada view untuk repeat-client-event atau cross-sell spa×event** — business rule kritis M3.1: dilarang jadi metrik otomatis (`client_name` teks bebas, tidak ada `guest_id` penghubung).

## HR (8 view)

| View | Fact Table Sumber | Dimension Di-join | Business Rule Tertanam |
|---|---|---|---|
| `v_hr_attendance_daily` | `fact_hr_attendance_daily` | `dim_property`, `dim_department` | — |
| `v_hr_employee_monthly` | `fact_hr_employee_monthly` | `dim_employee`→`dim_department` | **Tidak ada `property_id`** — lihat Known Gap di bawah |
| `v_hr_employee_performance_semester` | `fact_hr_employee_performance_semester` | `dim_employee`→`dim_department` | Sama — tidak ada `property_id` |
| `v_hr_turnover_snapshot` | `fact_hr_turnover_snapshot` | `dim_property`, `dim_department` | — |
| `v_hr_headcount_status_daily` | `fact_hr_headcount_status_daily` | `dim_property`, `dim_department`, `dim_employee_status` | — |
| `v_hr_performance_department_semester` | `fact_hr_performance_department_semester` | `dim_property`, `dim_department` | — |
| `v_hr_performance_by_status_semester` | `fact_hr_performance_by_status_semester` | `dim_property`, `dim_employee_status` | — |
| `v_hr_watchlist_monthly` | `fact_hr_watchlist_monthly` | `dim_employee`→`dim_department` | **Tidak ada `property_id`**; `in_watchlist` (M5.6) diteruskan apa adanya |

**Tidak ada view payroll di sini** — business rule kritis M3.1: eksklusif Corporate/Financial Analyst.

### Known Gap ditemukan di M3.2: `dim_employee` tidak punya `property_id`

`mart_aggregated.dim_employee` hanya berisi `employee_id`, `full_name`, `department_id`, `access_level_id` — **tidak ada `property_id`**, meski `employees.property_id` ada di produksi (`docs/01-architecture/Metadata.md` baris 134, `P06` = kantor pusat). Akibatnya `v_hr_employee_monthly`, `v_hr_employee_performance_semester`, `v_hr_watchlist_monthly` tidak bisa difilter per properti. Perbaikan (menambah kolom ke `dim_employee`) di luar cakupan M3.2 — **sudah diajukan** lewat mekanisme perubahan cakupan Milestone 5.6, lihat `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` §"Kolom `property_id` hilang di `dim_employee`" (status: Diajukan).

## Corporate/Financial (9 view)

| View | Fact Table Sumber | Dimension Di-join | Business Rule Tertanam |
|---|---|---|---|
| `v_financial_departmental_margin` | `fact_financial_business_line_monthly` | `dim_property`, `dim_business_line` | **`WHERE line_name NOT IN ('Overall','Corporate Overhead')` ditanam permanen** — business rule kritis #1 M3.1, diverifikasi KK2 |
| `v_financial_gop_overhead` | `fact_financial_overall_monthly` | `dim_property` | Sumber GOP/overhead yang benar (bukan dari tabel departmental margin) |
| `v_financial_revenue_runrate_daily` | `fact_financial_revenue_runrate_daily` | `dim_property` | — |
| `v_payroll_department_monthly` | `fact_payroll_department_monthly` | `dim_property`, `dim_department` | Eksklusif Corporate/Financial (HR dilarang) |
| `v_financial_service_charge_monthly` | `fact_financial_service_charge_monthly` | `dim_property` | Eksklusif Corporate/Financial |
| `v_financial_labor_cost_monthly` | `fact_financial_labor_cost_monthly` | `dim_property` | Eksklusif Corporate/Financial |
| `v_payroll_access_level_monthly` | `fact_payroll_access_level_monthly` | `dim_property`, `dim_access_level` | Eksklusif Corporate/Financial |
| `v_financial_business_line_group_monthly` | `fact_financial_business_line_group_monthly` | `dim_business_line` | **Grain grup, tanpa `property_id`** — Property/GM Analyst dilarang akses (business rule kritis #3 M3.1) |
| `v_financial_property_benchmark_monthly` | `fact_financial_property_benchmark_monthly` | `dim_property` | — |

---

## Property/GM Analyst

Tidak ada view baru untuk peran ini — sesuai desain union M3.1, peran ini terlayani penuh dari 39 view domain #1–5 (Revenue 8 + F&B 8 + Facility 9 + Spa&Event 6 + HR 8) di atas, dengan `property_id` (kolom asli tiap view) difilter ke 1 properti spesifik oleh pemakai/API (M3.4), bukan konstanta yang bisa ditanam di view generik. **9 view Corporate/Financial di atas — termasuk eksplisit `v_financial_business_line_group_monthly` — tetap di luar cakupan role ini**, larangan teknisnya akan diberlakukan lewat GRANT di Milestone 3.5 (schema `analyst_views` terpisah dari `mart_aggregated`/`mart_cleaned` justru dirancang untuk memudahkan hal ini).

## Verifikasi

Total 48 view aktif di `information_schema.views` schema `analyst_views` (Revenue 8 + F&B 8 + Facility 9 + Spa&Event 6 + HR 8 + Corporate/Financial 9), cocok dengan inventaris di atas. Detail bukti verifikasi KK1/KK2 per domain ada di `milestones/3.2-view-dan-query-pattern-per-domain/{logs.md,report.md}`.
