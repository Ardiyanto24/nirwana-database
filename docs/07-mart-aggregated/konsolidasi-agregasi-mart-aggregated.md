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

*(diisi Fase 1 — Task 2)*

---

## 2. F&B

*(diisi Fase 1 — Task 3)*

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
