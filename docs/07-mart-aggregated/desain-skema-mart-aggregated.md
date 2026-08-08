# Desain Struktur Tabel `mart_aggregated`

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 5.2 (`milestones/5.2-desain-struktur-tabel-mart-aggregated/`) |
| **Input utama** | `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md` (Milestone 5.1) — 94 baris metrik terkonsolidasi lintas 6 domain |
| **Dipakai oleh** | Milestone 5.3 (implementasi transformasi SQL + data dictionary penuh), `04-serving-data-analyst.md`, `05-serving-ai-chatbot.md` |
| **Status** | Draft — dibangun bertahap per checkpoint Milestone 5.2 |

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

23 dimension table, dikelompokkan per domain asal (beberapa dipakai lintas domain — conformed dimensions).

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
| `dim_ingredient` | `ingredient_id` (PK), `ingredient_name` | Natural key | `ingredient_price_history` | Task 3 (F&B) |

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

*(diisi lanjut Fase 3-4 — Task 6-8)*

---

## Audit PII

*(diisi Fase 5 — Task 9)*
