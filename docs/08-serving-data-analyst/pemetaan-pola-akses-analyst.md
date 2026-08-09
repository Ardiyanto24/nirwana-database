# Pemetaan Pola Akses per Peran Data Analyst

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 3.1 (`milestones/3.1-pemetaan-pola-akses-analyst/`) |
| **Input utama** | `docs/02-requirements/pemetaan-kebutuhan-data-analyst.md` (kebutuhan bisnis per domain) + `docs/07-mart-aggregated/DataSchema-mart-aggregated.md` (skema aktual, 46 fact + 27 dimension table) |
| **Dipakai oleh** | Milestone 3.2 (view/query pattern), 3.3 (index), 3.4 (API), 3.5 (kredensial) |
| **Status** | Dalam pengerjaan |

---

## Cara Membaca Dokumen Ini

Dokumen ini menerjemahkan kebutuhan bisnis per peran (`pemetaan-kebutuhan-data-analyst.md`) menjadi pemetaan konkret ke tabel `mart_aggregated`/`mart_cleaned` yang **benar-benar ada** di skema aktual (`DataSchema-mart-aggregated.md`, sumber kebenaran pasca-koreksi Milestone 5.3). Bukan pengulangan dokumen kebutuhan — rujuk dokumen itu untuk detail naratif dimensi/metrik lengkap per peran.

Skema kolom tabel pemetaan per peran:

`Peran | Cakupan Properti | Tabel mart_aggregated Relevan | Tabel mart_cleaned Relevan (row-level) | Filter Wajib | Business Rule Kritis Terkait | Catatan Gap`

---

## Tabel Referensi: Domain → Fact/Dim Table (dari `DataSchema-mart-aggregated.md`)

### Lintas domain
- **Dimension:** `dim_property`, `dim_employee`, `dim_department`, `dim_customer_type`

### Revenue (8 fact table domain + 1 kasus khusus)
- **Fact:** `fact_revenue_room_type_daily`, `fact_revenue_channel_daily`, `fact_revenue_los_daily`, `fact_revenue_property_daily`, `fact_revenue_gop_impact_monthly`, `fact_revenue_pricing_deviation`, `fact_revenue_loyalty_daily`, `fact_revenue_nationality_daily`
- **Fact (kasus khusus, out-of-scope reguler):** `fact_revenue_pace_booking_snapshot`
- **Dimension:** `dim_room_type`, `dim_room` (dipakai bersama Facility), `dim_channel`, `dim_loyalty_tier`, `dim_nationality_group`, `dim_pricing_reason`

### F&B (8 fact table)
- **Fact:** `fact_fnb_outlet_daily`, `fact_fnb_category_daily`, `fact_fnb_hourly`, `fact_fnb_customer_type_daily`, `fact_fnb_menu_item_daily`, `fact_fnb_waste_daily`, `fact_fnb_inventory_status`, `fact_fnb_ingredient_price_daily`
- **Dimension:** `dim_outlet`, `dim_outlet_type`, `dim_fnb_category`, `dim_menu_item`, `dim_waste_reason`, `dim_ingredient`

### Facility/Ops (9 fact table)
- **Fact:** `fact_facility_room_status_daily`, `fact_housekeeping_room_type_daily`, `fact_housekeeping_property_daily`, `fact_housekeeping_staff_daily`, `fact_maintenance_ticket_daily`, `fact_maintenance_cost_daily`, `fact_maintenance_room_recurrence_yearly`, `fact_maintenance_property_benchmark_yearly`, `fact_maintenance_technician_daily`
- **Dimension:** `dim_facility_area`, `dim_issue_type`, `dim_priority` (+ pakai ulang `dim_room`, `dim_property`, `dim_employee`)

### Spa & Event (6 fact table)
- **Fact:** `fact_spa_daily`, `fact_spa_customer_type_daily`, `fact_spa_service_daily`, `fact_event_venue_daily`, `fact_event_property_daily`, `fact_event_type_daily`
- **Dimension:** `dim_spa_service`, `dim_venue`, `dim_venue_type`, `dim_event_type`

### HR (7 fact table domain + 1 kasus khusus)
- **Fact:** `fact_hr_attendance_daily`, `fact_hr_employee_monthly`, `fact_hr_employee_performance_semester`, `fact_hr_turnover_snapshot`, `fact_hr_headcount_status_daily`, `fact_hr_performance_department_semester`, `fact_hr_performance_by_status_semester`
- **Fact (kasus khusus, watchlist):** `fact_hr_watchlist_monthly`
- **Dimension:** `dim_shift_type`, `dim_employee_status` (+ pakai ulang `dim_employee`, `dim_department`)

### Corporate/Financial (9 fact table)
- **Fact:** `fact_financial_business_line_monthly`, `fact_financial_overall_monthly`, `fact_financial_revenue_runrate_daily`, `fact_payroll_department_monthly`, `fact_financial_service_charge_monthly`, `fact_financial_labor_cost_monthly`, `fact_payroll_access_level_monthly`, `fact_financial_business_line_group_monthly`, `fact_financial_property_benchmark_monthly`
- **Dimension:** `dim_business_line`, `dim_access_level`

### Feedback Loop ML (provisional, M5.4 — belum sync ke serving PostgreSQL)
- **Fact:** `fact_ml_occupancy_forecast_property_room_type` — hanya ada di BigQuery, **tidak** tersedia untuk peran manapun di lapisan PostgreSQL yang jadi cakupan Milestone 3.1-3.5. Dicatat di sini agar tidak keliru diasumsikan tersedia.

---

## Pemetaan per Peran

*(diisi bertahap per checkpoint — lihat `milestones/3.1-pemetaan-pola-akses-analyst/logs.md`)*

---

## Daftar Business Rule Kritis (Konsolidasi)

*(diisi di Fase 4 — konsolidasi dari seluruh rule yang dicatat per peran)*
