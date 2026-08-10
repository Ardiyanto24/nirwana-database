# View dan Query Pattern — AI Chatbot

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 4.2 (`milestones/4.2-view-akses-granular-per-domain/`) |
| **Input utama** | `docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md` (Milestone 4.1) |
| **Lokasi teknis** | Schema `chatbot_views` di serving PostgreSQL project (terpisah dari `mart_aggregated`/`mart_cleaned`/`analyst_views`) |
| **Dipakai oleh** | Milestone 4.3 (kredensial), 4.4 (API) |
| **Status** | Selesai — 67 view (56 agregat/dimension + 17 lookup row-level + 2 guest PII, `properties_ref`/`employees_directory` masing-masing 1 view) |

---

## Cara Membaca Dokumen Ini

Inventaris seluruh view di schema `chatbot_views`, sumber SQL di `scripts/chatbot_views/views_*.sql` (1 file per domain). Beda dari `analyst_views` (M3.2, hanya view agregat): setiap domain di sini punya **2 lapis** — view agregat di atas `mart_aggregated` (pola identik M3.2: dimension di-`LEFT JOIN` ke nama) **dan** view lookup row-level baru di atas `mart_cleaned` (kolom dikurasi, bukan GRANT langsung ke tabel mentah — lihat `decisions.md` Keputusan #2). `property_id` selalu kolom mentah tanpa filter di-hardcode (M4.1 Keputusan #5) — filter `own_property`/`all_properties` sesungguhnya jadi tanggung jawab Milestone 4.4 (API).

## Reservation (8 agregat + 2 lookup)

| View | Sumber | Catatan |
|---|---|---|
| `v_reservation_room_type_daily` | `fact_revenue_room_type_daily` | Dinamai `reservation` (bukan `revenue` seperti `analyst_views`) — konsisten nama `data_domain` di `role_permissions` |
| `v_reservation_channel_daily` | `fact_revenue_channel_daily` | — |
| `v_reservation_los_daily` | `fact_revenue_los_daily` | — |
| `v_reservation_property_daily` | `fact_revenue_property_daily` | — |
| `v_reservation_gop_impact_monthly` | `fact_revenue_gop_impact_monthly` | Cross-domain, `gop_margin` dari `financial_summary` baris `Overall` |
| `v_reservation_pricing_deviation` | `fact_revenue_pricing_deviation` | — |
| `v_reservation_loyalty_daily` | `fact_revenue_loyalty_daily` | — |
| `v_reservation_nationality_daily` | `fact_revenue_nationality_daily` | — |
| `v_lookup_bookings` | `mart_cleaned.bookings` | Detail 1 booking, status hari ini, riwayat per `guest_id` |
| `v_lookup_daily_occupancy` | `mart_cleaned.daily_occupancy` | Ketersediaan kamar real-time |

**Dikecualikan:** `fact_revenue_pace_booking_snapshot` (Known Gap M3.1, status implementasi append-only belum final, berlaku sama di sini).

## F&B (8 agregat + 3 lookup)

| View | Sumber | Catatan |
|---|---|---|
| `v_fnb_outlet_daily` s.d. `v_fnb_ingredient_price_daily` | `fact_fnb_*` | Identik struktur `analyst_views` |
| `v_lookup_fnb_inventory` | `mart_cleaned.fnb_inventory` | `property_id` di-join dari `fnb_outlets` (tidak native) |
| `v_lookup_fnb_transactions` | `mart_cleaned.fnb_transactions` | `property_id` di-join dari `fnb_outlets`; untuk lookup "hari ini" (granularitas harian `mart_aggregated` bisa telat) |
| `v_lookup_recipe_bom` | `mart_cleaned.recipe_bom` | Tanpa `property_id` — komposisi bahan bersifat global |

**Tidak ada view basket analysis** — business rule kritis M3.1, berlaku sama: grain per struk hilang total di agregat.

## Facility/Ops (9 agregat + 3 lookup)

| View | Sumber | Catatan |
|---|---|---|
| `v_facility_room_status_daily` s.d. `v_maintenance_technician_daily` | `fact_facility_*`/`fact_housekeeping_*`/`fact_maintenance_*` | `v_maintenance_ticket_daily` reuse SLA threshold logic verbatim M3.2 |
| `v_lookup_rooms` | `mart_cleaned.rooms` | Status kamar real-time |
| `v_lookup_housekeeping_log` | `mart_cleaned.housekeeping_log` | `property_id` di-join dari `rooms` (tidak native) |
| `v_lookup_maintenance_tickets` | `mart_cleaned.maintenance_tickets` | Detail 1 tiket, riwayat per `room_id` |

**Performa individu staff** (`v_housekeeping_staff_daily`, `v_maintenance_technician_daily`, `v_lookup_housekeeping_log.staff_id`, `v_lookup_maintenance_tickets.assigned_staff_id`) — filtering "hanya lihat data sendiri" untuk role Staff adalah tanggung jawab Milestone 4.4, bukan view ini (carry-over business rule M3.1 #11).

**Koreksi M4.4**: `v_housekeeping_staff_daily` dan `v_maintenance_technician_daily` awalnya tidak mengekspos `property_id` sama sekali (cuma `staff_id`/`assigned_staff_id`+`period_date`), meski `dim_employee` yang sudah di-join di kedua view itu punya kolomnya — ditemukan saat Milestone 4.4 merancang filter `own_property`, tanpa perbaikan filter itu tidak bisa diterapkan di kedua view ini. Ditambal dengan menambahkan `e.property_id` di akhir `SELECT` (`scripts/chatbot_views/views_facility.sql`), diverifikasi 0 baris `NULL`.

## Spa & Event (6 agregat + 3 lookup)

| View | Sumber | Catatan |
|---|---|---|
| `v_spa_daily` s.d. `v_event_type_daily` | `fact_spa_*`/`fact_event_*` | Identik struktur `analyst_views` |
| `v_lookup_spa_bookings` | `mart_cleaned.spa_bookings` | `guest_id` nullable (walk-in) |
| `v_lookup_event_bookings` | `mart_cleaned.event_bookings` | Tidak ada `guest_id` sama sekali (lihat catatan Guests di bawah) |
| `v_lookup_venues` | `mart_cleaned.venues` | Kapasitas maksimal |

**Tidak ada view repeat-client-event/cross-sell spa×event** — business rule kritis M3.1, berlaku sama.

## HR (8 agregat + 2 lookup)

| View | Sumber | Catatan |
|---|---|---|
| `v_hr_attendance_daily` s.d. `v_hr_watchlist_monthly` | `fact_hr_*` | `property_id`/`property_name` sudah live sejak awal (M5.7 sudah selesai sebelum M4.2 dimulai) — tidak perlu pola "append di akhir" |
| `v_lookup_staff_shifts` | `mart_cleaned.staff_shifts` | `property_id` di-join dari `employees` (tidak native) |
| `v_lookup_employee_performance` | `mart_cleaned.employee_performance` | `property_id` di-join dari `employees` |

**Tidak ada view payroll** — business rule kritis M3.1 #2, berlaku sama: eksklusif domain `financial`.

## Financial (9 agregat + 2 lookup)

| View | Sumber | Catatan |
|---|---|---|
| `v_financial_departmental_margin` | `fact_financial_business_line_monthly` | **`WHERE line_name NOT IN ('Overall','Corporate Overhead')` ditanam permanen** — diverifikasi terprogram hanya berisi `Room`/`F&B`/`Spa&Event` |
| `v_financial_gop_overhead` s.d. `v_financial_property_benchmark_monthly` | `fact_financial_*`/`fact_payroll_*` | Identik struktur `analyst_views` |
| `v_lookup_financial_summary` | `mart_cleaned.financial_summary` | Termasuk baris `Overall`/`Corporate Overhead` — pemanggil wajib filter sendiri sesuai kebutuhan (GOP vs departmental) |
| `v_lookup_payroll` | `mart_cleaned.payroll` | `property_id` di-join dari `employees` |

## Properties_ref (1 view)

| View | Sumber |
|---|---|
| `v_properties_ref` | `mart_aggregated.dim_property` (`property_id`, `property_name`, `region`, `opening_date`) — cukup untuk seluruh kebutuhan, tidak perlu `mart_cleaned.properties` |

## Employees_directory (1 view)

| View | Sumber |
|---|---|
| `v_employees_directory` | `mart_aggregated.dim_employee` + join `dim_property`/`dim_department`/`dim_access_level` — `full_name` diteruskan apa adanya (diaudit PII aman, M5.2) |

## Guests_pii / Guests_profile (2 view di atas 1 tabel fisik)

| View | Kolom | Catatan |
|---|---|---|
| `guests_contact_view` | `guest_id`, `full_name`, `email`, `phone`, `last_active_property_id` | Tidak ada kolom `guests_profile` |
| `guests_profile_view` | `guest_id`, `loyalty_tier`, `nationality`, `registered_date`, `last_active_property_id` | Tidak ada kolom kontak |

`last_active_property_id` diturunkan dari `UNION ALL` `bookings` + `spa_bookings` (guest terakhir kali aktif di properti mana), diambil via `DISTINCT ON` 1x scan agregat — **bukan** `LEFT JOIN LATERAL` per baris (draf awal timeout >120 detik untuk 24.893 guest, diperbaiki jadi 0.44 detik, lihat `logs.md`). `event_bookings` **tidak** ikut di-`UNION` — tabel itu tidak punya kolom `guest_id` sama sekali (koreksi ditemukan saat implementasi, klien event diidentifikasi lewat `client_name` teks bebas).

---

## Verifikasi

Total 67 view aktif di `information_schema.views` schema `chatbot_views`. KK1 (kolom relevan domain saja) dicek manual per file SQL. KK2 (pemisahan PII vs profile) diverifikasi terprogram — `guests_profile_view` tidak punya `email`/`phone`/`full_name`, `guests_contact_view` tidak punya `loyalty_tier`/`nationality`. KK3 (filter `own_property`/`all_properties` bekerja) diverifikasi pada 6 view representatif (agregat dan lookup, termasuk yang butuh join `property_id`) — masing-masing menghasilkan baris berbeda dan tidak kosong untuk `property_id` berbeda. Detail bukti verifikasi ada di `milestones/4.2-view-akses-granular-per-domain/{logs.md,report.md}`.
