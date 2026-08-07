# Baseline Inventaris Data Production — Fase 1

**Hasil kerja Milestone 1.1** (`docs/03-implementation-plans/01-monitoring-data-production-fase1.md`)

| | |
|---|---|
| **Sumber data** | Supabase live (`SUPABASE_DB_URL`), diverifikasi read-only pada 2026-08-07 |
| **Dokumen rujukan** | `docs/01-architecture/Metadata.md`, `docs/01-architecture/DataSchema.md` |
| **Rubrik prioritas** | Lihat `milestones/1.1-inventarisasi-baseline-produksi/decisions.md` — skor gabungan (volume + kekritisan bisnis + konsumen downstream), rentang 3-9, dipetakan ke Tinggi (7-9) / Sedang (5-6) / Rendah (3-4) |
| **Status** | Task 1-7 selesai; Task 8 (report.md) menyusul |

> Dokumen ini adalah rujukan langsung untuk Milestone 1.2 (volume/freshness), 1.3 (kualitas data/anomali), dan 1.4 (schema drift). Tidak perlu analisis ulang dari nol.

---

## Temuan Penting Sebelum Membaca Tabel

1. **Nama tabel RBAC berbeda dari dokumentasi arsitektur.** `docs/01-architecture/DataSchema.md`/`Metadata.md` (v0.6) menyebut tabel RBAC sebagai `role_permissions_chatbot_v2`. Di database live, nama tabelnya adalah **`corporate_master.role_permissions`**. Isinya sudah versi v0.6 yang benar (77 baris, 10 `data_domain` granular, `permission_type` semua `read`) — hanya penamaan yang belum disinkronkan. **Seluruh tabel di bawah ini memakai nama live sebagai rujukan utama.** Direkomendasikan agar tim pemilik skema production menyamakan nama tabel dengan dokumentasi arsitektur (di luar scope Milestone 1.1 yang murni observasional).
2. **Ada 1 tabel tambahan di luar 23 tabel terdokumentasi**: `public._sim_state` (1 baris: `id`, `sim_date`, `last_run_at`). Ini tabel internal generator simulasi data, bukan tabel bisnis — **dikecualikan** dari inventaris di bawah dan dari cakupan Milestone 1.2-1.4.
3. **Volume live sedikit lebih tinggi dari `DataSchema.md`** (total 2.534.072 vs ~2.530.000 terdokumentasi) — selisih wajar karena data terus bertambah seiring operasional berjalan (sesuai catatan dokumen sumber), bukan indikasi masalah.
4. **6 schema Postgres di Supabase persis sama dengan 6 database logis** di dokumen arsitektur (`corporate_master`, `reservation_revenue`, `fnb_operations`, `facility_maintenance`, `spa_event`, `hr_finance`).

---

## Pemetaan 23 Tabel

Kolom **Skor** = Volume/frekuensi (1-3) + Kekritisan bisnis (1-3) + Konsumen downstream (1-3). Lihat `decisions.md` untuk definisi tiap komponen.

### 1. Schema `corporate_master`

| Tabel | Baris (live) | Skor | Prioritas | Kolom kritis bisnis | Kolom kotor/nullable yang sah |
|---|---|---|---|---|---|
| `properties` | 6 | 1+2+3=6 | **Sedang** | `total_rooms`, `star_rating` (dipakai kapasitas & benchmarking) | `total_rooms`/`star_rating` kosong untuk P06 (kantor pusat, sah — bukan properti tamu) |
| `employees` | 755 | 1+3+3=7 | **Tinggi** | `role_title` (kunci RBAC), `access_level`, `status` | `role_title` ~2% kosong (1,99% terverifikasi live); `department` 19 variasi penulisan untuk 8 nilai sebenarnya (**wajib normalisasi**, terverifikasi live); `hire_date` ~2% format `DD/MM/YYYY` |
| `guests` | 24.893 | 2+3+2=7 | **Tinggi** | `guest_id` (penentu populasi: G00001-G18000 tamu menginap vs G18001+ pelanggan lokal), `loyalty_tier` | `email` 3,97% kosong (live); `phone` 3,01% kosong (live) + 4 variasi format domestik; `nationality` kapitalisasi tidak konsisten; `full_name` ~2% typo; ~367 baris duplikat (guest_id G24501+) |
| `role_permissions` *(dok: `role_permissions_chatbot_v2`)* | 77 | 1+3+3=7 | **Tinggi** | `role_title`, `data_domain`, `access_scope` — jantung RBAC AI Chatbot | Tidak ada nilai kosong yang sah (matriks kontrol akses, harus selalu lengkap) |

### 2. Schema `reservation_revenue`

| Tabel | Baris (live) | Skor | Prioritas | Kolom kritis bisnis | Kolom kotor/nullable yang sah |
|---|---|---|---|---|---|
| `bookings` | 217.654 | 3+3+3=9 | **Tinggi** | `total_amount`, `status`, `check_in_date`/`check_out_date`, `room_rate` | Tidak ada — integritas relasi 100% bersih; hanya `status` kategori non-revenue (`cancelled`, `no-show`) yang perlu difilter, bukan data kosong |
| `daily_occupancy` | 19.746 | 2+2+1=5 | **Sedang** | `occupancy_rate`, `adr`, `revpar` | Tidak ada — hasil ETL dari `bookings`, selalu terisi penuh |
| `pricing_history` | 19.746 | 2+2+1=5 | **Sedang** | `applied_rate` vs `base_rate`, `reason` | Tidak ada |

### 3. Schema `fnb_operations`

| Tabel | Baris (live) | Skor | Prioritas | Kolom kritis bisnis | Kolom kotor/nullable yang sah |
|---|---|---|---|---|---|
| `fnb_outlets` | 17 | 1+1+2=4 | **Rendah** | `outlet_type` (menentukan pola walk-in) | Tidak ada |
| `recipe_bom` | 120 | 1+2+2=5 | **Sedang** | `qty_per_portion` (dasar rantai food cost) | Tidak ada |
| `ingredient_price_history` | 32.910 | 2+2+2=6 | **Sedang** | `unit_cost` (sumber fitur ML M2, shock harga musiman) | Tidak ada |
| `fnb_transactions` | 902.574 | 3+3+2=8 | **Tinggi** | `total_price`, `customer_type`, `transaction_datetime` | `guest_id` 31,06% kosong (**bermakna** — walk-in anonim, terverifikasi live, bukan data hilang) |
| `fnb_waste_log` | 108.733 | 3+2+1=6 | **Sedang** | `quantity_wasted`, `reason` | Cakupan pencatatan hanya ~25% sampel by design — bukan data hilang |
| `fnb_inventory` | 457 | 1+2+1=4 | **Rendah** | `stock_current` vs `stock_min_threshold` (11,8% baris kritis) | Tidak ada — snapshot selalu terisi |

### 4. Schema `facility_maintenance`

| Tabel | Baris (live) | Skor | Prioritas | Kolom kritis bisnis | Kolom kotor/nullable yang sah |
|---|---|---|---|---|---|
| `rooms` | 549 | 1+2+2=5 | **Sedang** | `status` (available/occupied/maintenance/out-of-order — memengaruhi kamar terjual) | Tidak ada |
| `housekeeping_log` | 425.172 | 3+2+1=6 | **Sedang** | `status` (delayed rate), durasi (`cleaning_end_time - cleaning_start_time`) | Tidak ada |
| `maintenance_tickets` | 13.514 | 2+2+1=5 | **Sedang** | `cost`, `priority`+SLA breach, `status` | `room_id` 27,54% kosong (bermakna — kerusakan di fasilitas umum, terverifikasi live); `parts_replaced` 52,21% kosong (bermakna — tidak ganti part); `resolved_date` kosong jika masih `open`/`in-progress` |

### 5. Schema `spa_event`

| Tabel | Baris (live) | Skor | Prioritas | Kolom kritis bisnis | Kolom kotor/nullable yang sah |
|---|---|---|---|---|---|
| `venues` | 20 | 1+1+2=4 | **Rendah** | `max_capacity` (acuan utilisasi) | Tidak ada |
| `spa_bookings` | 127.890 | 2+2+2=6 | **Sedang** | `price`, `status`, `customer_type` | `guest_id` 21,16% kosong (bermakna — walk-in anonim, terverifikasi live) |
| `event_bookings` | 1.333 | 1+2+2=5 | **Sedang** | `total_revenue`, `capacity_booked` (harus ≤ `venues.max_capacity`) | Tidak ada |

### 6. Schema `hr_finance`

| Tabel | Baris (live) | Skor | Prioritas | Kolom kritis bisnis | Kolom kotor/nullable yang sah |
|---|---|---|---|---|---|
| `staff_shifts` | 610.019 | 3+3+2=8 | **Tinggi** | `status` (sumber utama ML M4 turnover), jam kerja (`clock_in`/`clock_out`) | `clock_in`/`clock_out` kosong 100% pada status `absent`/`leave` (bermakna, terverifikasi live) |
| `employee_performance` | 3.748 | 1+2+1=4 | **Rendah** | `score` (sinyal pra-resign, promosi) | Tidak ada — hanya direview jika tenure ≥3 bulan (by design, bukan data hilang) |
| `payroll` | 23.383 | 2+3+2=7 | **Tinggi** | `net_salary`, `service_charge` (korelasi okupansi r=0,83-0,95) — **data paling sensitif di seluruh database** | `thr` hanya terisi 1x/tahun (Maret) — bermakna, bukan data hilang |
| `financial_summary` | 756 | 1+3+2=6 | **Sedang** | `gop`, `departmental_profit` — laporan resmi USALI, rahasia bisnis | `undistributed_expense`/`gop` hanya terisi di baris `department='Overall'` — bermakna (baris ringkasan, jangan dijumlahkan bersama baris departemen) |

### Ringkasan Prioritas

| Prioritas | Jumlah tabel | Tabel |
|---|---|---|
| **Tinggi** | 7 | `employees`, `guests`, `role_permissions`, `bookings`, `fnb_transactions`, `staff_shifts`, `payroll` |
| **Sedang** | 12 | `properties`, `daily_occupancy`, `pricing_history`, `recipe_bom`, `ingredient_price_history`, `fnb_waste_log`, `rooms`, `housekeeping_log`, `maintenance_tickets`, `spa_bookings`, `event_bookings`, `financial_summary` |
| **Rendah** | 4 | `fnb_outlets`, `fnb_inventory`, `venues`, `employee_performance` |

**Catatan penerapan**: 4 dari 7 tabel prioritas Tinggi bukan tabel dengan volume terbesar (`role_permissions` 77 baris, `employees` 755 baris, `payroll` 23.383 baris) — ini membuktikan alasan menolak rubrik "volume saja" di `decisions.md`: kekritisan bisnis & posisi sebagai konsumen-downstream-banyak-pihak bisa mengangkat tabel kecil ke prioritas tinggi.

---

## Katalog Kandidat Business Rule

> Katalog ini **bukan** implementasi test (lihat `decisions.md` — Milestone 1.1 sengaja berhenti di level katalog). Milestone 1.3 yang menentukan tool & menulis test aktual.

### `corporate_master`
- `employees.role_title` (bila terisi) HARUS ada di `role_permissions.role_title` (integritas RBAC).
- `employees.department` HARUS masuk 8 nilai baku setelah normalisasi `.strip().lower()`.
- `employees.access_level` HARUS salah satu dari `staff`/`manager`/`corporate`.
- `guests.email`, bila terisi, HARUS berformat email valid.
- `guests.loyalty_tier` HARUS salah satu dari `none`/`Silver`/`Gold`/`Platinum`.
- `role_permissions.permission_type` HARUS selalu `read` (AI Chatbot tidak pernah menulis — penyimpangan di sini adalah insiden keamanan, bukan data kotor biasa).

### `reservation_revenue`
- `bookings.total_amount = room_rate × nights` (konsistensi kalkulasi).
- `bookings.check_out_date > check_in_date`.
- `bookings.booking_date <= check_in_date`.
- `bookings.room_rate >= 0`, `total_amount >= 0`.
- `bookings.room_type = 'Villa'` HANYA valid untuk `property_id IN ('P01','P04','P05')`.
- `daily_occupancy.occupancy_rate` HARUS dalam rentang 0–1.
- `daily_occupancy.rooms_sold <= total_rooms_available`.

### `fnb_operations`
- `fnb_transactions.total_price = unit_price × quantity`.
- `fnb_transactions.customer_type = 'inhouse'` HARUS punya `guest_id` terisi (kontrak yang didokumentasikan: 100% cocok dengan `bookings`).
- `fnb_transactions.quantity > 0`, `unit_price >= 0`.
- `fnb_inventory.stock_current >= 0`.
- `ingredient_price_history.unit_cost > 0`.

### `facility_maintenance`
- `maintenance_tickets.resolved_date`, bila terisi, HARUS `>= reported_date`.
- `maintenance_tickets.cost >= 0`.
- `maintenance_tickets.priority` HARUS salah satu dari `low`/`medium`/`high`/`critical`.
- `housekeeping_log.cleaning_end_time > cleaning_start_time`.
- `rooms.status` HARUS salah satu dari 5 nilai baku (`available`/`occupied`/`cleaning`/`maintenance`/`out-of-order`).

### `spa_event`
- `event_bookings.capacity_booked <= venues.max_capacity` (join `venue_id`).
- `spa_bookings.service_date >= booking_date`.
- `spa_bookings.duration_minutes` HARUS salah satu dari `{45, 60, 90, 120}`.
- Tidak boleh ada dua `event_bookings` dengan `venue_id` & `event_date` yang sama (constraint venue tunggal per hari).

### `hr_finance`
- `staff_shifts.clock_out > clock_in` (bila keduanya terisi).
- `staff_shifts.status IN ('present','late','absent','leave')`.
- `payroll.net_salary = base_salary + service_charge + overtime_pay + thr - deduction`.
- `payroll.base_salary > 0`.
- `financial_summary.gop`/`undistributed_expense` HANYA boleh terisi jika `department = 'Overall'` (baris lain harus kosong).
- `employee_performance.score` HARUS dalam rentang 1,0–5,0.

---

## Cross-check terhadap Kriteria Keberhasilan Milestone 1.1

- ✅ **Setiap 23 tabel di 6 database punya klasifikasi prioritas dan catatan karakteristik yang jelas** — lihat 6 sub-tabel di atas, seluruhnya terisi (23/23).
- ✅ **Dokumen ini bisa dipakai sebagai rujukan langsung oleh milestone berikutnya tanpa analisis ulang** — baseline volume sudah diverifikasi live, pola dirty data sudah dikonfirmasi (bukan sekadar disalin dari dokumentasi), dan katalog business rule sudah tersedia sebagai starting point Milestone 1.3.

Detail keputusan & alasan di balik rubrik/metodologi ada di `milestones/1.1-inventarisasi-baseline-produksi/decisions.md`. Jurnal kerja & temuan (termasuk diskrepansi nama tabel RBAC) ada di `milestones/1.1-inventarisasi-baseline-produksi/logs.md`.
