# Rancangan Implementasi — Serving Data Analyst

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Data Analyst Serving) |
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` (Bagian 7, 8) |
| **Dokumen rujukan kebutuhan** | `pemetaan-kebutuhan-data-analyst.md` (6 pola domain Data Analyst) |
| **Cakupan pekerjaan** | Lapisan konsumsi di atas `mart_aggregated` dan `mart_cleaned` (keduanya sudah tersedia di PostgreSQL) — view/query per pola peran, index, kredensial, dan multi-endpoint API untuk Data Analyst; termasuk jalur akses BigQuery langsung via BI tool untuk kebutuhan analitis lanjutan yang tidak tersedia di serving layer |
| **Tidak termasuk** | Membangun struktur/isi `mart_aggregated` maupun `mart_cleaned` itu sendiri — keduanya sudah disediakan sebagai aset bersama (lihat `02-serving-data-scientist.md` dan `03-mart-aggregated-owner.md`). Jika ada kebutuhan agregasi baru yang belum tercakup, jalurnya adalah mengajukan ke pemilik `mart_aggregated` (Milestone 5.6), bukan membangun versi sendiri |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Sama seperti dokumen lain di project ini: berisi **milestone**, bukan task list atomic. Urutan di bawah adalah urutan yang disarankan, bukan urutan kaku — temuan di satu milestone wajar memengaruhi milestone sesudahnya.

Rujuk `pemetaan-kebutuhan-data-analyst.md` untuk detail lengkap dimensi, metrik, dan kebutuhan row-level per pola peran — dokumen ini tidak mengutip ulang seluruh isinya.

---

## Konteks: Kenapa Multi-Endpoint, Bukan Satu API Generik

Data Analyst di sistem ini bukan satu peran generik, melainkan **6 pola domain** dengan karakter kebutuhan berbeda-beda:

| # | Peran | Domain fokus | Cakupan properti |
|---|---|---|---|
| 1 | Revenue Analyst | `reservation_revenue` | 5 properti |
| 2 | F&B Analyst | `fnb_operations` | 5 properti |
| 3 | Facility/Ops Analyst | `facility_maintenance` | 5 properti |
| 4 | Spa & Event Analyst | `spa_event` (spa dan event punya karakter berbeda) | 5 properti |
| 5 | HR Analyst | `hr_finance` domain `hr` | 5 properti |
| 6 | Corporate/Financial Analyst | `hr_finance` domain `financial` + konsolidasi lintas semua domain (GOP/USALI) | 5 properti (grup) |

**Property/GM Analyst** (5 orang, satu per properti) tidak dipetakan sebagai pola terpisah — kebutuhannya adalah union dari peran #1–5, dengan filter wajib `property_id` dan tanpa akses `financial_summary` tingkat grup.

Konsekuensinya: satu endpoint generik "ambil semua data" tidak akan cocok untuk kebutuhan siapa pun secara spesifik. Desain API perlu mencerminkan pola akses nyata tiap peran — inilah alasan tugas ini eksplisit diminta menyediakan **beberapa endpoint**, bukan satu endpoint serba guna.

Dua karakter kebutuhan yang perlu diperhatikan sejak awal:
- **Kebutuhan agregat** (dashboard harian/mingguan/bulanan/kuartalan) — dilayani dari `mart_aggregated` di PostgreSQL.
- **Kebutuhan row-level untuk investigasi ad-hoc** (mis. "kenapa cancellation Bali Maret 2024 tinggi", drill-down ke tiket maintenance tertentu, analisis klien event tertentu) — dilayani dari `mart_cleaned` di PostgreSQL, bukan `mart_aggregated`. Kedua kebutuhan ini sama-sama nyata dan sudah eksplisit dipetakan per peran, sehingga pekerjaan ini perlu melayani keduanya, bukan hanya sisi agregat.

Selain dua jalur di atas, dokumen arsitektur (Bagian 2.2 dan 8.1) menyebutkan **jalur ketiga** yang eksplisit menjadi bagian kebutuhan Data Analyst: akses **BigQuery langsung via BI tool**, khusus untuk *"kebutuhan analitis lanjutan yang tidak tersedia di serving layer"* — PostgreSQL menyediakan `mart_cleaned` dan `mart_aggregated` versi penuh, tapi tetap merupakan salinan hasil reverse ETL; ada kelas kebutuhan analitis (mis. eksplorasi ad-hoc yang menyentuh kombinasi tabel/agregasi yang belum tentu terwakili di struktur PostgreSQL, atau kebutuhan yang secara alami lebih murah dijalankan di BigQuery skala besar) yang menurut arsitektur memang tidak dimaksudkan dipenuhi lewat PostgreSQL sama sekali. Jalur ini disediakan sebagai pelengkap, bukan pengganti Milestone 3.1-3.5.

---

## Milestone 3.1 — Pemetaan Pola Akses per Peran Analyst

### Lingkup
Menerjemahkan 6 pola domain dari `pemetaan-kebutuhan-data-analyst.md` menjadi pemetaan konkret: tabel `mart_aggregated`/`mart_cleaned` mana yang relevan untuk peran mana, filter wajib apa yang berlaku (mis. `property_id` untuk Property/GM Analyst, filter `department IN ('Room','F&B','Spa&Event')` untuk menghindari double-counting di `financial_summary`), dan kebutuhan row-level mana yang perlu dijembatani ke `mart_cleaned`.

### Kenapa Ini Jadi Milestone Terpisah
Ini pekerjaan analitis yang jadi dasar seluruh desain endpoint dan view berikutnya — tanpa pemetaan eksplisit, risiko tinggi terjadi kesalahan seperti lupa filter baris `Overall` pada metrik departmental margin (sudah ditandai sebagai risiko nyata di dokumen kebutuhan) atau salah asumsi cakupan properti untuk suatu peran.

### Output
- Tabel pemetaan: peran → tabel sumber (`mart_aggregated`/`mart_cleaned`) → filter wajib → kebutuhan row-level.
- Daftar business rule kritis yang wajib diterapkan di level query/view (mis. filter `department` pada `financial_summary`) agar tidak salah pakai oleh konsumen endpoint.

### Kriteria Keberhasilan
- Setiap 6 pola peran (plus Property/GM Analyst sebagai union) punya pemetaan akses yang jelas dan bisa langsung dipakai sebagai acuan Milestone 3.2 tanpa perlu membuka ulang dokumen kebutuhan dari nol.

---

## Milestone 3.2 — View dan Query Pattern per Domain

### Lingkup
Membangun view/query pattern di atas `mart_aggregated` dan `mart_cleaned` (di PostgreSQL) sesuai hasil pemetaan Milestone 3.1 — satu kelompok view per pola domain (Revenue, F&B, Facility, Spa & Event, HR, Corporate/Financial), dengan filter wajib sudah tertanam supaya konsumen endpoint tidak perlu menerapkannya sendiri secara manual berulang kali.

### Kenapa Ini Jadi Milestone Terpisah
Ini lapisan logis antara mart mentah dan API — dipisah dari Milestone 3.4 (API) agar logic akses dan filter bisa diuji secara independen dari mekanisme HTTP/endpoint-nya.

### Output
- View/query pattern per domain, mencakup kebutuhan agregat maupun row-level sesuai pemetaan.
- Validasi bahwa business rule kritis (mis. filter `Overall` vs departemen) sudah tertanam dan tidak bisa terlewat oleh pemakai view.

### Kriteria Keberhasilan
- Untuk tiap domain, hasil query dari view yang dibangun cocok dengan hasil perhitungan manual/sampel pada beberapa metrik kunci yang representatif.
- Percobaan query tanpa filter eksplisit (mis. lupa filter properti) tetap menghasilkan output yang benar karena filter sudah tertanam di view, bukan bergantung pada pemakai selalu ingat menambahkannya.

---

## Milestone 3.3 — Index dan Optimasi Performa untuk Pola Akses Analyst

### Lingkup
Merancang dan memasang index (termasuk composite index bila diperlukan) di PostgreSQL sesuai pola akses nyata Data Analyst — karakternya berbeda dari AI Chatbot: query Data Analyst cenderung lebih jarang dijalankan tapi lebih berat (agregasi rentang waktu panjang, join lintas tabel untuk laporan bulanan/kuartalan), bukan banyak query kecil dan sering seperti chatbot.

### Kenapa Ini Jadi Milestone Terpisah
Optimasi performa butuh pola query nyata dari Milestone 3.2 sebagai masukan — tidak efektif dikerjakan lebih dulu sebelum tahu bentuk query apa yang benar-benar akan dijalankan.

### Output
- Index dan composite index terpasang pada kolom yang menjadi filter/join utama di view Milestone 3.2.
- Baseline waktu eksekusi untuk query representatif tiap domain, sebagai acuan jika performa menurun di kemudian hari.

### Kriteria Keberhasilan
- Query representatif tiap domain (mis. laporan bulanan Revenue Analyst, laporan kuartalan Corporate/Financial Analyst) berjalan dalam waktu yang wajar untuk kebutuhan analisis interaktif, diverifikasi lewat `EXPLAIN ANALYZE`.
- Index yang dipasang benar-benar terpakai oleh query plan (bukan index yang tidak pernah dipakai).

> **Catatan ketergantungan**: `mart_aggregated` dan `mart_cleaned` di PostgreSQL di-refresh lewat `full refresh + swap table` (dikerjakan pemilik `mart_aggregated`/`mart_cleaned`, lihat Milestone 5.5 di `03-mart-aggregated-owner.md`). Tabel hasil swap tidak otomatis mewarisi statistik index dari tabel lama, sehingga performa index di sini bisa terlihat baik saat pertama dipasang tapi menurun pasca-swap berikutnya jika mekanisme `REINDEX`/`ANALYZE` pasca-swap tidak berjalan konsisten di sisi pemilik mart. Baseline waktu eksekusi di milestone ini sebaiknya diperiksa ulang secara berkala (bukan hanya sekali di awal) untuk mendeteksi degradasi semacam ini.

---

## Milestone 3.4 — Multi-Endpoint API untuk Data Analyst

### Lingkup
Membangun endpoint API terpisah sesuai pola domain (bukan satu endpoint generik) — mencakup endpoint untuk kebutuhan agregat (dashboard harian/mingguan/bulanan/kuartalan) per domain, dan endpoint terpisah untuk kebutuhan row-level/investigasi ad-hoc. Termasuk mekanisme filter dan parameter yang mencerminkan dimensi yang sudah dipetakan (`property_id`, rentang waktu, dsb).

### Kenapa Ini Jadi Milestone Terpisah
Ini titik akhir yang benar-benar dipakai Data Analyst sehari-hari — baru bisa difinalisasi setelah view (Milestone 3.2) dan performanya (Milestone 3.3) stabil.

### Output
- Endpoint API per domain (Revenue, F&B, Facility, Spa & Event, HR, Corporate/Financial), mencakup jalur agregat dan jalur row-level sesuai kebutuhan yang dipetakan.
- Dokumentasi API (parameter, format respons, contoh pemanggilan) untuk tim Data Analyst.

### Kriteria Keberhasilan
- Setiap 6 pola peran (dan Property/GM Analyst sebagai union) bisa mendapatkan data yang relevan dengan perannya lewat endpoint yang sesuai, tanpa perlu mengakses endpoint domain lain di luar cakupannya.
- Endpoint row-level berhasil menjawab skenario investigasi ad-hoc yang representatif (mis. drill-down ke `bookings` granular untuk suatu periode/properti tertentu).

---

## Milestone 3.5 — Isolasi Akses dan Kredensial Read-Only

### Lingkup
Mengonfigurasi kredensial/akses read-only khusus untuk kebutuhan Data Analyst, dengan mempertimbangkan bahwa tidak semua peran analyst punya cakupan akses yang sama (mis. HR Analyst tidak mencakup payroll — itu domain Corporate/Financial Analyst; Property/GM Analyst tidak mencakup `financial_summary` tingkat grup). Isolasi ini memakai mekanisme role read-only yang disediakan oleh pemilik infrastruktur Postgres serving layer (lihat `03-mart-aggregated-owner.md`), dikonfigurasi sesuai kebutuhan spesifik tiap peran analyst.

### Kenapa Ini Jadi Milestone Terpisah
Keamanan akses layak berdiri sebagai unit kerja eksplisit yang divalidasi secara sadar, terutama karena beberapa data yang dikonsumsi analyst (mis. payroll, data personal untuk analisis turnover) cukup sensitif meski levelnya tidak setinggi kebutuhan penuh Data Scientist.

### Output
- Kredensial/role read-only per kelompok peran analyst (atau granularitas yang sesuai kebutuhan riil), dikonfigurasi terpisah dari kredensial Data Scientist maupun AI Chatbot.
- Dokumentasi kebijakan akses per peran.

### Kriteria Keberhasilan
- Kredensial yang diberikan ke suatu peran analyst terbukti **tidak bisa** mengakses data di luar cakupannya saat diuji coba (mis. HR Analyst tidak bisa mengakses `payroll`).
- Seluruh kredensial analyst bersifat read-only, tidak bisa menulis/mengubah data di `mart_aggregated` maupun `mart_cleaned`.

---

## Milestone 3.6 — Akses BigQuery Langsung via BI Tool

### Lingkup
Menyediakan jalur akses BigQuery langsung (bukan lewat PostgreSQL) bagi Data Analyst untuk kebutuhan analitis lanjutan yang tidak tersedia di serving layer — menghubungkan BI tool yang dipakai tim analyst ke BigQuery, dengan kredensial `analyst-readonly` yang di-scope terpisah sesuai prinsip keamanan dokumen arsitektur (Bagian 8.3). Berbeda dari Milestone 3.1–3.5 yang seluruhnya beroperasi di atas data hasil reverse ETL di PostgreSQL, milestone ini membuka jalur ke `mart_cleaned`/`mart_aggregated` versi asli di BigQuery.

### Kenapa Ini Jadi Milestone Terpisah
Sifat teknisnya sepenuhnya berbeda dari milestone lain di dokumen ini — bukan membangun view/API di atas PostgreSQL, melainkan menghubungkan alat eksternal (BI tool) ke sistem lain (BigQuery) dengan kredensial terpisah. Independen dari Milestone 3.1–3.5, bisa dikerjakan kapan saja setelah `mart_cleaned` dan `mart_aggregated` tersedia di BigQuery (tidak perlu menunggu jalur PostgreSQL selesai).

### Output
- Kredensial `analyst-readonly` di BigQuery, read-only, di-scope ke `mart_cleaned` dan `mart_aggregated` saja (tidak ke `raw_production` maupun `ml_output`).
- Koneksi BI tool ke BigQuery menggunakan kredensial tersebut, terdokumentasi cara pakainya untuk tim Data Analyst.

### Kriteria Keberhasilan
- Tim Data Analyst berhasil menjalankan query eksploratif langsung dari BI tool ke `mart_cleaned`/`mart_aggregated` di BigQuery menggunakan kredensial yang disediakan.
- Kredensial `analyst-readonly` terbukti **tidak bisa** mengakses `raw_production` atau `ml_output` saat diuji coba.
- Kredensial terbukti hanya bisa membaca (tidak bisa menulis/mengubah) data di BigQuery.

---

## Catatan Serah Terima

Pekerjaan ini bergantung penuh pada `mart_aggregated` dan `mart_cleaned` yang disediakan pemilik pekerjaan di `03-mart-aggregated-owner.md` dan `02-serving-data-scientist.md`, baik versi PostgreSQL (Milestone 3.1–3.5) maupun versi BigQuery asli (Milestone 3.6). Jika dalam proses Milestone 3.1–3.2 ditemukan kebutuhan agregasi yang ternyata belum tercakup di `mart_aggregated`, jalur yang benar adalah mengajukan lewat mekanisme yang sudah ditetapkan di Milestone 5.6 (`03-mart-aggregated-owner.md`) — bukan membangun agregasi versi sendiri di layer ini, untuk menjaga `mart_aggregated` tetap menjadi satu sumber kebenaran yang konsisten dengan yang dikonsumsi AI Chatbot.
