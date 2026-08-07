# Pemetaan Kebutuhan AI Chatbot — Layer Staff

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` |
| **Dokumen terkait** | `rancangan-rbac-ai-chatbot.md` (basis RBAC 20 persona), `role_permissions_chatbot_v2.csv` (RBAC final) |
| **Tujuan dokumen** | Memetakan kebutuhan tanya-jawab AI Chatbot untuk 7 posisi Staff, sebagai masukan cakupan `mart_aggregated` |
| **Metodologi** | Role-play per posisi → audit kebutuhan → **verifikasi setiap klaim kolom/tabel ke `DataSchema.md` aktual** (bukan mengandalkan ingatan) |
| **Status** | Layer Staff selesai, sudah diverifikasi ulang terhadap skema aktual |

---

## Catatan Penting: Verifikasi Data

Setiap klaim "kolom X ada/tidak ada di tabel Y" pada dokumen ini telah diverifikasi langsung terhadap `DataSchema.md`. Verifikasi awal (sebelum audit ulang ini) sempat memuat satu kekeliruan yang sudah dikoreksi — dicatat secara eksplisit di bagian F&B Staff di bawah — sebagai pengingat bahwa setiap kebutuhan yang dituliskan harus bisa ditelusuri ke kolom/tabel nyata, bukan diasumsikan dari kesan umum terhadap skema.

---

## 1. Front Office Staff

**RBAC**: `reservation` (own_property) + `properties_ref` (own_property) + `guests_pii` (own_property)

### Role-Play

Berhadapan langsung dengan tamu saat check-in/check-out, chatbot dipakai untuk jawaban instan di counter.

**Pertanyaan yang mungkin diajukan**:
- Status kamar tertentu saat ini, sudah bisa dihuni atau belum
- Kontak tamu untuk konfirmasi ulang booking
- Daftar tamu yang belum check-in hari ini
- Riwayat menginap tamu sebelumnya, loyalty tier untuk sapaan personal
- Detail satu booking spesifik untuk menjawab pertanyaan tamu di counter
- Ketersediaan kamar untuk upgrade mendadak
- Status housekeeping/out-of-order kamar (agar tidak salah assign)

### Audit & Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Status kamar & housekeeping | `rooms.status`, `housekeeping_log` ada di domain `facility` — **bukan** `reservation` | **Ditolak RBAC** — meski data ada di sistem, Front Office Staff tidak dapat akses domain `facility` |
| Kontak tamu untuk konfirmasi | `guests.email`, `guests.phone` — **terverifikasi ada** | Dalam cakupan (`guests_pii`) |
| Alasan harga berbeda dari ekspektasi tamu | `bookings.room_rate`, `total_amount` ada; tapi tidak ada kolom `reason` di `bookings` (beda dari `pricing_history.reason` yang levelnya Revenue Manager) | Front Office hanya bisa lihat **angka final** booking, tidak bisa jelaskan alasan strategis harga |
| Riwayat menginap tamu sebelumnya | `bookings.guest_id` sebagai FK — **terverifikasi**, bisa query row-level per guest_id | Dalam cakupan, butuh row-level bukan agregat |
| Ketersediaan kamar untuk upgrade | `daily_occupancy.rooms_sold`/`total_rooms_available` per `room_type` — **terverifikasi ada** di domain `reservation` | Dalam cakupan |

### Kebutuhan Data (domain `reservation`+`properties_ref`+`guests_pii`, own_property)

1. Status booking hari ini per kamar/tamu (check-in/check-out/no-show) — dari `bookings.status`, filter `check_in_date`/`check_out_date`
2. Detail satu booking spesifik by nama tamu/kamar/tanggal, termasuk `room_rate`/`total_amount` — dari `bookings`
3. Kontak tamu (`full_name`, `email`, `phone`) untuk tamu dengan booking aktif di propertinya — dari `guests`
4. Riwayat booking tamu tersebut di properti ini — row-level `bookings` per `guest_id`
5. `loyalty_tier` tamu — dari `guests`
6. Ketersediaan kamar per `room_type` — dari `daily_occupancy`

**Di luar cakupan (ditolak RBAC)**: status housekeeping/out-of-order (`facility`), alasan strategi harga (`pricing_history.reason`, levelnya Revenue Manager)

---

## 2. F&B Staff

**RBAC**: `fnb` (own_property) saja

### Role-Play

Bekerja di outlet F&B, chatbot dipakai saat melayani order/shift sibuk.

**Pertanyaan yang mungkin diajukan**:
- Ketersediaan bahan untuk suatu menu
- Harga jual menu saat ini
- Menu terlaris hari ini
- Stok bahan yang menipis
- Total penjualan outlet hari berjalan
- Komposisi bahan menu (untuk info alergi ke tamu)

### Audit & Verifikasi — Termasuk Koreksi Kekeliruan Sebelumnya

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| **Harga jual menu saat ini** | **[KOREKSI]** Klaim sebelumnya menyebut ini tersedia dari `recipe_bom` — **ini keliru setelah verifikasi ulang**. `recipe_bom` hanya berisi `item_name`, `ingredient_id`, `qty_per_portion` (komposisi bahan, bukan harga jual). Tidak ada tabel/kolom `selling_price` atau daftar harga menu resmi di skema manapun. Yang ada hanya `unit_price`/`total_price` di `fnb_transactions` — itu harga transaksi yang sudah terjadi | **Gap data sumber.** Bisa diakali dengan mengambil `unit_price` dari transaksi terakhir per `item_name` sebagai proxy, tapi ini bukan lookup harga resmi dan berisiko keliru jika ada perbedaan harga antar waktu/outlet tanpa tabel referensi eksplisit |
| Ketersediaan bahan baku | `fnb_inventory.stock_current` vs `stock_min_threshold` — **terverifikasi ada** | Dalam cakupan |
| Menu terlaris hari ini | `fnb_transactions.item_name`, `quantity` — **terverifikasi ada**, agregasi ringan harian | Dalam cakupan |
| Total penjualan outlet berjalan | `fnb_transactions.total_price` per `outlet_id` — **terverifikasi ada** | Dalam cakupan |
| Komposisi bahan menu | `recipe_bom.ingredient_id`, `qty_per_portion` — **terverifikasi ada** | Dalam cakupan |
| Target/budget penjualan harian | Tidak ada tabel target/budget di skema manapun (konsisten dengan gap yang sama ditemukan di Revenue Analyst) | Gap data sumber |
| Jadwal rekan kerja shift | Domain `hr` (`staff_shifts`), bukan `fnb` | Ditolak RBAC |
| Status/identitas tamu | F&B Staff tidak dapat domain `guests` apa pun | Ditolak RBAC |
| Analisis food cost/margin | Butuh join `fnb_transactions`×`recipe_bom`×`ingredient_price_history`, levelnya F&B Manager | Di luar cakupan staff |

### Kebutuhan Data (domain `fnb`, own_property)

1. Level stok bahan baku saat ini per item, per outlet — dari `fnb_inventory`
2. Menu terlaris hari ini/shift ini — agregasi ringan dari `fnb_transactions`
3. Total penjualan outlet hari berjalan — dari `fnb_transactions`
4. Komposisi bahan suatu menu — dari `recipe_bom`

**Gap data sumber**: harga jual menu resmi (tidak ada tabel harga menu, hanya harga transaksi historis sebagai proxy); target/budget penjualan harian

**Di luar cakupan (ditolak RBAC)**: jadwal staff lain (`hr`), identitas tamu (`guests`), analisis food cost (levelnya manager)

---

## 3. Housekeeping Staff

**RBAC**: `facility` (own_property) saja

### Role-Play

Membersihkan kamar sesuai penugasan harian, chatbot dipakai lewat HP di sela tugas.

**Pertanyaan yang mungkin diajukan**:
- Daftar kamar yang perlu dibersihkan hari ini
- Status kamar tertentu saat ini
- Durasi rata-rata pembersihan dirinya sendiri per tipe kamar
- Catatan khusus/permintaan tamu terkait kamar
- Tiket maintenance terbuka terkait kamar yang dikerjakan
- Perbandingan kecepatan kerja dengan staff lain

### Audit & Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Daftar kamar tugas & status | `rooms.status`, `housekeeping_log.room_id`/`date` — **terverifikasi ada** | Dalam cakupan |
| Durasi pembersihan dirinya sendiri | `housekeeping_log.cleaning_start_time`, `cleaning_end_time`, `staff_id` — **terverifikasi ada**, filter wajib `staff_id`=dirinya | Dalam cakupan, dengan filter wajib individu |
| Catatan/permintaan khusus tamu | **Terverifikasi tidak ada** — tidak ada kolom notes di `rooms` maupun `housekeeping_log` | Gap data sumber |
| Tiket maintenance terkait kamar | `maintenance_tickets.room_id` — **terverifikasi ada**, masih domain `facility` yang sama | Dalam cakupan |
| Perbandingan dengan staff lain | Data ada (`housekeeping_log.staff_id` semua staff), tapi ini benchmarking performa — levelnya Housekeeping Manager | Ditolak — staff hanya lihat data dirinya sendiri |
| Okupansi hari ini | Domain `reservation`, bukan `facility` | Ditolak RBAC |

### Kebutuhan Data (domain `facility`, own_property, dengan filter `staff_id` untuk data performa individu)

1. Daftar kamar yang perlu dibersihkan hari ini/shift ini, dengan status — dari `rooms`, `housekeeping_log`
2. Status kamar spesifik saat ini — dari `rooms.status`
3. Durasi pembersihan historis dirinya sendiri per tipe kamar — dari `housekeeping_log`, filter `staff_id`=dirinya
4. Jumlah kamar yang sudah diselesaikan hari ini (dirinya sendiri)
5. Tiket maintenance terbuka terkait kamar yang dikerjakan — dari `maintenance_tickets.room_id`

**Gap data sumber**: catatan/permintaan khusus tamu terkait kamar

**Di luar cakupan (ditolak RBAC)**: performa staff housekeeping lain, data okupansi/reservasi

---

## 4. Maintenance Staff (Teknisi)

**RBAC**: `facility` (own_property) saja

### Role-Play

Mengerjakan tiket perbaikan yang ditugaskan, chatbot dipakai untuk cek detail tiket & riwayat kamar.

**Pertanyaan yang mungkin diajukan**:
- Tiket yang ditugaskan hari ini, prioritas mana dulu
- Detail satu tiket spesifik
- Riwayat perbaikan kamar tertentu
- Status SLA — apakah sudah mendekati batas waktu
- Part yang pernah dipakai untuk kasus serupa (miliknya sendiri)
- Perbandingan jumlah tiket dengan teknisi lain

### Audit & Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Tiket ditugaskan & detail | `maintenance_tickets.assigned_staff_id`, `facility_area`, `issue_type`, `priority`, `reported_date` — **terverifikasi ada** | Dalam cakupan |
| Riwayat tiket per kamar | `maintenance_tickets.room_id` — **terverifikasi ada** (nullable, bisa fasilitas umum). Dilihat sebagai objek (kamar), bukan menilai staff lain, sehingga tetap dalam cakupan meski melibatkan histori kerja teknisi lain di kamar tsb | Dalam cakupan |
| SLA — mendekati batas waktu | `reported_date`, `resolved_date`, `priority` tersedia untuk menghitung durasi. Namun nilai ambang batas SLA per `priority` belum ditentukan di dokumen manapun (konsisten dengan area validasi Bagian 10 dokumen induk) | Data pendukung tersedia, tapi threshold-nya menunggu keputusan — bukan gap data, gap parameter |
| Part yang pernah dipakai (dirinya sendiri) | `maintenance_tickets.parts_replaced`, `assigned_staff_id` — **terverifikasi ada**, `parts_replaced` nullable teks bebas | Dalam cakupan, dengan catatan `parts_replaced` bukan kategori terstruktur |
| Perbandingan dengan teknisi lain | Data ada tapi ini benchmarking performa, levelnya Maintenance Manager | Ditolak — staff hanya lihat tiketnya sendiri |
| Total maintenance cost properti | Agregasi finansial level manager | Di luar cakupan staff |

### Kebutuhan Data (domain `facility`, own_property)

1. Daftar tiket ditugaskan (`assigned_staff_id`=dirinya), status open/in-progress, diurutkan `priority` — dari `maintenance_tickets`
2. Detail satu tiket spesifik — dari `maintenance_tickets`
3. Riwayat tiket per kamar tertentu (row-level, valid dilihat siapa pun teknisi) — dari `maintenance_tickets.room_id`
4. Riwayat tiket & `parts_replaced` yang pernah ditangani dirinya sendiri — filter `assigned_staff_id`
5. Jumlah tiket diselesaikan dirinya dalam periode tertentu

**Menunggu keputusan lanjutan (gap parameter, bukan gap data)**: threshold SLA per `priority`

**Di luar cakupan (ditolak RBAC)**: perbandingan/jumlah tiket teknisi lain, total maintenance cost properti

---

## 5. Spa & Event Staff

**RBAC**: `spa_event` (own_property) + `guests_pii` (own_property) — direvisi dari rancangan awal

### Role-Play

Menangani booking spa & event, chatbot dipakai untuk cek jadwal & ketersediaan venue.

**Pertanyaan yang mungkin diajukan**:
- Jadwal booking spa hari ini
- Ketersediaan venue untuk tanggal tertentu
- Kapasitas maksimal venue
- Layanan terlaris minggu ini
- Detail booking event tertentu
- Siapa terapis yang menangani booking tertentu
- Kontak/status tamu yang booking

### Audit & Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Jadwal booking spa | `spa_bookings.booking_date`, `service_date`, `service_name` — **terverifikasi ada** | Dalam cakupan |
| Ketersediaan venue & kapasitas | `venues.max_capacity`, `event_bookings.capacity_booked` — **terverifikasi ada** | Dalam cakupan |
| Layanan terlaris jangka pendek | `spa_bookings.service_name` — **terverifikasi ada**, agregasi ringan mingguan | Dalam cakupan |
| Detail booking event | `event_bookings.client_name`, `event_type`, `event_date`, `venue_name` — **terverifikasi ada** | Dalam cakupan |
| Terapis yang menangani booking | **Terverifikasi tidak ada** — `spa_bookings` tidak punya kolom staff/terapis yang menangani | Gap data sumber — bukan cuma di luar akses, datanya memang tidak dicatat |
| Kontak/identitas tamu yang booking | `guests.full_name`, `email`, `phone` via `spa_bookings.guest_id` (nullable untuk walk-in) — **terverifikasi ada**, dan dalam cakupan RBAC setelah revisi (`guests_pii`) | Dalam cakupan |
| Revenue/tren bulanan spa & event | Data ada tapi analisis level manager | Di luar cakupan staff |

### Kebutuhan Data (domain `spa_event`+`guests_pii`, own_property)

1. Jadwal booking spa hari ini/mendatang — dari `spa_bookings`
2. Jadwal & lokasi event hari ini/mendatang — dari `event_bookings`
3. Ketersediaan venue untuk tanggal/jam tertentu, termasuk kapasitas — dari `venues`, `event_bookings`
4. Layanan terlaris jangka pendek (mingguan) — dari `spa_bookings.service_name`
5. Detail satu booking event spesifik — dari `event_bookings`
6. Kontak tamu untuk booking dengan `guest_id` terisi (bukan walk-in anonim) — dari `guests`

**Gap data sumber**: staff/terapis yang menangani booking spa — tidak dicatat di `spa_bookings`

**Di luar cakupan (ditolak RBAC)**: analisis revenue/tren bulanan spa & event

---

## 6. HR Staff

**RBAC**: `hr` (own_property) + `employees_directory` (own_property) — direvisi dari rancangan awal

### Role-Play

Mengurus administrasi kepegawaian propertinya — pengurus data, bukan sekadar subjek data.

**Pertanyaan yang mungkin diajukan**:
- Siapa yang belum absen/masih leave hari ini
- Resolve nama dari employee_id
- Skor performa terakhir karyawan tertentu
- Karyawan paling sering telat bulan ini
- Jumlah karyawan per departemen
- Catatan kualitatif hasil review performa

### Audit & Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Status kehadiran hari ini | `staff_shifts.status` (present/late/absent/leave), `date` — **terverifikasi ada** | Dalam cakupan |
| Resolve nama dari employee_id | `employees.full_name`, `department` — **terverifikasi ada**, dalam cakupan setelah revisi RBAC (`employees_directory`) | Dalam cakupan |
| Skor performa terakhir | `employee_performance.score`, `review_period` — **terverifikasi ada** | Dalam cakupan |
| Catatan kualitatif review | **[TEMUAN BARU]** `employee_performance.notes` — **terverifikasi ada**, sebelumnya tidak disebutkan sama sekali dalam kebutuhan HR Staff meski relevan untuk administrasi | Ditambahkan ke kebutuhan |
| Karyawan paling sering telat (administratif) | `staff_shifts.status='late'`, agregasi sederhana per `employee_id` — **terverifikasi ada** | Dalam cakupan, sebagai daftar administratif, bukan analisis prediktif |
| Jumlah karyawan per departemen | `employees.department` — **terverifikasi ada** | Dalam cakupan |
| Watchlist turnover (analisis prediktif) | Data ada, tapi ini analisis lintas periode dengan baseline individu, levelnya HR Manager | Di luar cakupan staff |
| Payroll karyawan lain | `payroll` — RBAC HR Staff hanya `own_subject` (dirinya sendiri), bukan `own_property` | Di luar cakupan — hanya payroll dirinya sendiri |

### Kebutuhan Data (domain `hr`+`employees_directory`, own_property)

1. Status kehadiran karyawan hari ini per departemen/properti — dari `staff_shifts`
2. Resolve nama & department dari `employee_id` — dari `employees`
3. Skor performa & catatan kualitatif terakhir karyawan tertentu — dari `employee_performance` (`score`, `notes`)
4. Daftar sederhana keterlambatan bulan berjalan (administratif) — dari `staff_shifts`
5. Jumlah karyawan per departemen — dari `employees`

**Di luar cakupan (ditolak RBAC)**: watchlist/analisis prediktif turnover (levelnya HR Manager), payroll karyawan lain (hanya payroll dirinya sendiri)

---

## 7. Finance Staff

**RBAC**: `financial` (own_property) + `employees_directory` (own_property) — direvisi dari rancangan awal

### Role-Play

Mengurus pembukuan keuangan propertinya, chatbot dipakai untuk rekonsiliasi & cek angka cepat.

**Pertanyaan yang mungkin diajukan**:
- Revenue/expense departemen bulan ini
- GOP margin bulan lalu
- Undistributed expense bulan ini
- Resolve nama dari employee_id (rekonsiliasi payroll)
- Departemen dengan expense tertinggi

### Audit & Verifikasi

| Temuan | Verifikasi terhadap skema | Keputusan |
|---|---|---|
| Revenue/expense/profit departemen | `financial_summary.departmental_revenue`, `departmental_expense`, `departmental_profit`, `department` — **terverifikasi ada** | Dalam cakupan |
| GOP & margin | `financial_summary.gop` — **terverifikasi ada** | Dalam cakupan |
| Undistributed expense | `financial_summary.undistributed_expense` — **terverifikasi ada**, hanya terisi baris `department='Overall'` | Dalam cakupan, dengan catatan wajib filter baris `Overall` |
| Resolve nama dari employee_id | `employees.full_name` — dalam cakupan setelah revisi RBAC | Dalam cakupan |
| Payroll individual karyawan lain (row-level, untuk rekonsiliasi) | `payroll` — RBAC Finance Staff hanya `own_subject` (dirinya sendiri). `financial_summary.departmental_expense` sudah mencakup agregat payroll (disebutkan eksplisit: "payroll + COGS + alokasi service charge"), sehingga rekonsiliasi tingkat departemen tidak memerlukan row-level payroll individu | Cukup dari angka agregat `financial_summary`, tidak perlu payroll row-level orang lain — bukan gap, tapi memang tidak diperlukan pada level ini |
| Penyusunan laporan USALI formal | Data ada, tapi kepemilikan laporan levelnya Finance Manager/Corporate Financial Analyst | Finance Staff membantu ambil angka, bukan pemilik laporan |

### Kebutuhan Data (domain `financial`+`employees_directory`, own_property)

1. Departmental revenue/expense/profit bulan berjalan & bulan lalu, per departemen — dari `financial_summary`
2. GOP bulan berjalan/bulan lalu — dari `financial_summary.gop`, filter baris `Overall`
3. Undistributed expense breakdown bulan berjalan — dari `financial_summary`, filter baris `Overall`
4. Resolve nama & department dari `employee_id` — dari `employees`
5. Departemen dengan `departmental_expense` tertinggi bulan berjalan

**Di luar cakupan (ditolak RBAC/tidak diperlukan)**: payroll individual karyawan lain (cukup agregat `financial_summary`), kepemilikan penyusunan laporan USALI formal

---

## Ringkasan Perubahan dari Audit Ulang

| Posisi | Perubahan setelah verifikasi ulang |
|---|---|
| F&B Staff | Koreksi kekeliruan: harga jual menu ternyata tidak tersedia sebagai data resmi (bukan di `recipe_bom`) — diturunkan jadi gap data sumber |
| Housekeeping Staff | Tidak ada perubahan, klaim "tidak ada kolom notes" terkonfirmasi benar |
| Maintenance Staff | Tidak ada perubahan signifikan, seluruh klaim terkonfirmasi |
| Spa & Event Staff | Tidak ada perubahan signifikan; kolom terapis terkonfirmasi tidak ada |
| HR Staff | Temuan baru: `employee_performance.notes` ternyata ada dan relevan, ditambahkan ke kebutuhan |
| Finance Staff | Diperjelas: rekonsiliasi payroll cukup pakai `financial_summary` agregat, tidak perlu payroll row-level karyawan lain |

---

*Dokumen ini merupakan hasil pemetaan kebutuhan AI Chatbot untuk layer Staff, dengan setiap klaim data terverifikasi terhadap `DataSchema.md`. Layer Manager dan Korporat menyusul dengan metodologi dan standar verifikasi yang sama.*
