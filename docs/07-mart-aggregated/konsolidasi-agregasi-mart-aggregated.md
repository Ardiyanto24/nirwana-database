# Konsolidasi dan Rasionalisasi Kebutuhan Agregasi — `mart_aggregated`

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 5.1 (`milestones/5.1-konsolidasi-rasionalisasi-kebutuhan-agregasi/`) |
| **Dokumen sumber** | `docs/02-requirements/pemetaan-kebutuhan-data-analyst.md` (6 pola domain), `pemetaan-kebutuhan-chatbot-layer-staff.md` (7 persona), `-manager.md` (8 persona), `-korporat.md` (5 persona) |
| **Dipakai oleh** | Milestone 5.2 (`docs/03-implementation-plans/03-mart-aggregated-owner.md`) — desain skema tabel `mart_aggregated` |
| **Status** | Draft — dibangun bertahap per checkpoint Milestone 5.1 |

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

*(diisi Fase 2 — Task 4)*

---

## 4. Spa & Event

*(diisi Fase 2 — Task 5)*

---

## 5. HR

*(diisi Fase 3 — Task 6)*

---

## 6. Corporate/Financial

*(diisi Fase 3 — Task 7)*

---

## Kebutuhan Khusus (Cakupan Khusus, Lintas Domain)

*(diisi Fase 4 — Task 8)*

---

## Eksplisit Luar Cakupan

*(diisi Fase 4 — Task 8)*
