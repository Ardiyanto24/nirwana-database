# Pemetaan Kebutuhan Data Analyst — Dasar Penentuan Cakupan `mart_aggregated` & `mart_cleaned`

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` |
| **Referensi silang** | Bagian 5.2.1 (cakupan `mart_aggregated` belum ditentukan) dan Bagian 10 No. 6 (area validasi) dokumen induk |
| **Tujuan dokumen** | Memetakan kebutuhan konkret Data Analyst sebagai dasar penentuan cakupan agregasi `mart_aggregated`, serta konfirmasi kebutuhan row-level dari `mart_cleaned` |
| **Sumber data** | `Metadata.md` dan `DataSchema.md` — Nirwana Hospitality Group |
| **Metodologi** | Role-play per peran analyst: memposisikan diri sebagai analyst tersebut, membayangkan dashboard/laporan konkret yang dipegang, lalu menurunkan kebutuhan data dari situ — bukan menerka dimensi/metrik secara abstrak |
| **Status** | Selesai — 6 dari 6 domain dipetakan (Revenue, F&B, Facility, Spa & Event, HR, Corporate/Financial) |

---

## Cara Membaca Dokumen Ini

Dokumen ini adalah pekerjaan lanjutan dari Bagian 5.2.1 dan Bagian 10 No. 6 dokumen arsitektur induk, yang secara eksplisit menandai cakupan `mart_aggregated` sebagai belum ditentukan karena pemetaan kebutuhan nyata konsumen belum dilakukan.

### Struktur Organisasi Data Analyst yang Dipetakan

Karena skala sistem ini (6 domain data, 5 properti), Data Analyst tidak dipetakan sebagai satu peran generik, melainkan sebagai **6 pola kebutuhan per domain**, masing-masing dipegang oleh analyst yang fokus lintas 5 properti pada satu domain:

| # | Peran | Domain fokus | Cakupan properti |
|---|---|---|---|
| 1 | **Revenue Analyst** | `reservation_revenue` | Semua 5 properti |
| 2 | **F&B Analyst** | `fnb_operations` | Semua 5 properti |
| 3 | **Facility/Ops Analyst** | `facility_maintenance` | Semua 5 properti |
| 4 | **Spa & Event Analyst** | `spa_event` | Semua 5 properti |
| 5 | **HR Analyst** | `hr_finance` domain `hr` | Semua 5 properti |
| 6 | **Corporate/Financial Analyst** | `hr_finance` domain `financial` + konsolidasi lintas semua domain (GOP/USALI) — penyusun laporan CEO | Semua 5 properti (grup) |

**Property/GM Analyst** (pendukung GM tiap properti, 5 orang: P01–P05) **tidak dipetakan sebagai pola ke-7 terpisah** — kebutuhannya adalah union dari peran #1–5 (Revenue, F&B, Facility, Spa&Event, HR), dengan filter wajib `property_id` dan tanpa akses `financial_summary` tingkat grup. Begitu 5 pola domain operasional selesai dipetakan, kebutuhan Property/GM Analyst otomatis terpenuhi dari gabungan kelimanya.

### Metodologi per Domain

Setiap domain dipetakan dengan urutan:
1. **Role-play** — narasi memposisikan diri sebagai analyst tersebut, membayangkan dashboard harian/mingguan/bulanan/kuartalan yang nyata dipegang
2. **Audit kebutuhan** — setiap hal yang disebut di narasi dashboard diperiksa ulang: apakah sudah eksplisit diturunkan jadi item konkret di daftar dimensi/metrik, atau perlu ditandai sebagai kategori berbeda (mis. butuh mekanisme snapshot, bukan agregasi historis biasa), atau **tidak tersedia dari data sumber** (harus jujur ditandai, bukan dikarang)
3. **Kebutuhan final** — tabel sumber, dimensi, metrik siap pakai untuk `mart_aggregated`, dan kebutuhan row-level untuk `mart_cleaned`

---

## 1. Revenue Analyst

### 1.1 Role-Play: Dashboard & Laporan yang Dipegang

Saya Revenue Analyst di Nirwana Hospitality Group, lapor ke Revenue Manager tiap properti, dengan akses lintas 5 properti sehingga juga jadi rujukan benchmarking antar hotel. Kerja saya berkutat di okupansi, ADR, RevPAR, channel mix, dan pricing.

**Daily Revenue Dashboard** (dicek tiap pagi sebelum briefing):
- Okupansi kemarin per properti/tipe kamar, dibanding hari biasa (kemarin lusa, hari sama minggu lalu)
- ADR & RevPAR kemarin per properti
- Alert otomatis: okupansi anjlok, atau ADR di luar rentang wajar

**Weekly Channel Performance Report** (ke Revenue Manager tiap Senin):
- Distribusi booking & revenue per channel, minggu ini vs minggu lalu
- Tren porsi OTA (naik ~2%/tahun menurut data historis) — penting karena komisi OTA menggerus margin
- Cancellation rate & no-show rate per channel

**Monthly Property Performance Report** (bahan rapat bulanan dengan GM):
- Okupansi/ADR/RevPAR bulanan per properti, MoM dan YoY
- Room type mix — kontribusi revenue per tipe kamar
- Pricing effectiveness — seberapa sering & seberapa besar `applied_rate` menyimpang dari `base_rate`, breakdown per alasan (manual/promo/dynamic-pricing-AI)
- Rata-rata lama menginap (length of stay) per properti/room type/channel
- Rata-rata lead time booking (jarak booking ke check-in)

**Quarterly/Annual Strategic Review** (bahan ke Corporate/CEO via Corporate Analyst):
- Tren musiman tahunan (konfirmasi pola berulang atau anomali)
- Benchmarking antar 5 properti — siapa RevPAR tertinggi/terendah, posisi tiap properti relatif ke rata-rata grup
- Segmentasi domestik vs mancanegara (relevan terutama untuk Bali/Lombok sebagai destinasi resort)
- Repeat guest rate — porsi booking dari guest yang pernah booking sebelumnya vs guest baru

**Ad-hoc investigation** (saat leadership tanya sesuatu spesifik):
- "Kenapa cancellation Bali Maret 2024 tinggi?" — butuh drill-down row-level `bookings`
- Price elasticity — butuh histori row-level harga vs okupansi harian

### 1.2 Audit Kebutuhan

| Temuan audit | Keputusan |
|---|---|
| **Pace booking** (kamar terjual untuk tanggal check-in *masa depan*, dihitung "as of hari ini") | **Dikeluarkan dari cakupan mart_aggregated reguler.** Ini bukan fakta historis yang bisa diagregasi dari data yang sudah terjadi — nilainya berubah tiap hari untuk tanggal check-in yang sama. Butuh mekanisme snapshot harian terpisah. Ditandai sebagai kebutuhan yang memerlukan desain lanjutan, di luar cakupan dokumen ini. |
| **Length of stay (LOS)** | Ditambahkan eksplisit sebagai metrik — sebelumnya hanya tersirat dari kolom `nights`, kini masuk daftar metrik konkret |
| **Booking lead time** | Ditambahkan eksplisit sebagai metrik — sebelumnya hanya disebut naratif tanpa diturunkan |
| **Net revenue setelah komisi OTA** | **Tidak tersedia dari data sumber.** Skema `bookings` tidak punya kolom komisi OTA eksplisit. Ditandai sebagai gap data sumber, bukan gap pemetaan — direkomendasikan ke pemilik sistem untuk dipertimbangkan penambahan kolom `commission_rate`/`commission_amount` di production jika metrik ini dianggap penting |
| **Ranking/percentile antar properti** | Ditambahkan eksplisit sebagai metrik pembanding — sebelumnya `property_id` hanya jadi dimensi filter, bukan metrik benchmarking |
| **Segmentasi domestik vs mancanegara** (`guests.nationality`) | Ditambahkan sebagai dimensi baru |
| **Repeat guest / guest frequency** | Ditambahkan sebagai metrik baru — beda dari `loyalty_tier` (status) |
| **Target/budget vs actual** | **Tidak tersedia dari data sumber.** Tidak ada tabel target/budget di 23 tabel yang ada. Ditandai sebagai gap data sumber |

### 1.3 Kebutuhan Final

**Tabel sumber**: `bookings`, `daily_occupancy`, `pricing_history` (dari `reservation_revenue`); `properties`, `guests` (untuk konteks region/loyalty/nationality)

**Dimensi (filter & group-by)**:
- `property_id`, `region`
- `room_type`
- `booking_channel`
- Waktu: harian → mingguan → bulanan → kuartalan → tahunan
- `loyalty_tier`
- `nationality` (domestik vs mancanegara — perlu aturan kategorisasi eksplisit saat implementasi, mis. `Indonesia` vs selain itu)

**Metrik siap pakai untuk `mart_aggregated`**:
1. `occupancy_rate`, `adr`, `revpar` — diteruskan dari `daily_occupancy`, digulung ke berbagai grain waktu
2. Revenue & jumlah booking per channel, per periode
3. Cancellation rate & no-show rate (per properti/channel/periode), dihitung dari `bookings.status`
4. Room type revenue mix (% kontribusi tiap tipe kamar terhadap total revenue properti)
5. MoM & YoY growth (occupancy, ADR, RevPAR) — kolom pembanding, bukan hanya angka absolut, karena benchmarking berkala adalah kerja rutin bukan sesekali
6. Pricing deviation: rata-rata `applied_rate − base_rate`, dan persentase hari per `reason` (manual/promo/dynamic-pricing-AI), per periode
7. Rata-rata & median length of stay (`nights`), per properti/room type/channel
8. Rata-rata & median booking lead time (`check_in_date − booking_date`), per properti/periode
9. Ranking/percentile RevPAR, ADR, occupancy antar 5 properti, per periode
10. Revenue & booking share: domestik vs mancanegara, per properti/periode
11. Repeat guest rate: % booking dari guest dengan riwayat booking sebelumnya vs guest baru, per periode

**Kebutuhan row-level (`mart_cleaned`, bukan `mart_aggregated`)**:
- Investigasi ad-hoc anomali (mis. lonjakan cancellation) — butuh `bookings` granular penuh
- Price elasticity analysis — butuh histori harian row-level harga vs okupansi

**Gap data sumber (dicatat, tidak diisi dengan asumsi)**:
- Komisi OTA per booking — tidak ada kolom di `bookings`
- Target/budget okupansi & revenue — tidak ada tabel target di skema yang ada

---

## 2. F&B Analyst

### 2.1 Role-Play: Dashboard & Laporan yang Dipegang

Saya F&B Analyst di Nirwana Hospitality Group, lapor ke F&B Manager, dengan akses lintas 5 properti untuk benchmarking outlet antar hotel. Domain ini punya karakter lebih kompleks dari Revenue — bukan cuma soal berapa banyak terjual, tapi ada rantai sebab-akibat operasional: dari harga bahan baku → food cost → margin, dan dari pola konsumsi (inhouse vs walk-in) → strategi outlet.

**Daily Outlet Sales Dashboard** (dicek tiap pagi):
- Revenue kemarin per outlet, dibanding hari biasa
- Jumlah struk (transaction count) dan average check per struk
- Breakdown revenue per kategori (Food/Beverage/Dessert)
- Pola intraday: sarapan/lunch/dinner/late-night — outlet mana ramai jam berapa

**Weekly Food Cost & Margin Report** (ke F&B Manager tiap Senin):
- Food cost ratio realisasi vs target per kategori (target: Food 34%, Beverage 24%, Dessert 28%)
- Menu dengan food cost melenceng jauh dari target minggu ini
- Alert kenaikan harga bahan baku signifikan (early warning sebelum margin tergerus)

**Weekly Waste Report**:
- Total waste (value & quantity) per outlet, breakdown per `reason` (overproduction/expired/spillage)
- Waste ratio terhadap total pemakaian, dibanding baseline
- Breakdown per reason untuk rekomendasi aksi berbeda (overproduction & expired bisa dicegah, spillage sebagian)

**Monthly Outlet Performance Report** (bahan rapat bulanan dengan F&B Manager & GM):
- Revenue per outlet, MoM & YoY
- Capture rate — porsi tamu inhouse yang belanja F&B
- Walk-in ratio per outlet & trennya
- Revenue mix per kategori item, top/bottom performing menu items
- Inventory health — jumlah item di bawah `stock_min_threshold`

**Quarterly/Annual Strategic Review** (bahan ke Corporate):
- Benchmarking antar outlet & antar properti — deteksi outlet underperform
- Tren harga bahan baku tahunan untuk perencanaan menu
- Perbandingan inhouse vs walk-in — revenue per kunjungan, kategori favorit masing-masing

**Ad-hoc investigation**:
- Investigasi anomali penjualan menu tertentu — butuh drill row-level `fnb_transactions`
- Basket analysis — item yang sering dibeli bersamaan dalam satu struk

### 2.2 Audit Kebutuhan

| Temuan audit | Keputusan |
|---|---|
| **Food cost ratio (realisasi vs target)** | Ditandai sebagai **agregasi cross-table**, bukan agregasi sederhana satu tabel — perlu join `fnb_transactions` × `recipe_bom` × `ingredient_price_history` berdasarkan tanggal transaksi |
| **Capture rate** (tamu inhouse yang belanja F&B) | Ditandai sebagai **agregasi cross-table** — perlu join `fnb_transactions` (customer_type=inhouse) dengan populasi tamu menginap dari `bookings`/`daily_occupancy` pada tanggal yang sama |
| **Basket analysis** | **Dikeluarkan dari cakupan `mart_aggregated`.** Butuh row-level per struk (`transaction_id`) — agregasi akan menghilangkan makna analisis ini. Kebutuhan ini dipenuhi dari `mart_cleaned`, bukan `mart_aggregated` |
| **Outlet underperform detection** | Ditambahkan eksplisit sebagai metrik pembanding (revenue outlet vs rata-rata outlet sejenis/properti sejenis) — sebelumnya hanya disebut naratif tanpa metrik konkret, mengikuti pola yang sama dengan "ranking antar properti" di Revenue Analyst |
| **Rekomendasi/pricing menu** | **Sengaja tidak dimasukkan.** F&B Analyst tidak berwenang menentukan harga menu — berbeda dari Revenue Analyst yang memang berurusan dengan pricing kamar |
| **Supplier/vendor performance** | **Tidak tersedia dari data sumber.** Tidak ada tabel supplier di skema manapun |
| **Waktu penyiapan/kecepatan servis outlet** | **Tidak tersedia dari data sumber.** Tidak ada kolom waktu servis di `fnb_transactions` (berbeda dari `housekeeping_log` yang punya start/end time) |

### 2.3 Kebutuhan Final

**Tabel sumber**: `fnb_transactions`, `fnb_outlets`, `recipe_bom`, `ingredient_price_history`, `fnb_inventory`, `fnb_waste_log` (dari `fnb_operations`); `bookings`/`daily_occupancy` (untuk capture rate, lintas domain)

**Dimensi (filter & group-by)**:
- `property_id`, `outlet_id`, `outlet_type` (Restaurant/Bar/Room Service)
- `category` (Food/Beverage/Dessert)
- `customer_type` (inhouse/walk-in)
- Waktu: jam (untuk pola intraday) → harian → mingguan → bulanan → kuartalan → tahunan
- `item_name` (untuk analisis per menu)

**Metrik siap pakai untuk `mart_aggregated`**:
1. Revenue, jumlah struk (transaction count), average check per struk — per outlet/periode
2. Revenue per kategori (Food/Beverage/Dessert) — per outlet/periode
3. Distribusi transaksi per jam/segmen waktu (sarapan/lunch/dinner/late-night) — per outlet
4. Food cost ratio realisasi (agregasi cross-table `fnb_transactions` × `recipe_bom` × `ingredient_price_history`) vs target per kategori, per outlet/periode
5. Daftar menu dengan deviasi food cost terbesar dari target, per periode
6. Total waste (value & quantity) dan waste ratio terhadap pemakaian, breakdown per `reason`, per outlet/periode
7. Revenue per outlet MoM & YoY growth
8. Capture rate (agregasi cross-table `fnb_transactions` × populasi tamu menginap), per properti/periode
9. Walk-in ratio dan trennya, per outlet/periode
10. Top & bottom performing menu items berdasarkan revenue/quantity, per outlet/periode
11. Jumlah & daftar item inventory di bawah `stock_min_threshold`, per outlet (snapshot terkini)
12. Ranking/pembanding revenue outlet terhadap rata-rata outlet sejenis (outlet_type sama) atau properti sejenis — untuk deteksi outlet underperform
13. Revenue per kunjungan dan kategori favorit — inhouse vs walk-in, per properti/periode
14. Tren harga rata-rata bahan baku per periode (dari `ingredient_price_history`, untuk perencanaan menu)

**Kebutuhan row-level (`mart_cleaned`, bukan `mart_aggregated`)**:
- Investigasi anomali penjualan menu tertentu — butuh `fnb_transactions` granular penuh
- Basket analysis — butuh row-level per `transaction_id` untuk melihat kombinasi item dalam satu struk

**Gap data sumber (dicatat, tidak diisi dengan asumsi)**:
- Data supplier/vendor bahan baku — tidak ada tabel ini di skema
- Waktu penyiapan/kecepatan servis per transaksi — tidak ada kolom timestamp granular di `fnb_transactions` (hanya `transaction_datetime`, tidak ada waktu selesai/durasi servis)

---

## 3. Facility/Ops Analyst

### 3.1 Role-Play: Dashboard & Laporan yang Dipegang

Saya Facility/Ops Analyst di Nirwana Hospitality Group, lapor ke Housekeeping/Maintenance Manager, dengan akses lintas 5 properti untuk benchmarking kondisi fisik antar hotel. Domain ini beda karakter dari Revenue dan F&B — bukan soal revenue, tapi efisiensi operasional, kualitas layanan (SLA), dan kondisi aset fisik. Dua sub-area: housekeeping (kebersihan) dan maintenance (perbaikan).

**Daily Room Status Dashboard** (dicek tiap pagi, koordinasi dengan Front Office):
- Distribusi status kamar saat ini per properti: occupied/available/cleaning/maintenance/out-of-order
- Jumlah kamar out-of-order (tidak bisa dijual) — prioritas tinggi karena berdampak langsung ke revenue
- Housekeeping progress hari ini — sesi selesai vs berjalan, jumlah delayed

**Weekly Housekeeping Performance Report** (ke Housekeeping Manager):
- Durasi rata-rata pembersihan per tipe kamar, dibanding baseline per tipe
- Delayed rate mingguan, dan korelasinya dengan okupansi
- Performa staff — siapa konsisten lebih lambat dari rata-rata staff lain

**Weekly Maintenance Report** (ke Maintenance Manager):
- Jumlah tiket baru per `facility_area` dan `issue_type` minggu ini
- SLA breach rate per `priority`, dibanding target
- Total cost minggu ini, breakdown dengan/tanpa ganti part
- Kamar dengan tiket berulang (recurring issue) — sinyal kamar butuh perbaikan struktural, bukan sekadar tambal

**Monthly Facility Cost & Trend Report** (bahan rapat bulanan dengan GM):
- Total maintenance cost bulanan per properti, MoM & YoY
- Breakdown cost per `issue_type`, tren mana yang naik
- Tiket per kamar per tahun — benchmark antar properti
- Housekeeping efficiency — rata-rata durasi & delayed rate per properti, dibanding rata-rata grup

**Quarterly/Annual Strategic Review** (bahan ke Corporate):
- Tren cost jangka panjang — dasar justifikasi budget maintenance
- Korelasi usia gedung vs frekuensi kerusakan — argumen untuk keputusan renovasi
- Ringkasan kamar/area bermasalah kronis untuk keputusan capital expenditure

**Ad-hoc investigation**:
- Investigasi lonjakan keluhan tipe kerusakan tertentu — butuh drill row-level `maintenance_tickets`
- Investigasi riwayat tiket per kamar tertentu — butuh row-level per kamar

### 3.2 Audit Kebutuhan

| Temuan audit | Keputusan |
|---|---|
| **Recurring issue detection** (kamar dengan tiket berulang) | Ditambahkan eksplisit sebagai metrik: jumlah tiket per `room_id` per periode, dibanding median/rata-rata kamar sejenis — identifikasi outlier di level entitas kamar, bukan hanya jumlah tiket total |
| **SLA breach — cara hitung & status pending** | Ditegaskan: breach dihitung dari `(resolved_date − reported_date) > SLA_hours` sesuai `priority`. Tiket yang masih `open`/`in-progress` (belum ada `resolved_date`) **ditandai sebagai kategori terpisah** ("pending" — SLA belum bisa dievaluasi final), tidak otomatis dihitung breach atau tidak breach |
| **Housekeeping delayed rate terkait okupansi** | Ditandai sebagai **agregasi cross-table** — perlu join `housekeeping_log` dengan `daily_occupancy` berdasarkan properti + tanggal |
| **Staff performance benchmarking (housekeeping)** | Ditambahkan eksplisit sebagai metrik per `staff_id`. Dicatat sebagai keputusan sadar: meski domain `facility` levelnya "Rendah" secara sensitivitas RBAC sementara ini data performa personal, metrik ini tetap dimasukkan karena Facility Analyst membutuhkannya untuk operasional harian — filtering akses granular tetap jadi tanggung jawab application layer, bukan pembatasan di desain mart |
| **Preventive maintenance** | **Tidak tersedia dari data sumber.** `maintenance_tickets` hanya berisi tiket reaktif (dilaporkan karena ada masalah); tidak ada tabel jadwal preventive maintenance terjadwal |
| **Dampak revenue dari kamar out-of-order** | Dibatasi ke level **jumlah/durasi kamar out-of-order** (dari `rooms.status`) tanpa estimasi kehilangan revenue — estimasi revenue butuh join cross-domain ke `daily_occupancy`/`bookings` yang belum tentu akurat (asumsi kamar pasti akan terjual), sehingga tidak dimasukkan sebagai metrik siap pakai |
| **Teknisi/staff maintenance workload** | Ditambahkan — sebelumnya tidak disebut di narasi awal. Natural diturunkan dari `assigned_staff_id` dan `labor_hours` yang tersedia di `maintenance_tickets` |
| **Vendor/parts cost breakdown** | **Kemampuan terbatas.** `parts_replaced` berupa teks bebas, bukan kategori terstruktur — breakdown "part apa paling mahal" tidak bisa diagregasi rapi. Yang tersedia: agregat cost tiket dengan-vs-tanpa penggantian part |

### 3.3 Kebutuhan Final

**Tabel sumber**: `rooms`, `housekeeping_log`, `maintenance_tickets` (dari `facility_maintenance`); `daily_occupancy` (untuk korelasi okupansi, lintas domain)

**Dimensi (filter & group-by)**:
- `property_id`
- `room_id`, `room_type` (untuk analisis per kamar/tipe kamar)
- `facility_area`, `issue_type`, `priority` (maintenance)
- `staff_id` / `assigned_staff_id` (housekeeping & maintenance)
- Waktu: harian → mingguan → bulanan → kuartalan → tahunan

**Metrik siap pakai untuk `mart_aggregated`**:
1. Distribusi status kamar saat ini per properti (occupied/available/cleaning/maintenance/out-of-order) — snapshot
2. Jumlah & durasi kamar out-of-order, per properti/periode
3. Durasi rata-rata pembersihan per tipe kamar, per properti/periode, dibanding baseline
4. Delayed rate housekeeping, per properti/periode
5. Delayed rate housekeeping terkait okupansi (agregasi cross-table dengan `daily_occupancy`), per properti/periode
6. Durasi pembersihan rata-rata per staff (`staff_id`), dibanding rata-rata staff lain — untuk benchmarking performa
7. Jumlah tiket maintenance baru per `facility_area`/`issue_type`, per properti/periode
8. SLA breach rate per `priority`, per properti/periode (tiket `open`/`in-progress` dikategorikan "pending", terpisah dari breach/tidak breach)
9. Total maintenance cost, breakdown dengan-vs-tanpa ganti part, per properti/periode
10. Cost breakdown per `issue_type`, MoM & YoY, per properti
11. Jumlah tiket per `room_id` per periode, dibanding median/rata-rata kamar sejenis — deteksi kamar recurring issue
12. Tiket per kamar per tahun — benchmark antar properti
13. Jumlah tiket & total `labor_hours` per teknisi (`assigned_staff_id`), per periode — workload teknisi
14. Tren cost & jumlah tiket bulanan jangka panjang, per properti (dasar proyeksi budget)

**Kebutuhan row-level (`mart_cleaned`, bukan `mart_aggregated`)**:
- Investigasi lonjakan keluhan tipe kerusakan tertentu — butuh `maintenance_tickets` granular penuh
- Investigasi riwayat tiket per kamar spesifik — butuh row-level per `room_id`

**Gap data sumber / kemampuan terbatas (dicatat, tidak diisi dengan asumsi)**:
- Jadwal preventive maintenance — tidak ada tabel ini; semua tiket bersifat reaktif
- Estimasi kehilangan revenue akibat kamar out-of-order — tidak dimasukkan sebagai metrik siap pakai karena butuh asumsi cross-domain yang belum tentu akurat
- Breakdown biaya per jenis part — `parts_replaced` teks bebas, bukan kategori terstruktur

---

## 4. Spa & Event Analyst

### 4.1 Role-Play: Dashboard & Laporan yang Dipegang

Saya Spa & Event Analyst di Nirwana Hospitality Group, lapor ke Spa & Event Manager, dengan akses lintas 5 properti. Domain ini sebenarnya dua bisnis berbeda karakter yang digabung satu departemen: **Spa** (volume tinggi, transaksi kecil-menengah, mirip pola F&B) dan **Event/MICE** (volume rendah, nilai per transaksi sangat besar, lebih mirip pola B2B/sales kontrak). Cara berpikir untuk keduanya perlu dipisah, bukan disamakan.

**Daily/Weekly Spa Performance Dashboard**:
- Revenue & jumlah booking spa kemarin/minggu ini per properti
- Revenue per kunjungan, breakdown inhouse vs walk-in (gap besar antar keduanya)
- Distribusi booking per `service_name` (9 layanan) — mana yang paling laku
- Walk-in ratio per properti & trennya

**Weekly/Monthly Event Pipeline Report** (ritme beda dari spa — event direncanakan jauh hari, bukan transaksi harian):
- Event terkonfirmasi untuk periode mendatang (pipeline), per venue/properti
- Utilisasi venue (`capacity_booked ÷ max_capacity`), per event dan rata-rata per venue
- Cancellation rate event — signifikan karena satu event batal nilainya besar
- Revenue per `event_type` dan mix-nya

**Monthly Spa & Event Combined Performance** (bahan rapat bulanan dengan Manager & GM):
- Total revenue spa vs event, kontribusi masing-masing terhadap departemen
- Spa: tren popularitas layanan MoM/YoY — pergeseran preferensi
- Event: revenue per venue, venue paling produktif vs paling sering "nganggur"
- Lead time booking spa (booking_date ke service_date) — jauh lebih pendek dari lead time kamar

**Quarterly/Annual Strategic Review** (bahan ke Corporate):
- Benchmarking walk-in ratio & capture spa antar properti — dasar strategi pemasaran lokal
- Benchmarking utilisasi venue antar properti — dasar keputusan ekspansi/renovasi venue
- Tren revenue event tahunan, terutama musiman (wedding season, corporate year-end events)

**Ad-hoc investigation**:
- Investigasi anomali utilisasi venue antar properti — butuh drill row-level `event_bookings`
- Investigasi klien event tertentu — butuh row-level `client_name`

### 4.2 Audit Kebutuhan

| Temuan audit | Keputusan |
|---|---|
| **Revenue per kunjungan inhouse vs walk-in** | Ditegaskan sebagai metrik eksplisit per periode (bukan angka statis satu kali) |
| **Tren popularitas layanan** (`service_name` share over time) | Ditambahkan eksplisit: % kontribusi tiap `service_name` terhadap total booking/revenue, per periode — supaya pergeseran tren terlihat dari data aktual |
| **Venue "nganggur" kronis** | Ditambahkan sebagai metrik pembanding eksplisit: venue dengan utilisasi di bawah threshold secara **berulang** (bukan rata-rata sekali hitung) — mengikuti pola "recurring issue" yang sama seperti di Facility Analyst |
| **Repeat client event** | **Kemampuan terbatas.** `client_name` adalah teks bebas (nama pasangan/perusahaan), tidak ada ID klien terstruktur — deteksi repeat client akan rapuh terhadap variasi penulisan nama. Tidak dimasukkan sebagai metrik siap pakai di `mart_aggregated`; jika dibutuhkan, harus dilakukan row-level dengan fuzzy matching manual oleh analyst |
| **Venue double-booking/konflik jadwal** | **Tidak diperlukan sebagai metrik pemantauan.** Data dictionary menyatakan constraint ini terjaga sistem (0 pelanggaran) — berbeda dari SLA breach di Facility yang memang terjadi secara riil di data |
| **Diskon/promo pada spa/event** | **Tidak tersedia dari data sumber.** Tidak ada kolom promo/discount di `spa_bookings` maupun `event_bookings` (berbeda dari `pricing_history` yang eksplisit punya `reason=promo`) |
| **Cross-sell spa × event** | **Kemampuan sangat terbatas.** Event umumnya terkait klien non-individual (perusahaan/pasangan), bukan `guest_id` terdaftar — join yang andal antara `spa_bookings` dan `event_bookings` tidak dapat diasumsikan tersedia. Tidak dimasukkan sebagai metrik andal |
| **Pemetaan venue_type ke event_type yang cocok** | **Tidak dimasukkan sebagai metrik.** Ini aturan bisnis/konfigurasi tetap, bukan sesuatu yang perlu diagregasi atau dianalisis trennya |

### 4.3 Kebutuhan Final

Dipisah dua sub-bagian karena karakter data yang berbeda signifikan (volume tinggi/nilai kecil vs volume rendah/nilai besar).

#### 4.3.1 Spa

**Tabel sumber**: `spa_bookings` (dari `spa_event`)

**Dimensi (filter & group-by)**:
- `property_id`
- `service_name`
- `customer_type` (inhouse/walk-in)
- Waktu: harian → mingguan → bulanan → kuartalan → tahunan

**Metrik siap pakai untuk `mart_aggregated`**:
1. Revenue & jumlah booking, per properti/periode
2. Revenue per kunjungan, breakdown inhouse vs walk-in, per properti/periode
3. Distribusi booking & revenue per `service_name`, per periode
4. Walk-in ratio per properti dan trennya, per periode
5. % kontribusi tiap `service_name` terhadap total booking/revenue, per periode (tren popularitas layanan)
6. Rata-rata & median lead time booking (`service_date − booking_date`), per properti/periode
7. Cancellation rate spa, per properti/periode

**Kebutuhan row-level (`mart_cleaned`)**:
- Tidak ada kebutuhan khusus row-level di luar yang sudah tercakup skema `mart_cleaned` standar untuk investigasi ad-hoc

#### 4.3.2 Event/MICE

**Tabel sumber**: `event_bookings`, `venues` (dari `spa_event`)

**Dimensi (filter & group-by)**:
- `property_id`, `venue_id`, `venue_type`
- `event_type`
- Waktu: `event_date`, digulung mingguan → bulanan → kuartalan → tahunan

**Metrik siap pakai untuk `mart_aggregated`**:
1. Jumlah & revenue event terkonfirmasi untuk periode mendatang (pipeline), per venue/properti
2. Utilisasi venue (`capacity_booked ÷ max_capacity`) rata-rata, per venue/periode
3. Venue dengan utilisasi di bawah threshold secara berulang (recurring low-utilization), per periode
4. Cancellation rate event, per properti/periode
5. Revenue & jumlah event per `event_type`, mix per periode
6. Revenue per venue, MoM & YoY

**Kebutuhan row-level (`mart_cleaned`)**:
- Investigasi anomali utilisasi venue tertentu — butuh `event_bookings` granular penuh
- Investigasi klien event tertentu (`client_name`) — butuh row-level, termasuk untuk analisis repeat client dengan fuzzy matching manual

**Gap data sumber / kemampuan terbatas (dicatat, tidak diisi dengan asumsi)**:
- Diskon/promo pada spa maupun event — tidak ada kolom ini di skema
- Repeat client event — `client_name` teks bebas tanpa ID terstruktur, deteksi otomatis tidak andal
- Cross-sell spa × event — tidak ada penghubung `guest_id` yang konsisten antara kedua tabel

---

## 5. HR Analyst

### 5.1 Role-Play: Dashboard & Laporan yang Dipegang

Saya HR Analyst di Nirwana Hospitality Group, lapor ke HR Manager, dengan akses lintas 5 properti. Domain ini beda dari Revenue/F&B/Facility — saya tidak bicara revenue atau biaya operasional, saya bicara manusia: kehadiran, kinerja, dan yang paling krusial, risiko turnover. Sensitivitasnya jelas lebih tinggi — domain `hr`, bukan `facility` yang "Rendah".

**Daily/Weekly Attendance Dashboard**:
- Attendance rate hari/minggu ini per properti/departemen: present/late/leave/absent
- Departemen/properti dengan absensi/keterlambatan di luar kebiasaan minggu ini — early warning, bukan cuma laporan retrospektif
- Overtime hours — total dan distribusinya, terutama saat okupansi tinggi

**Weekly/Monthly Turnover Risk Watchlist** (laporan paling penting yang dipegang):
- Daftar karyawan dengan sinyal gejala pra-resign — absensi & keterlambatan meningkat dibandingkan histori mereka sendiri, bukan dibanding karyawan lain
- Skor performa terakhir per karyawan, terutama tren menurun antar periode review
- Watchlist yang diperbarui rutin untuk ditindaklanjuti HR Manager (percakapan retensi, dsb)

**Monthly Departmental HR Report** (bahan rapat bulanan dengan HR Manager & GM):
- Turnover rate per departemen/properti, MoM & YoY
- Distribusi status karyawan (active/resigned/terminated) per departemen
- Rata-rata skor performa per departemen, tren antar periode review
- Jam lembur berlebihan — siapa yang konsisten lembur jauh di atas normal
- Keterlambatan kronis — siapa yang konsisten sering telat

**Quarterly/Annual Strategic Review** (bahan ke Corporate):
- Tren turnover tahunan per departemen — dasar keputusan staffing/kompensasi
- Benchmarking turnover antar properti
- Korelasi kinerja & retensi — apakah performer bagus yang resign (kehilangan lebih mahal) atau performer biasa

**Ad-hoc investigation**:
- Investigasi lonjakan absensi departemen/periode tertentu — butuh drill row-level `staff_shifts`
- Investigasi karyawan tertentu yang masuk watchlist — butuh row-level histori shift & performance

### 5.2 Audit Kebutuhan

| Temuan audit | Keputusan |
|---|---|
| **Gejala pra-resign — perbandingan terhadap baseline individu** | Ditandai sebagai **kategori metrik tersendiri**: bukan angka absolut per periode, melainkan rasio perubahan pola individu terhadap histori orang itu sendiri (mis. rate absen 3 bulan terakhir dibanding rate absen individu tersebut sebelumnya). Berbeda sifat dari metrik agregat biasa yang membandingkan antar entitas/periode grup — ini perbandingan *within-entity over time* |
| **Threshold "di luar kebiasaan" untuk early warning** | **Tidak ditentukan di sini.** Dokumen induk (Bagian 10 No. 3) sudah eksplisit menandai ambang batas drift/anomali sebagai area yang perlu didiskusikan terpisah dengan pihak berwenang. Metrik dasarnya (rate absen/telat per periode, per individu) disediakan; threshold di luar cakupan pemetaan ini |
| **Turnover benchmark per departemen** | Ditegaskan: metrik ini dihitung dari data aktual (`status != 'active'` dibagi total karyawan pernah aktif di departemen itu, per periode) — bukan diasumsikan hasilnya duluan dari insight naratif metadata |
| **Overtime dalam satuan jam vs rupiah** | Diklarifikasi: HR Analyst mendapat metrik overtime dalam **satuan jam**, dihitung langsung dari `staff_shifts` (`clock_out − clock_in − 8 jam`). Nilai rupiah lembur (`payroll.overtime_pay`) **tidak** menjadi kebutuhan HR Analyst — lihat poin payroll di bawah |
| **Korelasi kinerja & retensi** | Ditandai sebagai metrik struktur khusus: perbandingan skor performa terakhir antar populasi resign vs aktif — bukan agregasi periode biasa, mirip pola gejala pra-resign |
| **Payroll/kompensasi** | **Sengaja dikeluarkan dari cakupan HR Analyst.** Mengikuti praktik industri: HR (people operations — attendance, performance, turnover) secara struktural terpisah dari Payroll/Compensation (pengeluaran keuangan perusahaan), umumnya di bawah Finance untuk segregation of duties. Ini konsisten dengan pemisahan domain `hr` vs `financial` di `role_permissions` data kamu sendiri. Payroll (`base_salary`, `service_charge`, `overtime_pay` dalam rupiah, `net_salary`) sepenuhnya menjadi cakupan **Corporate/Financial Analyst** |
| **Exit interview / alasan resign** | **Tidak tersedia dari data sumber.** `employees.status` hanya menyatakan status akhir, tanpa tanggal atau alasan resign di tabel resmi |
| **Training/sertifikasi karyawan** | **Tidak tersedia dari data sumber.** Tidak ada tabel ini di skema manapun |

### 5.3 Kebutuhan Final

**Tabel sumber**: `staff_shifts`, `employee_performance` (dari `hr_finance` domain `hr`); `employees` (untuk konteks departemen/status)

**Dimensi (filter & group-by)**:
- `property_id`, `department`
- `employee_id` (untuk analisis level individu — watchlist, korelasi kinerja-retensi)
- `shift_type` (Morning/Afternoon/Night)
- Waktu: harian → mingguan → bulanan → per periode review (semesteran) → tahunan

**Metrik siap pakai untuk `mart_aggregated`**:
1. Attendance rate (present/late/leave/absent) per properti/departemen/periode
2. Jam lembur total & distribusinya, per properti/departemen/periode
3. Jam lembur per individu dibanding rata-rata departemen — deteksi lembur berlebihan kronis
4. Rate keterlambatan per individu dibanding rata-rata departemen — deteksi keterlambatan kronis
5. **Rasio perubahan pola individu** (rate absen & rate telat periode terkini dibanding baseline historis individu tersebut) — metrik inti watchlist gejala pra-resign
6. Skor performa terakhir per karyawan, dan tren antar periode review
7. Turnover rate per departemen/properti (dihitung dari data aktual), MoM & YoY
8. Distribusi status karyawan (active/resigned/terminated) per departemen/properti
9. Rata-rata skor performa per departemen, tren antar periode review
10. Perbandingan skor performa terakhir: populasi resign/terminated vs populasi aktif — untuk analisis korelasi kinerja-retensi

**Kebutuhan row-level (`mart_cleaned`, bukan `mart_aggregated`)**:
- Investigasi lonjakan absensi pada departemen/periode tertentu — butuh `staff_shifts` granular penuh
- Investigasi karyawan tertentu yang masuk watchlist — butuh row-level histori shift & performance individu

**Gap data sumber / di luar cakupan (dicatat, tidak diisi dengan asumsi)**:
- Payroll/kompensasi — sengaja di luar cakupan HR Analyst, menjadi domain Corporate/Financial Analyst
- Exit interview / alasan resign — tidak ada di tabel resmi
- Training/sertifikasi karyawan — tidak ada tabel ini di skema

---

## 6. Corporate/Financial Analyst

### 6.1 Role-Play: Dashboard & Laporan yang Dipegang

Saya Corporate/Financial Analyst di Nirwana Hospitality Group, lapor ke Corporate Finance Director — peran yang di `role_permissions` memegang domain `financial` dengan `access_scope=all_properties`, satu-satunya kombinasi ini di seluruh matriks RBAC. Laporan saya jadi bahan utama CEO. Peran ini berbeda fundamental dari 5 peran sebelumnya — mereka masing-masing bekerja *dalam* satu domain, saya bekerja *di atas* semua domain: mengonsolidasi Revenue + F&B + Facility + Spa&Event + biaya HR jadi satu bahasa, yaitu profitabilitas. Saya juga satu-satunya yang menyentuh `financial_summary` dan `payroll` secara penuh.

**Weekly Corporate Snapshot** (ringkas, untuk CEO tiap Senin):
- Revenue run-rate tiap properti minggu berjalan
- Flag properti yang performanya menyimpang dari biasanya minggu ini

**Monthly USALI Report** (laporan formal bulanan, inti pekerjaan):
- Departmental revenue, expense, profit per properti (Room/F&B/Spa&Event), sesuai struktur USALI
- Undistributed expense breakdown (Admin&General, Sales&Marketing, Utilities, Property Maintenance, IT)
- GOP per properti, dan GOP margin (%), MoM & YoY
- Departmental margin per lini bisnis (Room/F&B/Spa&Event)
- Koherensi check — revenue Room di laporan ini harus cocok dengan total transaksi booking dari sumbernya

**Monthly Payroll & Labor Cost Report** (satu-satunya yang memegang detail payroll):
- Total base_salary, service_charge, overtime_pay, THR, deduction, net_salary — per properti/departemen, MoM
- Service charge pool per properti dan korelasinya dengan okupansi
- Labor cost sebagai % dari revenue
- Rasio service charge terhadap base salary per level (staff vs manager)

**Quarterly/Annual Strategic Review** (bahan utama ke CEO & Board — menjawab kebutuhan "laporan analisis untuk CEO"):
- Benchmarking GOP margin antar 5 properti
- Tren profitabilitas jangka panjang per properti dan grup
- Kontribusi tiap lini bisnis terhadap total revenue grup, dan pergeserannya dari waktu ke waktu
- Overhead ratio (undistributed expense terhadap revenue)

**Ad-hoc investigation**:
- Investigasi penurunan margin lini bisnis tertentu — drill lintas domain (revenue turun atau cost naik)
- Audit alokasi service charge — memastikan alokasi proporsional sesuai kontribusi revenue tidak keliru

### 6.2 Audit Kebutuhan

| Temuan audit | Keputusan |
|---|---|
| **GOP mingguan** | **Kemampuan terbatas.** `financial_summary` granularitasnya bulanan (`period` format `YYYY-MM`) — tidak ada versi mingguan/harian, dan expense tidak tersedia granular harian dari domain lain. GOP mingguan tidak dapat dihitung akurat dari sumber yang ada. Diturunkan menjadi: dashboard mingguan cukup memakai **revenue run-rate** (dari data transaksi harian tiap domain), bukan GOP penuh |
| **Koherensi check** (`financial_summary` vs total transaksi booking) | Dipisahkan secara eksplisit sebagai **kebutuhan validasi/monitoring data quality**, bukan metrik analisis bisnis biasa — relevan terhadap Bagian 9 dokumen induk (Data Quality Gate), bukan sekadar item pelaporan |
| **Overhead ratio — filter baris `Overall`** | Ditegaskan: `undistributed_expense` hanya terisi pada baris `department='Overall'`. Metrik ini wajib difilter ke baris tersebut, tidak dijumlah bersama baris departemen lain |
| **Departmental margin — filter baris `Overall`** | Ditegaskan: metrik "departmental margin" wajib filter `department IN ('Room','F&B','Spa&Event')`, tidak menyertakan `Overall` maupun `Corporate Overhead`, sesuai aturan baku data dictionary yang eksplisit memperingatkan risiko double counting |
| **Rasio service charge vs base salary per level** | Ditambahkan eksplisit sebagai metrik — sebelumnya hanya disebut naratif, kini diturunkan menjadi agregasi payroll di-breakdown per `access_level` (staff/manager) |
| **Breakdown komponen cost dari domain lain** (food cost, maintenance cost, dst) | **Sengaja tidak dimasukkan.** `departmental_expense` di `financial_summary` sudah berupa angka agregat jadi. Breakdown detail komponennya adalah tanggung jawab masing-masing domain analyst (F&B Analyst sudah memegang food cost, Facility Analyst sudah memegang maintenance cost) — Corporate Analyst memakai angka `departmental_expense` yang sudah tersedia, tidak mengulang detail tersebut. Ditandai sebagai batasan cakupan yang disengaja |
| **Payroll sebagai cakupan eksklusif** | Konsisten dengan audit HR Analyst: seluruh `payroll` (base_salary, service_charge, overtime_pay rupiah, THR, deduction, net_salary) sepenuhnya menjadi cakupan Corporate/Financial Analyst, bukan HR Analyst |
| **Cost of capital / depresiasi / finansial non-operasional** | **Tidak tersedia dari data sumber.** Tidak ada kolom ini di skema manapun. Konsisten dengan struktur USALI yang memang berhenti di level GOP ("below GOP line" tidak dicakup data ini) |

### 6.3 Kebutuhan Final

**Tabel sumber**: `financial_summary`, `payroll` (dari `hr_finance` domain `financial`); `bookings` (untuk koherensi check, lintas domain); `employees` (untuk konteks `access_level` pada breakdown service charge)

**Dimensi (filter & group-by)**:
- `property_id`, `region`
- `department` (khusus USALI: `Room`/`F&B`/`Spa&Event` untuk margin per lini bisnis; `Overall` khusus untuk GOP & overhead — tidak pernah dicampur)
- `access_level` (staff/manager, untuk breakdown service charge)
- Waktu: bulanan (grain asli `financial_summary`/`payroll`) → kuartalan → tahunan; harian hanya untuk revenue run-rate dari domain sumber lain

**Metrik siap pakai untuk `mart_aggregated`**:
1. Departmental revenue, expense, profit per properti/departemen (Room/F&B/Spa&Event), per periode
2. GOP dan GOP margin (%) per properti, MoM & YoY (dari baris `Overall`)
3. Undistributed expense breakdown per komponen (Admin&General, Sales&Marketing, Utilities, Property Maintenance, IT), per properti/periode (dari baris `Overall`)
4. Departmental margin (%) per lini bisnis, per properti/periode (filter `Room`/`F&B`/`Spa&Event`)
5. Overhead ratio (undistributed expense ÷ revenue), per properti/periode (dari baris `Overall`)
6. Revenue run-rate harian/mingguan per properti (dari agregasi domain sumber, bukan `financial_summary`) — untuk snapshot mingguan
7. Total komponen payroll (base_salary, service_charge, overtime_pay, THR, deduction, net_salary), per properti/departemen, MoM
8. Service charge pool per properti dan korelasinya dengan occupancy rate (agregasi cross-table dengan `daily_occupancy`)
9. Labor cost sebagai % dari revenue, per properti/periode
10. Rasio service charge terhadap base salary, per `access_level`, per properti/periode
11. Kontribusi tiap lini bisnis (Room/F&B/Spa&Event) terhadap total revenue grup, dan pergeserannya antar periode
12. Benchmarking/ranking GOP margin antar 5 properti, per periode

**Kebutuhan validasi/monitoring (bukan metrik analisis, terkait Data Quality Gate di Bagian 9 dokumen induk)**:
- Koherensi revenue Room di `financial_summary` terhadap total transaksi booking (status completed/confirmed) dari sumbernya — selisih harus 0 atau dalam toleransi yang disepakati

**Kebutuhan row-level (`mart_cleaned`, bukan `mart_aggregated`)**:
- Investigasi penurunan margin lini bisnis tertentu — drill ke `financial_summary` granular per bulan/departemen untuk menelusuri sumber perubahan
- Audit alokasi service charge — butuh `payroll` row-level per karyawan untuk verifikasi proporsionalitas alokasi

**Gap data sumber (dicatat, tidak diisi dengan asumsi)**:
- GOP/financial granularitas mingguan atau harian — sumber hanya bulanan
- Cost of capital, depresiasi, dan komponen finansial non-operasional (below GOP line) — tidak ada di skema

---

## Ringkasan Lintas Domain

| Domain | Fokus | Ciri khas kebutuhan yang ditemukan |
|---|---|---|
| Revenue | Okupansi, ADR, RevPAR, channel, pricing | Ada kebutuhan forward-looking (pace booking) yang sengaja dikeluarkan dari cakupan — butuh desain snapshot terpisah |
| F&B | Sales outlet, food cost, waste, capture rate | Banyak metrik butuh agregasi cross-table (food cost, capture rate); basket analysis butuh row-level |
| Facility | Housekeeping, maintenance, kondisi aset | Ada metrik performa individu staff yang sensitivitasnya lebih tinggi dari label domain RBAC "Rendah" — dimasukkan sebagai keputusan sadar |
| Spa & Event | Spa (volume tinggi) dan Event/MICE (volume rendah, nilai besar) | Dipisah 2 sub-bagian karena karakter data berbeda signifikan; beberapa metrik (repeat client, cross-sell) dibatasi karena `client_name` teks bebas tanpa ID terstruktur |
| HR | Attendance, performance, turnover risk | Metrik inti (gejala pra-resign) bersifat *within-entity over time*, bukan agregasi grup biasa; payroll sengaja dikeluarkan mengikuti segregation of duties dunia nyata |
| Corporate/Financial | Konsolidasi USALI, GOP, payroll, laporan CEO | Satu-satunya domain yang memegang payroll penuh; beberapa metrik dibatasi granularitas waktu (GOP mingguan tidak akurat dari sumber bulanan) |

Enam pola ini menjadi dasar penentuan cakupan `mart_aggregated` (Bagian 5.2.1 dokumen induk) dan konfirmasi bagian dari `mart_cleaned` yang dibutuhkan Data Analyst untuk investigasi row-level, melengkapi Bagian 10 No. 6 dokumen arsitektur induk.

---

*Dokumen ini merupakan hasil pemetaan kebutuhan Data Analyst, sebagai masukan untuk penentuan cakupan `mart_aggregated` pada dokumen arsitektur induk.*
