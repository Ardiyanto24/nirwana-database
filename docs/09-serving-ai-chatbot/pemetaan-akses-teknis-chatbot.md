# Pemetaan Akses Teknis AI Chatbot

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 4.1 (`milestones/4.1-pemetaan-rbac-struktur-akses-teknis/`) |
| **Input utama** | `corporate_master.role_permissions` production (77 baris, 20 role, 10 `data_domain`, diverifikasi sinkron dengan `rancangan-rbac-ai-chatbot.md` Bagian 2), `docs/07-mart-aggregated/DataSchema-mart-aggregated.md`, `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md` (reuse mapping domain operasional), 3 dokumen kebutuhan persona (`pemetaan-kebutuhan-chatbot-layer-staff/manager/korporat.md`) |
| **Dipakai oleh** | Milestone 4.2 (view), 4.3 (kredensial), 4.4 (API) |
| **Status** | Selesai |

---

## Cara Membaca Dokumen Ini

Dokumen ini menerjemahkan 10 `data_domain` di `role_permissions` menjadi struktur teknis konkret: tabel `mart_aggregated` mana untuk kebutuhan agregat/tren, tabel `mart_cleaned` mana untuk kebutuhan lookup row-level (lihat revisi boundary Lapis 2 di `milestones/4.1-.../decisions.md` Keputusan #1), dan bagaimana filter properti diterapkan. 6 domain operasional (`reservation`, `fnb`, `facility`, `spa_event`, `hr`, `financial`) memakai ulang tabel referensi domain→fact/dim dari `pemetaan-pola-akses-analyst.md` (M3.1) untuk sisi agregat — tidak didesain ulang dari nol — ditambah pemetaan row-level baru khusus kebutuhan lookup real-time chatbot (beda karakter dari Data Analyst yang aggregate-first). 4 domain granular (`properties_ref`, `employees_directory`, `guests_pii`, `guests_profile`) adalah pemetaan baru, tidak ada preseden M3.1.

---

## 1. Mekanisme Filter `own_property` vs `all_properties`

**Keputusan (lihat `decisions.md` Keputusan #5):** Filter properti diterapkan sebagai **parameter runtime di layer API (Milestone 4.4)**, divalidasi terhadap identitas/properti user yang dikirim Lapis 1 (application layer chatbot) — **bukan** lewat kredensial Postgres terpisah per properti seperti pola `property_gm_analyst_reader` di Milestone 3.5.

**Kenapa beda dari pola Data Analyst (M3.5):** Data Analyst M3.5 punya 1 kredensial statis per 1 orang tetap (mis. 1 GM = 1 role Postgres dengan property_id dibakar di level role). Chatbot melayani banyak individu berbeda (ratusan karyawan) secara dinamis lewat kredensial yang sama per kelompok akses (Milestone 4.3) — membuat 1 role Postgres per staff tidak skalabel. Sebagai gantinya:

1. Setiap view (Milestone 4.2) di domain yang punya konsep properti **selalu** menyertakan kolom `property_id` mentah (tidak difilter di level view).
2. API (Milestone 4.4) menerima `property_id` yang diklaim Lapis 1 sebagai bagian request, memvalidasinya terhadap `access_scope` role tersebut di `role_permissions`:
   - `access_scope = 'own_property'` → API **wajib** menyuntikkan `WHERE property_id = :user_property_id` ke query, mengabaikan/menolak `property_id` lain yang diminta.
   - `access_scope = 'all_properties'` → API meneruskan `property_id` apa pun yang diminta (termasuk tanpa filter, untuk benchmarking lintas 5 properti).
3. Kredensial Postgres (Milestone 4.3) tetap terbatas per `data_domain` (defense-in-depth terhadap domain yang salah), tapi **tidak** terbatas per properti — pembatasan properti murni tanggung jawab API, bukan database.

**Implikasi untuk `guests_pii`/`guests_profile`:** Tabel `guests` (`mart_cleaned`) tidak punya kolom `property_id` (dikonfirmasi terhadap `Metadata.md`) — properti tamu diturunkan secara implisit lewat properti booking/transaksi terkait (lihat §5-6).

---

## 2. Tabel Pemetaan: 10 `data_domain` → Struktur Teknis

### 2.1 `reservation`

| Field | Isi |
|---|---|
| **Sensitivitas** | Rendah–Sedang |
| **Tabel `mart_aggregated`** | `fact_revenue_room_type_daily`, `fact_revenue_channel_daily`, `fact_revenue_los_daily`, `fact_revenue_property_daily`, `fact_revenue_gop_impact_monthly`, `fact_revenue_pricing_deviation`, `fact_revenue_loyalty_daily`, `fact_revenue_nationality_daily` (+ kasus khusus `fact_revenue_pace_booking_snapshot`, append-only, jangan digabung agregasi reguler) — dim: `dim_property`, `dim_room_type`, `dim_channel`, `dim_loyalty_tier`, `dim_nationality_group`, `dim_pricing_reason` |
| **Tabel `mart_cleaned` (row-level, baru — Keputusan #1)** | `bookings` (status booking hari ini, detail 1 booking spesifik, riwayat booking 1 tamu), `daily_occupancy` (ketersediaan kamar per room_type real-time) |
| **Filter properti** | `property_id` — lihat §1. `bookings`/`daily_occupancy` sudah punya `property_id` langsung. |
| **Catatan** | `pricing_history.reason` (alasan strategi harga) **tidak** termasuk row-level domain ini di level Staff — cuma tersedia lewat `fact_revenue_pricing_deviation` (agregat), levelnya Revenue Manager ke atas, konsisten temuan `pemetaan-kebutuhan-chatbot-layer-staff.md` §1. |

### 2.2 `fnb`

| Field | Isi |
|---|---|
| **Sensitivitas** | Rendah |
| **Tabel `mart_aggregated`** | `fact_fnb_outlet_daily`, `fact_fnb_category_daily`, `fact_fnb_hourly`, `fact_fnb_customer_type_daily`, `fact_fnb_menu_item_daily`, `fact_fnb_waste_daily`, `fact_fnb_inventory_status`, `fact_fnb_ingredient_price_daily` — dim: `dim_outlet`, `dim_outlet_type`, `dim_fnb_category`, `dim_menu_item`, `dim_waste_reason`, `dim_ingredient` |
| **Tabel `mart_cleaned` (row-level, baru)** | `fnb_inventory` (stok per item real-time), `fnb_transactions` (menu terlaris/total penjualan hari berjalan — granularitas harian di `mart_aggregated` bisa telat untuk "hari ini"), `recipe_bom` (komposisi bahan per menu) |
| **Filter properti** | Via `dim_outlet.property_id` / `fnb_transactions.outlet_id` → outlet selalu terikat 1 properti (pola sama M3.1). |
| **Catatan Gap (carry-over dari dokumen kebutuhan)** | Tidak ada tabel harga jual menu resmi — proxy dari `unit_price` transaksi terakhir. Tidak ada tabel target/budget penjualan. |

### 2.3 `facility`

| Field | Isi |
|---|---|
| **Sensitivitas** | Rendah (operasional), **Sedang** untuk data performa individu staff |
| **Tabel `mart_aggregated`** | `fact_facility_room_status_daily`, `fact_housekeeping_room_type_daily`, `fact_housekeeping_property_daily`, `fact_housekeeping_staff_daily`, `fact_maintenance_ticket_daily`, `fact_maintenance_cost_daily`, `fact_maintenance_room_recurrence_yearly`, `fact_maintenance_property_benchmark_yearly`, `fact_maintenance_technician_daily` — dim: `dim_facility_area`, `dim_issue_type`, `dim_priority`, `dim_room`, `dim_property`, `dim_employee` |
| **Tabel `mart_cleaned` (row-level, baru)** | `rooms` (status kamar tertentu saat ini), `housekeeping_log` (durasi pembersihan, status delayed, `staff_id`), `maintenance_tickets` (detail 1 tiket, riwayat per `room_id`, `parts_replaced`) |
| **Filter properti** | `property_id`. **Filter tambahan wajib untuk Staff**: `staff_id`/`assigned_staff_id` = identitas user sendiri saat role Staff meminta data performa individu (housekeeping duration, maintenance ticket milik sendiri) — Manager ke atas boleh lihat seluruh staff timnya tanpa filter ini (business rule dari `pemetaan-kebutuhan-chatbot-layer-staff.md` §3-4, carry-over `pemetaan-pola-akses-analyst.md` rule #11). Ditegakkan di API (M4.4), bukan di view. |
| **Catatan Gap** | Tidak ada kolom catatan/permintaan khusus tamu di `rooms`/`housekeeping_log`. Threshold SLA per `priority` belum diputuskan (gap parameter, bukan gap data). |

### 2.4 `spa_event`

| Field | Isi |
|---|---|
| **Sensitivitas** | Rendah |
| **Tabel `mart_aggregated`** | `fact_spa_daily`, `fact_spa_customer_type_daily`, `fact_spa_service_daily`, `fact_event_venue_daily`, `fact_event_property_daily`, `fact_event_type_daily` — dim: `dim_spa_service`, `dim_venue`, `dim_venue_type`, `dim_event_type` |
| **Tabel `mart_cleaned` (row-level, baru)** | `spa_bookings` (jadwal booking spa, `guest_id`), `event_bookings` (detail booking event, `client_name`), `venues` (kapasitas venue) |
| **Filter properti** | `property_id` langsung tersedia di ketiga tabel. |
| **Catatan Gap** | Tidak ada kolom terapis/staff penangan di `spa_bookings`. |

### 2.5 `hr`

| Field | Isi |
|---|---|
| **Sensitivitas** | Sedang |
| **Tabel `mart_aggregated`** | `fact_hr_attendance_daily`, `fact_hr_employee_monthly`, `fact_hr_employee_performance_semester`, `fact_hr_turnover_snapshot`, `fact_hr_headcount_status_daily`, `fact_hr_performance_department_semester`, `fact_hr_performance_by_status_semester`, `fact_hr_watchlist_monthly` — dim: `dim_shift_type`, `dim_employee_status`, `dim_employee`, `dim_department`, `dim_property` |
| **Tabel `mart_cleaned` (row-level, baru)** | `staff_shifts` (status kehadiran hari ini, `employee_id`), `employee_performance` (skor & `notes` performa terakhir 1 karyawan) |
| **Filter properti** | `property_id`, `department_id`. |
| **Business Rule Kritis (carry-over M3.1 rule #2)** | **Domain `hr` TIDAK PERNAH mencakup `payroll`** — payroll eksklusif domain `financial`. Berlaku identik untuk chatbot (segregation of duties). |

### 2.6 `financial`

| Field | Isi |
|---|---|
| **Sensitivitas** | Tinggi |
| **Tabel `mart_aggregated`** | `fact_financial_business_line_monthly`, `fact_financial_overall_monthly`, `fact_financial_revenue_runrate_daily`, `fact_payroll_department_monthly`, `fact_financial_service_charge_monthly`, `fact_financial_labor_cost_monthly`, `fact_payroll_access_level_monthly`, `fact_financial_business_line_group_monthly`, `fact_financial_property_benchmark_monthly` — dim: `dim_business_line`, `dim_access_level`, `dim_department`, `dim_property` |
| **Tabel `mart_cleaned` (row-level, baru)** | `financial_summary` (revenue/expense/profit/gop per departemen, baris `Overall`/`Corporate Overhead`), `payroll` (komponen payroll individual — termasuk domain `financial` per `rancangan-rbac-ai-chatbot.md`) |
| **Filter properti** | `property_id`. |
| **Business Rule Kritis (carry-over M3.1 rule #1)** | Metrik "departmental margin" dari `fact_financial_business_line_monthly` WAJIB filter `business_line_id IN ('Room','F&B','Spa&Event')` — jangan pernah sertakan `Overall`/`Corporate Overhead` (risiko double counting). GOP/overhead ratio WAJIB dari `fact_financial_overall_monthly`. |

### 2.7 `properties_ref`

| Field | Isi |
|---|---|
| **Sensitivitas** | Rendah |
| **Tabel `mart_aggregated`** | `dim_property` (`property_id`, `property_name`, `region`, `opening_date`) — cukup untuk seluruh kebutuhan (metadata ringan, sudah teraudit aman diteruskan apa adanya, M5.2). |
| **Tabel `mart_cleaned`** | Tidak diperlukan — `dim_property` sudah menjangkau kolom yang sama seperti `mart_cleaned.properties`. |
| **Filter properti** | `property_id` (own_property = 1 baris, all_properties = seluruh baris). |
| **Catatan** | Tidak ada gap. Domain paling sederhana dari 10 domain. |

### 2.8 `employees_directory`

| Field | Isi |
|---|---|
| **Sensitivitas** | Sedang–Tinggi |
| **Tabel `mart_aggregated`** | `dim_employee` (`employee_id`, `property_id`, `full_name`, `department_id`→`dim_department`, `access_level_id`) — `full_name` sudah diaudit PII M5.2 dan sengaja diteruskan apa adanya (kebutuhan name-resolution eksplisit, bukan insidental). |
| **Tabel `mart_cleaned` (row-level, opsional)** | `employees` — dipakai hanya kalau ada kolom di luar `dim_employee` yang dibutuhkan (mis. `status`, `hire_date`); default utamakan `dim_employee` karena sudah cukup untuk seluruh kebutuhan "resolve nama dari employee_id" di 3 dokumen persona. |
| **Filter properti** | `property_id`. |
| **Catatan** | Tidak ada gap data — beda dari `guests_pii`/`guests_profile`, domain ini **tidak** butuh perluasan boundary M4.1 karena `dim_employee` di `mart_aggregated` sudah cukup. |

### 2.9 `guests_pii`

| Field | Isi |
|---|---|
| **Sensitivitas** | Tinggi (PII) |
| **Tabel `mart_aggregated`** | **Tidak ada** — dikonfirmasi audit M5.2 (0 kolom PII individual di 46 fact + 27 dim table). |
| **Tabel `mart_cleaned` (row-level, baru — Keputusan #1)** | `guests`, kolom kontak: `guest_id`, `full_name`, `email`, `phone`. Lihat §3 (view `guests_contact_view`). |
| **Filter properti** | **`guests` tidak punya kolom `property_id`** (dikonfirmasi `Metadata.md`) — own_property diturunkan lewat join ke booking terkait (lihat §3, mekanisme join). |
| **Catatan** | Domain ini yang tadinya direkomendasikan lewat change request M5.6 — supersede, lihat `decisions.md` Keputusan #2. |

### 2.10 `guests_profile`

| Field | Isi |
|---|---|
| **Sensitivitas** | Sedang |
| **Tabel `mart_aggregated`** | Kategori agregat (`dim_loyalty_tier`, `dim_nationality_group`) hanya untuk metrik bucket (mis. `fact_revenue_loyalty_daily`) — **bukan** untuk lookup 1 tamu spesifik. |
| **Tabel `mart_cleaned` (row-level, baru — Keputusan #1)** | `guests`, kolom atribut analitis: `guest_id`, `loyalty_tier`, `nationality`, **tidak termasuk kolom kontak**. Riwayat booking via join ke `bookings.guest_id`. Lihat §3 (view `guests_profile_view`). |
| **Filter properti** | Sama seperti `guests_pii` — join ke booking terkait. |

### 2.11 `role_permissions` — Konfirmasi Eksplisit

**Tidak ada baris di tabel manapun di atas yang mengarah ke `corporate_master.role_permissions`.** Tabel ini tidak pernah menjadi target `SELECT` chatbot dalam skenario apa pun — bukan karena kebetulan tidak ada baris izinnya, tapi ditegaskan sadar sebagai batasan teknis di Lapis 2 (defense-in-depth terhadap kegagalan Lapis 1), konsisten `rancangan-rbac-ai-chatbot.md` Bagian 1.

---

## 3. Kontrak View `guests_pii` / `guests_profile` (untuk Milestone 4.2)

Dua view berbeda di atas tabel fisik `mart_cleaned.guests` yang sama (bukan dua tabel terpisah), sesuai `rancangan-rbac-ai-chatbot.md` Bagian 4.

### `guests_contact_view` (domain `guests_pii`)
```
guest_id, full_name, email, phone, last_active_property_id
```
`last_active_property_id` diturunkan dari `property_id` booking/transaksi guest_id tersebut yang paling baru di antara `bookings`, `spa_bookings`, `event_bookings` (guest tidak terikat 1 properti tetap — lihat `Metadata.md` "guests adalah master PELANGGAN"). Kolom ini yang dipakai API (M4.4) untuk menegakkan filter `own_property`.

### `guests_profile_view` (domain `guests_profile`)
```
guest_id, loyalty_tier, nationality, registered_date, last_active_property_id
```
Tidak ada kolom `full_name`/`email`/`phone` — pemisahan kolom murni sesuai `rancangan-rbac-ai-chatbot.md` Bagian 1 ("guests_profile: atribut analitis, tidak termasuk kontak"). Riwayat booking lengkap (row-level per booking) tetap query terpisah ke `bookings` (domain `reservation`), bukan kolom di view ini — konsisten prinsip "view tidak menduplikasi domain lain".

**Catatan implementasi (diteruskan ke M4.2):** kedua view butuh join `guests` ↔ `UNION` dari `bookings`/`spa_bookings`/`event_bookings` untuk `last_active_property_id` — perlu dicek performanya saat implementasi (kandidat index tambahan kalau lambat, pola sama M3.3).

---

## 4. Ringkasan Kelompok Kredensial (input untuk Milestone 4.3)

10 kelompok akses, 1 per `data_domain` (Keputusan #6 di `decisions.md`), masing-masing dengan `SELECT` ke kombinasi tabel `mart_aggregated`+`mart_cleaned` pada baris terkait di §2. Tidak ada kredensial yang menjangkau lebih dari 1 domain sekaligus — komposisi akses multi-domain per persona (mis. GM yang punya 7 domain operasional + 4 granular) ditangani di layer API (M4.4) dengan menggabungkan kredensial/scope sesuai `role_permissions` user tersebut, bukan lewat 1 kredensial super lebar.
