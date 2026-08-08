# Desain Struktur Tabel `mart_aggregated`

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 5.2 (`milestones/5.2-desain-struktur-tabel-mart-aggregated/`) |
| **Input utama** | `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md` (Milestone 5.1) — 94 baris metrik terkonsolidasi lintas 6 domain |
| **Dipakai oleh** | Milestone 5.3 (implementasi transformasi SQL + data dictionary penuh), `04-serving-data-analyst.md`, `05-serving-ai-chatbot.md` |
| **Status** | Selesai — 45 fact table + 27 dimension table, seluruh audit PII tercatat (Milestone 5.2, ditutup 2026-08-08) |

---

## Cara Membaca Dokumen Ini

Dokumen ini mendesain **struktur** `mart_aggregated`, bukan implementasi SQL (itu Milestone 5.3) dan bukan data dictionary penuh (juga Milestone 5.3 — lihat `docs/keputusan-tertunda.md`). Skema dirancang sebagai **star schema (Kimball)** dengan conformed dimension tables — dijelaskan alasannya di `milestones/5.2-.../decisions.md` Keputusan #1-2.

Setiap tabel didokumentasikan dengan:
- **Grain** — 1 baris mewakili apa.
- **Kolom** — nama, tipe, keterangan singkat (bukan cara hitung detail — itu tugas M5.3).
- **Partition/Cluster key** (khusus fact table).
- **Sumber** — tabel `mart_cleaned` asal.

Seluruh kategori/referensi (channel, department, issue_type, dst) sengaja dijadikan dimension table tersendiri, bukan kolom inline — keputusan eksplisit user (Keputusan #2 di `decisions.md`) untuk extensibility jangka panjang.

---

## Dimension Tables

27 dimension table (23 diinventarisasi di Task 1 + 4 amendemen ditemukan saat desain fact table), dikelompokkan per domain asal (beberapa dipakai lintas domain — conformed dimensions).

### Lintas domain (dipakai ≥2 domain)

| Dimension Table | Kolom | Key | Sumber |
|---|---|---|---|
| `dim_property` | `property_id` (PK), `property_name`, `region`, `opening_date` | Natural key (`property_id` sudah stabil di produksi) | `properties` |
| `dim_employee` | `employee_id` (PK), `full_name`, `department_id` (FK `dim_department`), `access_level_id` (FK `dim_access_level`) | Natural key | `employees` |
| `dim_department` | `department_id` (PK), `department_name` | Surrogate | `employees.department` |
| `dim_customer_type` | `customer_type_id` (PK), `customer_type_name` (inhouse/walk-in) | Surrogate | `fnb_transactions.customer_type`, `spa_bookings` (implisit inhouse/walk-in) |

### Revenue

| Dimension Table | Kolom | Key | Sumber |
|---|---|---|---|
| `dim_room_type` | `room_type_id` (PK), `room_type_name` | Surrogate | `bookings.room_type` |
| `dim_room` | `room_id` (PK), `property_id` (FK), `room_type_id` (FK) | Natural key | `rooms` |
| `dim_channel` | `channel_id` (PK), `channel_name` | Surrogate | `bookings.booking_channel` |
| `dim_loyalty_tier` | `loyalty_tier_id` (PK), `loyalty_tier_name` | Surrogate | `guests.loyalty_tier` |
| `dim_nationality_group` | `nationality_group_id` (PK), `group_name` (Domestik/Mancanegara) | Surrogate | `guests.nationality` (dikategorikan saat transformasi M5.3 — aturan kategorisasi eksplisit menyusul, dicatat di M5.1) |

**Catatan:** `dim_room` dipakai bersama Facility/Ops (grain `room_id` untuk recurring issue, status kamar).

### F&B

| Dimension Table | Kolom | Key | Sumber |
|---|---|---|---|
| `dim_outlet` | `outlet_id` (PK), `outlet_name`, `property_id` (FK), `outlet_type_id` (FK) | Natural key | `fnb_outlets` |
| `dim_outlet_type` | `outlet_type_id` (PK), `outlet_type_name` (Restaurant/Bar/Room Service) | Surrogate | `fnb_outlets.outlet_type` |
| `dim_fnb_category` | `category_id` (PK), `category_name` (Food/Beverage/Dessert) | Surrogate | `fnb_transactions.category` |
| `dim_menu_item` | `item_name` (PK — teks, tidak ada ID terstruktur di skema sumber), `outlet_id` (FK, opsional) | Natural key (teks) | `fnb_transactions.item_name`, `recipe_bom.item_name` |

### Facility/Ops

| Dimension Table | Kolom | Key | Sumber |
|---|---|---|---|
| `dim_facility_area` | `facility_area_id` (PK), `facility_area_name` | Surrogate | `maintenance_tickets.facility_area` |
| `dim_issue_type` | `issue_type_id` (PK), `issue_type_name` | Surrogate | `maintenance_tickets.issue_type` |
| `dim_priority` | `priority_id` (PK), `priority_name` | Surrogate | `maintenance_tickets.priority` |

*(`dim_room`, `dim_property`, `dim_employee` dipakai ulang dari Revenue/lintas-domain.)*

### Spa & Event

| Dimension Table | Kolom | Key | Sumber |
|---|---|---|---|
| `dim_spa_service` | `service_id` (PK), `service_name` | Surrogate | `spa_bookings.service_name` |
| `dim_venue` | `venue_id` (PK), `venue_name`, `property_id` (FK), `venue_type_id` (FK), `max_capacity` | Natural key | `venues` |
| `dim_venue_type` | `venue_type_id` (PK), `venue_type_name` | Surrogate | `venues.venue_type` |
| `dim_event_type` | `event_type_id` (PK), `event_type_name` | Surrogate | `event_bookings.event_type` |

### HR

| Dimension Table | Kolom | Key | Sumber |
|---|---|---|---|
| `dim_shift_type` | `shift_type_id` (PK), `shift_type_name` (Morning/Afternoon/Night) | Surrogate | `staff_shifts.shift_type` |

*(`dim_employee`, `dim_department`, `dim_property` dipakai ulang dari lintas-domain.)*

### Corporate/Financial

| Dimension Table | Kolom | Key | Sumber |
|---|---|---|---|
| `dim_business_line` | `business_line_id` (PK), `line_name` (Room/F&B/Spa&Event/Overall/Corporate Overhead) | Surrogate | `financial_summary.department` |
| `dim_access_level` | `access_level_id` (PK), `access_level_name` (staff/manager) | Surrogate | `employees.access_level` / `payroll` |

**Catatan disambiguasi penting:** `dim_business_line` (Corporate/Financial) **sengaja dipisah** dari `dim_department` (HR/employee) meski sama-sama disebut "department" di dokumen sumber. Keduanya taksonomi berbeda — `dim_department` adalah unit organisasi tempat karyawan bekerja (Housekeeping, F&B, Maintenance, Spa&Event, HR, Finance), sedangkan `dim_business_line` adalah baris lini bisnis USALI di `financial_summary` (Room/F&B/Spa&Event untuk margin per lini, plus `Overall`/`Corporate Overhead` yang tidak punya padanan departemen karyawan manapun). Menyamakan keduanya akan salah secara konsep dan berisiko query yang salah filter (mis. mencampur `Overall` sebagai "departemen").

### Ditemukan saat desain fact table (amendemen Task 2-3, dicatat di sini agar Dimension Tables tetap 1 sumber kebenaran)

| Dimension Table | Kolom | Key | Sumber | Ditemukan saat |
|---|---|---|---|---|
| `dim_pricing_reason` | `reason_id` (PK), `reason_name` (manual/promo/dynamic-pricing-AI) | Surrogate | `pricing_history.reason` | Task 2 (Revenue) — breakdown pricing deviation butuh dimensi ini, terlewat di Task 1 |
| `dim_waste_reason` | `reason_id` (PK), `reason_name` (overproduction/expired/spillage) | Surrogate | `fnb_waste_log.reason` | Task 3 (F&B) |
| `dim_ingredient` | `ingredient_id` (PK, STRING — berperan ganda sebagai nama, mis. "Rice"/"Chicken") | Natural key | `ingredient_price_history` | Task 3 (F&B); **dikoreksi M5.3**: `ingredient_name` terpisah ternyata tidak ada di skema sumber, `ingredient_id` sendiri sudah berupa teks nama |
| `dim_employee_status` | `status_id` (PK), `status_name` (active/resigned/terminated) | Surrogate | `employees.status` | Task 6 (HR) |

---

## Fact Tables

### Revenue

**Catatan temuan:** Saat mendesain tabel ini, ditemukan 1 metrik yang tersirat sebagai dimensi (`loyalty_tier`) di §1.3 dokumen konsolidasi M5.1 tapi tidak eksplisit jadi baris metrik tersendiri, padahal Revenue Manager (chatbot) eksplisit meminta "jumlah booking per `loyalty_tier`, per periode". Ditambahkan di sini sebagai `fact_revenue_loyalty_daily` — bukan revisi M5.1 (dokumen itu tetap closed sebagaimana ditutup), murni penambahan yang wajar muncul saat kerja desain skema lebih detail dari kerja konsolidasi requirement.

#### `fact_revenue_daily`
**Grain:** 1 baris per `property_id` × `room_type_id` × `channel_id` × `period_date`.
**Kolom:** `property_id` (FK), `room_type_id` (FK), `channel_id` (FK), `period_date` (DATE), `rooms_sold`, `total_rooms_available`, `occupancy_rate`, `adr`, `revpar`, `revenue`, `bookings_count`, `cancellations_count`, `no_shows_count`, `avg_los_nights`, `avg_lead_time_days`, `mom_occupancy_growth`, `yoy_occupancy_growth`, `mom_adr_growth`, `yoy_adr_growth`, `mom_revpar_growth`, `yoy_revpar_growth`.
**Partition:** `period_date`. **Cluster:** `property_id`, `room_type_id`.
**Cakupan M5.1:** baris 1,2,3,4,5,7,8.

#### `fact_revenue_pricing_deviation`
**Grain:** 1 baris per `property_id` × `pricing_reason_id` × `period_date`.
**Kolom:** `property_id` (FK), `pricing_reason_id` (FK `dim_pricing_reason`), `period_date` (DATE), `avg_applied_rate`, `avg_base_rate`, `avg_deviation_pct`, `day_share_pct`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 6.

#### `fact_revenue_property_summary`
**Grain:** 1 baris per `property_id` × `period_date` (grain lebih kasar — tanpa room_type/channel, sesuai grain asli metrik-metrik ini di M5.1).
**Kolom:** `property_id` (FK), `period_date` (DATE), `repeat_guest_rate`, `revpar_rank_group`, `adr_rank_group`, `occupancy_rank_group`, `gop_pricing_impact` (cross-domain, precompute dari `financial_summary` — Keputusan #6).
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 9, 11, 12.

#### `fact_revenue_loyalty_daily`
**Grain:** 1 baris per `property_id` × `loyalty_tier_id` × `period_date`.
**Kolom:** `property_id` (FK), `loyalty_tier_id` (FK), `period_date` (DATE), `bookings_count`, `revenue`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** temuan tambahan (lihat Catatan di atas).

#### `fact_revenue_nationality_daily`
**Grain:** 1 baris per `property_id` × `nationality_group_id` × `period_date`.
**Kolom:** `property_id` (FK), `nationality_group_id` (FK), `period_date` (DATE), `bookings_count`, `revenue`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 10.

*(Pace booking — baris 13, Cakupan Khusus — didesain terpisah di Task 8, bukan bagian tabel di atas.)*

---

### F&B

#### `fact_fnb_outlet_daily`
**Grain:** 1 baris per `outlet_id` × `period_date`.
**Kolom:** `outlet_id` (FK), `period_date` (DATE), `revenue`, `transaction_count`, `avg_check`, `mom_revenue_growth`, `yoy_revenue_growth`, `capture_rate` (cross-domain, precompute dari `bookings`/`daily_occupancy` — Keputusan #6), `walk_in_ratio`, `revenue_rank_vs_outlet_type_avg`.
**Partition:** `period_date`. **Cluster:** `outlet_id`.
**Cakupan M5.1:** baris 1, 7, 8, 9, 12.

#### `fact_fnb_category_daily`
**Grain:** 1 baris per `outlet_id` × `category_id` × `period_date`.
**Kolom:** `outlet_id` (FK), `category_id` (FK `dim_fnb_category`), `period_date` (DATE), `revenue`.
**Partition:** `period_date`. **Cluster:** `outlet_id`.
**Cakupan M5.1:** baris 2.

#### `fact_fnb_hourly`
**Grain:** 1 baris per `outlet_id` × `period_date` × `hour_of_day`.
**Kolom:** `outlet_id` (FK), `period_date` (DATE), `hour_of_day` (INT64), `transaction_count`.
**Partition:** `period_date`. **Cluster:** `outlet_id`.
**Cakupan M5.1:** baris 3.

#### `fact_fnb_customer_type_daily`
**Grain:** 1 baris per `outlet_id` × `customer_type_id` × `period_date`.
**Kolom:** `outlet_id` (FK), `customer_type_id` (FK), `period_date` (DATE), `revenue`, `visit_count`, `revenue_per_visit`.
**Partition:** `period_date`. **Cluster:** `outlet_id`.
**Cakupan M5.1:** baris 13.

#### `fact_fnb_menu_item_daily`
**Grain:** 1 baris per `outlet_id` × `item_name` (FK `dim_menu_item`) × `period_date`.
**Kolom:** `outlet_id` (FK), `item_name` (FK), `period_date` (DATE), `revenue`, `quantity_sold`, `food_cost_ratio_actual`, `food_cost_ratio_target`, `food_cost_deviation`.
**Partition:** `period_date`. **Cluster:** `outlet_id`.
**Cakupan M5.1:** baris 4, 5, 10.

#### `fact_fnb_waste_daily`
**Grain:** 1 baris per `outlet_id` × `waste_reason_id` × `period_date`.
**Kolom:** `outlet_id` (FK), `waste_reason_id` (FK `dim_waste_reason`), `period_date` (DATE), `waste_value`, `waste_quantity`, `waste_ratio`.
**Partition:** `period_date`. **Cluster:** `outlet_id`.
**Cakupan M5.1:** baris 6.

#### `fact_fnb_inventory_status`
**Grain:** 1 baris per `outlet_id` × `period_date` (snapshot harian, bukan histori berjenjang — hanya state terkini per hari).
**Kolom:** `outlet_id` (FK), `period_date` (DATE), `low_stock_item_count`.
**Partition:** `period_date`. **Cluster:** `outlet_id`.
**Cakupan M5.1:** baris 11. **Catatan:** daftar item spesifik di bawah threshold tetap dilayani row-level dari `mart_cleaned.fnb_inventory` — tabel ini hanya untuk hitungan agregat/tren, konsisten prinsip M5.1 (row-level bukan tanggung jawab `mart_aggregated`).

#### `fact_fnb_ingredient_price_daily`
**Grain:** 1 baris per `ingredient_id` (FK `dim_ingredient`) × `period_date`.
**Kolom:** `ingredient_id` (FK), `period_date` (DATE), `avg_unit_cost`.
**Partition:** `period_date`. **Cluster:** `ingredient_id`.
**Cakupan M5.1:** baris 14.

**Catatan:** "Daftar staf F&B propertinya" (baris 15, kebutuhan chatbot-only) **tidak** perlu fact table — cukup dilayani lewat query langsung ke `dim_employee` difilter `department_id`='F&B' dan `property_id`, karena ini murni lookup dimension, bukan metrik agregat.

### Facility/Ops

#### `fact_facility_room_status_daily`
**Grain:** 1 baris per `room_id` (FK `dim_room`) × `period_date` (snapshot harian).
**Kolom:** `room_id` (FK), `period_date` (DATE), `status`, `is_out_of_order` (BOOL), `out_of_order_hours`.
**Partition:** `period_date`. **Cluster:** `room_id`.
**Cakupan M5.1:** baris 1, 2. Distribusi status per properti diturunkan via agregasi `GROUP BY property_id` (dari `dim_room`) di query M5.3/serving, tidak perlu tabel terpisah.

#### `fact_housekeeping_room_type_daily`
**Grain:** 1 baris per `property_id` × `room_type_id` × `period_date`.
**Kolom:** `property_id` (FK), `room_type_id` (FK), `period_date` (DATE), `avg_cleaning_duration_minutes`, `baseline_duration_minutes`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 3.

#### `fact_housekeeping_property_daily`
**Grain:** 1 baris per `property_id` × `period_date`.
**Kolom:** `property_id` (FK), `period_date` (DATE), `delayed_rate`, `delayed_rate_vs_occupancy` (cross-domain, precompute — Keputusan #6).
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 4, 5.

#### `fact_housekeeping_staff_daily`
**Grain:** 1 baris per `staff_id` (FK `dim_employee`) × `period_date`.
**Kolom:** `staff_id` (FK), `period_date` (DATE), `avg_cleaning_duration_minutes`, `team_avg_duration_minutes`.
**Partition:** `period_date`. **Cluster:** `staff_id`.
**Cakupan M5.1:** baris 6. Data performa individu (Keputusan project M5.1: dimasukkan sadar, filtering akses granular jadi tanggung jawab application layer/serving).

#### `fact_maintenance_ticket_daily`
**Grain:** 1 baris per `property_id` × `facility_area_id` × `issue_type_id` × `priority_id` × `period_date`.
**Kolom:** `property_id` (FK), `facility_area_id` (FK), `issue_type_id` (FK), `priority_id` (FK), `period_date` (DATE), `new_ticket_count`, `avg_sla_duration_hours` (mentah, **bukan** flag breach — Keputusan #7), `pending_count` (tiket `open`/`in-progress`).
**Partition:** `period_date`. **Cluster:** `property_id`, `priority_id`.
**Cakupan M5.1:** baris 7, 8.

#### `fact_maintenance_cost_daily`
**Grain:** 1 baris per `property_id` × `issue_type_id` × `period_date`.
**Kolom:** `property_id` (FK), `issue_type_id` (FK), `period_date` (DATE), `total_cost`, `cost_with_parts`, `cost_without_parts`, `mom_cost_growth`, `yoy_cost_growth`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 9, 10, 14 (tren jangka panjang diturunkan via roll-up bulanan dari tabel ini, tidak perlu tabel terpisah).

#### `fact_maintenance_room_recurrence_yearly`
**Grain:** 1 baris per `room_id` (FK `dim_room`) × `year`.
**Kolom:** `room_id` (FK), `year` (INT64), `ticket_count`, `vs_median_ratio`.
**Cluster:** `room_id`. **Partition:** tidak perlu (grain tahunan, volume kecil).
**Cakupan M5.1:** baris 11.

#### `fact_maintenance_property_benchmark_yearly`
**Grain:** 1 baris per `property_id` × `year`.
**Kolom:** `property_id` (FK), `year` (INT64), `tickets_per_room`, `building_age_years` (dari `dim_property.opening_date`), `tickets_per_room_normalized`.
**Cluster:** `property_id`.
**Cakupan M5.1:** baris 12.

#### `fact_maintenance_technician_daily`
**Grain:** 1 baris per `assigned_staff_id` (FK `dim_employee`) × `period_date`.
**Kolom:** `assigned_staff_id` (FK), `period_date` (DATE), `ticket_count`, `labor_hours`.
**Partition:** `period_date`. **Cluster:** `assigned_staff_id`.
**Cakupan M5.1:** baris 13.

---

### Spa & Event

#### `fact_spa_daily`
**Grain:** 1 baris per `property_id` × `period_date`.
**Kolom:** `property_id` (FK), `period_date` (DATE), `revenue`, `booking_count`, `walk_in_ratio`, `avg_lead_time_days`, `median_lead_time_days`, `cancellation_rate`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** §4.1 baris 1, 4, 6, 7.

#### `fact_spa_customer_type_daily`
**Grain:** 1 baris per `property_id` × `customer_type_id` × `period_date`.
**Kolom:** `property_id` (FK), `customer_type_id` (FK), `period_date` (DATE), `revenue`, `visit_count`, `revenue_per_visit`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** §4.1 baris 2.

#### `fact_spa_service_daily`
**Grain:** 1 baris per `property_id` × `service_id` (FK `dim_spa_service`) × `period_date`.
**Kolom:** `property_id` (FK), `service_id` (FK), `period_date` (DATE), `booking_count`, `revenue`, `revenue_share_pct`.
**Partition:** `period_date`. **Cluster:** `property_id`, `service_id`.
**Cakupan M5.1:** §4.1 baris 3, 5.

#### `fact_event_venue_daily`
**Grain:** 1 baris per `venue_id` (FK `dim_venue`) × `period_date`.
**Kolom:** `venue_id` (FK), `period_date` (DATE), `bookings_pipeline_count`, `revenue_pipeline`, `utilization_rate`, `mom_revenue_growth`, `yoy_revenue_growth`, `low_utilization_streak_days` (untuk deteksi utilisasi rendah berulang).
**Partition:** `period_date`. **Cluster:** `venue_id`.
**Cakupan M5.1:** §4.2 baris 1 (bagian venue), 2, 3, 6.

#### `fact_event_property_daily`
**Grain:** 1 baris per `property_id` × `period_date`.
**Kolom:** `property_id` (FK), `period_date` (DATE), `cancellation_rate`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** §4.2 baris 4.

#### `fact_event_type_daily`
**Grain:** 1 baris per `property_id` × `event_type_id` × `period_date`.
**Kolom:** `property_id` (FK), `event_type_id` (FK), `period_date` (DATE), `event_count`, `revenue`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** §4.2 baris 5.

### HR

**Catatan:** Watchlist gejala pra-resign (baris 5, "Kebutuhan Khusus kategori B" di M5.1) **tidak** didesain di sini — dipisah ke Task 8 sesuai Keputusan #9 (karakter within-entity-over-time berbeda dari fact table agregat biasa).

#### `fact_hr_attendance_daily`
**Grain:** 1 baris per `property_id` × `department_id` × `period_date`.
**Kolom:** `property_id` (FK), `department_id` (FK), `period_date` (DATE), `present_count`, `late_count`, `leave_count`, `absent_count`, `overtime_hours_total`.
**Partition:** `period_date`. **Cluster:** `property_id`, `department_id`.
**Cakupan M5.1:** baris 1, 2.

#### `fact_hr_employee_monthly`
**Grain:** 1 baris per `employee_id` (FK `dim_employee`) × `period` (bulanan/periode review).
**Kolom:** `employee_id` (FK), `period_date` (DATE, awal bulan/periode), `overtime_hours`, `overtime_vs_dept_avg`, `late_rate`, `late_vs_dept_avg`, `latest_performance_score`.
**Partition:** `period_date`. **Cluster:** `employee_id`.
**Cakupan M5.1:** baris 3, 4, 6 (tren antar periode diturunkan via query lintas baris periode berbeda pada tabel yang sama, bukan kolom terpisah).

#### `fact_hr_turnover_monthly`
**Grain:** 1 baris per `property_id` × `department_id` × `period_date`.
**Kolom:** `property_id` (FK), `department_id` (FK), `period_date` (DATE), `turnover_rate`, `mom_growth`, `yoy_growth`.
**Partition:** `period_date`. **Cluster:** `property_id`, `department_id`.
**Cakupan M5.1:** baris 7.

#### `fact_hr_headcount_status_daily`
**Grain:** 1 baris per `property_id` × `department_id` × `status_id` (FK `dim_employee_status`) × `period_date` (snapshot).
**Kolom:** `property_id` (FK), `department_id` (FK), `status_id` (FK), `period_date` (DATE), `employee_count`.
**Partition:** `period_date`. **Cluster:** `property_id`, `department_id`.
**Cakupan M5.1:** baris 8.

#### `fact_hr_performance_department_monthly`
**Grain:** 1 baris per `property_id` × `department_id` × `period_date`.
**Kolom:** `property_id` (FK), `department_id` (FK), `period_date` (DATE), `avg_performance_score`.
**Partition:** `period_date`. **Cluster:** `property_id`, `department_id`.
**Cakupan M5.1:** baris 9.

#### `fact_hr_performance_by_status_monthly`
**Grain:** 1 baris per `property_id` × `status_id` (FK `dim_employee_status`) × `period_date`.
**Kolom:** `property_id` (FK), `status_id` (FK), `period_date` (DATE), `avg_performance_score`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 10 (korelasi kinerja-retensi — perbandingan `status_id`='resigned'/'terminated' vs `status_id`='active' dilakukan di query, bukan kolom terpisah).

---

### Corporate/Financial

**Catatan disambiguasi:** Kolom "department" pada `payroll` merujuk ke **unit organisasi karyawan** (`dim_department`, sama seperti HR) — **bukan** `dim_business_line` (USALI). Payroll terikat ke karyawan yang punya departemen organisasi, bukan baris lini bisnis `financial_summary`. Tabel `fact_payroll_*` di bawah pakai `dim_department`, sedangkan tabel `fact_financial_*` yang bersumber dari `financial_summary` pakai `dim_business_line`.

#### `fact_financial_business_line_monthly`
**Grain:** 1 baris per `property_id` × `business_line_id` (FK `dim_business_line`) × `period_date`.
**Kolom:** `property_id` (FK), `business_line_id` (FK), `period_date` (DATE), `revenue`, `expense`, `profit`, `margin_pct`.
**Partition:** `period_date`. **Cluster:** `property_id`, `business_line_id`.
**Cakupan M5.1:** baris 1, 4, 13 (`Corporate Overhead` adalah salah satu nilai `dim_business_line`, tidak perlu tabel terpisah — lihat Keputusan/temuan M5.1 "Overhead Korporat").
**Catatan wajib:** margin per lini bisnis (baris 4) HARUS filter `business_line_id` ke `Room`/`F&B`/`Spa&Event` saja saat dipakai untuk metrik "departmental margin" — jangan sertakan `Overall`/`Corporate Overhead` (risiko double counting, ditegaskan sejak M5.1).

#### `fact_financial_overall_monthly`
**Grain:** 1 baris per `property_id` × `period_date` (setara baris `Overall` di `financial_summary`).
**Kolom:** `property_id` (FK), `period_date` (DATE), `gop`, `gop_margin_pct`, `mom_gop_growth`, `yoy_gop_growth`, `undistributed_expense_admin_general`, `undistributed_expense_sales_marketing`, `undistributed_expense_utilities`, `undistributed_expense_property_maintenance`, `undistributed_expense_it`, `overhead_ratio`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 2, 3, 5.

#### `fact_financial_revenue_runrate_daily`
**Grain:** 1 baris per `property_id` × `period_date`.
**Kolom:** `property_id` (FK), `period_date` (DATE), `revenue_runrate`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 6.

#### `fact_payroll_department_monthly`
**Grain:** 1 baris per `property_id` × `department_id` (FK `dim_department`) × `period_date`.
**Kolom:** `property_id` (FK), `department_id` (FK), `period_date` (DATE), `base_salary_total`, `service_charge_total`, `overtime_pay_total`, `thr_total`, `deduction_total`, `net_salary_total`, `mom_growth`.
**Partition:** `period_date`. **Cluster:** `property_id`, `department_id`.
**Cakupan M5.1:** baris 7.

#### `fact_financial_service_charge_daily`
**Grain:** 1 baris per `property_id` × `period_date`.
**Kolom:** `property_id` (FK), `period_date` (DATE), `service_charge_pool`, `occupancy_rate` (cross-domain, precompute — Keputusan #6), `deviation_from_correlation`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 8.

#### `fact_financial_labor_cost_monthly`
**Grain:** 1 baris per `property_id` × `period_date`.
**Kolom:** `property_id` (FK), `period_date` (DATE), `labor_cost_pct_revenue`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 9.

#### `fact_payroll_access_level_monthly`
**Grain:** 1 baris per `property_id` × `access_level_id` (FK `dim_access_level`) × `period_date`.
**Kolom:** `property_id` (FK), `access_level_id` (FK), `period_date` (DATE), `service_charge_total`, `base_salary_total`, `service_charge_to_base_ratio`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 10.

#### `fact_financial_business_line_group_monthly`
**Grain:** 1 baris per `business_line_id` (FK `dim_business_line`) × `period_date` (grup, lintas 5 properti — tanpa `property_id`).
**Kolom:** `business_line_id` (FK), `period_date` (DATE), `group_revenue`, `revenue_share_pct`.
**Partition:** `period_date`. **Cluster:** `business_line_id`.
**Cakupan M5.1:** baris 11.

#### `fact_financial_property_benchmark_monthly`
**Grain:** 1 baris per `property_id` × `period_date`.
**Kolom:** `property_id` (FK), `period_date` (DATE), `gop_margin_rank`.
**Partition:** `period_date`. **Cluster:** `property_id`.
**Cakupan M5.1:** baris 12.

### Kasus Khusus Lintas Domain

Kedua tabel di bawah **sengaja terpisah** dari fact table utama domainnya (Keputusan #9) — grain/karakternya fundamental berbeda dari metrik agregat historis biasa.

#### `fact_revenue_pace_booking_snapshot`
**Grain:** 1 baris per `property_id` × `room_type_id` × `stay_date` (tanggal check-in masa depan) × `snapshot_date` (tanggal snapshot diambil, "as of").
**Kolom:** `property_id` (FK), `room_type_id` (FK), `stay_date` (DATE), `snapshot_date` (DATE), `rooms_sold_asof`, `rooms_available_asof`.
**Partition:** `snapshot_date` (setiap hari snapshot baru masuk partition sendiri). **Cluster:** `property_id`, `stay_date`.
**Cakupan M5.1:** "Kebutuhan Khusus kategori A" (pace booking).
**Catatan penting untuk M5.3:** tabel ini secara desain **append-only** (baris `snapshot_date` lama tidak pernah diupdate, hanya ditambah baris baru tiap hari) — beda karakter dari seluruh fact table lain di dokumen ini yang full-refresh mengikuti pola `mart_cleaned`/`mart_aggregated` di bawah BigQuery Sandbox mode (lihat `docs/keputusan-tertunda.md` "Aktivasi billing GCP"). Bagaimana append-only ini didamaikan dengan constraint "DML diblokir total" di Sandbox mode **belum diputuskan** — pertanyaan implementasi eksplisit untuk M5.3, bukan diselesaikan di sini (M5.2 hanya menjamin strukturnya benar).

#### `fact_hr_watchlist_monthly`
**Grain:** 1 baris per `employee_id` (FK `dim_employee`) × `period_date`.
**Kolom:** `employee_id` (FK), `period_date` (DATE), `current_absence_rate`, `baseline_absence_rate` (rata-rata historis individu tersebut), `current_late_rate`, `baseline_late_rate`, `absence_deviation_ratio`, `late_deviation_ratio`.
**Partition:** `period_date`. **Cluster:** `employee_id`.
**Cakupan M5.1:** "Kebutuhan Khusus kategori B" (watchlist gejala pra-resign).
**Catatan:** hanya menyimpan rasio deviasi mentah, **tidak** ada kolom flag "masuk watchlist" — threshold "di luar kebiasaan" belum ditentukan (M5.1 "Kebutuhan Khusus kategori C"), konsisten Keputusan #7. Klasifikasi watchlist final ditentukan di layer konsumen (chatbot/analyst) atau M5.3 setelah threshold diputuskan.

---

## Audit PII

Audit menyeluruh seluruh dimension table dan fact table di atas untuk kolom yang berpotensi menyentuh domain RBAC `guests_pii`, `guests_profile`, atau `employees_directory` (cakupan diperluas — Keputusan #8). Setiap kolom yang teridentifikasi punya keputusan eksplisit di bawah — tidak ada yang masuk skema tanpa keputusan sadar (KK#3).

| Kolom | Tabel | Domain RBAC | Keputusan | Alasan |
|---|---|---|---|---|
| `full_name` | `dim_employee` | `employees_directory` | **Diteruskan apa adanya, tidak di-mask** | Name-resolution eksplisit diminta banyak persona chatbot (HR Staff, Finance Staff, F&B Manager, dst) — kebutuhan bisnis nyata, bukan insidental. Akses granular (siapa boleh lihat) diatur di RBAC layer (Milestone 4.1-4.3, view + kredensial), bukan masking di level data — konsisten prinsip *defense in depth* dokumen arsitektur (kontrol akses berlapis, bukan penghilangan data di sumbernya). |
| `loyalty_tier_name` | `dim_loyalty_tier` | `guests_profile` | **Diteruskan apa adanya** | Label kategori agregat (mis. "Gold", "Silver"), bukan atribut individual. Fact table pemakainya (`fact_revenue_loyalty_daily`) hanya menyimpan hitungan/agregat per bucket per properti per hari — tidak pernah ada baris per-tamu, sehingga tidak ada risiko re-identifikasi individu dari kombinasi ini. |
| `group_name` | `dim_nationality_group` | `guests_profile` | **Diteruskan apa adanya** | Sama alasan `loyalty_tier_name` — sudah dikategorikan jadi 2 bucket (Domestik/Mancanegara) saat transformasi, bukan nilai `nationality` individual mentah dari `guests`. |

### Konfirmasi: tidak ada kolom `guests_pii` (email, phone) di `mart_aggregated`

Ditelusuri ulang seluruh 45 fact table + 27 dimension table (23 awal + 4 amendemen) di dokumen ini — **tidak ada satu pun kolom** yang menyimpan `email`, `phone`, atau `guest_id` individual. Seluruh kebutuhan kontak tamu yang diminta persona chatbot (Front Office Staff — konfirmasi booking; Revenue Manager — retensi loyalty tinggi; Spa & Event Manager — eskalasi komplain; CEO — kasus jarang komplain besar) tetap dilayani **row-level dari `mart_cleaned.guests`**, bukan `mart_aggregated` — konsisten dengan pembagian row-level vs agregat yang sudah ditegaskan di M5.1. Ini bukan kebetulan: setiap metrik yang menyentuh populasi tamu di skema ini (loyalty, nationality, repeat guest rate, capture rate) sudah dalam bentuk hitungan/rasio teragregasi sejak didesain, tidak pernah butuh identitas individual untuk dihitung.

**Kesimpulan audit:** Tidak ada kolom yang perlu masking/anonymization di `mart_aggregated` — bukan karena PII diabaikan, tapi karena desain skema (star schema teragregasi, tanpa grain per-tamu) secara struktural sudah tidak pernah memuat PII tamu mentah sejak awal. Satu-satunya data personal yang diteruskan apa adanya (`dim_employee.full_name`) adalah data internal staf dengan kebutuhan bisnis eksplisit, diamankan lewat RBAC layer terpisah (di luar scope M5.2).
