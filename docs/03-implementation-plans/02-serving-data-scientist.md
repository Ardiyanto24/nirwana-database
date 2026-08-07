# Rancangan Implementasi — Serving Data Scientist

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Data Scientist Serving) |
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` (Bagian 4, 5.1, 5.2, 7) |
| **Dokumen rujukan kebutuhan** | `pemetaan-kebutuhan-konsumen-data-mart.md` (kebutuhan Data Scientist, dasar skema `mart_cleaned`) |
| **Cakupan pekerjaan** | Setup fondasi orchestrator bersama → extract production → `raw_production` → transform s/d `mart_cleaned` (BigQuery) → reverse ETL `mart_cleaned` → PostgreSQL → API akses untuk Data Scientist |
| **Tidak termasuk** | `mart_aggregated` (transform, join `ml_output`, reverse ETL-nya) — itu tanggung jawab terpisah (lihat dokumen `03-mart-aggregated-owner.md`), meski `mart_cleaned` yang dibangun di sini menjadi **fondasi** bagi pekerjaan tersebut |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Sama seperti dokumen rancangan implementasi lain di project ini: berisi **milestone**, bukan task list atomic. Tiap milestone adalah satu lingkup kerja koheren, punya output dan kriteria keberhasilan yang jelas, dan aman dihentikan sementara tanpa merusak bagian lain. Urutan di bawah adalah urutan yang disarankan (mengikuti dependency data), bukan urutan kaku — temuan di satu milestone (misalnya karakteristik data yang ternyata berbeda dari dokumentasi, atau volume yang lebih besar dari perkiraan) wajar mengubah detail milestone sesudahnya.

Rujuk `pemetaan-kebutuhan-konsumen-data-mart.md` untuk detail lengkap 23 tabel dan aturan cleaning per tabel — dokumen ini tidak mengutip ulang seluruh isinya, hanya merujuk pada prinsip-prinsip kunci yang memengaruhi urutan dan pendekatan kerja.

---

## Konteks dan Prinsip Kunci yang Perlu Dipegang

Beberapa keputusan desain dari dokumen kebutuhan sudah final dan **membatasi** bagaimana pekerjaan ini dilakukan — bukan pilihan bebas milik pemilik pekerjaan:

- **Cleaning-only, tanpa feature engineering.** `mart_cleaned` hanya membersihkan format (dedup, null handling, type cast, normalisasi format). Tidak ada kolom turunan hasil kalkulasi apa pun — feature engineering sepenuhnya di luar cakupan platform ini.
- **1:1 dengan tabel sumber.** 23 tabel production → 23 tabel `mart_cleaned`, tidak digabung lintas domain, tidak dipecah ulang, apa pun granularitas aslinya (termasuk tabel pre-aggregated seperti `daily_occupancy` dan `financial_summary`, yang tetap dipertahankan utuh sebagai fitur time-series).
- **Missing value bermakna dipertahankan** (mis. `guest_id` kosong untuk walk-in), **dirty data yang sengaja disuntikkan juga dipertahankan** (mis. 367 baris duplicate di `guests`, typo nama, format telepon tidak konsisten) — keputusan dedup/koreksi lebih lanjut sengaja diserahkan ke eksperimen Data Scientist sendiri, bukan keputusan platform ini. Ini pengecualian eksplisit terhadap prinsip "dedup" yang umumnya melekat pada definisi cleaning.
- **Full history, tanpa windowing** — konsisten dengan strategi reverse ETL full sync.
- **Lokasi cleaning ada di Layer Staging**, bukan di Layer Marts — `mart_cleaned` secara teknis hanya meneruskan hasil staging.
- **Implikasi keamanan tinggi**: `mart_cleaned` menyertakan data sensitif penuh (PII di `guests`/`employees`, seluruh data `payroll`) karena Data Scientist butuh akses granular penuh untuk fitur model (mis. model turnover). Ini menjadikan isolasi akses di titik ini kritis, bukan opsional.

---

## Catatan Kepemilikan: Fondasi Orchestrator Bersama

Dokumen arsitektur (Bagian 9.1) menyatakan seluruh pipeline — dari ekstraksi sampai reverse ETL, 10 langkah — diatur oleh **satu orchestrator** dengan dependency eksplisit antar tahap. Orchestrator ini adalah infrastruktur bersama yang akan dipakai juga oleh pemilik `mart_aggregated` (`03-mart-aggregated-owner.md`) dan disinggahi pekerjaan monitoring (`06-monitoring-warehouse-serving-fase2.md`) — bukan sesuatu yang eksklusif milik pekerjaan ini.

Karena pekerjaan ini adalah titik **paling awal** dalam pipeline (ekstraksi harus "berjalan terjadwal" sebelum apa pun yang lain bisa mulai), pemilik pekerjaan ini paling masuk akal untuk **men-setup platform orchestrator-nya** — bukan mendefinisikan seluruh 10 langkah dependency dari awal (langkah 4-9 belum ada saat pekerjaan ini dimulai), tapi menyediakan fondasi yang bisa **diperluas** pemilik pekerjaan berikutnya dengan menambahkan job mereka sendiri ke instance yang sama. Lihat Milestone 2.0 di bawah.

---

## Milestone 2.0 — Fondasi Orchestrator Bersama

### Lingkup
Men-setup platform orchestrator yang akan dipakai bersama sepanjang pipeline — instalasi/provisioning tool, konvensi penamaan job dan dependency, mekanisme dasar penjadwalan, serta akses yang diperlukan pemilik pekerjaan lain (Orang 5, dan pekerjaan monitoring) untuk menambahkan job mereka sendiri ke instance yang sama di kemudian hari. Tidak mencakup mendefinisikan seluruh 10 langkah dependency dari dokumen arsitektur — hanya langkah yang relevan dengan pekerjaan ini (ekstraksi, transformasi s/d `mart_cleaned`, reverse ETL `mart_cleaned`); langkah-langkah berikutnya (scoring, join `ml_output`, transformasi `mart_aggregated`, reverse ETL-nya) ditambahkan oleh pemilik pekerjaan tersebut sebagai perluasan, bukan dibangun ulang di sini.

### Kenapa Ini Jadi Milestone Terpisah
Ini prasyarat murni infrastruktur yang harus ada sebelum Milestone 2.1 pun bisa "berjalan terjadwal" — dipisah secara eksplisit dari Milestone 2.1 (yang fokus ke logic ekstraksi) agar keputusan platform (tool apa, bagaimana konvensi job) tidak tercampur dengan keputusan konten pipeline itu sendiri.

### Output
- Platform orchestrator terpasang dan bisa menjalankan job terjadwal.
- Konvensi penamaan job dan dependency yang terdokumentasi, sebagai acuan bagi pemilik pekerjaan lain saat menambahkan job mereka.
- Mekanisme akses bagi pemilik pekerjaan lain (Orang 5, pekerjaan monitoring) untuk menambahkan/melihat job di instance yang sama.

### Kriteria Keberhasilan
- Job percobaan sederhana berhasil dijadwalkan dan dijalankan melalui platform ini.
- Pemilik pekerjaan lain (diverifikasi lewat uji coba akses) bisa menambahkan job baru ke instance yang sama tanpa perlu membangun instance terpisah.

---

## Milestone 2.1 — Extraction Production ke Raw Warehouse

### Lingkup
Membangun jalur ekstraksi dari 6 database production ke `raw_production` di BigQuery untuk seluruh 23 tabel, menggunakan strategi incremental sync dari read replica (bukan primary), dengan skema raw yang identik 1:1 dengan sumbernya (tanpa transformasi bisnis apa pun di titik ini). Termasuk konfigurasi teknis di sisi production yang menjadi prasyarat: aktivasi kemampuan CDC/incremental yang sesuai (mis. `wal_level=logical` untuk PostgreSQL, atau binlog format `ROW` untuk MySQL), dan pembuatan user replikasi dengan **privilese terbatas serta whitelist tabel eksplisit** — sinkronisasi tidak dilakukan membabi buta ke seluruh tabel, terutama yang memuat PII.

### Kenapa Ini Jadi Milestone Terpisah
Ini fondasi paling dasar — seluruh pekerjaan berikutnya bergantung pada data yang sudah landing di `raw_production`. Sifatnya independen dari milestone transform, sehingga bisa diuji dan divalidasi tuntas sebelum lanjut ke layer berikutnya. Konfigurasi teknis production disatukan di sini (bukan dipisah) karena keduanya adalah prasyarat yang tidak berguna sendiri-sendiri — user replikasi tanpa whitelist yang benar sama berisikonya dengan tidak ada ekstraksi sama sekali.

### Output
- Jalur ekstraksi berjalan untuk 23 tabel dari 6 database production ke `raw_production`.
- Skema raw 1:1 dengan sumber, dilengkapi metadata kolom (mis. waktu sinkronisasi).
- Partitioning pada tabel raw sesuai kolom tanggal yang relevan.
- User replikasi dengan privilese terbatas dan whitelist tabel eksplisit, terkonfigurasi dan terdokumentasi.

### Kriteria Keberhasilan
- Seluruh 23 tabel berhasil tersinkronisasi ke `raw_production` dengan jumlah baris yang cocok dengan sumber pada snapshot yang sama.
- Sinkronisasi berjalan terjadwal secara incremental tanpa membebani database primary (tervalidasi lewat read replica).
- User replikasi terbukti **tidak bisa** mengakses tabel di luar whitelist saat diuji coba — bukan diasumsikan aman karena "hanya tabel yang di-sync yang dipakai".

---

## Milestone 2.2 — Layer Staging: Cleaning per Tabel

### Lingkup
Membangun transformasi staging untuk seluruh 23 tabel, menerapkan aturan cleaning spesifik per tabel sesuai pemetaan di `pemetaan-kebutuhan-konsumen-data-mart.md` — mencakup normalisasi format (telepon, kapitalisasi, tanggal), trim whitespace, type casting, sambil secara sadar **mempertahankan** missing value bermakna dan dirty data yang disengaja sesuai daftar pengecualian yang sudah ditentukan.

### Kenapa Ini Jadi Milestone Terpisah
Ini titik paling rawan kesalahan interpretasi — cleaning yang berlebihan (misalnya ikut memperbaiki typo nama atau men-dedup `guests`) akan bertentangan langsung dengan kebutuhan Data Scientist yang sudah dipetakan. Memisahkannya sebagai milestone sendiri memungkinkan validasi ketat sebelum data ini menjadi fondasi `mart_cleaned`.

### Output
- Model staging untuk 23 tabel dengan aturan cleaning sesuai tabel per tabel (lihat rujukan dokumen kebutuhan).
- Dokumentasi eksplisit: daftar kolom/tabel yang **sengaja tidak dibersihkan** (typo, duplicate rows, format tidak konsisten yang dipertahankan) agar tidak "diperbaiki" secara tidak sengaja di iterasi berikutnya.

### Kriteria Keberhasilan
- Untuk tabel dengan aturan normalisasi (mis. `employees.department`, `guests.phone`, `guests.nationality`), hasil staging menunjukkan nilai yang sudah dinormalisasi sesuai aturan.
- Untuk kolom/baris yang harus dipertahankan apa adanya (mis. 367 duplicate di `guests`, typo nama, `guest_id` kosong), hasil staging **identik** dengan raw pada kolom/baris tersebut — bukan ikut terkoreksi.
- Tidak ada kolom turunan/fitur hasil kalkulasi yang muncul di layer ini.

---

## Milestone 2.3 — Layer Intermediate dan Mart Cleaned

### Lingkup
Membangun layer intermediate (jika ada kebutuhan join antar staging yang sifatnya struktural, bukan business logic agregasi) dan menyelesaikan `mart_cleaned` sebagai hasil akhir — 23 tabel `mart_cleaned.<nama_tabel>` yang siap dikonsumsi, beserta data quality gate (pengujian `not_null`, `unique`, `relationships`, `accepted_values`, dan custom business rule) di titik ini sebagai gerbang sebelum data diteruskan. Sesuai panduan materialisasi di dokumen arsitektur (Bagian 9.3.1), `mart_cleaned` dibangun sebagai **tabel dengan refresh incremental** (bukan full refresh) — volumenya besar (row-level, 23 tabel), sehingga hanya baris baru/berubah yang diproses tiap kali refresh, bukan menghitung ulang seluruhnya. Ini keputusan materialisasi **di titik transformasi BigQuery** dan berbeda dari strategi sync `mart_cleaned` ke PostgreSQL di Milestone 2.4 (yang tetap full refresh + swap, karena volume di sisi PostgreSQL masih dalam rentang wajar) — keduanya bukan kontradiksi, hanya dua keputusan terpisah untuk dua titik berbeda.

### Kenapa Ini Jadi Milestone Terpisah
Ini titik penyelesaian `mart_cleaned` sebagai aset yang akan dikonsumsi Data Scientist maupun jadi fondasi `mart_aggregated` (pekerjaan orang lain). Data quality gate perlu berdiri sebagai kontrol eksplisit di sini — data yang tidak lolos pengujian tidak boleh diteruskan.

### Output
- 23 tabel `mart_cleaned` lengkap di BigQuery, full history, dengan strategi refresh incremental (overwrite per partition, bukan merge berbasis pencocokan baris, bila memungkinkan).
- Rangkaian pengujian data quality terpasang dan berjalan sebagai bagian dari proses transformasi.

### Kriteria Keberhasilan
- Seluruh 23 tabel `mart_cleaned` tersedia dan dapat diquery di BigQuery.
- Pengujian data quality berjalan dan hasilnya (lolos/gagal) tercatat serta bisa ditelusuri.
- Percobaan memasukkan data yang melanggar business rule (mis. `revenue < 0`, uji coba terkontrol) berhasil ditangkap oleh gate dan tidak diteruskan ke mart.
- Refresh `mart_cleaned` pada hari dengan sedikit perubahan data terbukti lebih murah/cepat dibanding full refresh (memvalidasi bahwa incremental benar-benar berjalan, bukan diam-diam full scan).

---

## Milestone 2.4 — Reverse ETL Mart Cleaned ke PostgreSQL

### Lingkup
Membangun job reverse ETL yang mendorong seluruh `mart_cleaned` (full history) dari BigQuery ke PostgreSQL sebagai serving layer, menggunakan strategi full refresh dengan swap table, beserta mekanisme validasi pasca-sync (kecocokan jumlah baris antara BigQuery dan PostgreSQL).

### Kenapa Ini Jadi Milestone Terpisah
Ini pekerjaan yang secara alami baru bisa dimulai setelah `mart_cleaned` di BigQuery stabil (Milestone 2.3). Sifatnya berbeda secara teknis (operasi lintas sistem, bukan transformasi SQL murni), sehingga wajar dipisah sebagai satu unit kerja.

### Output
- Job reverse ETL `mart_cleaned` berjalan terjadwal, full refresh + swap table.
- Mekanisme row count parity check otomatis setelah setiap sinkronisasi.

### Kriteria Keberhasilan
- Seluruh 23 tabel `mart_cleaned` tersedia di PostgreSQL dengan jumlah baris yang cocok dengan versi BigQuery pasca-sync.
- Swap table berjalan tanpa downtime yang mengganggu akses berjalan (query yang sedang berlangsung tidak gagal akibat proses swap).

---

## Milestone 2.5 — API Akses Data Scientist

### Lingkup
Menyediakan jalur API bagi Data Scientist untuk mengambil data `mart_cleaned` secara terprogram — perlu diperhatikan bahwa dokumen arsitektur menyatakan Data Scientist **tetap mengakses BigQuery langsung** (bukan PostgreSQL) untuk kebutuhan training karena butuh pemindaian data historis skala besar yang menjadi kekuatan alami BigQuery. Karena itu API ini kemungkinan besar berfungsi sebagai lapisan otentikasi/otorisasi terkontrol di atas akses BigQuery langsung, bukan menduplikasi data ke sistem API terpisah — namun keputusan bentuk teknisnya (BigQuery client langsung dengan kredensial terkontrol vs REST API perantara) perlu dikonfirmasi bersama tim Data Scientist berdasarkan preferensi tooling mereka.

### Kenapa Ini Jadi Milestone Terpisah
Ini titik akhir pekerjaan — antarmuka yang benar-benar dipakai Data Scientist sehari-hari, terpisah dari pekerjaan pipeline data itu sendiri. Baru bisa difinalisasi setelah `mart_cleaned` stabil dan kebutuhan akses konkret (kredensial, kolom sensitif, pola query) dipahami.

### Output
- Mekanisme akses (kredensial/API) yang memungkinkan Data Scientist mengambil data `mart_cleaned` secara terprogram dari BigQuery.
- Dokumentasi cara pakai (autentikasi, contoh query/panggilan) untuk tim Data Scientist.

### Kriteria Keberhasilan
- Tim Data Scientist berhasil mengambil data dari `mart_cleaned` secara terprogram menggunakan mekanisme yang disediakan, tanpa memerlukan akses langsung ke kredensial admin/service account inti.
- Akses yang diberikan bersifat read-only dan terisolasi dari layer raw maupun `mart_aggregated`.

---

## Milestone 2.6 — Isolasi Akses dan Kredensial Read-Only

### Lingkup
Mengonfigurasi service account/kredensial terpisah khusus untuk kebutuhan Data Scientist, dengan prinsip least-privilege: read-only, terbatas ke `mart_cleaned` saja (tidak ke raw, tidak ke `mart_aggregated`, tidak ke dataset lain). Mengingat `mart_cleaned` memuat data sensitif penuh (PII, payroll), isolasi ini bukan langkah opsional.

### Kenapa Ini Jadi Milestone Terpisah
Keamanan akses ke data sensitif layak berdiri sebagai unit kerja eksplisit, bukan menyatu diam-diam ke dalam Milestone 2.5, agar validasinya bisa dilakukan secara sadar dan terdokumentasi — termasuk sebagai bagian dari RBAC lapis kedua (isolasi kredensial di level database) yang menjadi tanggung jawab pemilik infrastruktur data di seluruh sistem ini.

### Output
- Service account/role read-only khusus Data Scientist, terisolasi dari data lain di luar `mart_cleaned`.
- Dokumentasi kebijakan akses (siapa yang boleh menggunakan kredensial ini, batasannya apa).

### Kriteria Keberhasilan
- Kredensial yang diberikan ke Data Scientist terbukti **tidak bisa** mengakses dataset raw maupun `mart_aggregated` saat diuji coba.
- Kredensial terbukti hanya bisa membaca (tidak bisa menulis/mengubah) `mart_cleaned`.

---

## Catatan Serah Terima ke Pekerjaan Lain

`mart_cleaned` yang dihasilkan di sini menjadi **fondasi langsung** bagi pekerjaan pemilik `mart_aggregated` (lihat `03-mart-aggregated-owner.md`), yang akan membangun transformasi lanjutan (agregasi bisnis, join ke `ml_output`) di atas hasil Milestone 2.3. Perubahan pada struktur atau isi `mart_cleaned` di kemudian hari — misalnya penambahan tabel baru dari production, atau perubahan aturan cleaning — perlu dikomunikasikan ke pemilik `mart_aggregated` karena berdampak langsung pada pekerjaannya.

Selain itu, platform orchestrator yang di-setup di Milestone 2.0 menjadi **fondasi bersama** yang akan diperluas oleh pemilik `mart_aggregated` (menambahkan langkah scoring trigger, sensor `ml_output`, transformasi `mart_aggregated`, dan reverse ETL-nya) serta disinggahi pekerjaan monitoring Fase 2 (`06-monitoring-warehouse-serving-fase2.md`) untuk mengamati seluruh job yang berjalan di atasnya. Konvensi penamaan job dan dependency yang didokumentasikan di Milestone 2.0 perlu diikuti konsisten oleh kedua pekerjaan tersebut agar instance orchestrator tetap satu, bukan berpecah menjadi beberapa instance terpisah.
