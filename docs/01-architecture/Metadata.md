# Metadata & Data Dictionary
## Nirwana Hospitality Group — AI Agent Data Analysis Portfolio
 
> **Tujuan dokumen ini**: menjadi sumber kebenaran tunggal tentang arti setiap database, tabel, kolom, dan nilai. Ini bukan sekadar dokumentasi — ini **fondasi teknis AI Agent**: LLM perlu tahu arti tiap kolom untuk menerjemahkan pertanyaan user ("outlet mana yang paling rugi?") menjadi query yang benar. Tanpa metadata yang presisi, AI Agent akan menebak-nebak dan menghasilkan jawaban salah.
>
> Dokumen pendamping: `01-skema-database-hospitality-group.md` (struktur & keputusan desain), `02-use-case-statistik-ml.md` (cakupan analisis).
 
---
 
## Konteks Bisnis
 
**Nirwana Hospitality Group** adalah grup perhotelan fiktif yang mengelola 5 properti hotel/resort di Indonesia plus 1 kantor pusat. Setiap properti punya empat lini bisnis: Kamar (Room), F&B, Spa & Wellness, dan Event/MICE.
 
| Parameter | Nilai |
|---|---|
| Rentang data | 1 Juli 2023 – 30 Juni 2026 (36 bulan) |
| Mata uang | Rupiah (IDR), semua nilai moneter |
| Zona waktu | Waktu lokal properti (tidak ada konversi timezone) |
| Random seed | 42 (data reproducible) |
| Total volume | ~2,53 juta baris di 23 tabel |
 
### Peta 6 Database
 
| # | Database | Domain RBAC | Pemilik Data Utama | Isi |
|---|---|---|---|---|
| 1 | `corporate_master` | `corporate_master` | Corporate/CEO | Master data: properti, karyawan, pelanggan, izin akses |
| 2 | `reservation_revenue` | `reservation` | Revenue Manager | Reservasi kamar, okupansi, riwayat harga |
| 3 | `fnb_operations` | `fnb` | F&B Manager | Transaksi outlet, resep, harga bahan, stok, waste |
| 4 | `facility_maintenance` | `facility` | Housekeeping/Maintenance Manager | Kamar, log pembersihan, tiket perbaikan |
| 5 | `spa_event` | `spa_event` | Spa & Event Manager | Venue, booking spa, event MICE |
| 6 | `hr_finance` | `hr` / `financial` | HR Manager / Corporate Finance | Shift, performance, payroll, laporan keuangan |
 
> **Catatan RBAC**: kolom `data_domain` di tabel `role_permissions_chatbot_v2` memakai nama domain di atas, bukan nama database. `hr_finance` sengaja dipecah jadi dua domain (`hr` dan `financial`) karena sensitivitasnya berbeda — HR Manager boleh lihat data karyawan tapi tidak laporan keuangan grup.
 
### Relasi Antar Database
 
```
corporate_master (master data)
    ├── properties ──────┬──> reservation_revenue.bookings
    │                    ├──> fnb_operations.fnb_outlets
    │                    ├──> facility_maintenance.rooms
    │                    ├──> spa_event.venues
    │                    └──> hr_finance.financial_summary
    │
    ├── guests ──────────┬──> reservation_revenue.bookings
    │                    ├──> fnb_operations.fnb_transactions  (nullable)
    │                    └──> spa_event.spa_bookings           (nullable)
    │
    └── employees ───────┬──> facility_maintenance.housekeeping_log (staff_id)
                         ├──> facility_maintenance.maintenance_tickets (assigned_staff_id)
                         ├──> hr_finance.staff_shifts
                         ├──> hr_finance.employee_performance
                         └──> hr_finance.payroll
```
 
---
 
# ⚠️ Peringatan Penting untuk Konsumen Data
 
Tiga hal yang **wajib** diketahui sebelum menganalisis data ini:
 
### 1. Ada "data kotor" yang disengaja
 
Sebagian kolom sengaja dikotori untuk mensimulasikan kondisi nyata (portofolio ini ingin menunjukkan tahap *data cleaning*). **Jangan asumsikan data sudah bersih.** Detail per kolom ditandai dengan 🧹 di bawah.
 
Contoh paling berdampak: kolom `employees.department` punya **19 variasi penulisan** untuk 8 departemen sebenarnya (`Housekeeping`, `HOUSEKEEPING`, `housekeeping`, `Housekeeping ` dengan trailing space). **Selalu normalisasi** (`.str.strip().str.lower()`) sebelum `GROUP BY`.
 
### 2. `guests` adalah master PELANGGAN, bukan master TAMU MENGINAP
 
Tabel ini berisi dua populasi berbeda:
 
| Populasi | Rentang guest_id | Jumlah | Pernah menginap? |
|---|---|---|---|
| Tamu menginap | G00001–G18000 | 18.000 | Ya |
| Pelanggan lokal (F&B/spa saja) | G18001–G24500 | 6.500 | **Tidak pernah** |
| Duplikat (data kotor) | G24501+ | 367 | — |
 
Riset industri: outlet F&B & spa hotel urban sangat bergantung pelanggan lokal (59% revenue spa hotel urban dari warga lokal). Jadi query seperti *"berapa total tamu kita?"* harus jelas: tamu menginap saja, atau semua pelanggan?
 
### 3. Nilai moneter adalah Rupiah tanpa desimal
 
Semua kolom harga/biaya bertipe integer dalam Rupiah penuh (bukan ribuan/juta). `room_rate = 1450000` berarti Rp 1.450.000.
 
---
 
# 1. Database: `corporate_master`
 
**Deskripsi**: Master data seluruh grup — entitas properti, karyawan, pelanggan, dan matriks izin akses. Semua database lain mereferensikan tabel di sini. Ini database yang paling jarang berubah (slowly changing dimension).
 
**Domain RBAC**: `corporate_master`
 
---
 
## Tabel: `properties`
 
**Deskripsi**: Master 6 entitas — 5 hotel/resort yang menerima tamu, plus 1 kantor pusat. Kantor pusat (P06) sengaja dimasukkan di tabel yang sama agar karyawan corporate punya `property_id` yang valid.
 
**Granularitas**: 1 baris = 1 properti | **6 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `property_id` | string (PK) | Kode properti. Format `P01`–`P06`. |
| `property_name` | string | Nama lengkap properti. |
| `city` | string | Kota/kabupaten lokasi. |
| `region` | string | Wilayah geografis: `Bali`, `Jawa`, `Nusa Tenggara`. |
| `total_rooms` | integer | Jumlah kamar. **Bernilai 0 untuk P06** (kantor pusat, tidak punya kamar). |
| `star_rating` | integer | Klasifikasi bintang (4 atau 5). **Kosong untuk P06.** |
| `opening_date` | date | Tanggal pembukaan properti. Dipakai menghitung usia gedung → memengaruhi frekuensi kerusakan (lihat `maintenance_tickets`). |
 
**Isi lengkap** (data ini tetap, bukan acak):
 
| property_id | property_name | city | region | total_rooms | star_rating | opening_date | Karakter |
|---|---|---|---|---|---|---|---|
| P01 | Nirwana Beach Resort Bali | Badung | Bali | 120 | 5 | 2015-03-01 | Resort leisure |
| P02 | Nirwana Grand Jakarta | Jakarta | Jawa | 200 | 5 | 2012-06-15 | City hotel bisnis (tertua) |
| P03 | Nirwana Heritage Yogyakarta | Yogyakarta | Jawa | 90 | 4 | 2017-01-10 | Urban-heritage |
| P04 | Nirwana Hills Bandung | Bandung | Jawa | 80 | 4 | 2019-08-20 | Urban-resort |
| P05 | Nirwana Lombok Escape | Lombok | Nusa Tenggara | 60 | 5 | 2020-11-05 | Resort remote (terbaru) |
| P06 | Nirwana Corporate Office | Jakarta | Jawa | 0 | — | 2010-01-01 | Kantor pusat |
 
> **Penting**: perbedaan usia gedung (Jakarta 2012 → Lombok 2020) bukan kebetulan — sengaja dirancang agar analisis benchmarking maintenance punya sinyal nyata (gedung tua lebih sering rusak).
 
---
 
## Tabel: `employees`
 
**Deskripsi**: Master karyawan seluruh grup, termasuk yang sudah keluar. Menjadi acuan untuk RBAC (lewat `role_title` + `access_level` + `property_id`).
 
**Granularitas**: 1 baris = 1 karyawan | **755 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `employee_id` | string (PK) | Format `E0001`–`E0755`. |
| `property_id` | string (FK) | Properti tempat bertugas. `P06` = karyawan kantor pusat. |
| `full_name` | string | 🧹 Nama karyawan. ~2% punya spasi berlebih di awal/akhir/tengah. |
| `role_title` | string | 🧹 Jabatan. **Ini kunci join ke `role_permissions_chatbot_v2`.** ~2% kosong (belum diisi HR admin). |
| `department` | string | 🧹 **PALING KOTOR** — 19 variasi penulisan untuk 8 departemen. Wajib dinormalisasi. |
| `access_level` | enum | Jenjang wewenang: `staff`, `manager`, `corporate`. |
| `hire_date` | date | 🧹 Tanggal masuk kerja. ~2% berformat `DD/MM/YYYY` (bukan ISO `YYYY-MM-DD`). |
| `status` | enum | `active` (655), `resigned` (73), `terminated` (27). |
 
**Makna `department`** (8 nilai sebenarnya, setelah normalisasi):
 
| Nilai | Arti | Shift |
|---|---|---|
| `Housekeeping` | Pembersihan kamar & area publik | 3 shift |
| `F&B` | Food & Beverage (restoran, bar, room service) | 3 shift |
| `Revenue` | Front office, reservasi, revenue management | 3 shift |
| `Spa&Event` | Spa, wellness, MICE | 3 shift |
| `Facility` | Maintenance/engineering | 3 shift |
| `HR` | Sumber daya manusia | Morning saja |
| `Finance` | Keuangan properti | Morning saja |
| `Corporate` | GM properti & jajaran direksi pusat | Morning saja |
 
**Makna `access_level`**:
 
| Nilai | Arti | Cakupan akses | Dapat service charge? |
|---|---|---|---|
| `staff` | Pelaksana operasional | Data domainnya sendiri, properti sendiri | Ya (bobot 1.0) |
| `manager` | Kepala departemen / GM | Data domainnya, properti sendiri | Ya (bobot 2.2) |
| `corporate` | CEO & Direktur pusat | Lintas properti | Tidak (bukan staf properti) |
 
**Makna `status`**:
 
| Nilai | Arti |
|---|---|
| `active` | Masih bekerja per akhir periode data |
| `resigned` | Mengundurkan diri atas kemauan sendiri |
| `terminated` | Diberhentikan perusahaan |
 
> **Untuk ML M4 (Turnover Prediction)**: target variable = `status != 'active'`. Tanggal resign **tidak ada di tabel ini** — tersimpan di file bantu `_pattern_seeds/resign_candidates.json` (bukan bagian data resmi). Ini disengaja: di dunia nyata, data tanggal keluar biasanya di sistem HR terpisah.
 
**20 nilai `role_title`**: `CEO`, `Corporate Finance Director`, `Corporate HR Director`, `Corporate Operations Director`, `Corporate Revenue Director`, `F&B Manager`, `F&B Staff`, `Finance Manager`, `Finance Staff`, `Front Office Staff`, `General Manager`, `HR Manager`, `HR Staff`, `Housekeeping Manager`, `Housekeeping Staff`, `Maintenance Manager`, `Maintenance Staff`, `Revenue Manager`, `Spa & Event Manager`, `Spa & Event Staff`
 
---
 
## Tabel: `guests`
 
**Deskripsi**: **Master pelanggan** — bukan hanya tamu yang menginap. Lihat peringatan di atas: berisi 18.000 tamu menginap + 6.500 pelanggan lokal (F&B/spa) + 367 duplikat.
 
**Granularitas**: 1 baris = 1 pelanggan | **24.867 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `guest_id` | string (PK) | Format `G00001`–`G24867`. **Rentang menentukan populasi** (lihat peringatan #2). |
| `full_name` | string | 🧹 Nama. ~2% mengandung typo (huruf tertukar/hilang) — simulasi human input error. |
| `email` | string | 🧹 ~4% kosong (guest walk-in tidak isi form lengkap). |
| `phone` | string | 🧹 **Format sangat tidak konsisten** — nomor domestik punya 4 variasi (`+62 812-xxxx-xxxx`, `0812xxxxxxxx`, `62812xxxxxxxx`, `0812-xxxx-xxxx`). ~3% kosong. Nomor asing pakai format negara asal. |
| `nationality` | string | 🧹 Negara asal. ~3% kapitalisasi tidak konsisten (`indonesia`, `INDONESIA`, `Indonesia ` dengan trailing space). |
| `loyalty_tier` | enum | `none`, `Silver`, `Gold`, `Platinum` |
| `registered_date` | date | Tanggal pertama terdaftar. |
 
**Makna `loyalty_tier`**:
 
| Nilai | Jumlah | Arti |
|---|---|---|
| `none` | 13.929 | Bukan member — transaksional |
| `Silver` | 6.721 | Member dasar |
| `Gold` | 2.920 | Member menengah |
| `Platinum` | 1.297 | Member tertinggi — paling bernilai, paling mahal jika churn |
 
> **Untuk ML M5 (Guest Churn)**: kandidat churn hanya dipilih dari Gold & Platinum (paling berdampak bisnis). Daftar guest_id + tanggal mulai churn ada di `_pattern_seeds/churn_candidates.json`.
 
---
 
## Tabel: `role_permissions_chatbot_v2`
 
**Deskripsi**: **Jantung sistem RBAC untuk AI Chatbot.** Matriks izin yang menentukan role mana boleh akses domain data apa, dengan cakupan seberapa luas. AI Agent **wajib** membaca tabel ini sebelum menjalankan query apapun. Menggantikan `role_permissions` (versi asli 42 baris) — domain `corporate_master` yang tadinya satu izin gabungan untuk data properti, karyawan, dan tamu sekaligus, sekarang dipecah jadi 4 kelompok granular agar makna tiap izin presisi.
 
**Granularitas**: 1 baris = 1 kombinasi (role × domain) | **77 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `role_title` | string (FK) | Join ke `employees.role_title`. |
| `data_domain` | enum | Domain data yang diizinkan. |
| `access_scope` | enum | Cakupan: `own_property` atau `all_properties`. |
| `permission_type` | enum | Selalu `read` — AI Chatbot hanya membaca data, tidak pernah menulis. |
 
**Makna `data_domain`** (10 nilai):
 
| Nilai | Merujuk ke | Sensitivitas |
|---|---|---|
| `reservation` | DB2 (`reservation_revenue`) | Sedang |
| `fnb` | DB3 (`fnb_operations`) | Sedang |
| `facility` | DB4 (`facility_maintenance`) | Rendah |
| `spa_event` | DB5 (`spa_event`) | Sedang |
| `hr` | DB6 — shift, performance, payroll | **Tinggi** (data personal) |
| `financial` | DB6 — `financial_summary` + `payroll` | **Tinggi** (rahasia bisnis) |
| `properties_ref` | DB1 — `properties` | Rendah |
| `employees_directory` | DB1 — `employees` | Sedang–Tinggi (data pribadi karyawan) |
| `guests_pii` | DB1 — `guests`, kolom kontak (`full_name`, `email`, `phone`) | Tinggi (PII personal) |
| `guests_profile` | DB1 — `guests`, kolom atribut analitis (`loyalty_tier`, `nationality`, riwayat booking) | Sedang |
 
> **Catatan**: tabel `role_permissions_chatbot_v2` itu sendiri **tidak pernah** menjadi target akses siapa pun, termasuk CEO — tidak ada nilai `data_domain` yang merujuk padanya. Ini sengaja: sistem yang diatur oleh sebuah matriks kontrol tidak boleh bisa membaca ulang matriks itu sendiri lewat jalur yang ia atur.
 
**Makna `access_scope`**:
 
| Nilai | Arti |
|---|---|
| `own_property` | Hanya data properti tempat karyawan bertugas. Revenue Manager Bali **tidak bisa** lihat data Jakarta. |
| `all_properties` | Lintas properti. Hanya untuk level corporate dan General Manager. |
 
**Prinsip desain yang tertanam di matriks ini**:
1. **Need-to-know** — F&B Manager tidak punya baris untuk domain `hr`, jadi tidak bisa lihat data gaji.
2. **Segregation of duties** — General Manager punya akses ke *semua* domain operasional tapi tetap `read` dan `own_property`. Dia bisa memantau, tapi tidak mengubah data operasional departemen lain.
3. **Eskalasi vertikal** — Corporate Director punya `all_properties` tapi terbatas di domainnya (Corporate Finance Director tidak bisa lihat `fnb`).
4. **CEO** punya `read` + `all_properties` di semua domain — pengawasan penuh, tanpa hak ubah, kecuali `role_permissions_chatbot_v2` itu sendiri.
5. **Superset hierarkis** — karena AI Chatbot dirancang menggantikan rantai eskalasi manual (Director tidak perlu lagi bertanya ke Manager, Manager ke Staff), setiap posisi yang lebih tinggi wajib memiliki minimal seluruh akses granular yang dimiliki bawahannya pada domain yang sama, ditambah kapabilitas khas levelnya (mis. benchmarking antar properti untuk level corporate). Prinsip ini diverifikasi berlaku konsisten di seluruh 20 posisi lewat pemeriksaan menyeluruh, bukan diasumsikan otomatis benar hanya karena tingkat jabatannya lebih tinggi.
> **Cara pakai untuk AI Agent**: `employees.role_title` → lookup ke tabel ini → dapat daftar domain + scope → filter query di level SQL (bukan di level prompt LLM). Ini penting: keamanan tidak boleh bergantung pada LLM "berjanji tidak membocorkan".
 
---
 
# 2. Database: `reservation_revenue`
 
**Deskripsi**: Seluruh aktivitas reservasi kamar dan performa revenue. Sumber kebenaran untuk okupansi — database lain (F&B, spa, HR) mereferensikan okupansi dari sini untuk menghitung volume mereka.
 
**Domain RBAC**: `reservation`
 
---
 
## Tabel: `bookings`
 
**Deskripsi**: Transaksi reservasi kamar. Tabel fakta utama grup. Satu baris = satu reservasi (bisa mencakup beberapa malam).
 
**Granularitas**: 1 baris = 1 reservasi | **217.155 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `booking_id` | string (PK) | Format `BK0000001`. |
| `property_id` | string (FK) | Properti yang dipesan. |
| `guest_id` | string (FK) | Pemesan. **Selalu G00001–G18000** (pelanggan lokal tidak pernah booking kamar). |
| `room_type` | enum | `Standard`, `Deluxe`, `Suite`, `Villa` |
| `booking_channel` | enum | Kanal pemesanan (lihat tabel makna di bawah). |
| `check_in_date` | date | Tanggal masuk. |
| `check_out_date` | date | Tanggal keluar. Selalu > `check_in_date`. |
| `booking_date` | date | Kapan reservasi dibuat. **Selalu ≤ `check_in_date`.** |
| `nights` | integer | Jumlah malam = `check_out_date` − `check_in_date`. |
| `room_rate` | integer | Tarif **per malam** (Rupiah). |
| `total_amount` | integer | `room_rate × nights`. |
| `status` | enum | Status akhir reservasi. |
 
**Makna `room_type`**:
 
| Nilai | Ketersediaan | Rentang tarif (Rp/malam) |
|---|---|---|
| `Standard` | Semua properti | 550rb – 950rb |
| `Deluxe` | Semua properti | 850rb – 1,45jt |
| `Suite` | Semua properti | 1,6jt – 2,8jt |
| `Villa` | **Hanya P01, P04, P05** | 3,2jt – 5,5jt |
 
> ⚠️ **Jakarta (P02) & Yogyakarta (P03) tidak punya Villa.** Query yang mengasumsikan semua properti punya semua tipe kamar akan menghasilkan hasil menyesatkan.
 
**Makna `booking_channel`**:
 
| Nilai | Arti | Implikasi biaya |
|---|---|---|
| `Direct` | Langsung ke hotel (website/telepon) | Tanpa komisi — paling menguntungkan |
| `OTA-Booking.com` | Online Travel Agent | Kena komisi OTA |
| `OTA-Agoda` | Online Travel Agent | Kena komisi OTA |
| `Travel Agent` | Agen perjalanan konvensional | Kena komisi agen |
| `Corporate` | Kontrak korporat | Tarif khusus, volume stabil |
 
> **Tren tertanam**: porsi OTA naik ~2%/tahun sementara Direct & Travel Agent turun — mengikuti tren industri nyata. Ini bisa dianalisis sebagai use case 1.5 (benchmarking channel).
 
**Makna `status`**:
 
| Nilai | Jumlah | Arti | Hitung sebagai revenue? |
|---|---|---|---|
| `completed` | ~192rb | Tamu sudah menginap & checkout | ✅ Ya |
| `confirmed` | ~450 | Sudah dikonfirmasi, belum menginap | ✅ Ya |
| `cancelled` | ~20rb | Dibatalkan sebelum check-in | ❌ Tidak |
| `no-show` | ~4rb | Tidak datang tanpa pembatalan | ❌ Tidak |
 
> **Aturan baku**: untuk analisis revenue, **selalu filter** `status IN ('completed', 'confirmed')`. Ini konvensi yang dipakai konsisten di seluruh database (F&B, spa, financial_summary mengikuti aturan yang sama).
 
---
 
## Tabel: `daily_occupancy`
 
**Deskripsi**: Agregat okupansi harian per properti per tipe kamar. **Tabel ini hasil ETL dari `bookings`**, bukan data mentah independen — dihitung ulang dari booking sehingga dijamin konsisten 100%. Di dunia nyata, dashboard baca dari tabel agregat seperti ini, bukan query jutaan baris transaksi.
 
**Granularitas**: 1 baris = (properti × tipe kamar × tanggal) | **19.728 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `property_id` | string (FK) | |
| `room_type` | enum | |
| `date` | date | Tanggal okupansi (malam yang ditempati). |
| `rooms_sold` | integer | Jumlah kamar terjual malam itu. |
| `adr` | float | **Average Daily Rate** — rata-rata tarif kamar terjual. Metrik industri standar. |
| `total_rooms_available` | integer | Jumlah kamar tersedia untuk tipe ini. |
| `occupancy_rate` | float | `rooms_sold ÷ total_rooms_available`. Rentang 0–1. |
| `revpar` | float | **Revenue Per Available Room** = `adr × occupancy_rate`. Metrik profitabilitas utama industri hotel. |
 
**Metrik industri yang perlu dipahami**:
 
| Metrik | Rumus | Kenapa penting |
|---|---|---|
| **ADR** | Total room revenue ÷ rooms sold | Mengukur *harga* — tapi mengabaikan kamar kosong |
| **Occupancy** | Rooms sold ÷ rooms available | Mengukur *volume* — tapi mengabaikan harga |
| **RevPAR** | ADR × Occupancy | **Menggabungkan keduanya** — metrik paling representatif. Hotel dengan ADR tinggi tapi okupansi rendah bisa kalah dari hotel ADR sedang tapi okupansi tinggi. |
 
**Pola musiman yang tertanam** (penting untuk ML M1 - Demand Forecasting):
 
| Periode | Okupansi rata-rata | Penyebab |
|---|---|---|
| Desember | 82.7% | Puncak liburan akhir tahun |
| Juli | 80.4% | Puncak liburan sekolah |
| Januari | 79.8% | Sisa liburan tahun baru |
| Juni | 77.0% | Awal liburan sekolah |
| September | 58.3% | Low season |
| Februari | 59.1% | Low season |
 
Plus: tren pertumbuhan +4%/tahun, dan weekend effect (Jumat-Sabtu lebih tinggi, terutama di leisure destination seperti Bali +18%).
 
---
 
## Tabel: `pricing_history`
 
**Deskripsi**: Riwayat harga kamar harian — tarif dasar vs tarif yang benar-benar diterapkan. Memungkinkan analisis strategi pricing dan mendeteksi anomali harga.
 
**Granularitas**: 1 baris = (properti × tipe kamar × tanggal) | **19.728 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `property_id` | string (FK) | |
| `room_type` | enum | |
| `date` | date | |
| `base_rate` | integer | Tarif dasar (rack rate) — harga referensi tetap. |
| `applied_rate` | integer | Tarif yang benar-benar diterapkan hari itu. |
| `reason` | enum | Alasan `applied_rate` berbeda dari `base_rate`. |
 
**Makna `reason`**:
 
| Nilai | Jumlah | Arti |
|---|---|---|
| `manual` | 13.190 | Penyesuaian manual revenue manager (high season / normal) |
| `promo` | 6.456 | Diskon terencana saat low season untuk dorong demand |
| `dynamic-pricing-AI` | 82 | Penyesuaian oleh sistem dynamic pricing otomatis |
 
> **Konteks cerita**: `dynamic-pricing-AI` hanya 82 baris karena sistem AI pricing baru dipakai di periode tertentu (window anomali). Ini bagian dari narasi: perusahaan baru mulai mengadopsi AI, dan portofolio ini adalah lanjutannya.
 
---
 
# 3. Database: `fnb_operations`
 
**Deskripsi**: Operasional Food & Beverage lengkap — dari transaksi pelanggan, resep, harga bahan baku, sampai waste. Database dengan **rantai sebab-akibat paling dalam**: harga cabai naik → food cost menu bercabai naik → margin F&B turun.
 
**Domain RBAC**: `fnb`
 
---
 
## Tabel: `fnb_outlets`
 
**Deskripsi**: Master outlet F&B. Setiap properti punya 3–4 outlet.
 
**Granularitas**: 1 baris = 1 outlet | **17 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `outlet_id` | string (PK) | Format `OUT001`–`OUT017`. |
| `property_id` | string (FK) | |
| `outlet_name` | string | Nama outlet. |
| `outlet_type` | enum | `Restaurant`, `Bar`, `Room Service` |
 
**Makna `outlet_type`**:
 
| Nilai | Jumlah | Jam operasi | Terima walk-in? |
|---|---|---|---|
| `Restaurant` | 5 | Sarapan 06-10, lunch 11-14, dinner 18-22 | ✅ Ya |
| `Bar` | 7 | Siang 11-15, sunset 16-19, malam 19-24 | ✅ Ya |
| `Room Service` | 5 | 06-10, 11-14, 18-22, late night 22-24 | ❌ **Tidak** — mustahil pesan room service tanpa kamar |
 
**Daftar lengkap outlet**:
 
| Properti | Outlet |
|---|---|
| P01 Bali | Sunset Restaurant, Beach Bar, Pool Bar, In-Room Dining Bali |
| P02 Jakarta | Nusantara All-Day Dining, Lobby Lounge, Skyline Rooftop Bar, In-Room Dining Jakarta |
| P03 Yogyakarta | Joglo Restaurant, Heritage Lobby Cafe, In-Room Dining Yogyakarta |
| P04 Bandung | Pinus Restaurant, Garden Cafe, In-Room Dining Bandung |
| P05 Lombok | Ombak Restaurant, Sunset Beach Bar, In-Room Dining Lombok |
 
> **Dua outlet sengaja dibuat underperform** untuk use case benchmarking (2.5): *Heritage Lobby Cafe* (Yogyakarta, 55% dari normal) dan *Sunset Beach Bar* (Lombok, 62%).
 
---
 
## Tabel: `fnb_transactions`
 
**Deskripsi**: Transaksi F&B **granular per struk × item**. Tabel terbesar di seluruh database. Beberapa baris berbagi `transaction_id` yang sama = satu struk berisi beberapa item.
 
**Granularitas**: 1 baris = 1 item dalam 1 struk | **901.360 baris** (387.581 struk unik)
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `transaction_id` | string | **ID struk, BUKAN primary key baris.** Berulang untuk item dalam struk yang sama. Format `TX00000001`. |
| `outlet_id` | string (FK) | |
| `guest_id` | string (FK, **nullable**) | **Kosong untuk walk-in anonim** (~31% baris). Lihat penjelasan di bawah. |
| `customer_type` | enum | `inhouse` atau `walk-in` |
| `transaction_datetime` | datetime | Tanggal **+ jam** transaksi. Memungkinkan analisis pola intraday. |
| `item_name` | string | Nama menu. Join ke `recipe_bom` untuk hitung food cost. |
| `category` | enum | `Food`, `Beverage`, `Dessert` |
| `quantity` | integer | Jumlah porsi item ini dalam struk. |
| `unit_price` | integer | Harga satuan saat itu (sudah termasuk penyesuaian musiman). |
| `total_price` | integer | `unit_price × quantity` |
 
**Makna `customer_type`** — konsep paling penting di tabel ini:
 
| Nilai | Arti | guest_id |
|---|---|---|
| `inhouse` | Tamu yang **sedang menginap** di properti itu pada tanggal itu | Selalu terisi (terverifikasi 100% cocok dengan `bookings`) |
| `walk-in` | Pelanggan dari **luar** — warga lokal, ekspat, tamu hotel lain | 30% terisi (member/repeat), **70% kosong** (bayar tanpa memberi identitas) |
 
> **Kenapa `guest_id` boleh kosong?** Ini **bukan data kotor** — ini *missing value yang bermakna*. Di restoran hotel, mayoritas walk-in bayar tunai/kartu tanpa memberi identitas. Insight bisnisnya justru: *"kita tidak kenal 31% pelanggan kita."*
 
**Proporsi walk-in per properti** (berbasis riset industri):
 
| Properti | Walk-in | Alasan |
|---|---|---|
| P02 Jakarta | 63% | Urban — rooftop bar populer untuk publik |
| P04 Bandung | 53% | Dekat Jakarta, garden cafe favorit warga lokal |
| P03 Yogyakarta | 47% | Urban-heritage |
| P01 Bali | 25% | Resort destinasi |
| P05 Lombok | 17% | Resort remote — bisnis lokal minimal |
 
**Analisis yang mungkin berkat granularitas ini** (mustahil dengan data agregat):
- Pola intraday: sarapan/lunch/dinner/late-night
- Average check per struk: Rp 253.502 (median Rp 210.000)
- Item per struk: rata-rata 2,33
- Basket analysis: item apa yang sering dibeli bersamaan
- Perbandingan perilaku walk-in vs inhouse
---
 
## Tabel: `recipe_bom`
 
**Deskripsi**: **Bill of Material** — komposisi bahan baku per porsi menu. Tabel kecil tapi krusial: ini yang membuat food cost punya sebab-akibat nyata, bukan angka tempelan.
 
**Granularitas**: 1 baris = (menu × bahan) | **120 baris** (30 menu × rata-rata 4 bahan)
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `item_name` | string (FK) | Join ke `fnb_transactions.item_name`. |
| `ingredient_id` | string (FK) | Join ke `ingredient_price_history.ingredient_id`. |
| `qty_per_portion` | float | Takaran bahan per satu porsi (dalam satuan bahan: kg/liter/pcs). |
 
**Cara menghitung food cost** (rumus deterministik):
 
```sql
food_cost_per_portion = SUM(recipe_bom.qty_per_portion × ingredient_price_history.unit_cost)
                        WHERE ingredient_price_history.date = tanggal_transaksi
```
 
**Contoh rantai sebab-akibat nyata**:
- Januari 2024: harga cabai melonjak dari Rp 46rb → Rp 122rb/kg (panen gagal)
- Resep Rendang Daging mengandung cabai
- → Food cost Rendang otomatis naik Rp 59.984 → Rp 68.252
- → Margin F&B tertekan
**Target food cost ratio** (dikalibrasi ke standar industri, dengan variasi natural per menu):
 
| Kategori | Target | Realisasi rata-rata | Rentang |
|---|---|---|---|
| Food | 34% | 33.4% | 27.3% – 42.0% |
| Beverage | 24% | 24.1% | 19.3% – 28.6% |
| Dessert | 28% | 28.1% | 22.5% – 32.4% |
 
> Variasi antar menu disengaja — di dunia nyata tidak ada restoran yang food cost tiap menunya persis sama.
 
---
 
## Tabel: `ingredient_price_history`
 
**Deskripsi**: Riwayat harga bahan baku harian. Sumber fitur "tren harga bahan baku" untuk ML M2 (Food Cost Forecasting).
 
**Granularitas**: 1 baris = (bahan × tanggal) | **32.880 baris** (30 bahan × 1.096 hari)
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `ingredient_id` | string (FK) | Format `ING001`–`ING030`. |
| `date` | date | |
| `unit_cost` | float | Harga per satuan bahan (Rp/kg, Rp/liter, atau Rp/pcs) pada tanggal itu. |
 
**Karakter harga**: setiap bahan punya volatilitas berbeda. Bahan segar (cabai 35%, tomat 32%, sayuran 30%) jauh lebih fluktuatif dari bahan kering (beras 5%, soda water 4%). Semua bahan juga mengalami inflasi ~4%/tahun.
 
**Shock harga yang tertanam** (untuk anomali food cost):
 
| Bahan | Periode | Puncak | Cerita |
|---|---|---|---|
| Cabai Merah | Jan–Feb 2024 | 2.8x | Panen gagal |
| Bawang Merah | Jan–Feb 2024 | 2.1x | Ikut terdampak |
| Minyak Goreng | Sep–Nov 2023 | 1.75x | Krisis minyak goreng |
| Daging Sapi | Mar–Apr 2025 | 1.55x | Jelang Lebaran |
| Cabai Merah | Nov–Des 2025 | 2.3x | Musim hujan |
 
> Shock memakai kurva sinus (naik bertahap → puncak → turun bertahap), bukan lompatan datar — lebih realistis dan lebih menantang untuk model forecasting.
 
---
 
## Tabel: `fnb_inventory`
 
**Deskripsi**: **Snapshot** stok bahan per outlet pada tanggal terakhir data (30 Juni 2026). Bukan time-series — ini kondisi "saat ini".
 
**Granularitas**: 1 baris = (outlet × bahan) | **457 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `ingredient_id` | string (FK) | |
| `outlet_id` | string (FK) | |
| `ingredient_name` | string | Nama bahan (denormalisasi untuk kemudahan). |
| `unit` | enum | `kg`, `liter`, `pcs` |
| `stock_current` | float | Stok tersedia saat ini. |
| `stock_min_threshold` | float | Batas minimum (safety stock) = kebutuhan 3 hari berdasarkan rata-rata pemakaian historis. |
| `unit_cost` | float | Harga terkini — **diambil dari baris terakhir `ingredient_price_history`** agar tidak ada dua sumber kebenaran. |
 
> **Untuk use case 2.4 (Stok Kritis)**: `stock_current < stock_min_threshold` → 54 dari 457 baris (11.8%) dalam kondisi kritis.
 
---
 
## Tabel: `fnb_waste_log`
 
**Deskripsi**: Log pembuangan bahan baku. Waste dihitung sebagai persentase dari pemakaian aktual (yang dihitung dari penjualan × BOM).
 
**Granularitas**: 1 baris = (outlet × tanggal × bahan) yang tercatat waste | **108.630 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `waste_id` | string (PK) | Format `WS0000001`. |
| `outlet_id` | string (FK) | |
| `date` | date | |
| `ingredient_id` | string (FK) | |
| `quantity_wasted` | float | Jumlah terbuang (satuan bahan). |
| `reason` | enum | Penyebab pembuangan. |
 
**Makna `reason`**:
 
| Nilai | Proporsi | Arti | Bisa dicegah? |
|---|---|---|---|
| `overproduction` | 50% | Masak berlebihan dari kebutuhan | ✅ Ya — perbaiki forecasting |
| `expired` | 30% | Kadaluarsa sebelum terpakai | ✅ Ya — perbaiki rotasi stok (FIFO) |
| `spillage` | 20% | Tumpah/rusak saat penanganan | ⚠️ Sebagian — pelatihan staf |
 
> **Baseline waste ratio**: 3.5% dari pemakaian. Tidak semua kombinasi outlet×hari×bahan tercatat (hanya ~25% sampel) — realistis, karena di dunia nyata pencatatan waste tidak selalu lengkap.
 
---
 
# 4. Database: `facility_maintenance`
 
**Deskripsi**: Operasional fisik properti — inventaris kamar, log pembersihan, dan tiket perbaikan lengkap dengan rincian biaya.
 
**Domain RBAC**: `facility`
 
---
 
## Tabel: `rooms`
 
**Deskripsi**: Master kamar fisik. Distribusi tipe kamar **konsisten 100% dengan DB2** — tidak akan ada Villa di Jakarta.
 
**Granularitas**: 1 baris = 1 kamar | **549 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `room_id` | string (PK) | Format `RM0001`–`RM0549`. |
| `property_id` | string (FK) | |
| `room_number` | string | Nomor kamar. Kamar reguler: `{lantai}{urutan}` (mis. `201` = lantai 2 kamar 1). Villa: `V01`, `V02`. |
| `room_type` | enum | `Standard`, `Deluxe`, `Suite`, `Villa` |
| `floor` | integer | Lantai. Villa selalu 1 (standalone). |
| `status` | enum | Kondisi kamar **saat ini** (snapshot akhir periode). |
 
**Makna `status`**:
 
| Nilai | Proporsi | Arti | Bisa dijual? |
|---|---|---|---|
| `occupied` | ~55% | Sedang ditempati tamu | — |
| `available` | ~28% | Siap dijual | ✅ |
| `cleaning` | ~9% | Sedang dibersihkan | ⏳ Sementara |
| `maintenance` | ~6% | Sedang diperbaiki | ❌ |
| `out-of-order` | ~2% | Rusak berat, tidak bisa dipakai | ❌ |
 
> **Penomoran kamar**: Suite ditempatkan di lantai atas, Standard di lantai bawah — mengikuti praktik hotel nyata.
 
---
 
## Tabel: `housekeeping_log`
 
**Deskripsi**: Log pembersihan kamar. Mencakup kamar terjual + sebagian kamar kosong (deep cleaning berkala 12%).
 
**Granularitas**: 1 baris = 1 sesi pembersihan | **424.719 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `log_id` | string (PK) | Format `HK0000001`. |
| `room_id` | string (FK) | |
| `date` | date | |
| `cleaning_start_time` | datetime | Mulai membersihkan. Shift housekeeping 08:00–15:00. |
| `cleaning_end_time` | datetime | Selesai. Selalu > start. |
| `staff_id` | string (FK) | Join ke `employees.employee_id`. Hanya staf departemen Housekeeping. |
| `status` | enum | `completed` atau `delayed` |
 
**Durasi pembersihan** (dihitung dari `cleaning_end_time − cleaning_start_time`):
 
| Tipe kamar | Rata-rata | Alasan |
|---|---|---|
| Villa | 81.6 menit | Paling luas, fasilitas terbanyak |
| Suite | 54.8 menit | |
| Deluxe | 37.0 menit | |
| Standard | 29.5 menit | Paling cepat |
 
**Korelasi dengan okupansi** (pola penting yang tertanam):
 
| Kondisi | Durasi rata-rata | Delayed rate |
|---|---|---|
| Hari sibuk (okupansi ≥85%) | 51.7 menit | 19.1% |
| Hari normal | 39.8 menit | 5.9% |
 
> Saat hotel penuh, staf kewalahan → durasi naik 30% dan keterlambatan naik 3x. Ini pola nyata yang disebut riset industri ("absenteeism triggers a vicious domino effect").
>
> **~10% staf sengaja dibuat konsisten lebih lambat** (30% lebih lama) — untuk analisis benchmarking performa staf.
 
---
 
## Tabel: `maintenance_tickets`
 
**Deskripsi**: Tiket perbaikan fasilitas dengan **rincian biaya lengkap**. Sumber data untuk ML M3 (Maintenance Cost Forecasting).
 
**Granularitas**: 1 baris = 1 tiket | **13.503 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `ticket_id` | string (PK) | Format `MT000001`. |
| `property_id` | string (FK) | |
| `room_id` | string (FK, **nullable**) | **Kosong jika kerusakan di fasilitas umum** (pool, lobby, elevator). |
| `facility_area` | enum | Lokasi kerusakan. |
| `issue_type` | enum | Jenis kerusakan. |
| `reported_date` | datetime | Kapan dilaporkan. |
| `resolved_date` | datetime | **Kosong jika status masih open/in-progress.** |
| `status` | enum | `open`, `in-progress`, `resolved` |
| `priority` | enum | `low`, `medium`, `high`, `critical` |
| `assigned_staff_id` | string (FK) | Teknisi yang ditugaskan. Hanya staf departemen Facility. |
| `labor_hours` | float | Jam kerja teknisi. |
| `parts_replaced` | string (nullable) | Nama part yang diganti. **Kosong jika tidak ganti part** (~52%). |
| `cost` | integer | Total biaya = `(labor_hours × tarif_teknisi) + harga_part`. |
 
**Makna `facility_area`**:
 
| Nilai | Proporsi | room_id terisi? |
|---|---|---|
| `Room` | 72% | ✅ Ya |
| `Pool` | 7% | ❌ Kosong |
| `Lobby` | 6% | ❌ Kosong |
| `Elevator` | 5% | ❌ Kosong |
| `Restaurant` | 5% | ❌ Kosong |
| `Gym` | 3% | ❌ Kosong |
| `Parking` | 2% | ❌ Kosong |
 
**Makna `issue_type`**:
 
| Nilai | Proporsi | Rentang labor (jam) | Peluang ganti part |
|---|---|---|---|
| `AC` | 28% | 1.0 – 6.0 | 45% |
| `Plumbing` | 22% | 0.8 – 5.0 | 50% |
| `Electrical` | 16% | 0.5 – 8.0 | 40% |
| `Furniture` | 14% | 0.5 – 4.0 | 55% |
| `TV/Elektronik` | 8% | 0.5 – 3.0 | 60% |
| `Kunci/Lock` | 6% | 0.3 – 2.0 | 70% |
| `Lainnya` | 6% | 0.5 – 3.0 | 25% |
 
**Makna `priority` & SLA** (Service Level Agreement):
 
| Nilai | Proporsi | SLA | Realisasi pelanggaran |
|---|---|---|---|
| `critical` | 6% | 8 jam | 16.4% |
| `high` | 19% | 24 jam | 22.9% |
| `medium` | 40% | 48 jam | ~15% |
| `low` | 35% | 72 jam | ~12% |
 
> **Cara hitung SLA breach**: `(resolved_date − reported_date) > SLA_hours` untuk priority tersebut. Ini use case 3.1.
 
**Struktur biaya** (deterministik, bisa ditelusuri):
 
```
cost = (labor_hours × tarif_teknisi_saat_itu) + harga_part
tarif_teknisi = Rp 75.000/jam, naik 5%/tahun mengikuti inflasi
```
 
| Kondisi | Rata-rata biaya |
|---|---|
| Dengan ganti part | Rp 1.167.000 |
| Tanpa ganti part | Rp 263.000 |
| Priority critical | Rp 778.000 |
| Priority medium | Rp 666.000 |
| **Keseluruhan** | **Rp 695.000** |
 
**Pola yang tertanam**:
1. **Usia gedung** → frekuensi kerusakan. Jakarta (2012) 8.81 tiket/kamar/tahun vs Lombok (2020) 7.01.
2. **Okupansi** → wear & tear. Makin ramai, makin cepat rusak.
3. **18 kamar bermasalah** sengaja punya tiket berulang 4x lipat median — untuk use case 3.2.
4. **Tren jenis keluhan**: AC di Jakarta melonjak dari 25% → 48-51% (Sep-Okt 2024), lalu normal.
> **Untuk ML M3**: model memprediksi **agregat bulanan** (total cost & jumlah tiket per bulan), bukan per-tiket. Pada level bulanan, coefficient of variation = 0.132 (sinyal kuat), sedangkan per-tiket 1.46 (terlalu noisy). Tren terbaca jelas: +Rp 1,07jt cost/bulan, +1,02 tiket/bulan.
 
---
 
# 5. Database: `spa_event`
 
**Deskripsi**: Layanan spa/wellness dan bisnis MICE (Meeting, Incentive, Conference, Exhibition).
 
**Domain RBAC**: `spa_event`
 
---
 
## Tabel: `venues`
 
**Deskripsi**: Master venue untuk event. Venue punya atribut yang melekat padanya (kapasitas, tipe), sehingga dipisah sebagai master data.
 
**Granularitas**: 1 baris = 1 venue | **20 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `venue_id` | string (PK) | Format `VN001`–`VN020`. |
| `property_id` | string (FK) | |
| `venue_name` | string | Nama venue. |
| `venue_type` | enum | `Ballroom`, `Meeting Room`, `Outdoor` |
| `max_capacity` | integer | Kapasitas maksimal (orang). **Acuan untuk hitung utilisasi.** |
 
**Makna `venue_type`**:
 
| Nilai | Cocok untuk event | Rentang kapasitas |
|---|---|---|
| `Ballroom` | Wedding, Conference, Gala Dinner, Corporate Meeting, Product Launch | 250 – 800 |
| `Meeting Room` | Corporate Meeting, Training/Workshop, Product Launch | 20 – 80 |
| `Outdoor` | Wedding, Gala Dinner | 150 – 250 |
 
> Venue terbesar: Jakarta Grand Ballroom (800 orang). Terkecil: Boardroom Jakarta (20 orang).
 
---
 
## Tabel: `spa_bookings`
 
**Deskripsi**: Booking layanan spa & wellness. Sama seperti F&B, menerima tamu menginap **dan** walk-in lokal.
 
**Granularitas**: 1 baris = 1 booking treatment | **127.762 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `spa_booking_id` | string (PK) | Format `SP000001`. |
| `property_id` | string (FK) | |
| `guest_id` | string (FK, **nullable**) | Kosong untuk walk-in anonim (~21%). |
| `customer_type` | enum | `inhouse` atau `walk-in` |
| `service_name` | string | Jenis treatment. |
| `booking_date` | date | Kapan dipesan. Spa sering dadakan — lead time rata-rata 1-2 hari. |
| `service_date` | date | Kapan treatment dilakukan. |
| `duration_minutes` | integer | Durasi treatment: 45, 60, 90, atau 120 menit. |
| `price` | integer | Harga (sudah disesuaikan multiplier properti). |
| `status` | enum | `completed`, `cancelled`, `confirmed` |
 
**Makna `service_name`** (9 layanan):
 
| Layanan | Durasi | Harga dasar | Preferensi |
|---|---|---|---|
| `Couple Package` | 120 min | Rp 1.800.000 | **Inhouse** (15.0% vs 1.3%) |
| `Hot Stone Massage` | 90 min | Rp 850.000 | **Inhouse** (13.9% vs 5.1%) |
| `Aromatherapy Massage 90min` | 90 min | Rp 700.000 | Inhouse |
| `Balinese Massage 90min` | 90 min | Rp 650.000 | Inhouse |
| `Aromatherapy Massage 60min` | 60 min | Rp 500.000 | Seimbang |
| `Balinese Massage 60min` | 60 min | Rp 450.000 | Seimbang (terpopuler) |
| `Facial Treatment` | 60 min | Rp 400.000 | Walk-in |
| `Body Scrub` | 45 min | Rp 350.000 | **Walk-in** (13.8% vs 5.1%) |
| `Reflexology` | 45 min | Rp 280.000 | **Walk-in** (12.0% vs 2.6%) |
 
> **Temuan riset yang tertanam**: tamu menginap (sedang liburan) cenderung memilih paket panjang & premium; warga lokal (wellness rutin) memilih layanan pendek & terjangkau agar bisa datang lebih sering. Realisasi: revenue per kunjungan **inhouse Rp 800rb vs walk-in Rp 477rb**.
 
**Proporsi walk-in per properti** (riset: spa hotel urban 59% dari lokal):
 
| Properti | Walk-in |
|---|---|
| P02 Jakarta | 64.1% |
| P04 Bandung | 57.1% |
| P03 Yogyakarta | 50.0% |
| P01 Bali | 33.8% |
| P05 Lombok | 24.3% |
 
**Pergeseran tren layanan** (2023 → 2026): Hot Stone naik 7.8% → 13.3%, Couple Package naik 6.6% → 11.0%, sementara Reflexology turun 8.4% → 3.4% dan Body Scrub turun 10.2% → 6.8%.
 
---
 
## Tabel: `event_bookings`
 
**Deskripsi**: Booking event/MICE. Volume jauh lebih kecil dari spa, tapi nilai per transaksi sangat besar.
 
**Granularitas**: 1 baris = 1 event | **1.331 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `event_id` | string (PK) | Format `EV00001`. |
| `property_id` | string (FK) | |
| `venue_id` | string (FK) | Join ke `venues` untuk dapat `max_capacity`. |
| `client_name` | string | Nama klien. **Wedding**: nama pasangan (`Andi & Sari`). **Korporat**: nama perusahaan. |
| `event_type` | enum | Jenis acara. |
| `event_date` | date | Tanggal acara. |
| `venue_name` | string | Nama venue (denormalisasi dari `venues`). |
| `capacity_booked` | integer | Jumlah peserta. **Dijamin ≤ `venues.max_capacity`.** |
| `total_revenue` | integer | Total pendapatan event. |
| `status` | enum | `completed`, `cancelled`, `confirmed` |
 
**Makna `event_type`**:
 
| Nilai | Jumlah | Revenue/pax (dasar) | Venue cocok |
|---|---|---|---|
| `Corporate Meeting` | 432 | Rp 350.000 | Meeting Room, Ballroom |
| `Wedding` | 353 | Rp 850.000 | Ballroom, Outdoor |
| `Conference` | 260 | Rp 450.000 | Ballroom |
| `Gala Dinner` | 130 | Rp 750.000 | Ballroom, Outdoor |
| `Product Launch` | 99 | Rp 550.000 | Ballroom, Meeting Room |
| `Training/Workshop` | 67 | Rp 280.000 | Meeting Room |
 
**Utilisasi venue** (untuk use case 5.3):
 
```sql
utilization = capacity_booked ÷ venues.max_capacity
```
 
| Metrik | Nilai |
|---|---|
| Rata-rata utilisasi | 66.9% |
| Event utilisasi rendah (<45%) | 16.8% |
 
> **Constraint yang dijaga**: satu venue tidak bisa dipakai dua event di hari yang sama (0 pelanggaran), dan `capacity_booked` tidak pernah melebihi `max_capacity`.
 
---
 
# 6. Database: `hr_finance`
 
**Deskripsi**: Sumber daya manusia dan keuangan. **Database paling sensitif** — berisi data personal karyawan dan rahasia bisnis. Sengaja dipecah jadi dua domain RBAC (`hr` dan `financial`).
 
**Domain RBAC**: `hr` (shift, performance, payroll) + `financial` (financial_summary)
 
---
 
## Tabel: `staff_shifts`
 
**Deskripsi**: Log kehadiran & shift harian karyawan. Sumber fitur utama untuk ML M4 (Turnover Prediction).
 
**Granularitas**: 1 baris = (karyawan × hari kerja) | **609.364 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `shift_id` | string (PK) | Format `SH0000001`. |
| `employee_id` | string (FK) | |
| `date` | date | |
| `shift_type` | enum | `Morning`, `Afternoon`, `Night` |
| `clock_in` | datetime | **Kosong jika `absent` atau `leave`.** |
| `clock_out` | datetime | **Kosong jika `absent` atau `leave`.** |
| `status` | enum | Status kehadiran hari itu. |
 
**Makna `shift_type`**:
 
| Nilai | Jam | Siapa |
|---|---|---|
| `Morning` | 07:00–15:00 | Semua departemen |
| `Afternoon` | 15:00–23:00 | Hanya departemen operasional |
| `Night` | 23:00–07:00 | Hanya departemen operasional |
 
> Departemen office (HR, Finance, Corporate) **hanya punya shift Morning** — mereka bukan operasional 24 jam.
 
**Makna `status`**:
 
| Nilai | Proporsi | Arti | clock_in/out |
|---|---|---|---|
| `present` | 87.2% | Hadir tepat waktu | ✅ Terisi |
| `late` | 5.8% | Hadir tapi terlambat (8–55 menit) | ✅ Terisi |
| `leave` | 5.0% | Cuti resmi | ❌ Kosong |
| `absent` | 2.0% | Tidak hadir tanpa keterangan | ❌ Kosong |
 
**Cara hitung lembur**:
 
```sql
jam_kerja = clock_out − clock_in
lembur = MAX(0, jam_kerja − 8)
```
 
**Pola yang tertanam**:
 
| Pola | Detail |
|---|---|
| **Gejala pra-resign** | Lihat penjelasan khusus di bawah |
| Lembur naik saat okupansi tinggi | 2.4x lipat saat okupansi ≥85% |
| ~8% staf lembur berlebihan | 3.2x lipat dari normal (use case 4.3) |
| ~7% staf sering telat | 4x lipat dari normal (use case 4.4) |
| Anomali absensi | 3 window: F&B Jakarta Des 2024 (3.2x), Housekeeping Bali Jul 2025 (2.8x), F&B Bandung Jun 2024 (2.5x) |
 
### 🎯 Gejala Pra-Resign — Penjelasan Khusus untuk ML M4
 
Ini pola paling penting di database ini. Berbasis riset industri:
 
> *"Frequent absences, repeated late arrivals... signal a higher turnover risk"* — Hire Elite Consultants
>
> *"Never assume a quiet high-performer is a happy high-performer. Quiet compliance often masks deep emotional withdrawal and impending resignation."* — 5 Starr Engagement
 
Karena itu, dari 100 karyawan yang resign/terminated:
 
| Kelompok | Jumlah | Absensi (sebelum → 3 bulan terakhir) | Telat (sebelum → 3 bulan terakhir) |
|---|---|---|---|
| **Bergejala (70%)** | 70 | 1.89% → 4.24% (**2.24x**) | 5.85% → 10.88% (**1.86x**) |
| **Mendadak (30%)** | 30 | 2.07% → 1.85% (0.90x) | 5.59% → 6.19% (1.11x) |
| *Baseline (karyawan aktif)* | 655 | *1.99%* | *5.84%* |
 
**Implikasi untuk pemodelan**:
- Model M4 **tidak akan** mencapai akurasi mendekati 100% — dan itu **benar secara metodologis**.
- Ceiling realistis: menangkap ~70% resign yang bergejala (70 dari 100).
- Model yang "terlalu bagus" biasanya tanda data bocor (leakage) atau data dibuat-buat.
- File `_pattern_seeds/resign_symptomatic.json` mencatat siapa yang bergejala — bisa dipakai validasi: apakah model menangkap yang bergejala dan melewatkan yang mendadak?
---
 
## Tabel: `employee_performance`
 
**Deskripsi**: Penilaian kinerja semesteran.
 
**Granularitas**: 1 baris = (karyawan × periode review) | **3.748 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `review_id` | string (PK) | Format `PR00001`. |
| `employee_id` | string (FK) | |
| `review_period` | string | Format `YYYY-S1` (Januari–Juni) atau `YYYY-S2` (Juli–Desember). |
| `score` | float | Skor 1.00–5.00. |
| `notes` | string | Catatan kualitatif, konsisten dengan rentang skor. |
 
**Makna `score`**:
 
| Rentang | Arti | Contoh catatan |
|---|---|---|
| 4.3 – 5.0 | Sangat baik, melebihi ekspektasi | "Inisiatif tinggi, layak dipertimbangkan untuk promosi" |
| 3.5 – 4.29 | Baik, memenuhi target | "Stabil dan dapat diandalkan" |
| 2.5 – 3.49 | Cukup, ada ruang perbaikan | "Perlu peningkatan konsistensi" |
| 1.0 – 2.49 | Di bawah standar | "Perlu coaching intensif" |
 
**Aturan review**: karyawan hanya direview jika sudah bekerja **minimal 3 bulan**, dan tidak direview setelah tanggal resign.
 
**Pola pra-resign**: skor karyawan bergejala menurun menjelang resign.
 
| Kelompok | Skor review terakhir |
|---|---|
| Bergejala | 3.22 |
| Mendadak | 3.53 |
| Aktif | 3.60 |
 
---
 
## Tabel: `payroll`
 
**Deskripsi**: Penggajian bulanan. **Tabel paling sensitif di seluruh database** — sengaja dipisah dari `employees` karena di dunia nyata payroll punya sistem & kontrol akses terpisah.
 
**Granularitas**: 1 baris = (karyawan × bulan) | **23.383 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `payroll_id` | string (PK) | Format `PY000001`. |
| `employee_id` | string (FK) | |
| `period` | string | Format `YYYY-MM`. |
| `base_salary` | integer | Gaji pokok. Naik 6.5%/tahun mengikuti UMK. |
| `service_charge` | integer | **Bagi hasil biaya layanan** — lihat penjelasan khusus. |
| `overtime_pay` | integer | Upah lembur = `(base_salary ÷ 173) × jam_lembur`. |
| `thr` | integer | Tunjangan Hari Raya. **Hanya terisi 1x/tahun** (Maret). |
| `deduction` | integer | Potongan: BPJS Kesehatan 1% + BPJS Ketenagakerjaan 3% + PPh21 ~5%. |
| `net_salary` | integer | `base + service_charge + overtime + thr − deduction`. |
 
### 💰 Service Charge — Penjelasan Khusus
 
Ini komponen yang **wajib dipahami** untuk analisis payroll hotel Indonesia:
 
> *"Di hotel bintang 4 atau 5 yang ramai (seperti di Bali atau Jakarta), service charge bisa melebihi gaji pokok."* — riset industri
 
**Cara kerja**:
```
Pool service charge properti = Revenue properti × 10% × 85%
Service charge per karyawan  = (Pool ÷ Total poin properti) × Poin karyawan
```
 
| Level | Poin | Alasan |
|---|---|---|
| `staff` | 1.0 | Baseline |
| `manager` | 2.2 | Senioritas dapat porsi lebih besar |
| `corporate` | 0.0 | **Tidak dapat** — bukan staf properti |
 
**Konsekuensi penting**: service charge **berkorelasi kuat dengan okupansi** (r = 0.83–0.95 per properti). Saat low season, take-home pay karyawan turun signifikan.
 
| Bali | Okupansi | Service charge |
|---|---|---|
| Maret 2024 (terendah) | 57% | Rp 4.016.175 |
| Desember 2025 (tertinggi) | 88% | Rp 6.052.929 |
 
> Ini bisa jadi **sinyal tambahan untuk M4**: pendapatan turun saat low season → motivasi turun → risiko resign naik. Riset menyebut *"payroll patterns such as declining hours, missed shifts, or reduced tip earnings can signal dissatisfaction."*
 
**Rata-rata komponen gaji**:
 
| Komponen | Rata-rata |
|---|---|
| `base_salary` | Rp 7.900.767 |
| `service_charge` | Rp 3.531.911 |
| `overtime_pay` | Rp 569.863 |
| **`net_salary`** | **Rp 11.690.717** |
 
**Rasio service charge terhadap gaji pokok**:
 
| Level | Rasio | Nominal |
|---|---|---|
| staff | 0.74x | SC Rp 3,7jt vs base Rp 5,0jt |
| manager | 0.40x | SC Rp 7,9jt vs base Rp 19,6jt |
 
**Rentang gaji pokok** (berbasis riset Hotel Job Indonesia 2025):
 
| Posisi | Rentang (Rp/bulan) |
|---|---|
| Housekeeping / F&B Staff | 3,5 – 5,0 juta |
| Front Office Staff | 4,0 – 5,5 juta |
| HR / Finance Staff | 4,5 – 7,0 juta |
| Housekeeping Manager | 10 – 20 juta |
| F&B Manager | 15 – 30 juta |
| General Manager | 25 – 45 juta |
| CEO & Director | 35 – 90 juta |
 
**Pengali lokasi** (mengikuti UMK 2025 — Jakarta tertinggi Rp 5,3jt; Badung Rp 3,5jt):
 
| Properti | Pengali |
|---|---|
| P02 Jakarta | 1.18x |
| P06 Corporate | 1.20x |
| P01 Bali | 1.00x (baseline) |
| P05 Lombok | 0.92x |
| P04 Bandung | 0.85x |
| P03 Yogyakarta | 0.78x |
 
---
 
## Tabel: `financial_summary`
 
**Deskripsi**: Laporan keuangan bulanan per properti per departemen, mengikuti **standar USALI** (Uniform System of Accounts for the Lodging Industry) — format akuntansi baku industri perhotelan global.
 
**Granularitas**: 1 baris = (properti × bulan × departemen) | **756 baris**
 
| Kolom | Tipe | Deskripsi |
|---|---|---|
| `property_id` | string (FK) | |
| `period` | string | Format `YYYY-MM`. |
| `department` | enum | Departemen atau baris ringkasan. |
| `departmental_revenue` | integer | Pendapatan departemen. |
| `departmental_expense` | integer | Biaya langsung departemen. |
| `departmental_profit` | integer | `departmental_revenue − departmental_expense`. |
| `undistributed_expense` | integer | Overhead bersama. **Hanya terisi di baris `Overall`.** |
| `gop` | integer | **Gross Operating Profit**. Hanya terisi di baris `Overall`. |
 
**Makna `department`**:
 
| Nilai | Arti | Sumber revenue |
|---|---|---|
| `Room` | Departemen kamar | `bookings` (DB2) |
| `F&B` | Food & Beverage | `fnb_transactions` (DB3) |
| `Spa&Event` | Spa + MICE | `spa_bookings` + `event_bookings` (DB5) |
| `Overall` | **Baris ringkasan properti** — di sinilah `undistributed_expense` & `gop` terisi | Total semua |
| `Corporate Overhead` | Kantor pusat (P06) — hanya biaya, tanpa revenue | — |
 
> ⚠️ **Penting**: baris `Overall` adalah **ringkasan**, bukan departemen tambahan. Menjumlahkan semua baris termasuk `Overall` akan menghasilkan **double counting**. Untuk analisis per departemen, filter `department IN ('Room','F&B','Spa&Event')`.
 
**Struktur USALI**:
 
```
  Departmental Revenue        (Room + F&B + Spa&Event)
− Departmental Expense        (payroll + COGS + alokasi service charge)
= Departmental Profit
− Undistributed Expenses      (overhead bersama, lihat di bawah)
= GOP (Gross Operating Profit)
```
 
**Rincian `undistributed_expense`** (overhead yang tidak bisa dibebankan ke satu departemen):
 
| Komponen | % dari revenue |
|---|---|
| Administrative & General | 7.5% |
| Sales & Marketing | 6.5% |
| Utilities | 4.2% |
| Property Operations & Maintenance | 4.8% (**memakai data nyata dari DB4**) |
| Information & Telecom | 1.8% |
| **Total** | **24.8%** |
 
**Realisasi margin**:
 
| Departemen | Margin | Sesuai riset? |
|---|---|---|
| `Room` | 70.3% | ✅ Rooms dept expense paling rendah |
| `Spa&Event` | 45.0% | ✅ |
| `F&B` | 10.7% | ✅ *"F&B presents such tight margins"* |
 
| GOP margin | Nilai |
|---|---|
| P05 Lombok | 42.5% |
| P01 Bali | 39.4% |
| P04 Bandung | 37.2% |
| P03 Yogyakarta | 32.5% |
| P02 Jakarta | 31.8% |
 
> Riset CoStar: GOP margin full-service **25–35%**, di atas 35% tergolong "strong". Resort (Bali/Lombok) di atas rentang karena ADR premium.
 
**Koherensi terverifikasi**: `Room` revenue di tabel ini **cocok 100%** dengan total `bookings.total_amount` (status completed/confirmed) di DB2. Tabel ini benar-benar dihitung dari data nyata, bukan digenerate independen.
 
> **Catatan alokasi service charge**: service charge berasal dari revenue *seluruh* properti, jadi dialokasikan ke tiap departemen **proporsional dengan kontribusi revenue-nya** — bukan dibebankan ke departemen tempat karyawan bekerja. Tanpa koreksi ini, F&B akan terlihat rugi (-0.1%) padahal seharusnya 10.7%.
 
---
 
# Lampiran: File Pendukung
 
File-file ini **bukan bagian data resmi** — alat bantu internal untuk koordinasi pola lintas-database dan validasi.
 
| File | Isi | Kegunaan |
|---|---|---|
| `_pattern_seeds/resign_candidates.json` | 100 karyawan + tanggal resign | Menentukan siapa yang resign & kapan; dipakai DB6 untuk menanam gejala |
| `_pattern_seeds/resign_symptomatic.json` | 70 karyawan yang bergejala | **Validasi M4**: apakah model menangkap yang bergejala & melewatkan yang mendadak? |
| `_pattern_seeds/churn_candidates.json` | 434 guest loyal + tanggal mulai churn | Menentukan pola penurunan booking; dipakai DB2 |
| `_pattern_seeds/data_quality_issues_log_db1.csv` | 15.346 baris "kunci jawaban" data kotor | **Validasi data cleaning**: baris mana yang sengaja dikotori, nilai asli vs kotor |
 
> **Kenapa disimpan terpisah?** Skema tabel yang sudah disepakati tidak punya kolom untuk informasi ini (misal `resign_date`, `is_symptomatic`). Menaruhnya di file terpisah menjaga skema tetap bersih sekaligus memungkinkan koordinasi pola antar script yang dijalankan terpisah.
 
---
 
# Lampiran: Konvensi & Aturan Baku
 
Aturan yang berlaku konsisten di seluruh database:
 
| Aturan | Detail |
|---|---|
| **Filter revenue** | Selalu `status IN ('completed','confirmed')`. Berlaku untuk `bookings`, `spa_bookings`, `event_bookings`. |
| **Normalisasi department** | Kolom `employees.department` wajib `.str.strip().str.lower()` sebelum agregasi. |
| **Nilai moneter** | Integer, Rupiah penuh, tanpa desimal. |
| **Tanggal** | ISO `YYYY-MM-DD`, kecuali ~2% `employees.hire_date` yang sengaja `DD/MM/YYYY`. |
| **Datetime** | `YYYY-MM-DD HH:MM:SS`, waktu lokal properti. |
| **Kolom kosong** | String kosong (`""`), bukan `NULL` atau `NaN`. |
| **Integritas relasi** | 100% bersih — semua FK valid, tidak ada orphan record. |
| **Baris ringkasan** | `financial_summary.department = 'Overall'` adalah ringkasan, jangan dijumlahkan bersama baris departemen. |
 
---
 
## Riwayat Revisi
 
- **v1.0** — Metadata awal lengkap untuk 6 database, 23 tabel. Mencakup deskripsi database, tabel, kolom, makna setiap nilai enum, pola tertanam, landasan riset, konvensi baku, dan peringatan untuk konsumen data.