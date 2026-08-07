# Rancangan Implementasi — Monitoring Warehouse dan Serving Layer (Fase 2)

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Monitoring & Dashboard — sama dengan Fase 1) |
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` (Bagian 9) |
| **Cakupan fase ini** | Monitoring dari `raw_production` (BigQuery) sampai serving layer (PostgreSQL) — seluruh proses transformasi, reverse ETL, dan konsumsi |
| **Prinsip monitoring fase ini** | (1) Melihat apa yang terjadi — log proses; (2) Mendeteksi kesalahan/anomali; (3) Memantau performa query, terutama query dari AI Chatbot |
| **Tidak termasuk** | Monitoring sisi database production sebelum masuk `raw_production` — itu cakupan Fase 1 (`01-monitoring-data-production-fase1.md`, sudah selesai dikerjakan sebelumnya) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Sama seperti Fase 1: berisi **milestone**, bukan task list atomic. Urutan di bawah adalah urutan yang disarankan, bukan urutan kaku — temuan di satu milestone wajar memengaruhi milestone sesudahnya.

Rujuk Bagian 9 `rancangan-arsitektur-data-platform-elt.md` (lima pilar monitoring, orkestrasi end-to-end, performance optimization, deteksi perubahan data) untuk detail konseptual — dokumen ini tidak mengutip ulang seluruh isinya.

---

## Konteks: Apa yang Sudah Berjalan Saat Fase Ini Dimulai

Berbeda dari Fase 1 (yang dimulai dari nol), Fase 2 dimulai setelah beberapa bagian pipeline sudah dibangun oleh pekerjaan lain:

- **Orang 2**: extraction production → `raw_production` → transform s/d `mart_cleaned` → reverse ETL `mart_cleaned` → API Data Scientist
- **Orang 5**: transform `mart_cleaned` → `mart_aggregated` (+ join `ml_output`) → reverse ETL `mart_aggregated`
- **Orang 3**: view/API konsumsi Data Analyst di atas `mart_aggregated` dan `mart_cleaned` di PostgreSQL
- **Orang 4**: view/API/kredensial konsumsi AI Chatbot di atas `mart_aggregated` di PostgreSQL, termasuk **audit log query chatbot** (Milestone 4.5 di `05-serving-ai-chatbot.md`) yang menjadi salah satu masukan penting bagi fase ini

Pekerjaan monitoring ini **mengamati** seluruh rangkaian di atas — bukan membangunnya. Titik mulai pengamatan adalah `raw_production`, konsisten dengan batas serah terima dari Fase 1.

Alur yang perlu dipantau, mengikuti urutan orkestrasi end-to-end dari dokumen arsitektur:
1. Sinkronisasi ekstraksi (production → `raw_production`)
2. Transformasi: staging → intermediate → `mart_cleaned`
3. Pengujian data: validasi `mart_cleaned`
4. Trigger scoring job eksternal (pipeline Data Scientist)
5. Sensor: menunggu `ml_output` selesai ditulis
6. Transformasi: `mart_aggregated` (join ke `ml_output`)
7. Pengujian data: validasi `mart_aggregated`
8. Reverse ETL: `mart_aggregated` → PostgreSQL
9. Reverse ETL: `mart_cleaned` → PostgreSQL
10. Post-sync validation (row count parity check)
11. Konsumsi oleh Data Analyst dan AI Chatbot di PostgreSQL

---

## Milestone 6.1 — Inventarisasi Titik Pengamatan dan Baseline Pipeline

### Lingkup
Memetakan seluruh titik dalam alur 10 langkah di atas yang perlu diamati, beserta bentuk sinyal yang tersedia di tiap titik (log job orkestrator, hasil pengujian data, metrik row count, dsb). Termasuk memahami dependency antar langkah (langkah mana menunggu langkah lain) sebagai dasar menentukan bagaimana kegagalan di satu titik seharusnya terlihat kaitannya dengan titik lain. Pekerjaan ini **mengamati** instance orchestrator yang fondasinya sudah di-setup di Milestone 2.0 (`02-serving-data-scientist.md`) dan diperluas di Milestone 5.4 (`03-mart-aggregated-owner.md`) — bukan membangun mekanisme penjadwalan terpisah.

### Kenapa Ini Jadi Milestone Terpisah
Sama seperti Fase 1, membangun monitoring tanpa pemahaman menyeluruh atas apa yang diamati menghasilkan alert yang tidak bisa dipercaya. Pekerjaan ini murni observasional, aman dihentikan sewaktu-waktu.

### Output
- Peta 10 titik pengamatan dengan sinyal yang tersedia di masing-masing, dan dependency-nya satu sama lain.
- Klasifikasi prioritas per titik (mis. kegagalan di titik 2 berdampak ke seluruh downstream, sementara kegagalan di titik 4/5 sudah dirancang untuk tidak menjatuhkan seluruh `mart_aggregated` — lihat catatan di `03-mart-aggregated-owner.md` Milestone 5.4).

### Kriteria Keberhasilan
- Setiap 10 titik pengamatan punya sumber sinyal yang jelas dan bisa dirujuk langsung oleh milestone berikutnya.
- Dependency antar titik terdokumentasi sehingga saat menyusun alerting nanti, satu kegagalan akar tidak memicu banjir alert yang membingungkan dari titik-titik downstream-nya.

---

## Milestone 6.2 — Monitoring Log Proses Pipeline

### Lingkup
Membangun kemampuan untuk **melihat apa yang terjadi** di sepanjang pipeline — status tiap job (berjalan/berhasil/gagal), durasi eksekusi, dan riwayat historisnya. Ini prinsip monitoring pertama yang diminta secara eksplisit untuk fase ini: bukan hanya tahu ada masalah, tapi bisa menelusuri proses apa yang sedang/sudah terjadi di setiap tahap.

### Kenapa Ini Jadi Milestone Terpisah
Ini kapabilitas paling dasar untuk fase ini — sebelum bisa bicara soal error/anomali atau performa, tim harus lebih dulu punya visibilitas dasar atas jalannya proses itu sendiri. Independen dari Milestone 6.3 dan 6.4, bisa dikerjakan lebih dulu.

### Output
- Mekanisme pencatatan status dan durasi tiap job/tahap dalam pipeline (10 titik dari Milestone 6.1).
- Kemampuan menelusuri riwayat eksekusi (kapan suatu tahap terakhir berjalan, berapa lama, apa hasilnya) tanpa perlu masuk ke sistem orkestrator secara manual.

### Kriteria Keberhasilan
- Untuk setiap titik pengamatan, tim bisa menjawab "apakah tahap ini sudah berjalan hari ini, kapan, dan berapa lama" tanpa query manual ke log mentah.
- Riwayat eksekusi tersimpan cukup lama untuk keperluan investigasi tren (bukan hanya snapshot hari ini).

---

## Milestone 6.3 — Monitoring Kesalahan dan Anomali di Pipeline Warehouse

### Lingkup
Membangun deteksi untuk tiga jenis kejadian yang berbeda sifat: kegagalan job (pipeline health), penyimpangan kualitas/nilai data di tiap layer transformasi (`mart_cleaned`, `mart_aggregated`), dan volume/row count yang tidak wajar dibanding baseline historis — termasuk validasi row count parity antara BigQuery dan PostgreSQL pasca-reverse ETL. Termasuk juga memantau hasil pengujian data (data quality gate) yang sudah dipasang oleh Orang 2 dan Orang 5 di titik transformasi masing-masing — pekerjaan ini mengonsolidasikan hasilnya menjadi satu pandangan, bukan membangun ulang pengujiannya. Secara khusus, **freshness check untuk `ml_output`** perlu jadi titik pengamatan eksplisit — ini satu-satunya sumber data yang diproduksi pihak eksternal (pipeline scoring tim Data Scientist) di tengah pipeline internal, sehingga risiko "terlambat tanpa diketahui" lebih tinggi dibanding titik lain yang seluruhnya dikendalikan tim data engineering sendiri.

### Kenapa Ini Jadi Milestone Terpisah
Berbeda sifat dari Milestone 6.2 — ini bicara soal **kebenaran dan kewajaran**, bukan sekadar status jalan/gagal. Butuh baseline historis sebagai rujukan, serupa prinsipnya dengan Fase 1, hanya sekarang diterapkan di titik warehouse dan serving, bukan production.

### Output
- Konsolidasi hasil data quality gate dari `mart_cleaned` dan `mart_aggregated` ke satu pandangan yang bisa dipantau.
- Mekanisme volume/row count anomaly dengan baseline rolling, di tiap tahap transformasi dan pasca-reverse ETL.
- Row count parity check antara BigQuery dan PostgreSQL, dikonsolidasikan sebagai bagian monitoring (bukan sekadar log terpisah).
- Freshness check khusus `ml_output` — kapan terakhir ditulis, dan apakah sensor (Milestone 5.4 di `03-mart-aggregated-owner.md`) menunggu lebih lama dari wajar.

### Kriteria Keberhasilan
- Kegagalan pengujian data pada `mart_cleaned` atau `mart_aggregated` (uji coba terkontrol) terlihat di monitoring tanpa perlu membuka log mentah proses transformasi.
- Penyimpangan volume buatan (uji coba terkontrol) pada salah satu tahap berhasil terdeteksi dan bisa dibedakan dari tahap mana asalnya.
- Ketidakcocokan row count antara BigQuery dan PostgreSQL (uji coba terkontrol) terdeteksi dan teridentifikasi tabel mana yang bermasalah.
- Keterlambatan `ml_output` (uji coba terkontrol, mis. simulasi scoring job eksternal yang telat) terdeteksi sebagai freshness issue, bukan hanya terlihat belakangan sebagai kegagalan sensor yang sulit ditelusuri sebabnya.

---

## Milestone 6.4 — Monitoring Data Drift Feedback Loop ML

### Lingkup
Memantau kesehatan feedback loop ML sesuai prinsip yang sudah ditetapkan di dokumen arsitektur: model staleness (seberapa lama sejak `model_version` terakhir retrain), validasi kelengkapan `ml_output` (jumlah baris dibanding jumlah entity di `mart_cleaned`, untuk mendeteksi entity yang gagal ter-score), dan pemantauan tren feature/prediction drift yang datanya diekspos oleh pipeline scoring tim Data Scientist (bukan dihitung ulang oleh pekerjaan ini, tapi dipantau trennya melalui dashboard yang sama).

### Kenapa Ini Jadi Milestone Terpisah
Sifatnya berbeda dari monitoring pipeline pada umumnya — mengamati siklus yang melibatkan sistem eksternal (training/scoring di luar warehouse) dan menyentuh kepercayaan (*trust*) jawaban yang akhirnya sampai ke AI Chatbot. Independen dari Milestone 6.2/6.3, meski secara konseptual saling melengkapi.

### Output
- Mekanisme pemantauan model staleness per `model_version`.
- Validasi kelengkapan `ml_output` terhadap populasi entity di `mart_cleaned`.
- Dashboard/tampilan tren feature drift dan prediction drift, bersumber dari data yang diekspos pipeline scoring (mis. tabel `ml_monitoring.feature_drift` atau setara).

### Kriteria Keberhasilan
- Tim bisa melihat kapan model terakhir di-retrain untuk tiap `model_version` yang aktif tanpa bertanya langsung ke tim Data Scientist.
- Entity yang gagal ter-score (ada di `mart_cleaned` tapi tidak muncul di `ml_output`) teridentifikasi otomatis.
- Tren drift (jika data drift sudah diekspos oleh pipeline scoring) tervisualisasi dan bisa dipantau dari waktu ke waktu.

> **Catatan ketergantungan**: threshold "signifikan" untuk feature/prediction drift, dan bentuk konkret tabel drift itu sendiri, bergantung pada kesepakatan dengan tim Data Scientist (ditandai sebagai area validasi terbuka di dokumen arsitektur induk). Milestone ini menyediakan kapasitas pemantauan begitu data drift tersedia — bukan menentukan threshold-nya, karena itu bukan wewenang pekerjaan data engineering.

---

## Milestone 6.5 — Monitoring Performa Query AI Chatbot

### Lingkup
Membangun pemantauan performa query yang dijalankan AI Chatbot terhadap PostgreSQL — ini prinsip monitoring ketiga yang diminta secara eksplisit untuk fase ini, dengan penekanan khusus pada AI Chatbot karena karakteristik query-nya (banyak, kecil, sering, butuh respons cepat) paling sensitif terhadap masalah performa dibanding konsumen lain. Memanfaatkan audit log query chatbot yang sudah dibangun Orang 4 (Milestone 4.5 di `05-serving-ai-chatbot.md`) sebagai salah satu sumber data, dikombinasikan dengan metrik performa PostgreSQL langsung (`pg_stat_statements`, latency, connection pool usage).

### Kenapa Ini Jadi Milestone Terpisah
Ini kapabilitas paling spesifik diminta secara eksplisit di antara seluruh cakupan Fase 2 — layak berdiri sendiri agar kedalamannya tidak tenggelam di antara monitoring pipeline warehouse yang lebih umum. Bergantung pada audit log dari Orang 4 sudah tersedia, sehingga wajar dikerjakan setelah pekerjaan itu selesai (atau setidaknya stabil).

### Output
- Dashboard performa query chatbot: latency (p50/p95/p99), volume query per satuan waktu, query yang gagal/ditolak (dari audit log Orang 4), dan query paling lambat/paling sering.
- Pemantauan `pg_stat_statements` dan `EXPLAIN ANALYZE` berkala terhadap pola query representatif chatbot.
- Pemantauan connection pool usage di depan PostgreSQL.

### Kriteria Keberhasilan
- Tim bisa melihat latency end-to-end (dari prompt pengguna hingga jawaban tersaji, sejauh data ini tersedia dari audit log) dan mengidentifikasi query paling lambat tanpa investigasi manual ke `pg_stat_statements` langsung.
- Persentase query yang gagal/ditolak (dari audit log Orang 4) terlihat sebagai tren, bukan hanya angka harian sesaat — indikator kualitas semantic layer/RBAC yang perlu diperbaiki bisa terlihat dari tren ini.
- Lonjakan penggunaan connection pool (uji coba terkontrol, mis. simulasi banyak query bersamaan) terdeteksi.

---

## Milestone 6.6 — Monitoring Reverse ETL dan Serving Layer PostgreSQL

### Lingkup
Memantau kesehatan PostgreSQL sebagai serving layer secara umum (di luar spesifik chatbot) — storage growth, table bloat/status vacuum, dan kesehatan proses `full refresh + swap table` yang dipakai baik oleh `mart_aggregated` maupun `mart_cleaned`. Termasuk memastikan swap table tidak menyebabkan downtime baca yang tidak disengaja.

### Kenapa Ini Jadi Milestone Terpisah
Berbeda fokus dari Milestone 6.5 (yang spesifik ke pola akses chatbot) — ini soal kesehatan infrastruktur serving layer secara keseluruhan, relevan untuk seluruh konsumen (Data Analyst maupun AI Chatbot), bukan hanya satu pihak.

### Output
- Pemantauan storage growth dan table bloat/status vacuum PostgreSQL.
- Pemantauan kesehatan proses swap table pasca-reverse ETL (durasi, keberhasilan, dampak ke query yang sedang berjalan).

### Kriteria Keberhasilan
- Tim bisa melihat tren pertumbuhan storage dan kondisi vacuum tanpa perlu login manual ke PostgreSQL setiap kali.
- Proses swap table (uji coba terkontrol) yang berjalan lambat atau gagal terdeteksi dan dibedakan dari masalah query biasa.

---

## Milestone 6.7 — Dashboard dan Alerting Terpadu (Fase 2)

### Lingkup
Menyatukan hasil Milestone 6.2–6.6 ke dalam satu tampilan yang mencerminkan kesehatan pipeline warehouse-hingga-serving secara keseluruhan, beserta jalur alerting yang jelas — termasuk mempertimbangkan cara menyajikan dependency antar titik (dari Milestone 6.1) supaya satu akar masalah tidak muncul sebagai banjir alert yang terpisah-pisah dan membingungkan.

### Kenapa Ini Jadi Milestone Terpisah
Sama seperti Fase 1: murni pekerjaan konsolidasi dan presentasi, sengaja diletakkan terakhir karena baru bisa dikerjakan dengan baik setelah komponen individualnya menghasilkan data yang bisa ditampilkan.

### Output
- Dashboard tunggal yang mencerminakan kesehatan pipeline dari `raw_production` hingga serving layer, termasuk performa query chatbot.
- Konfigurasi alerting dengan tujuan/kanal yang jelas per jenis kejadian, mempertimbangkan dependency antar titik agar tidak menghasilkan alert berlebihan untuk satu akar masalah.

### Kriteria Keberhasilan
- Dashboard mencerminkan kondisi terkini seluruh pipeline dan dapat diakses tim.
- Simulasi kegagalan di satu titik akar (uji coba terkontrol) menghasilkan alert yang jelas menunjukkan titik akar tersebut, bukan alert terpisah dari setiap tahap downstream yang ikut terdampak.

---

## Catatan Penutup: Hubungan dengan Fase 1

Fase 1 dan Fase 2 dikerjakan oleh orang yang sama, dan meskipun scope-nya terpisah tegas (production vs warehouse-serving), pola dirty data dan karakteristik anomali yang sudah dikenali di Fase 1 (lihat `01-monitoring-data-production-fase1.md`) tetap relevan sebagai konteks di sini — gejala masalah yang berasal dari sisi production kerap baru terlihat dampaknya di layer warehouse maupun serving. Disarankan kedua dashboard (Fase 1 dan Fase 2) dapat saling dirujuk, meski tetap sebagai dua tampilan terpisah sesuai cakupan masing-masing.
