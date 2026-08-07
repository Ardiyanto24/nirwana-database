
# Skema Database — Nirwana Hospitality Group (AI Agent Data Analysis Portfolio)
 
> Status: Skema tabel operasional (6 database logis). Dokumen pendamping: `02-use-case-statistik-ml.md` (cakupan analisis) dan `03-metadata-data-dictionary.md` (**data dictionary lengkap** — arti setiap kolom & nilai). Tabel hasil ML/alert/decision log menyusul setelah detail teknis tiap use case (fitur, formula, output) dirampungkan.
 
## Ringkasan 6 Database Logis
 
| # | Database | Owner Role Utama | Isi | Status Generate |
|---|---|---|---|---|
| 1 | `corporate_master` | Corporate/CEO | Data properti, karyawan, guest master, referensi umum | ✅ Selesai |
| 2 | `reservation_revenue` | Revenue Manager | Booking, okupansi, pricing, channel | ✅ Selesai |
| 3 | `fnb_operations` | F&B Manager | Transaksi outlet, menu, resep, harga bahan, inventory | ✅ Selesai |
| 4 | `facility_maintenance` | Housekeeping/Maintenance Manager | Status kamar, log kerusakan, jadwal perawatan | ✅ Selesai |
| 5 | `spa_event` | Spa & Event Manager | Venue, booking spa, event/MICE | ✅ Selesai |
| 6 | `hr_finance` | HR Manager / Corporate Finance | Shift, performance, payroll, laporan keuangan USALI | ✅ Selesai |
 
## Parameter Global Data Sintetis
 
| Parameter | Nilai |
|---|---|
| Rentang waktu | 1 Juli 2023 – 30 Juni 2026 (3 tahun / 36 bulan) |
| Random seed | 42 (reproducible) |
| Jumlah properti | 5 hotel/resort + 1 corporate office |
| Format output | CSV per tabel, per folder database |
 
## Realisasi Volume Data (yang sudah digenerate)
 
| Database | Tabel | Baris |
|---|---|---|
| `corporate_master` | properties | 6 |
| | employees | 755 |
| | guests | 24.867 |
| | role_permissions_chatbot_v2 | 77 |
| `reservation_revenue` | bookings | 217.155 |
| | daily_occupancy | 19.728 |
| | pricing_history | 19.728 |
| `fnb_operations` | fnb_outlets | 17 |
| | recipe_bom | 120 |
| | ingredient_price_history | 32.880 |
| | **fnb_transactions** | **900.416** |
| | fnb_waste_log | 108.211 |
| | fnb_inventory | 457 |
| `facility_maintenance` | rooms | 549 |
| | housekeeping_log | 425.108 |
| | maintenance_tickets | 13.535 |
| `spa_event` | venues | 20 |
| | spa_bookings | 127.762 |
| | event_bookings | 1.331 |
| `hr_finance` | staff_shifts | 609.364 |
| | employee_performance | 3.748 |
| | payroll | 23.383 |
| | financial_summary | 756 |
 
**Total: ~2,53 juta baris** di 23 tabel. **Semua 6 database selesai.**
 
Catatan konteks bisnis:
- Grup mengelola 5 properti hotel/resort di kota berbeda + 1 kantor pusat (Corporate).
- Setiap properti punya lini bisnis: Kamar (Room), F&B, Spa & Wellness, Event/MICE.
- Role berlapis dua dimensi: per **properti** (horizontal) dan per **level jabatan** (staff → manager → corporate).
---
 
## 1. Database: `corporate_master`
 
### Tabel `properties`
- `property_id` (PK)
- `property_name`
- `city`
- `region`
- `total_rooms`
- `star_rating`
- `opening_date`
### Tabel `employees`
- `employee_id` (PK)
- `property_id` (FK, nullable kalau corporate)
- `full_name`
- `role_title`
- `department` (Revenue, F&B, Housekeeping, Spa&Event, HR, Finance, Corporate)
- `access_level` (staff, manager, corporate) — kolom kunci untuk RBAC
- `hire_date`
- `status` (active, resigned, terminated)
### Tabel `guests`
- `guest_id` (PK)
- `full_name`
- `email`
- `phone`
- `nationality`
- `loyalty_tier` (Silver, Gold, Platinum, none)
- `registered_date`
### Tabel `role_permissions_chatbot_v2`
> Tabel kunci sistem RBAC untuk AI Chatbot — dibaca AI Agent sebelum menjalankan query apapun. Menggantikan `role_permissions` (versi asli 42 baris, 7 data_domain) dengan granularitas yang lebih presisi khusus untuk kebutuhan chatbot: domain `corporate_master` dipecah jadi 4 kelompok terpisah (`properties_ref`, `employees_directory`, `guests_pii`, `guests_profile`) agar makna izin akses lebih jelas — misalnya seorang manager tidak otomatis mendapat akses ke data pribadi tamu hanya karena mendapat akses ke data properti. Seluruh `permission_type` diperlakukan sebagai `read` saja, karena AI Chatbot hanya membaca data, tidak pernah menulis.
- `role_title`
- `data_domain` (10 nilai: `reservation`, `fnb`, `facility`, `spa_event`, `hr`, `financial`, `properties_ref`, `employees_directory`, `guests_pii`, `guests_profile`)
- `access_scope` (`own_property`, `all_properties`)
- `permission_type` (`read`)
---
 
## 2. Database: `reservation_revenue`
 
### Tabel `bookings`
- `booking_id` (PK)
- `property_id` (FK)
- `guest_id` (FK)
- `room_type` (Standard, Deluxe, Suite, Villa)
- `booking_channel` (Direct, OTA-Booking.com, OTA-Agoda, Travel Agent, Corporate)
- `check_in_date`
- `check_out_date`
- `booking_date`
- `nights`
- `room_rate`
- `total_amount`
- `status` (confirmed, cancelled, no-show, completed)
### Tabel `daily_occupancy`
> Agregat harian, hasil ETL dari `bookings`.
- `date`
- `property_id` (FK)
- `room_type`
- `total_rooms_available`
- `rooms_sold`
- `occupancy_rate`
- `adr` (Average Daily Rate)
- `revpar` (Revenue per Available Room)
### Tabel `pricing_history`
- `property_id` (FK)
- `room_type`
- `date`
- `base_rate`
- `applied_rate`
- `reason` (manual, promo, dynamic-pricing-AI)
> **Catatan implementasi (v0.3)**: `reason` diisi berdasarkan konteks — `promo` saat low season (harga diturunkan untuk dorong demand), `manual` saat high season/normal (penyesuaian revenue manager), `dynamic-pricing-AI` saat window anomali pricing. Realisasi: 13.190 manual, 6.456 promo, 82 dynamic-pricing-AI.
 
---
 
## 3. Database: `fnb_operations`
 
> **Perubahan struktur di v0.4** (revisi besar dari v0.3):
> 1. **`fnb_daily_sales` DIHAPUS**, diganti **`fnb_transactions`** granular per struk. Alasan: agregat harian menghilangkan informasi yang dibutuhkan untuk analisis walk-in, pola intraday, dan average check per struk. Volume naik dari 378rb → 900rb baris, tapi membuka analisis yang sebelumnya mustahil.
> 2. **Kolom baru `customer_type`** (`inhouse` / `walk-in`) — menjawab pertanyaan bisnis "berapa persen revenue dari pelanggan lokal?"
> 3. **`guest_id` jadi nullable** — walk-in anonim (mayoritas) tidak memberi identitas. Ini *missing value yang bermakna*, bukan data kotor.
> 4. **`transaction_date` → `transaction_datetime`** — ada jam, memungkinkan analisis pola sarapan/lunch/dinner.
> 5. **Capture rate dikoreksi berbasis riset industri** (lihat catatan di bawah).
 
### Tabel `fnb_outlets`
- `outlet_id` (PK)
- `property_id` (FK)
- `outlet_name`
- `outlet_type` (Restaurant, Bar, Room Service)
### Tabel `recipe_bom`
> Bill of Material: komposisi bahan baku per porsi menu. Jantung koherensi food cost.
- `item_name`
- `ingredient_id` (FK)
- `qty_per_portion` — takaran bahan per satu porsi
### Tabel `ingredient_price_history`
> Riwayat harga bahan baku harian. Sumber fitur untuk ML M2.
- `ingredient_id` (FK)
- `date`
- `unit_cost`
### Tabel `fnb_transactions` *(menggantikan `fnb_daily_sales` di v0.4)*
> Granular per struk × item. Beberapa baris berbagi `transaction_id` yang sama (satu struk berisi beberapa item).
- `transaction_id` — ID struk (bukan ID baris)
- `outlet_id` (FK)
- `guest_id` (FK, **nullable**) — kosong untuk walk-in anonim
- `customer_type` — `inhouse` / `walk-in`
- `transaction_datetime` — tanggal + jam
- `item_name`
- `category` (Food, Beverage, Dessert)
- `quantity`
- `unit_price`
- `total_price`
### Tabel `fnb_inventory`
> Snapshot stok terkini. `unit_cost` diambil dari baris terakhir `ingredient_price_history`.
- `ingredient_id` (PK)
- `outlet_id` (FK)
- `ingredient_name`
- `unit`
- `stock_current`
- `stock_min_threshold`
- `unit_cost`
### Tabel `fnb_waste_log`
- `waste_id` (PK)
- `outlet_id` (FK)
- `date`
- `ingredient_id` (FK)
- `quantity_wasted`
- `reason` (expired, overproduction, spillage)
## 4. Database: `facility_maintenance`
 
### Tabel `rooms`
- `room_id` (PK)
- `property_id` (FK)
- `room_number`
- `room_type`
- `floor`
- `status` (available, occupied, cleaning, maintenance, out-of-order)
### Tabel `housekeeping_log`
- `log_id` (PK)
- `room_id` (FK)
- `date`
- `cleaning_start_time`
- `cleaning_end_time`
- `staff_id` (FK ke employees)
- `status` (completed, delayed)
### Tabel `maintenance_tickets`
- `ticket_id` (PK)
- `property_id` (FK)
- `room_id` (FK, nullable — bisa fasilitas umum bukan kamar)
- `facility_area` (Room, Pool, Lobby, Elevator, dll)
- `issue_type` (AC, Plumbing, Electrical, Furniture, dll)
- `reported_date`
- `resolved_date`
- `status` (open, in-progress, resolved)
- `priority` (low, medium, high, critical)
- `assigned_staff_id` (FK)
- `labor_hours` *(baru v0.4)* — jam kerja teknisi
- `parts_replaced` *(baru v0.4, nullable)* — nama part yang diganti
- `cost` *(baru v0.4)* — total biaya = (labor_hours × tarif_teknisi) + harga_part
> **Catatan v0.4**: tiga kolom ini ditambahkan agar ML M3 bisa memprediksi *biaya* maintenance, bukan hanya frekuensi. `cost` dihitung deterministik — tarif teknisi naik mengikuti inflasi 5%/tahun, sehingga tiket AC critical yang butuh 8 jam + ganti kompresor otomatis mahal. Bukan angka acak.
 
---
 
## 5. Database: `spa_event`
 
> **Perubahan struktur di v0.4**:
> 1. **Tabel `venues` ditambahkan** — venue punya atribut yang melekat padanya (kapasitas maksimal, tipe), bukan pada event. Tanpa ini, use case 5.3 (deteksi utilisasi venue rendah) tidak bisa dijawab: "kapasitas terpakai dibanding berapa?". Konsisten dengan pola master data lain (`fnb_outlets`, `rooms`).
> 2. **`spa_bookings.customer_type`** — spa hotel lazim menerima walk-in lokal yang tidak menginap (lihat catatan riset).
> 3. **`spa_bookings.guest_id` jadi nullable** — walk-in anonim.
> 4. **`event_bookings.venue_id`** (FK baru) — relasi ke tabel `venues`.
 
### Tabel `venues` *(baru di v0.4)*
- `venue_id` (PK)
- `property_id` (FK)
- `venue_name`
- `venue_type` (Ballroom, Meeting Room, Outdoor)
- `max_capacity`
### Tabel `spa_bookings`
- `spa_booking_id` (PK)
- `property_id` (FK)
- `guest_id` (FK, **nullable**) — kosong untuk walk-in anonim
- `customer_type` *(baru v0.4)* — `inhouse` / `walk-in`
- `service_name`
- `booking_date`
- `service_date`
- `duration_minutes`
- `price`
- `status` (confirmed, cancelled, completed)
### Tabel `event_bookings`
> MICE — Meeting, Incentive, Conference, Exhibition
- `event_id` (PK)
- `property_id` (FK)
- `venue_id` *(baru v0.4, FK)*
- `client_name` — nama perusahaan (korporat) atau pasangan (wedding)
- `event_type` (Wedding, Corporate Meeting, Conference, Gala Dinner, Product Launch, Training/Workshop)
- `event_date`
- `venue_name`
- `capacity_booked` — dijamin ≤ `max_capacity` venue
- `total_revenue`
- `status`
## 6. Database: `hr_finance`
 
> **Perubahan struktur di v0.5** (berbasis riset industri):
> 1. **`payroll.service_charge`** (baru) — riset: *"Service charge bisa melebihi gaji pokok di hotel bintang 4-5 yang ramai"*. Ini komponen gaji terbesar kedua di hotel Indonesia dan **berkorelasi dengan okupansi** (bagi hasil 10% revenue properti). Tanpa ini, struktur gaji tidak realistis.
> 2. **`payroll.overtime_pay`** & **`payroll.thr`** (baru) — THR wajib per regulasi Indonesia; lembur dihitung 1/173 × gaji × jam.
> 3. **`financial_summary` direstrukturisasi ke format USALI** — memisahkan *departmental* dari *undistributed operating expenses*, standar akuntansi industri hospitality.
 
### Tabel `staff_shifts`
- `shift_id` (PK)
- `employee_id` (FK)
- `date`
- `shift_type` (Morning 07-15, Afternoon 15-23, Night 23-07)
- `clock_in` — kosong jika absent/leave
- `clock_out` — kosong jika absent/leave
- `status` (present, late, absent, leave)
> Departemen operasional (Housekeeping, F&B, Revenue, Spa&Event, Facility) pakai 3 shift; departemen office (HR, Finance, Corporate) hanya Morning.
 
### Tabel `employee_performance`
- `review_id` (PK)
- `employee_id` (FK)
- `review_period` — format `YYYY-S1` / `YYYY-S2` (semesteran)
- `score` (1.0–5.0)
- `notes` — catatan kualitatif sesuai rentang skor
### Tabel `payroll`
> Sensitif — akses paling terbatas.
- `payroll_id` (PK)
- `employee_id` (FK)
- `period` (YYYY-MM)
- `base_salary` — gaji pokok, naik 6.5%/tahun mengikuti UMK
- `service_charge` *(baru v0.5)* — 10% revenue properti × 85% dibagi ke karyawan by point (staff 1.0, manager 2.2)
- `overtime_pay` *(baru v0.5)* — (gaji ÷ 173) × jam lembur
- `thr` *(baru v0.5)* — 1× gaji, proporsional jika tenure < 12 bulan
- `deduction` — BPJS Kesehatan 1% + Ketenagakerjaan 3% + PPh21 ~5%
- `net_salary`
### Tabel `financial_summary` *(format USALI)*
> Agregat bulanan per properti per departemen. **Dihitung dari data nyata DB2/DB3/DB5**, bukan digenerate independen — terverifikasi cocok 100% dengan `bookings`.
- `property_id` (FK)
- `period` (YYYY-MM)
- `department` (Room, F&B, Spa&Event, Overall, Corporate Overhead)
- `departmental_revenue` — Room dari DB2, F&B dari DB3, Spa&Event dari DB5
- `departmental_expense` — payroll + COGS (food cost dari `recipe_bom`) + alokasi service charge
- `departmental_profit`
- `undistributed_expense` — hanya terisi di baris `Overall` (Admin & General, Sales & Marketing, IT, Utilities, Property Maintenance)
- `gop` — Gross Operating Profit
> **Catatan alokasi service charge (koreksi penting)**: versi pertama membebankan 100% service charge ke departemen tempat karyawan bekerja, membuat F&B terlihat **rugi (-0.1%)**. Padahal service charge berasal dari revenue *seluruh* properti. Diperbaiki dengan mengalokasikan proporsional sesuai kontribusi revenue tiap departemen (praktik USALI untuk shared cost) → F&B margin jadi **10.7%**, sesuai riset ("F&B presents such tight margins").
 
---
 
## Landasan Riset Industri (v0.4)
 
> Angka-angka kunci di data sintetis ini **tidak dikarang** — diambil dari riset industri hospitality. Ini penting untuk kredibilitas portofolio: kalau ada yang bertanya "kenapa capture rate Jakarta 16%?", jawabannya bukan "kira-kira segitu".
 
### Capture Rate F&B (% tamu menginap yang makan di outlet hotel)
 
Sumber: CBRE Trends, Regulr Hotel F&B Capture Rate Guide
 
| Temuan | Angka |
|---|---|
| Hotel urban full-service, dinner | 12–18% |
| Hotel urban full-service, lunch | 8–12% (tamu menyebar ke kota) |
| Resort & properti destinasi, dinner | 40–60% (tamu terkurung geografis) |
| Benchmark umum "baik" | >50% |
 
**Diterapkan:**
 
| Properti | Karakter | Restaurant | Bar | Room Service |
|---|---|---|---|---|
| P01 Bali | Resort | 48% | 20% | 12% |
| P02 Jakarta | Urban | 16% | 12% | 8% |
| P03 Yogyakarta | Urban-heritage | 26% | 15% | 10% |
| P04 Bandung | Urban-resort | 30% | 18% | 10% |
| P05 Lombok | Resort remote | 52% | 22% | 14% |
 
### Walk-in / Pelanggan Lokal
 
Sumber: CBRE Trends in the Hotel Spa Industry (survei 192 hotel AS), Arch Amenities Group
 
| Temuan | Angka |
|---|---|
| Revenue spa hotel urban dari warga lokal & member | 59% |
| Revenue spa resort dari warga lokal | 38–41% |
| Rekomendasi industri untuk spa hotel/resort | 30–50% klien lokal |
| Hotel destinasi | "level bisnis lokal minimal" |
| Hotel urban | "bisa 80% atau lebih dari lokal" |
| Perilaku: tamu menginap (liburan) | Bayar lebih per kunjungan |
| Perilaku: warga lokal (wellness rutin) | Prioritaskan keterjangkauan, datang lebih sering |
 
**Diterapkan (walk-in ratio):**
 
| Properti | F&B | Spa |
|---|---|---|
| P01 Bali | 25% | 32% |
| P02 Jakarta | 65% | 62% |
| P03 Yogyakarta | 50% | 48% |
| P04 Bandung | 55% | 55% |
| P05 Lombok | 18% | 22% |
 
**Catatan metodologis penting**: riset menyebut kesalahan umum operator adalah *mencampur walk-in ke dalam perhitungan capture rate*. Karena itu dua konsep ini **sengaja dipisah** di config: `FNB_CAPTURE_RATE` (tamu menginap) vs `FNB_WALKIN_RATIO` (pelanggan luar). Room Service tidak punya walk-in sama sekali (mustahil pesan room service tanpa kamar).
 
 
### Turnover & Gejala Pra-Resign (untuk ML M4)
 
Sumber: Hire Elite Consultants, Forbes (Mark Murphy), Hybrid Payroll, 5 Starr Engagement, BLS JOLTS
 
| Temuan | Angka/Implikasi |
|---|---|
| Turnover industri hospitality (2021) | **86.3%** — tertinggi dari semua sektor (rata-rata nasional 47.2%) |
| Sinyal turnover | Absensi sering, telat berulang, permintaan cuti mendadak |
| Payroll pattern bisa prediksi turnover | Jam menurun, shift terlewat, tip turun |
| **Sebagian resign tanpa gejala** | *"Never assume a quiet high-performer is a happy high-performer. Quiet compliance often masks deep emotional withdrawal."* |
| Timing gejala | Muncul "berbulan-bulan sebelum" surat resign |
| Departemen paling terdampak | Housekeeping & F&B (burnout tertinggi) |
 
**Diterapkan:** 70% resign candidates bergejala (absensi & telat naik bertahap 3 bulan sebelum resign, performance turun), **30% resign mendadak tanpa gejala** — memberi M4 tantangan realistis, bukan model yang terlalu mudah.
 
### Struktur Gaji Hotel Indonesia
 
Sumber: Hotel Job Indonesia 2025, KantorKu, Jobstreet, IDN Times
 
| Posisi | Rentang (Rp/bulan) |
|---|---|
| Room Attendant / Housekeeping | 3,5 – 4,8 juta |
| Waiter / Bartender | 3,5 – 5,0 juta |
| Front Office / GRO | 4,0 – 5,5 juta |
| Supervisor | 5,0 – 8,0 juta |
| Restaurant Manager | 8 – 15 juta |
| Executive Housekeeper | 10 – 20 juta |
| F&B Manager | 15 – 30 juta |
| General Manager | 25 juta+ |
 
**UMK 2025**: DKI Jakarta ~Rp 5,3jt (tertinggi); Kab. Badung (Bali) ~Rp 3,5jt.
 
**Temuan kunci**: Take-home pay = Gaji Pokok + **Service Charge** + Tips. *"Di hotel bintang 4 atau 5 yang ramai, service charge bisa melebihi gaji pokok."* Service charge = bagi hasil biaya layanan ke tamu → **berkorelasi langsung dengan okupansi**.
 
**Diterapkan:** service charge 10% revenue properti × 85% dibagi ke karyawan. Realisasi korelasi dengan okupansi: **r = 0.83–0.95 per properti**.
 
### Struktur Biaya & Profitabilitas (USALI)
 
Sumber: CoStar, CBRE, STR, HotelData, Cloudbeds
 
| Metrik | Angka |
|---|---|
| GOP margin full-service | **25–35%** |
| GOP margin "strong" | >35% |
| Labor cost margin (STR 2024) | 34.4% dari revenue |
| Labor = ~50% total operating cost | Rooms Division 40–50% dari total labor |
| Net profit margin hotel (terkini) | 4.85% – 7.28% |
| F&B | *"Margin paling tipis, expense tertinggi setelah Rooms"* |
 
**Standar USALI**: memisahkan *operated departments* (penghasil revenue) dari *undistributed operating expenses* (overhead: Admin & General, Sales & Marketing, IT, Utilities, Property Maintenance). USALI juga mendorong pemisahan *in-house revenue* vs *external revenue* — yang sudah kita terapkan lewat `customer_type`.
 
**Realisasi:** GOP margin 31–42% per properti. Departmental margin: Room 70.3%, F&B 10.7%, Spa&Event 45.0% — pola persis seperti yang disebut riset.
 
### Konsekuensi: Tabel `guests` = Master Pelanggan
 
Karena walk-in perlu tercatat (sebagian ikut membership), tabel `guests` diperluas maknanya:
 
| Populasi | guest_id | Jumlah | Menginap? |
|---|---|---|---|
| Tamu menginap | G00001–G18000 | 18.000 | Ya |
| Pelanggan lokal (F&B/spa) | G18001–G24500 | 6.500 | **Tidak pernah** |
| Duplikat (data kotor) | G24501+ | 367 | — |
 
DB2 (`bookings`) **hanya memakai populasi pertama** — pelanggan lokal tidak pernah booking kamar. Ini diverifikasi: 0 overlap antara walk-in terdaftar dan guest yang punya booking.
 
---
 
## Pattern Injection (Pola yang Sengaja Disuntikkan)
 
> Data sintetis **tidak random murni**. Pola sebab-akibat sengaja ditanam supaya analisis statistik & ML nanti benar-benar menemukan sesuatu yang bermakna.
 
### Mekanisme Pattern Seed
 
Pola lintas-database dikoordinasikan lewat **file bantu internal** (bukan bagian data resmi, tidak menambah kolom apapun ke skema):
 
| File | Isi | Dipakai oleh |
|---|---|---|
| `_pattern_seeds/resign_candidates.json` | 100 karyawan + tanggal resign | DB6 (staff_shifts, employee_performance) |
| `_pattern_seeds/resign_symptomatic.json` | 70 karyawan yang bergejala (70%) | **Validasi M4** |
| `_pattern_seeds/churn_candidates.json` | 434 guest loyal + tanggal mulai churn | DB2 (bookings) |
| `_pattern_seeds/data_quality_issues_log_db1.csv` | 15.346 baris "kunci jawaban" data kotor | Validasi proses data cleaning |
 
### Pola Terverifikasi
 
| Domain | Pola | Realisasi |
|---|---|---|
| Revenue | Musiman | Des 82.7% & Jul 80.4% (tinggi); Feb 59.1% & Sep 58.3% (rendah) |
| Revenue | Tren YoY | 67.6% (2023) → 71.5% (2026) |
| Revenue | Weekend effect (Bali) | Jum-Sab ~81% vs weekday ~71% |
| Revenue | Guest churn | Rata-rata 18 booking sebelum churn → 0.87 sesudah |
| Revenue | Anomali cancellation (Bali, Mar 2024) | 35.6% vs baseline 7.5% |
| Revenue | Anomali lead time (Yogya, Ags 2024) | 1.4 hari vs baseline 17.9 hari |
| Revenue | Anomali ADR (Jakarta, Feb 2025) | Rp 599rb vs Rp 935rb normal |
| F&B | **Capture rate sesuai riset** | P01 48.0%, P02 16.0%, P05 52.1% |
| F&B | **Walk-in ratio** | P02 63%, P01 25%, P05 17% |
| F&B | Pola intraday | Sarapan 6-9, lunch 11-13, dinner 18-21 (dinner puncak) |
| F&B | Shock harga cabai (Jan 2024) | Rp 46rb → Rp 122rb (2.63x) |
| F&B | **Dampak berantai ke food cost** | Rendang: Rp 59.9rb → Rp 68.2rb saat cabai mahal |
| F&B | Anomali penjualan Rendang (Okt 2024) | 0.31x baseline |
| F&B | Anomali Sunset Cocktail (Jun 2025) | 2.75x baseline |
| Facility | SLA breach per priority | high 22.9%, critical 16.4% |
| Facility | Kerusakan berulang (18 kamar) | 4.05x median kamar normal |
| Facility | Durasi cleaning per tipe | Villa 81.6 > Suite 54.8 > Deluxe 37.0 > Standard 29.5 (menit) |
| Facility | Tren AC Jakarta (Sep-Okt 2024) | 25% → 48-51% lalu normal |
| Facility | Benchmarking usia gedung | Jakarta (2012) 8.81 → Lombok (2020) 7.01 tiket/kamar/thn |
| Facility | Korelasi okupansi ↔ housekeeping | Hari sibuk 51.7 min & 19.1% delayed vs normal 39.8 min & 5.9% |
| Facility | Tren cost bulanan (untuk M3) | +Rp 1.07jt/bulan, +1.02 tiket/bulan |
| Spa | **Walk-in ratio sesuai riset** | P02 64.1%, P05 24.3% |
| Spa | **Preferensi layanan walk-in vs inhouse** | Reflexology 12.0% vs 2.6%; Couple Package 1.3% vs 15.0% |
| Spa | **Revenue per kunjungan** | inhouse Rp 800rb vs walk-in Rp 477rb |
| Spa | Anomali utilisasi | P01 0.53x, P05 1.67x |
| Spa | Tren popularitas layanan | Hot Stone 7.8%→13.3%, Reflexology 8.4%→3.4% |
| Event | Anomali cancellation | P02 0%→28.6%, P01 15.8%→30.0% |
| Event | Utilisasi venue rendah | 16.8% event di bawah 45% |
| Event | Anomali revenue | P02 2.60x, P03 0.38x |
| HR | **Gejala pra-resign (70 org)** | Absen 1.89%→4.24% (**2.24x**), telat 5.85%→10.88% (**1.86x**) |
| HR | **Resign mendadak (30 org)** | Absen 0.90x, telat 1.11x — nyaris tak berubah (sesuai riset) |
| HR | Performance menjelang resign | Bergejala 3.22 vs mendadak 3.53 vs aktif 3.60 |
| HR | Benchmarking turnover antar dept | Housekeeping & F&B tertinggi (sesuai riset) |
| Finance | **Service charge ↔ okupansi** | r = 0.83–0.95 per properti |
| Finance | GOP margin (riset: 25-35%) | 32–43% per properti |
| Finance | Departmental margin | Room 70.3%, F&B 10.7%, Spa&Event 45.0% |
| Finance | **Koherensi revenue** | financial_summary cocok **100%** dengan bookings DB2 |
 
### Data Quality Issues (Data Kotor Terkontrol)
 
Sengaja disuntikkan ke `guests` & `employees` supaya portofolio bisa menunjukkan tahap **data cleaning**.
 
| Jenis | Jumlah | Kolom |
|---|---|---|
| Inconsistent phone format | 11.977 | `guests.phone` (domestik saja) |
| Missing value | 1.730 | `guests.email` (~4%), `guests.phone` (~3%), `employees.role_title` (~2%) |
| Inconsistent casing | 757 | `guests.nationality`, `employees.department` |
| Typo | 485 | `guests.full_name` |
| Duplicate row | 367 | `guests` (~1.5%, guest_id baru) |
| Inconsistent date format | 15 | `employees.hire_date` |
| Whitespace noise | 15 | `employees.full_name` |
| **Total** | **15.346** | |
 
**Prinsip yang dijaga ketat:**
1. Tidak pernah menyentuh kolom kunci relasi (PK/FK) — JOIN antar tabel tetap 100% berfungsi.
2. Baris pattern seed (resign/churn candidates) **dikecualikan** dari pengotoran di kolom kunci.
3. Hanya di kolom deskriptif/administratif, bukan kolom perhitungan statistik/ML.
---
 
## Catatan Desain (untuk ditinjau ulang)
 
1. **`role_permissions_chatbot_v2`** adalah jantung sistem RBAC — perlu dipastikan strukturnya cukup fleksibel untuk semua kombinasi role x domain data.
2. **Payroll** dipisah dari `employees` karena tingkat sensitivitasnya berbeda — realistis dengan praktik enterprise sesungguhnya.
3. Ada **tabel agregat** (`daily_occupancy`, `financial_summary`) yang diasumsikan hasil ETL/batch job dari tabel transaksi mentah — realistis untuk skala enterprise. `daily_occupancy` **dihitung ulang dari `bookings`** (bukan digenerate independen) supaya konsisten 100% dengan data mentahnya.
4. **Belum ditambahkan**: tabel khusus hasil ML (misal `churn_predictions`, `demand_forecast_results`, `anomaly_alerts`) — menunggu desain arsitektur ML pipeline lebih lanjut. Lihat `02-use-case-statistik-ml.md`.
5. **Food cost koherensi (v0.3)**: keputusan menambah `recipe_bom` + `ingredient_price_history` membuat food cost punya rantai sebab-akibat nyata. Saat harga bahan naik, food cost menu yang memakai bahan itu otomatis ikut naik — bukan angka anomali yang ditempelkan. Ini krusial supaya ML M2 belajar dari pola yang benar.
6. **Kalibrasi food cost ratio (v0.3)**: takaran resep dikalibrasi otomatis agar mencapai target ratio industri (Food 34%, Beverage 24%, Dessert 28%), dengan variasi natural per menu (rentang realisasi 19.3%–42.0%) supaya tidak terlihat artifisial.
---
 
## Riwayat Revisi
- **v0.1** — Draft awal, 6 database logis, belum termasuk tabel hasil ML/alert.
- **v0.2** — Dipisah dari dokumen use case statistik/ML menjadi file tersendiri untuk kerapian dokumentasi.
- **v0.3** — Update pasca-implementasi DB1–DB3:
  - DB2: `pricing_history.reason` diperjelas (manual / promo / dynamic-pricing-AI).
  - DB3: restrukturisasi dari 4 → 6 tabel. `fnb_transactions` → `fnb_daily_sales` (agregat harian, `guest_id` dihapus). Tambah `recipe_bom` & `ingredient_price_history`.
  - Ditambahkan: parameter global, realisasi volume data, dokumentasi pattern injection & data quality issues, status progres generate per database.
- **v0.4** — Revisi besar berbasis riset industri + implementasi DB4 & DB5:
  - **Koreksi asumsi walk-in**: versi sebelumnya salah mengasumsikan 100% pelanggan spa & sebagian besar pelanggan F&B adalah tamu menginap. Riset menunjukkan hotel urban justru mayoritas dari pelanggan lokal (59% revenue spa urban). Ditambahkan `customer_type` di `fnb_transactions` & `spa_bookings`.
  - **DB3 kembali granular**: `fnb_daily_sales` (agregat) dihapus → `fnb_transactions` per struk. Membuka analisis intraday, average check, dan walk-in.
  - **Capture rate dikoreksi**: dari 55% seragam → 16-52% bervariasi per karakter properti, sesuai benchmark industri.
  - **DB1**: tabel `guests` diperluas jadi master pelanggan (+6.500 pelanggan lokal non-menginap). Sebelumnya hanya 223 orang tersedia untuk walk-in — tidak realistis.
  - **DB4** (baru): `rooms`, `housekeeping_log`, `maintenance_tickets` + 3 kolom cost breakdown (`labor_hours`, `parts_replaced`, `cost`) untuk ML M3.
  - **DB5** (baru): tabel `venues` (master data), `spa_bookings`, `event_bookings`.
  - Ditambahkan bagian **Landasan Riset Industri** dengan sumber & angka yang dipakai.
- **v0.5** — Implementasi DB6 (terakhir) + koreksi struktural:
  - **DB6**: `staff_shifts`, `employee_performance`, `payroll` (+`service_charge`/`overtime_pay`/`thr`), `financial_summary` format USALI.
  - **Koreksi distribusi `hire_date` di DB1**: versi sebelumnya menyebar hire_date acak sepanjang periode data → 52% karyawan "baru direkrut" padahal hanya 11.5% resign, artinya staf bertambah net **+67%** untuk jumlah kamar TETAP. Tidak masuk akal. Diperbaiki: 82% existing staff (direkrut sebelum periode data), rekrutan baru hanya sebagai replacement → net **+2.6%**. Efek samping positif: korelasi service charge ↔ okupansi naik dari r=0.57 → **r=0.74** (per properti 0.83–0.95).
  - **Koreksi alokasi service charge**: awalnya dibebankan 100% ke departemen tempat karyawan bekerja → F&B terlihat **rugi (-0.1%)**. Diperbaiki dengan alokasi proporsional sesuai kontribusi revenue (praktik USALI) → F&B margin **10.7%**, sesuai riset.
  - **Semua 6 database selesai.** Total ~2,53 juta baris di 23 tabel.
- **v0.6** — Sinkronisasi tabel RBAC pasca-perancangan AI Chatbot:
  - `role_permissions` (42 baris, 7 data_domain) **digantikan** oleh `role_permissions_chatbot_v2` (77 baris, 10 data_domain).
  - Domain `corporate_master` dipecah menjadi 4 kelompok granular (`properties_ref`, `employees_directory`, `guests_pii`, `guests_profile`) agar makna izin akses presisi per jenis data, bukan satu izin gabungan untuk data properti, karyawan, dan tamu sekaligus.
  - Seluruh `permission_type` disederhanakan menjadi `read` saja, karena AI Chatbot tidak pernah menulis data.
  - Penambahan baris mengikuti prinsip superset: posisi yang lebih tinggi dalam hierarki organisasi wajib memiliki minimal seluruh akses granular yang dimiliki bawahannya pada domain yang sama, agar AI Chatbot benar-benar bisa menggantikan rantai eskalasi manual antar level.