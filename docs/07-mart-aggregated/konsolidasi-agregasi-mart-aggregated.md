# Konsolidasi dan Rasionalisasi Kebutuhan Agregasi — `mart_aggregated`

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 5.1 (`milestones/5.1-konsolidasi-rasionalisasi-kebutuhan-agregasi/`) |
| **Dokumen sumber** | `docs/02-requirements/pemetaan-kebutuhan-data-analyst.md` (6 pola domain), `pemetaan-kebutuhan-chatbot-layer-staff.md` (7 persona), `-manager.md` (8 persona), `-korporat.md` (5 persona) |
| **Dipakai oleh** | Milestone 5.2 (`docs/03-implementation-plans/03-mart-aggregated-owner.md`) — desain skema tabel `mart_aggregated` |
| **Status** | Selesai — seluruh 6 domain terkonsolidasi (Milestone 5.1, ditutup 2026-08-08) |

---

## Cara Membaca Dokumen Ini

Setiap metrik/agregasi dikelompokkan per domain (Revenue, F&B, Facility/Ops, Spa & Event, HR, Corporate/Financial), dengan skema kolom:

`Domain | Metrik/Agregasi | Grain | Konsumen Analyst | Konsumen Chatbot | Status | Catatan`

Status berisi salah satu dari:
- **Cakupan Awal** — masuk `mart_aggregated` sesuai pola agregasi standar.
- **Cakupan Khusus** — masuk cakupan tapi butuh perlakuan desain khusus (mis. snapshot harian untuk pace booking), keputusan desainnya menyusul di Milestone 5.2.
- **Luar Cakupan** — tidak dibangun karena keterbatasan data sumber, dengan alasan di kolom Catatan.

Bagian "Pemetaan Persona → Domain" di bawah adalah tabel rujukan lintas-domain (dibangun di Checkpoint 1), dipakai berulang di tiap bagian domain berikutnya untuk mengidentifikasi persona chatbot mana yang relevan — bukan diturunkan ulang per domain.

**Catatan tentang kebutuhan row-level:** Beberapa kebutuhan di dokumen sumber (Data Analyst) eksplisit ditandai butuh `mart_cleaned` (row-level), bukan `mart_aggregated` — mis. investigasi ad-hoc, basket analysis. Ini **bukan** "Luar Cakupan" dalam arti keterbatasan data (datanya ada dan akan tersedia dari `mart_cleaned`), jadi tidak diberi baris tersendiri di tabel metrik agregat tiap domain — cukup dicatat sebagai catatan singkat di akhir tiap bagian domain untuk kelengkapan penelusuran. Status "Luar Cakupan" pada tabel metrik direservasi murni untuk kebutuhan yang **tidak tersedia dari data sumber sama sekali** (gap data), sesuai definisi Output #3 dokumen sumber M5.1.

---

## Pemetaan Persona Chatbot → Domain

20 persona AI Chatbot (7 Staff + 8 Manager + 5 Korporat) dipetakan ke domain data yang disentuh, berdasarkan label RBAC eksplisit di tiap persona pada dokumen sumber. Prinsip superset (Manager mewarisi Staff, Korporat mewarisi Manager) berarti setiap domain yang dimiliki Staff otomatis juga dimiliki Manager/Korporat di atasnya — tabel ini mencatat domain **RBAC penuh** tiap persona (warisan + tambahan), bukan hanya tambahan barunya.

### Layer Staff (7 persona — akses `own_property`, mayoritas `own_subject` untuk data performa individu)

| Persona | Domain RBAC | Domain `mart_aggregated` Utama | Jenis Konsumsi |
|---|---|---|---|
| Front Office Staff | `reservation`+`properties_ref`+`guests_pii` | Revenue | Row-level (`mart_cleaned`) dominan — lookup booking/tamu spesifik; ketersediaan kamar per `room_type` bersifat snapshot state saat ini, bukan agregasi historis |
| F&B Staff | `fnb` | F&B | Campuran — row-level (stok, komposisi bahan) + agregasi ringan harian (menu terlaris, total penjualan hari berjalan) |
| Housekeeping Staff | `facility` | Facility/Ops | Row-level dominan — daftar tugas, status kamar, durasi individu (filter wajib `staff_id`=dirinya) |
| Maintenance Staff | `facility` | Facility/Ops | Row-level dominan — detail/riwayat tiket (filter wajib `assigned_staff_id`=dirinya untuk data performa) |
| Spa & Event Staff | `spa_event`+`guests_pii` | Spa & Event | Campuran — row-level (jadwal, detail booking) + agregasi ringan mingguan (layanan terlaris) |
| HR Staff | `hr`+`employees_directory` | HR | Campuran — row-level (kehadiran, resolve nama) + agregasi administratif sederhana (jumlah karyawan per departemen, daftar keterlambatan bulan berjalan) |
| Finance Staff | `financial`+`employees_directory` | Corporate/Financial | Aggregate dominan — seluruhnya dari `financial_summary` (tabel yang sudah berbentuk agregat departemen bulanan) |

### Layer Manager (8 persona — akses `own_property` penuh, superset Staff domainnya)

| Persona | Domain RBAC (penuh, termasuk warisan) | Domain `mart_aggregated` Utama | Domain Sentuhan Silang | Jenis Konsumsi |
|---|---|---|---|---|
| Revenue Manager | `reservation`+`properties_ref`+`guests_profile`+`guests_pii` | Revenue | — | Aggregate — tren MoM, breakdown pricing, cancellation rate |
| F&B Manager | `fnb`+`reservation`+`properties_ref`+`employees_directory` | F&B | Revenue (`reservation`, untuk capture rate tamu inhouse) | Aggregate |
| Housekeeping Manager | `facility`+`reservation`+`properties_ref`+`employees_directory` | Facility/Ops | Revenue (`reservation`, untuk delayed rate vs okupansi) | Aggregate |
| Maintenance Manager | `facility`+`properties_ref`+`employees_directory` | Facility/Ops | — | Aggregate |
| Spa & Event Manager | `spa_event`+`properties_ref`+`employees_directory`+`guests_pii` | Spa & Event | — | Aggregate |
| HR Manager | `hr`+`properties_ref`+`employees_directory` | HR | — | Aggregate, termasuk metrik *within-entity over time* (watchlist pra-resign — lihat Cakupan Khusus di bagian HR) |
| Finance Manager | `financial`+`reservation`+`properties_ref`+`employees_directory` | Corporate/Financial | Revenue (`reservation`, untuk service charge vs okupansi) | Aggregate |
| General Manager | Semua 7 domain (`reservation`,`fnb`,`facility`,`spa_event`,`hr`,`financial`,`properties_ref`)+`employees_directory`+`guests_pii`+`guests_profile` | **Lintas 6 domain sekaligus** | Semua domain | Aggregate, ringkasan lintas fungsi dalam satu jawaban |

### Layer Korporat (5 persona — akses `all_properties`, superset Manager domainnya, fokus benchmarking antar 5 properti)

| Persona | Domain RBAC (penuh) | Domain `mart_aggregated` Utama | Domain Sentuhan Silang | Jenis Konsumsi |
|---|---|---|---|---|
| CEO | Semua 7 domain+`properties_ref`+`employees_directory`+`guests_pii`+`guests_profile`, `all_properties` | **Lintas 6 domain sekaligus** | Semua domain | Aggregate, benchmark & ringkasan strategis lintas grup |
| Corporate Finance Director | `financial`+`reservation`+`properties_ref`+`employees_directory`, `all_properties` | Corporate/Financial | Revenue (`reservation`) | Aggregate, benchmark antar properti + metrik baru "Corporate Overhead" |
| Corporate HR Director | `hr`+`properties_ref`+`employees_directory`, `all_properties` | HR | — | Aggregate, benchmark antar properti |
| Corporate Operations Director | `facility`+`fnb`+`spa_event`+`reservation`+`properties_ref`+`employees_directory`+`guests_pii`, `all_properties` | **F&B + Facility/Ops + Spa & Event sekaligus** | Revenue (`reservation`) | Aggregate, benchmark antar properti untuk 3 domain operasional |
| Corporate Revenue Director | `reservation`+`financial`+`properties_ref`+`guests_profile`+`guests_pii`, `all_properties` | Revenue | Corporate/Financial (kombinasi unik `reservation`+`financial` untuk dampak pricing terhadap GOP) | Aggregate, benchmark antar properti |

**Verifikasi cakupan:** 20/20 persona (7+8+5) sudah terpetakan ke minimal 1 domain `mart_aggregated`. 3 persona (General Manager, CEO, Corporate Operations Director) menyentuh lebih dari 1 domain sekaligus secara struktural (akses lintas domain sejak awal RBAC, bukan pengecualian) — dicatat eksplisit sebagai "Konsumen Chatbot" di lebih dari satu bagian domain berikutnya.

---

## 1. Revenue

**Sumber:** `pemetaan-kebutuhan-data-analyst.md` §1.3. **Tabel sumber:** `bookings`, `daily_occupancy`, `pricing_history`, `properties`, `guests`.

| Metrik/Agregasi | Grain | Konsumen Analyst | Konsumen Chatbot | Status | Catatan |
|---|---|---|---|---|---|
| `occupancy_rate`, `adr`, `revpar` | property_id/room_type × harian..tahunan | Revenue Analyst | Revenue Manager (tren MoM), Corporate Revenue Director (benchmark antar properti), GM & CEO (ringkasan lintas domain/grup) | Cakupan Awal | — |
| Revenue & jumlah booking per channel | property_id/channel × periode | Revenue Analyst | Revenue Manager | Cakupan Awal | — |
| Cancellation rate & no-show rate | property_id/channel × periode | Revenue Analyst | Revenue Manager, Corporate Revenue Director (benchmark) | Cakupan Awal | — |
| Room type revenue mix | property_id/room_type × periode | Revenue Analyst | Revenue Manager (revenue per room_type) | Cakupan Awal | — |
| MoM & YoY growth (occupancy/ADR/RevPAR) | property_id × periode | Revenue Analyst | Revenue Manager (MoM), Corporate Revenue Director/CEO (YoY grup) | Cakupan Awal | — |
| Pricing deviation (`applied_rate−base_rate`, breakdown `reason`) | property_id × periode | Revenue Analyst | Revenue Manager, Corporate Revenue Director (lintas grup) | Cakupan Awal | — |
| Rata-rata & median length of stay | property_id/room_type/channel × periode | Revenue Analyst | — | Cakupan Awal | Tidak diminta eksplisit oleh persona chatbot manapun, tapi tetap kebutuhan Analyst yang valid |
| Rata-rata & median booking lead time | property_id × periode | Revenue Analyst | Revenue Manager | Cakupan Awal | — |
| Ranking/percentile RevPAR/ADR/occupancy antar 5 properti | properti × periode | Revenue Analyst | Corporate Revenue Director (benchmark okupansi/ADR/RevPAR), CEO (ringkasan performa grup) | Cakupan Awal | — |
| Revenue & booking share domestik vs mancanegara | property_id × periode | Revenue Analyst | — | Cakupan Awal | Butuh aturan kategorisasi `nationality` eksplisit saat implementasi M5.2/5.3 |
| Repeat guest rate | property_id × periode | Revenue Analyst | Corporate Revenue Director (repeat guest rate grup) | Cakupan Awal | — |
| Dampak strategi pricing terhadap GOP margin | property_id × periode | — (tidak eksplisit di Revenue Analyst) | Corporate Revenue Director (kombinasi domain unik `reservation`+`financial`) | Cakupan Awal | **Cross-domain**: join ke `financial_summary.gop` (domain Corporate/Financial) — dirujuk-silang di bagian 6 |
| Pace booking (kamar terjual untuk tanggal check-in masa depan, "as of hari ini") | property_id/room_type × snapshot harian | Revenue Analyst (ditandai keluar cakupan reguler) | Revenue Manager (pace booking 2 minggu ke depan) | Cakupan Khusus | Butuh mekanisme snapshot harian, bukan agregasi historis biasa — lihat bagian "Kebutuhan Khusus" |
| Komisi OTA per booking | — | Revenue Analyst | — | Luar Cakupan | Tidak ada kolom komisi di `bookings` — gap data sumber |
| Target/budget okupansi & revenue | — | Revenue Analyst | — | Luar Cakupan | Tidak ada tabel target/budget di skema manapun — gap data sumber |

**Row-level (`mart_cleaned`, bukan `mart_aggregated`):** investigasi ad-hoc anomali (mis. lonjakan cancellation), price elasticity analysis (histori harian row-level harga vs okupansi).

---

## 2. F&B

**Sumber:** `pemetaan-kebutuhan-data-analyst.md` §2.3. **Tabel sumber:** `fnb_transactions`, `fnb_outlets`, `recipe_bom`, `ingredient_price_history`, `fnb_inventory`, `fnb_waste_log`; `bookings`/`daily_occupancy` (untuk capture rate, cross-domain dari Revenue).

| Metrik/Agregasi | Grain | Konsumen Analyst | Konsumen Chatbot | Status | Catatan |
|---|---|---|---|---|---|
| Revenue, transaction count, avg check per outlet | outlet_id × periode | F&B Analyst | F&B Staff (total penjualan hari berjalan, grain harian), F&B Manager (MoM/YoY), Corporate Operations Director (benchmark antar properti) | Cakupan Awal | — |
| Revenue per kategori (Food/Beverage/Dessert) | outlet_id/category × periode | F&B Analyst | — | Cakupan Awal | — |
| Distribusi transaksi per jam/segmen waktu | outlet_id × jam | F&B Analyst | — | Cakupan Awal | — |
| Food cost ratio realisasi vs target | outlet_id/category × periode | F&B Analyst | F&B Manager, Corporate Operations Director (benchmark) | Cakupan Awal | Cross-table `fnb_transactions`×`recipe_bom`×`ingredient_price_history` |
| Daftar menu dengan deviasi food cost terbesar dari target | outlet_id × periode | F&B Analyst | F&B Manager (bagian monitoring food cost) | Cakupan Awal | — |
| Total waste (value & quantity) & waste ratio, breakdown `reason` | outlet_id × periode | F&B Analyst | F&B Manager, Corporate Operations Director (benchmark) | Cakupan Awal | — |
| Revenue per outlet MoM & YoY growth | outlet_id × periode | F&B Analyst | F&B Manager | Cakupan Awal | — |
| Capture rate (tamu inhouse belanja F&B) | property_id × periode | F&B Analyst | F&B Manager, Corporate Operations Director (benchmark) | Cakupan Awal | **Cross-domain**: join populasi tamu menginap dari `bookings`/`daily_occupancy` (domain Revenue) |
| Walk-in ratio dan trennya | outlet_id × periode | F&B Analyst | F&B Manager, Corporate Operations Director (benchmark) | Cakupan Awal | — |
| Top & bottom performing menu items (revenue/quantity) | outlet_id/item_name × periode | F&B Analyst | F&B Manager (revenue/margin per item → item paling untung/rugi) | Cakupan Awal | — |
| Jumlah & daftar item inventory di bawah `stock_min_threshold` | outlet_id × snapshot terkini | F&B Analyst | F&B Staff (level stok per item), F&B Manager (agregat lintas outlet) | Cakupan Awal | — |
| Ranking/pembanding revenue outlet vs rata-rata outlet/properti sejenis | outlet_id/outlet_type × periode | F&B Analyst | Corporate Operations Director (benchmark, granularitas antar properti bukan antar outlet — dicatat sebagai perbedaan level) | Cakupan Awal | — |
| Revenue per kunjungan & kategori favorit — inhouse vs walk-in | property_id × periode | F&B Analyst | F&B Manager (bagian dari walk-in ratio dan tren, tidak eksplisit dipisah) | Cakupan Awal | — |
| Tren harga rata-rata bahan baku | ingredient × periode | F&B Analyst | F&B Manager | Cakupan Awal | — |
| Daftar staf F&B propertinya | property_id | — (bukan kebutuhan Data Analyst, murni kebutuhan chatbot) | F&B Manager | Cakupan Awal | Sumber `employees` (`employees_directory`), bukan `fnb_operations` — ditambahkan di sini karena eksplisit diminta F&B Manager, dicatat sebagai kebutuhan chatbot-only |
| Waktu penyiapan/kecepatan servis outlet | — | F&B Analyst | — | Luar Cakupan | Tidak ada kolom timestamp granular servis di `fnb_transactions` — gap data sumber |
| Data supplier/vendor bahan baku | — | F&B Analyst | — | Luar Cakupan | Tidak ada tabel supplier di skema manapun — gap data sumber |

**Row-level (`mart_cleaned`, bukan `mart_aggregated`):** investigasi anomali penjualan menu tertentu, basket analysis (kombinasi item per struk, butuh grain per `transaction_id`).

---

## 3. Facility/Ops

**Sumber:** `pemetaan-kebutuhan-data-analyst.md` §3.3. **Tabel sumber:** `rooms`, `housekeeping_log`, `maintenance_tickets`; `daily_occupancy` (cross-domain Revenue, untuk korelasi okupansi).

| Metrik/Agregasi | Grain | Konsumen Analyst | Konsumen Chatbot | Status | Catatan |
|---|---|---|---|---|---|
| Distribusi status kamar saat ini (snapshot) | property_id | Facility/Ops Analyst | Housekeeping Staff (daftar tugas & status), Housekeeping Manager (distribusi seluruh properti), Corporate Operations Director (benchmark) | Cakupan Awal | — |
| Jumlah & durasi kamar out-of-order | property_id × periode | Facility/Ops Analyst | — | Cakupan Awal | Prioritas tinggi karena berdampak revenue, tapi tanpa estimasi kehilangan revenue (lihat baris Luar Cakupan) |
| Durasi rata-rata pembersihan per tipe kamar vs baseline | property_id/room_type × periode | Facility/Ops Analyst | Housekeeping Staff (durasi dirinya), Housekeeping Manager (agregat tim) | Cakupan Awal | — |
| Delayed rate housekeeping | property_id × periode | Facility/Ops Analyst | Housekeeping Manager | Cakupan Awal | — |
| Delayed rate housekeeping terkait okupansi | property_id × periode | Facility/Ops Analyst | Housekeeping Manager | Cakupan Awal | **Cross-domain**: join `daily_occupancy` (domain Revenue) |
| Durasi pembersihan per staff vs rata-rata staff lain | staff_id × periode | Facility/Ops Analyst | Housekeeping Staff (dirinya sendiri, filter wajib `staff_id`), Housekeeping Manager (seluruh tim) | Cakupan Awal | Data performa individu — keputusan sadar tetap dimasukkan meski label RBAC domain `facility` "Rendah"; filtering akses granular jadi tanggung jawab application layer |
| Jumlah tiket maintenance baru per `facility_area`/`issue_type` | property_id/facility_area/issue_type × periode | Facility/Ops Analyst | Maintenance Manager | Cakupan Awal | — |
| SLA breach rate per `priority` | property_id/priority × periode | Facility/Ops Analyst | Maintenance Manager, Maintenance Staff (status SLA per tiket) | Cakupan Awal | Tiket `open`/`in-progress` dikategorikan "pending", terpisah dari breach/tidak breach. **Threshold SLA per `priority` belum ditentukan** (gap parameter, bukan gap data) — keputusan menyusul di M5.2/5.3 |
| Total maintenance cost, breakdown dengan/tanpa ganti part | property_id × periode | Facility/Ops Analyst | Maintenance Manager | Cakupan Awal | — |
| Cost breakdown per `issue_type`, MoM & YoY | property_id/issue_type × periode | Facility/Ops Analyst | — | Cakupan Awal | — |
| Jumlah tiket per `room_id` vs median/rata-rata kamar sejenis (recurring issue) | room_id × periode | Facility/Ops Analyst | Maintenance Manager (kamar dengan tiket berulang) | Cakupan Awal | — |
| Tiket per kamar per tahun, benchmark antar properti | property_id × tahun | Facility/Ops Analyst | Corporate Operations Director (eksplisit: dinormalisasi `properties.opening_date`/usia gedung) | Cakupan Awal | — |
| Jumlah tiket & total `labor_hours` per teknisi (workload) | assigned_staff_id × periode | Facility/Ops Analyst | Maintenance Staff (jumlah tiket diselesaikan dirinya), Maintenance Manager (seluruh tim) | Cakupan Awal | — |
| Tren cost & jumlah tiket bulanan jangka panjang | property_id × bulanan | Facility/Ops Analyst | — | Cakupan Awal | Dasar proyeksi budget maintenance |
| Preventive maintenance (jadwal terjadwal) | — | Facility/Ops Analyst | — | Luar Cakupan | Tidak ada tabel jadwal preventive maintenance — semua tiket bersifat reaktif, gap data sumber |
| Estimasi kehilangan revenue akibat kamar out-of-order | — | Facility/Ops Analyst | — | Luar Cakupan | Butuh asumsi cross-domain (`daily_occupancy`/`bookings`) yang belum tentu akurat — sengaja tidak dijadikan metrik siap pakai |
| Breakdown biaya per jenis part | — | Facility/Ops Analyst | — | Luar Cakupan | `parts_replaced` teks bebas, bukan kategori terstruktur |

**Row-level (`mart_cleaned`, bukan `mart_aggregated`):** investigasi lonjakan keluhan tipe kerusakan tertentu, investigasi riwayat tiket per kamar spesifik.

---

## 4. Spa & Event

**Sumber:** `pemetaan-kebutuhan-data-analyst.md` §4.3. Dipisah 2 sub-bagian karena karakter data berbeda signifikan (spa: volume tinggi/nilai kecil; event: volume rendah/nilai besar).

### 4.1 Spa

**Tabel sumber:** `spa_bookings`.

| Metrik/Agregasi | Grain | Konsumen Analyst | Konsumen Chatbot | Status | Catatan |
|---|---|---|---|---|---|
| Revenue & jumlah booking | property_id × periode | Spa & Event Analyst | Spa & Event Staff (jadwal booking harian), Spa & Event Manager (revenue MoM) | Cakupan Awal | — |
| Revenue per kunjungan, inhouse vs walk-in | property_id × periode | Spa & Event Analyst | Spa & Event Manager (walk-in ratio dan revenue per kunjungan) | Cakupan Awal | — |
| Distribusi booking & revenue per `service_name` | property_id/service_name × periode | Spa & Event Analyst | Spa & Event Staff (layanan terlaris mingguan), Spa & Event Manager (tren layanan) | Cakupan Awal | — |
| Walk-in ratio dan trennya | property_id × periode | Spa & Event Analyst | Spa & Event Manager | Cakupan Awal | — |
| % kontribusi tiap `service_name` (tren popularitas) | property_id/service_name × periode | Spa & Event Analyst | Spa & Event Manager (tren popularitas layanan) | Cakupan Awal | — |
| Rata-rata & median lead time booking (`service_date−booking_date`) | property_id × periode | Spa & Event Analyst | — | Cakupan Awal | — |
| Cancellation rate spa | property_id × periode | Spa & Event Analyst | — | Cakupan Awal | Tidak diminta eksplisit oleh persona chatbot (beda dari cancellation rate event yang eksplisit diminta) |

**Row-level (`mart_cleaned`):** tidak ada kebutuhan row-level khusus di luar cakupan standar investigasi ad-hoc.

### 4.2 Event/MICE

**Tabel sumber:** `event_bookings`, `venues`.

| Metrik/Agregasi | Grain | Konsumen Analyst | Konsumen Chatbot | Status | Catatan |
|---|---|---|---|---|---|
| Jumlah & revenue event pipeline mendatang | property_id/venue_id × periode | Spa & Event Analyst | Spa & Event Staff (jadwal & lokasi event mendatang), Spa & Event Manager | Cakupan Awal | — |
| Utilisasi venue rata-rata (`capacity_booked÷max_capacity`) | venue_id × periode | Spa & Event Analyst | Spa & Event Staff (ketersediaan & kapasitas venue), Spa & Event Manager, Corporate Operations Director (benchmark) | Cakupan Awal | — |
| Venue dengan utilisasi rendah berulang | venue_id × periode | Spa & Event Analyst | Spa & Event Manager (eksplisit: venue utilisasi rendah berulang) | Cakupan Awal | Mengikuti pola "recurring issue" yang sama seperti Facility/Ops |
| Cancellation rate event | property_id × periode | Spa & Event Analyst | Spa & Event Manager, Corporate Operations Director (benchmark) | Cakupan Awal | — |
| Revenue & jumlah event per `event_type`, mix | property_id/event_type × periode | Spa & Event Analyst | Spa & Event Staff (detail booking event, row-level) | Cakupan Awal | — |
| Revenue per venue, MoM & YoY | venue_id × periode | Spa & Event Analyst | Spa & Event Manager (implied, bagian revenue spa & event MoM) | Cakupan Awal | — |
| Diskon/promo pada spa maupun event | — | Spa & Event Analyst | — | Luar Cakupan | Tidak ada kolom promo/discount di `spa_bookings` maupun `event_bookings` |
| Repeat client event | — | Spa & Event Analyst | — | Luar Cakupan | `client_name` teks bebas tanpa ID terstruktur — deteksi otomatis tidak andal, butuh fuzzy matching manual row-level jika diperlukan |
| Cross-sell spa × event | — | Spa & Event Analyst | — | Luar Cakupan | Tidak ada penghubung `guest_id` konsisten antara `spa_bookings` dan `event_bookings` |

**Row-level (`mart_cleaned`):** investigasi anomali utilisasi venue tertentu, investigasi klien event tertentu (`client_name`, termasuk fuzzy matching manual untuk repeat client).

**Catatan lintas sub-bagian (tidak dimasukkan sebagai metrik):** venue double-booking/konflik jadwal (constraint terjaga sistem, 0 pelanggaran — bukan sesuatu yang perlu dipantau); pemetaan `venue_type` ke `event_type` (aturan bisnis/konfigurasi tetap, bukan hal yang diagregasi/dianalisis trennya).

---

## 5. HR

**Sumber:** `pemetaan-kebutuhan-data-analyst.md` §5.3. **Tabel sumber:** `staff_shifts`, `employee_performance`, `employees`.

| Metrik/Agregasi | Grain | Konsumen Analyst | Konsumen Chatbot | Status | Catatan |
|---|---|---|---|---|---|
| Attendance rate (present/late/leave/absent) | property_id/department × periode | HR Analyst | HR Staff (hari ini), HR Manager (per departemen), Corporate HR Director (rata-rata grup) | Cakupan Awal | — |
| Jam lembur total & distribusi | property_id/department × periode | HR Analyst | — | Cakupan Awal | — |
| Jam lembur per individu vs rata-rata departemen | employee_id × periode | HR Analyst | HR Manager | Cakupan Awal | Deteksi lembur berlebihan kronis |
| Rate keterlambatan per individu vs rata-rata departemen | employee_id × periode | HR Analyst | HR Staff (daftar administratif keterlambatan), HR Manager (dibanding rata-rata) | Cakupan Awal | — |
| Rasio perubahan pola individu vs baseline historis (watchlist pra-resign) | employee_id × periode | HR Analyst | HR Manager (eksplisit: metrik inti watchlist) | Cakupan Awal | Metrik *within-entity over time*, bukan agregasi antar-entitas biasa. Threshold "di luar kebiasaan" untuk early warning **belum ditentukan** (Bagian 10 No. 3 dokumen induk) — di luar cakupan pemetaan ini, metrik dasarnya tetap disediakan |
| Skor performa terakhir & tren antar periode review | employee_id × periode review | HR Analyst | HR Staff (skor + catatan kualitatif), HR Manager (tren) | Cakupan Awal | — |
| Turnover rate per departemen/properti, MoM & YoY | property_id/department × periode | HR Analyst | HR Manager, Corporate HR Director (ranking antar properti) | Cakupan Awal | — |
| Distribusi status karyawan (active/resigned/terminated) | property_id/department × snapshot | HR Analyst | HR Manager, Corporate HR Director (jumlah karyawan aktif grup) | Cakupan Awal | — |
| Rata-rata skor performa per departemen, tren antar periode | property_id/department × periode | HR Analyst | HR Manager, Corporate HR Director (rata-rata grup) | Cakupan Awal | — |
| Perbandingan skor performa: populasi resign/terminated vs aktif | property_id × periode | HR Analyst | — | Cakupan Awal | Analisis korelasi kinerja-retensi, tidak diminta eksplisit oleh persona chatbot manapun |
| Payroll/kompensasi | — | HR Analyst (sengaja dikeluarkan) | — | Luar Cakupan | **Bukan gap data** — sengaja dipisah mengikuti segregation of duties HR vs Finance; sepenuhnya cakupan Corporate/Financial (lihat bagian 6) |
| Exit interview / alasan resign | — | HR Analyst | — | Luar Cakupan | `employees.status` hanya status akhir, tanpa tanggal/alasan resign — gap data sumber |
| Training/sertifikasi karyawan | — | HR Analyst | — | Luar Cakupan | Tidak ada tabel ini di skema manapun — gap data sumber |

**Row-level (`mart_cleaned`, bukan `mart_aggregated`):** investigasi lonjakan absensi departemen/periode tertentu, investigasi karyawan tertentu yang masuk watchlist (row-level histori shift & performance).

---

## 6. Corporate/Financial

**Sumber:** `pemetaan-kebutuhan-data-analyst.md` §6.3. **Tabel sumber:** `financial_summary`, `payroll`; `bookings` (koherensi check, cross-domain); `employees` (`access_level` untuk breakdown service charge).

| Metrik/Agregasi | Grain | Konsumen Analyst | Konsumen Chatbot | Status | Catatan |
|---|---|---|---|---|---|
| Departmental revenue/expense/profit (Room/F&B/Spa&Event) | property_id/department × periode | Corporate/Financial Analyst | Finance Staff, Corporate Finance Director (agregasi lanjut ke total grup) | Cakupan Awal | — |
| GOP dan GOP margin (%), MoM & YoY | property_id × periode, baris `Overall` | Corporate/Financial Analyst | Finance Staff, Finance Manager, Corporate Finance Director (ranking antar properti), CEO (vs rata-rata grup) | Cakupan Awal | — |
| Undistributed expense breakdown per komponen | property_id × periode, baris `Overall` | Corporate/Financial Analyst | Finance Staff, Corporate Finance Director (perbandingan antar properti) | Cakupan Awal | Wajib filter baris `Overall` — tidak dijumlah dengan baris departemen lain |
| Departmental margin (%) per lini bisnis | property_id/department × periode, filter `Room`/`F&B`/`Spa&Event` | Corporate/Financial Analyst | Finance Staff (bagian revenue/expense/profit per departemen) | Cakupan Awal | Wajib filter `department IN ('Room','F&B','Spa&Event')`, tidak menyertakan `Overall`/`Corporate Overhead` — risiko double counting jika salah filter |
| Overhead ratio (undistributed expense ÷ revenue) | property_id × periode, baris `Overall` | Corporate/Financial Analyst | — | Cakupan Awal | — |
| Revenue run-rate harian/mingguan (dari agregasi domain sumber lain, bukan `financial_summary`) | property_id × harian/mingguan | Corporate/Financial Analyst | — | Cakupan Awal | Pengganti GOP mingguan yang tidak bisa dihitung akurat (granularitas sumber bulanan) |
| Total komponen payroll (base_salary, service_charge, overtime_pay, THR, deduction, net_salary) | property_id/department × periode, MoM | Corporate/Financial Analyst | Finance Manager, Corporate Finance Director (breakdown per properti) | Cakupan Awal | — |
| Service charge pool vs occupancy rate | property_id × periode | Corporate/Financial Analyst | Finance Manager, Corporate Finance Director (properti mana paling menyimpang) | Cakupan Awal | **Cross-domain**: join `daily_occupancy` (domain Revenue) |
| Labor cost sebagai % revenue | property_id × periode | Corporate/Financial Analyst | Finance Manager, Corporate Finance Director (antar properti) | Cakupan Awal | — |
| Rasio service charge vs base salary, per `access_level` | property_id/access_level × periode | Corporate/Financial Analyst | — | Cakupan Awal | — |
| Kontribusi tiap lini bisnis terhadap revenue grup, pergeseran antar periode | group × periode | Corporate/Financial Analyst | — | Cakupan Awal | — |
| Benchmarking/ranking GOP margin antar 5 properti | properti × periode | Corporate/Financial Analyst | Corporate Finance Director, CEO | Cakupan Awal | — |
| Overhead korporat (`department='Corporate Overhead'`) | property_id/group × periode | — (bukan kebutuhan Data Analyst eksplisit) | Corporate Finance Director | Cakupan Awal | **Temuan baru** saat audit persona chatbot layer Korporat — value `department` terpisah dari `'Overall'`, belum pernah dibahas di layer manapun sebelumnya |
| Breakdown komponen cost dari domain lain (food cost, maintenance cost, dst) | — | Corporate/Financial Analyst (sengaja tidak dimasukkan) | — | Luar Cakupan | **Bukan gap data** — `departmental_expense` sudah agregat jadi; breakdown detail tetap tanggung jawab domain analyst masing-masing (F&B, Facility/Ops) — batasan cakupan yang disengaja |
| GOP/financial granularitas mingguan atau harian | — | Corporate/Financial Analyst | — | Luar Cakupan | `financial_summary` granularitas bulanan saja — diganti dengan revenue run-rate untuk kebutuhan mingguan |
| Cost of capital, depresiasi, komponen finansial non-operasional (below GOP line) | — | Corporate/Financial Analyst | — | Luar Cakupan | Tidak ada kolom ini di skema manapun — konsisten dengan struktur USALI yang berhenti di GOP |

**Kebutuhan validasi/monitoring (bukan metrik analisis — terkait Data Quality Gate, Bagian 9 dokumen arsitektur induk):** koherensi revenue Room di `financial_summary` terhadap total transaksi booking (status completed/confirmed) dari sumbernya — selisih harus 0 atau dalam toleransi yang disepakati. Relevan untuk implementasi DQ gate `mart_aggregated` di Milestone 5.3, bukan untuk skema tabel metrik itu sendiri.

**Row-level (`mart_cleaned`, bukan `mart_aggregated`):** investigasi penurunan margin lini bisnis tertentu, audit alokasi service charge (butuh `payroll` row-level per karyawan).

---

## Kebutuhan Khusus (Cakupan Khusus, Lintas Domain)

Dikelompokkan per jenis perlakuan khusus yang dibutuhkan — semua tetap **dalam cakupan** `mart_aggregated`, hanya butuh keputusan desain tambahan sebelum diimplementasikan (Milestone 5.2/5.3), bukan alasan untuk dikeluarkan.

### A. Butuh mekanisme snapshot harian terpisah (bukan agregasi dari histori yang sudah terjadi)

| Domain | Kebutuhan | Kenapa Khusus |
|---|---|---|
| Revenue | Pace booking (kamar terjual untuk tanggal check-in masa depan, "as of hari ini") | Nilainya berubah tiap hari untuk tanggal check-in yang sama — bukan fakta historis tetap seperti metrik lain. Butuh tabel/mekanisme snapshot harian tersendiri, desainnya di luar cakupan konsolidasi ini (menyusul Milestone 5.2) |

### B. Butuh pola query *within-entity over time* (individu dibanding baseline historisnya sendiri, bukan agregasi antar-entitas biasa)

| Domain | Kebutuhan | Kenapa Khusus |
|---|---|---|
| HR | Rasio perubahan pola individu (watchlist gejala pra-resign) — rate absen/telat periode terkini dibanding baseline historis individu yang sama | Beda struktur dari metrik agregat standar (`GROUP BY` per periode/entitas) — perlu window function atau tabel baseline per `employee_id` yang di-refresh berkala. Tetap masuk `mart_aggregated`, tapi desain kolom/mekanismenya perlu diputuskan eksplisit di Milestone 5.2, bukan dianggap sama dengan metrik agregat biasa |

### C. Parameter/threshold belum ditentukan (data pendukung tersedia, ambang batas menunggu keputusan terpisah)

| Domain | Kebutuhan | Status Parameter |
|---|---|---|
| Facility/Ops | SLA breach rate per `priority` | Cara hitung breach sudah jelas (`resolved_date−reported_date > SLA_hours`), tapi nilai `SLA_hours` per `priority` belum ditentukan di dokumen manapun — konsisten dengan Bagian 10 dokumen arsitektur induk yang menandai area ini untuk didiskusikan terpisah |
| HR | Threshold "di luar kebiasaan" untuk early warning watchlist pra-resign | Dokumen arsitektur induk (Bagian 10 No. 3) eksplisit menandai ambang batas drift/anomali sebagai area yang perlu didiskusikan terpisah dengan pihak berwenang |

---

## Eksplisit Luar Cakupan

16 kebutuhan dikonsolidasi dari 6 domain, dipisah 2 kategori:
- **Gap Data Sumber** — data benar-benar tidak tersedia di 23 tabel produksi (kandidat untuk dipertimbangkan penambahan kolom/tabel di production jika dianggap penting, tapi di luar cakupan pekerjaan ini).
- **Batasan Disengaja** — data sebenarnya tersedia, tapi sengaja tidak dimasukkan ke `mart_aggregated` karena alasan struktural (bukan keterbatasan data) — mis. dipindah ke domain lain, atau butuh asumsi cross-domain yang tidak cukup andal.

| Domain | Kebutuhan | Kategori | Alasan |
|---|---|---|---|
| Revenue | Komisi OTA per booking | Gap Data Sumber | Tidak ada kolom komisi di `bookings` |
| Revenue | Target/budget okupansi & revenue | Gap Data Sumber | Tidak ada tabel target/budget di skema manapun |
| F&B | Waktu penyiapan/kecepatan servis outlet | Gap Data Sumber | Tidak ada kolom timestamp granular servis di `fnb_transactions` |
| F&B | Data supplier/vendor bahan baku | Gap Data Sumber | Tidak ada tabel supplier di skema manapun |
| Facility/Ops | Preventive maintenance (jadwal terjadwal) | Gap Data Sumber | Semua tiket bersifat reaktif, tidak ada tabel jadwal preventive |
| Facility/Ops | Estimasi kehilangan revenue akibat kamar out-of-order | Batasan Disengaja | Butuh asumsi cross-domain (`daily_occupancy`/`bookings`) yang belum tentu akurat |
| Facility/Ops | Breakdown biaya per jenis part | Gap Data Sumber | `parts_replaced` teks bebas, bukan kategori terstruktur |
| Spa & Event | Diskon/promo pada spa maupun event | Gap Data Sumber | Tidak ada kolom promo/discount di `spa_bookings`/`event_bookings` |
| Spa & Event | Repeat client event | Gap Data Sumber | `client_name` teks bebas tanpa ID terstruktur |
| Spa & Event | Cross-sell spa × event | Gap Data Sumber | Tidak ada penghubung `guest_id` konsisten antar tabel |
| HR | Payroll/kompensasi | Batasan Disengaja | Dipindah ke Corporate/Financial mengikuti segregation of duties — bukan gap |
| HR | Exit interview / alasan resign | Gap Data Sumber | `employees.status` hanya status akhir, tanpa tanggal/alasan |
| HR | Training/sertifikasi karyawan | Gap Data Sumber | Tidak ada tabel ini di skema manapun |
| Corporate/Financial | Breakdown komponen cost dari domain lain (food cost, maintenance cost, dst) | Batasan Disengaja | `departmental_expense` sudah agregat jadi; breakdown detail tetap tanggung jawab domain analyst masing-masing |
| Corporate/Financial | GOP/financial granularitas mingguan atau harian | Gap Data Sumber | `financial_summary` granularitas bulanan saja |
| Corporate/Financial | Cost of capital, depresiasi, komponen finansial non-operasional | Gap Data Sumber | Tidak ada kolom ini di skema manapun — konsisten dengan struktur USALI yang berhenti di GOP |

**Ringkasan kuantitatif seluruh dokumen:** 94 baris metrik/kebutuhan terkonsolidasi lintas 6 domain — 77 Cakupan Awal, 1 Cakupan Khusus (pace booking; ditambah 2 pola khusus lain yang tetap berstatus Cakupan Awal tapi butuh perlakuan desain — lihat kategori B dan C di atas), 16 Luar Cakupan (10 Gap Data Sumber murni, 3 Batasan Disengaja struktural, sisanya kombinasi kemampuan terbatas).
