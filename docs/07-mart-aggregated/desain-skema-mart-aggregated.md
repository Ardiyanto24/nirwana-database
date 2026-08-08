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

---

## Fact Tables

*(diisi Fase 1-4 — Task 2-8)*

---

## Audit PII

*(diisi Fase 5 — Task 9)*
