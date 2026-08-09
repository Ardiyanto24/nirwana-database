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

### 3. Facility/Ops Analyst

| Field | Isi |
|---|---|
| **Cakupan Properti** | Semua 5 properti |
| **Tabel `mart_aggregated` Relevan** | `fact_facility_room_status_daily`, `fact_housekeeping_room_type_daily`, `fact_housekeeping_property_daily`, `fact_housekeeping_staff_daily`, `fact_maintenance_ticket_daily`, `fact_maintenance_cost_daily`, `fact_maintenance_room_recurrence_yearly`, `fact_maintenance_property_benchmark_yearly`, `fact_maintenance_technician_daily` — dim: `dim_facility_area`, `dim_issue_type`, `dim_priority`, `dim_room`, `dim_property`, `dim_employee` |
| **Tabel `mart_cleaned` Relevan (row-level)** | `maintenance_tickets` (investigasi lonjakan keluhan tipe kerusakan tertentu; riwayat tiket per `room_id` spesifik) |
| **Filter Wajib** | `property_id` |
| **Business Rule Kritis Terkait** | **SLA breach**: `fact_maintenance_ticket_daily.pending_count` (tiket `open`/`in-progress`) WAJIB dipisah dari `avg_sla_duration_hours` — tiket pending **tidak boleh** otomatis dihitung breach atau tidak-breach di view/API manapun. **Performa individu staff** (`fact_housekeeping_staff_daily`, `fact_maintenance_technician_daily`): sensitivitasnya lebih tinggi dari label domain RBAC "Rendah" pada `facility` — tetap dimasukkan sesuai keputusan sadar M5.1, tapi filtering akses granular (siapa boleh lihat performa siapa) adalah tanggung jawab Milestone 3.4 (API)/3.5 (kredensial), bukan dianggap otomatis aman di level mart. |
| **Catatan Gap** | Jadwal preventive maintenance — tidak ada tabel ini (semua tiket reaktif). Estimasi kehilangan revenue dari kamar out-of-order — sengaja tidak dimasukkan (butuh asumsi cross-domain tidak akurat). Breakdown biaya per jenis part — `parts_replaced` teks bebas, bukan kategori terstruktur. |

### 4. Spa & Event Analyst

| Field | Isi |
|---|---|
| **Cakupan Properti** | Semua 5 properti |
| **Tabel `mart_aggregated` Relevan** | Spa: `fact_spa_daily`, `fact_spa_customer_type_daily`, `fact_spa_service_daily`. Event: `fact_event_venue_daily`, `fact_event_property_daily`, `fact_event_type_daily` — dim: `dim_spa_service`, `dim_venue`, `dim_venue_type`, `dim_event_type` |
| **Tabel `mart_cleaned` Relevan (row-level)** | `event_bookings` (investigasi anomali utilisasi venue tertentu; investigasi klien event tertentu via `client_name`) |
| **Filter Wajib** | `property_id` |
| **Business Rule Kritis Terkait** | **Repeat client event tidak boleh dibangun sebagai metrik otomatis** di `mart_aggregated`/view/API manapun — `client_name` teks bebas tanpa ID terstruktur, deteksi otomatis rapuh terhadap variasi penulisan nama. Kalau dibutuhkan, wajib row-level dengan fuzzy matching manual oleh analyst, bukan query terlayani. **Cross-sell spa×event juga tidak boleh diklaim sebagai metrik andal** — tidak ada `guest_id` penghubung konsisten antara `spa_bookings` dan `event_bookings`. |
| **Catatan Gap** | Diskon/promo pada spa maupun event — tidak ada kolom ini di skema. Repeat client event dan cross-sell spa×event — lihat Business Rule Kritis (bukan sekadar gap data, tapi larangan eksplisit membangun metrik dari data yang tidak andal). |

### 5. HR Analyst

| Field | Isi |
|---|---|
| **Cakupan Properti** | Semua 5 properti |
| **Tabel `mart_aggregated` Relevan** | `fact_hr_attendance_daily`, `fact_hr_employee_monthly`, `fact_hr_employee_performance_semester`, `fact_hr_turnover_snapshot`, `fact_hr_headcount_status_daily`, `fact_hr_performance_department_semester`, `fact_hr_performance_by_status_semester`, `fact_hr_watchlist_monthly` — dim: `dim_employee`, `dim_department`, `dim_shift_type`, `dim_employee_status`, `dim_property` |
| **Tabel `mart_cleaned` Relevan (row-level)** | `staff_shifts` (investigasi lonjakan absensi departemen/periode tertentu), `employee_performance` (investigasi karyawan watchlist — histori shift & performance individu) |
| **Filter Wajib** | `property_id`, `department_id` |
| **Business Rule Kritis Terkait** | **HR Analyst TIDAK BOLEH mengakses payroll dalam bentuk apa pun** — seluruh `fact_payroll_department_monthly`, `fact_financial_service_charge_monthly`, `fact_financial_labor_cost_monthly`, `fact_payroll_access_level_monthly` (mart_aggregated) dan `mart_cleaned.payroll` (row-level) eksklusif milik Corporate/Financial Analyst (segregation of duties, ditegaskan sejak dokumen kebutuhan). **Threshold early-warning** (mis. rate absen "di luar kebiasaan" untuk watchlist) sengaja tidak ditentukan di sini — metrik dasar (`fact_hr_watchlist_monthly` kolom rasio baseline) tersedia, tapi kalibrasi threshold adalah keputusan terpisah (sudah diselesaikan sebagian untuk `in_watchlist` via Milestone 5.6, threshold lain masih terbuka per arsitektur §10 No. 3). |
| **Catatan Gap** | Exit interview/alasan resign — tidak ada di tabel resmi. Training/sertifikasi karyawan — tidak ada tabel ini. Payroll — bukan gap, melainkan pengecualian disengaja (lihat Business Rule Kritis). |

### 6. Corporate/Financial Analyst

| Field | Isi |
|---|---|
| **Cakupan Properti** | Semua 5 properti (grup) — satu-satunya peran dengan `access_scope=all_properties` di `role_permissions` |
| **Tabel `mart_aggregated` Relevan** | `fact_financial_business_line_monthly`, `fact_financial_overall_monthly`, `fact_financial_revenue_runrate_daily`, `fact_payroll_department_monthly`, `fact_financial_service_charge_monthly`, `fact_financial_labor_cost_monthly`, `fact_payroll_access_level_monthly`, `fact_financial_business_line_group_monthly`, `fact_financial_property_benchmark_monthly` — dim: `dim_business_line`, `dim_access_level`, `dim_department`, `dim_property` |
| **Tabel `mart_cleaned` Relevan (row-level)** | `financial_summary` (drill penurunan margin lini bisnis per bulan/departemen), `payroll` (audit alokasi service charge per karyawan) |
| **Filter Wajib** | `business_line_id` — lihat Business Rule Kritis (aturan filter berbeda per metrik, bukan filter tunggal). `fact_financial_business_line_group_monthly` tidak punya `property_id` (grain grup) — tidak difilter per properti by design. |
| **Business Rule Kritis Terkait** | **Aturan filter `business_line_id` paling kritis di seluruh dokumen ini**: (1) metrik "departmental margin" WAJIB filter `business_line_id IN ('Room','F&B','Spa&Event')` dari `fact_financial_business_line_monthly` — **jangan pernah** sertakan `Overall`/`Corporate Overhead` (risiko double counting, ditegaskan sejak M5.1); (2) GOP dan overhead ratio WAJIB dari `fact_financial_overall_monthly` (setara baris `Overall`/`Corporate Overhead`), bukan dari `fact_financial_business_line_monthly`. **Koherensi check** (revenue Room `financial_summary` vs total transaksi booking) adalah kebutuhan validasi/Data Quality Gate (Bagian 9 arsitektur), bukan endpoint metrik analisis biasa — jangan dicampur ke API analitik Milestone 3.4. **`undistributed_expense_total` hanya 1 kolom agregat** — tidak ada breakdown per komponen (Admin&General/Sales&Marketing/dst) di skema manapun (ditemukan saat implementasi M5.3), jangan asumsikan breakdown itu ada saat mendesain view/API. |
| **Catatan Gap** | GOP granularitas mingguan/harian — sumber `financial_summary`/`payroll` hanya bulanan. Cost of capital, depresiasi, komponen finansial non-operasional (below GOP line) — tidak ada di skema. |

*(1 peran lagi — Property/GM Analyst sebagai union — diisi di checkpoint final bersama daftar business rule konsolidasi, lihat `milestones/3.1-pemetaan-pola-akses-analyst/logs.md`.)*

---

## Daftar Business Rule Kritis (Konsolidasi)

*(diisi di Fase 4 — konsolidasi dari seluruh rule yang dicatat per peran)*
