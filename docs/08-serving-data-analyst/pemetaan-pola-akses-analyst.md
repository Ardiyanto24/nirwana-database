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

### 1. Revenue Analyst

| Field | Isi |
|---|---|
| **Cakupan Properti** | Semua 5 properti |
| **Tabel `mart_aggregated` Relevan** | `fact_revenue_room_type_daily`, `fact_revenue_channel_daily`, `fact_revenue_los_daily`, `fact_revenue_property_daily`, `fact_revenue_gop_impact_monthly`, `fact_revenue_pricing_deviation`, `fact_revenue_loyalty_daily`, `fact_revenue_nationality_daily` — dim: `dim_property`, `dim_room_type`, `dim_channel`, `dim_loyalty_tier`, `dim_nationality_group`, `dim_pricing_reason` |
| **Tabel `mart_cleaned` Relevan (row-level)** | `bookings` (investigasi ad-hoc cancellation, mis. "kenapa cancellation Bali Maret 2024 tinggi"), `pricing_history` (price elasticity — histori harian harga vs okupansi) |
| **Filter Wajib** | `property_id` (filter standar, tidak ada filter eksklusif khusus di domain ini) |
| **Business Rule Kritis Terkait** | `fact_revenue_pace_booking_snapshot` (di skema tapi didesain append-only, snapshot "as of hari ini" — **bukan** metrik historis biasa; jangan digabung dengan agregasi reguler `fact_revenue_property_daily`. Status implementasi append-only vs constraint BigQuery Sandbox (DML diblokir) masih dicatat sebagai belum final di `DataSchema-mart-aggregated.md` §Fact Tables Revenue — cek status aktual sebelum dipakai di Milestone 3.2). |
| **Catatan Gap** | Net revenue setelah komisi OTA — tidak tersedia (tidak ada kolom komisi di `bookings`). Target/budget okupansi & revenue — tidak ada tabel target di skema. |

### 2. F&B Analyst

| Field | Isi |
|---|---|
| **Cakupan Properti** | Semua 5 properti |
| **Tabel `mart_aggregated` Relevan** | `fact_fnb_outlet_daily`, `fact_fnb_category_daily`, `fact_fnb_hourly`, `fact_fnb_customer_type_daily`, `fact_fnb_menu_item_daily`, `fact_fnb_waste_daily`, `fact_fnb_inventory_status`, `fact_fnb_ingredient_price_daily` — dim: `dim_outlet`, `dim_outlet_type`, `dim_fnb_category`, `dim_menu_item`, `dim_waste_reason`, `dim_ingredient` |
| **Tabel `mart_cleaned` Relevan (row-level)** | `fnb_transactions` (investigasi anomali penjualan menu tertentu; basket analysis per `transaction_id`) |
| **Filter Wajib** | `property_id` (via `dim_outlet.property_id` — outlet selalu terikat 1 properti) |
| **Business Rule Kritis Terkait** | **Basket analysis WAJIB dari `mart_cleaned.fnb_transactions` row-level, tidak pernah dari `mart_aggregated`** — grain per struk hilang total di seluruh fact table F&B (semua sudah teragregasi per outlet/periode), mencoba merekonstruksinya dari fact table akan menghasilkan hasil salah, bukan sekadar kurang detail. |
| **Catatan Gap** | Data supplier/vendor bahan baku — tidak ada tabel ini. Waktu penyiapan/kecepatan servis — tidak ada kolom timestamp granular di `fnb_transactions` selain `transaction_datetime`. |

*(4 peran lain — Facility/Ops, Spa & Event, HR, Corporate/Financial, dan Property/GM Analyst — diisi di checkpoint berikutnya, lihat `milestones/3.1-pemetaan-pola-akses-analyst/logs.md`.)*

---

## Daftar Business Rule Kritis (Konsolidasi)

*(diisi di Fase 4 — konsolidasi dari seluruh rule yang dicatat per peran)*
