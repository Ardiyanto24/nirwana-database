# Rancangan Implementasi — Mart Aggregated Owner

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Mart Aggregated) |
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` (Bagian 5.2, 5.2.1, 6, 7) |
| **Dokumen rujukan kebutuhan** | `pemetaan-kebutuhan-data-analyst.md` (6 pola domain Data Analyst), `pemetaan-kebutuhan-chatbot-layer-staff.md`, `pemetaan-kebutuhan-chatbot-layer-manager.md`, `pemetaan-kebutuhan-chatbot-layer-korporat.md` (20 persona AI Chatbot) |
| **Cakupan pekerjaan** | Transform `mart_cleaned` → `mart_aggregated` (BigQuery) → join `ml_output` → reverse ETL `mart_aggregated` → PostgreSQL |
| **Tidak termasuk** | Membangun `mart_cleaned` itu sendiri (sudah selesai dikerjakan sebagai fondasi — lihat `02-serving-data-scientist.md`); lapisan konsumsi spesifik Data Analyst maupun AI Chatbot (view khusus, API, index sesuai pola akses masing-masing — itu tanggung jawab `04-serving-data-analyst.md` dan `05-serving-ai-chatbot.md`) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Sama seperti dokumen lain di project ini: berisi **milestone**, bukan task list atomic. Urutan di bawah adalah urutan yang disarankan, bukan urutan kaku — temuan di satu milestone wajar memengaruhi milestone sesudahnya.

Rujuk `pemetaan-kebutuhan-data-analyst.md` dan ketiga dokumen layer chatbot (Staff/Manager/Korporat) untuk detail lengkap metrik, dimensi, dan gap data per peran — dokumen ini tidak mengutip ulang seluruh isinya.

---

## Kenapa Pekerjaan Ini Dipisah Sebagai Kepemilikan Tersendiri

`mart_aggregated` adalah **aset bersama** — dikonsumsi baik oleh Data Analyst maupun AI Chatbot sekaligus. Kalau definisi agregasinya dibangun terpisah oleh masing-masing tim konsumen, risikonya adalah dua sumber kebenaran untuk metrik yang seharusnya sama (mis. definisi "occupancy rate" yang berbeda antara yang dipakai dashboard analyst dan yang dijawab chatbot). Karena itu satu kepemilikan tunggal memegang **struktur dan isi** `mart_aggregated`, sementara tim konsumen (Data Analyst, AI Chatbot) membangun lapisan tipis di atasnya sesuai kebutuhan akses masing-masing tanpa mendefinisikan ulang agregasi intinya.

Jika suatu saat tim konsumen menemukan kebutuhan agregasi yang belum tercakup, jalurnya adalah **mengajukan** ke pemilik pekerjaan ini — bukan membangun versi sendiri di luar `mart_aggregated`.

---

## Konteks dan Skala Pekerjaan

Cakupan `mart_aggregated` sebelumnya sengaja dikosongkan di dokumen arsitektur induk (Bagian 5.2.1) karena menunggu pemetaan kebutuhan nyata. Pemetaan itu sekarang sudah selesai dan menjadi dasar kerja di sini — mencakup:

- **6 pola domain Data Analyst**: Revenue, F&B, Facility/Ops, Spa & Event (spa dan event dipisah karena karakter data berbeda), HR, Corporate/Financial — masing-masing dengan puluhan metrik siap pakai, dimensi filter, dan grain waktu yang sudah dipetakan.
- **20 persona AI Chatbot** (7 Staff, 8 Manager, 5 Korporat) dengan kebutuhan tanya-jawab yang sudah diverifikasi ke skema aktual dan diaudit prinsip superset-nya (posisi lebih tinggi selalu mencakup akses granular bawahannya).
- Beberapa kebutuhan yang **secara sengaja ditandai bukan agregasi historis biasa** dan butuh perlakuan khusus, misalnya *pace booking* (butuh mekanisme snapshot harian, bukan agregasi dari histori yang sudah terjadi) — ini perlu keputusan desain eksplisit, bukan dipaksakan ke pola agregasi standar.
- Sejumlah kebutuhan yang **tidak tersedia dari data sumber** (sudah ditandai jujur di dokumen kebutuhan, mis. net revenue setelah komisi OTA, target/budget vs actual, exit interview) — tidak perlu diusahakan, cukup dikonfirmasi tetap di luar cakupan.
- **Masking/anonymization PII** — dokumen arsitektur (Bagian 8.3) mensyaratkan data sensitif (PII) yang mungkin ada di `raw_production` tidak diteruskan ke `mart_aggregated` tanpa proses masking/anonymization yang eksplisit. Ini relevan langsung di sini karena beberapa domain granular RBAC chatbot (`guests_pii`, `guests_profile`) menyentuh data personal — perlu keputusan sadar kolom mana yang benar-benar perlu masuk `mart_aggregated` apa adanya, dan mana yang perlu di-mask/dianonimkan terlebih dahulu (lihat Milestone 5.2).

---

## Milestone 5.1 — Konsolidasi dan Rasionalisasi Kebutuhan Agregasi

### Lingkup
Menggabungkan seluruh kebutuhan metrik dari 6 pola domain Data Analyst dan 20 persona AI Chatbot menjadi satu daftar agregasi yang akan dibangun — mengidentifikasi mana yang tumpang tindih (dipakai kedua jenis konsumen, sehingga cukup dibangun sekali), mana yang spesifik hanya untuk satu jenis konsumen, dan menyusun prioritas berdasarkan seberapa sering dibutuhkan lintas peran.

### Kenapa Ini Jadi Milestone Terpisah
Ini pekerjaan analitis murni (belum menyentuh implementasi), tapi krusial dilakukan sebelum menulis satu baris transformasi pun — tanpa konsolidasi ini, risiko membangun metrik yang sama dua kali dengan definisi berbeda, atau melewatkan metrik yang ternyata dibutuhkan banyak peran, sangat tinggi mengingat skala kebutuhan (6 domain analyst + 20 persona chatbot).

### Output
- Daftar konsolidasi metrik/agregasi yang akan dibangun di `mart_aggregated`, dikelompokkan per domain, dengan penanda konsumen mana saja yang membutuhkan tiap metrik.
- Daftar terpisah untuk kebutuhan yang butuh perlakuan khusus (mis. snapshot harian untuk pace booking) beserta rekomendasi pendekatannya.
- Daftar eksplisit kebutuhan yang **tidak** akan dibangun karena keterbatasan data sumber, sebagai referensi agar tidak ditanyakan ulang di kemudian hari.

### Kriteria Keberhasilan
- Setiap metrik siap pakai yang tercantum di dokumen kebutuhan Data Analyst dan ketiga dokumen layer chatbot sudah dipetakan statusnya: masuk cakupan awal, masuk cakupan dengan perlakuan khusus, atau ditandai di luar cakupan dengan alasan.
- Dokumen konsolidasi ini bisa dipakai langsung sebagai acuan kerja Milestone 5.2 tanpa perlu menerka ulang kebutuhan dari dokumen sumber.

---

## Milestone 5.2 — Desain Struktur Tabel Mart Aggregated

### Lingkup
Menentukan struktur tabel `mart_aggregated` (nama tabel, granularitas/grain per tabel, kolom dimensi, kolom metrik, partitioning dan clustering key) berdasarkan hasil konsolidasi Milestone 5.1. Termasuk keputusan desain untuk kasus khusus seperti pace booking (mekanisme snapshot) dan metrik yang butuh join lintas domain (mis. delayed rate housekeeping terkait okupansi, capture rate F&B terhadap populasi tamu menginap). Termasuk juga audit eksplisit kolom PII yang berpotensi masuk ke `mart_aggregated` (terutama pada domain `guests_pii`/`guests_profile` yang dikonsumsi AI Chatbot) dan keputusan sadar mana yang perlu masking/anonymization sebelum diteruskan, sesuai prinsip keamanan di dokumen arsitektur (Bagian 8.3).

### Kenapa Ini Jadi Milestone Terpisah
Ini murni pekerjaan desain skema — dipisah dari implementasi transformasi (Milestone 5.3) agar keputusan struktur bisa direview dan disepakati dulu sebelum ditulis dalam bentuk kode transformasi yang lebih mahal untuk diubah setelah berjalan. Keputusan masking PII disatukan di milestone desain ini (bukan ditunda ke implementasi) karena ini keputusan struktural — kolom yang di-mask berarti tidak pernah ada di skema final, bukan sesuatu yang bisa "ditambahkan belakangan" tanpa mengubah struktur tabel.

### Output
- Skema tabel `mart_aggregated` (nama tabel, grain, kolom) untuk seluruh cakupan hasil Milestone 5.1.
- Keputusan desain terdokumentasi untuk kasus khusus (snapshot, cross-domain join).
- Rencana partitioning dan clustering key per tabel besar.
- Daftar eksplisit kolom PII yang masuk `mart_aggregated` apa adanya vs yang di-mask/dianonimkan, beserta alasannya per kolom.

### Kriteria Keberhasilan
- Skema yang dihasilkan mencakup seluruh metrik prioritas dari Milestone 5.1 tanpa ambiguitas granularitas (setiap tabel punya definisi grain yang jelas: per apa, per periode apa).
- Skema sudah mempertimbangkan filter wajib yang akan dipakai konsumen (mis. `property_id`, `department`, rentang waktu) sebagai kolom yang mudah difilter/di-cluster, bukan tersembunyi di dalam kalkulasi.
- Setiap kolom yang berpotensi PII di `mart_aggregated` punya keputusan eksplisit (diteruskan apa adanya dengan alasan, atau di-mask/dianonimkan dengan metode yang jelas) — tidak ada kolom PII yang masuk skema tanpa keputusan sadar.

---

## Milestone 5.3 — Implementasi Transformasi Mart Aggregated

### Lingkup
Membangun transformasi SQL dari `mart_cleaned` ke `mart_aggregated` sesuai skema hasil Milestone 5.2 — termasuk business logic penuh (agregasi, kalkulasi metrik, join lintas domain), dan data quality gate di titik ini (data yang tidak lolos pengujian tidak diteruskan ke mart).

### Kenapa Ini Jadi Milestone Terpisah
Ini implementasi inti dari seluruh pekerjaan — dipisah dari desain skema agar pekerjaan menulis logic transformasi bisa dilakukan bertahap per domain/kelompok metrik tanpa menunggu seluruh desain 100% final di semua domain sekaligus.

### Output
- Transformasi SQL berjalan untuk seluruh tabel `mart_aggregated` sesuai skema.
- Pengujian data quality (business rule spesifik, mis. filter yang benar untuk baris `Overall` di `financial_summary` agar tidak double-counting) terpasang sebagai bagian dari transformasi.

### Kriteria Keberhasilan
- Seluruh tabel `mart_aggregated` terisi dan dapat diquery di BigQuery, dengan hasil yang tervalidasi cocok terhadap perhitungan manual/sampel dari `mart_cleaned` untuk beberapa metrik kunci.
- Data quality gate berhasil menangkap pelanggaran business rule pada uji coba terkontrol (mis. data yang seharusnya menyebabkan double-counting jika salah filter).
- Kolom yang sudah diputuskan untuk di-mask/dianonimkan pada Milestone 5.2 terbukti benar-benar termask di hasil akhir `mart_aggregated` — bukan diteruskan apa adanya karena terlewat saat implementasi.

---

## Milestone 5.4 — Integrasi Feedback Loop ML (Join ke ml_output)

### Lingkup
Mengimplementasikan join terkontrol dari `ml_output` ke `mart_aggregated` sesuai alur yang sudah ditentukan di dokumen arsitektur (Bagian 6): `mart_cleaned` selesai refresh → trigger scoring eksternal → sensor menunggu `ml_output` selesai ditulis → transformasi `mart_aggregated` (LEFT JOIN ke `ml_output`) → pengujian data final. Termasuk validasi bahwa kolom wajib `model_version` dan `feature_snapshot_at` selalu terisi pada hasil join. Langkah-langkah ini ditambahkan sebagai **perluasan** ke platform orchestrator yang sudah di-setup di Milestone 2.0 (`02-serving-data-scientist.md`) — mengikuti konvensi penamaan job dan dependency yang sudah didokumentasikan di sana, bukan membangun instance orchestrator terpisah.

### Kenapa Ini Jadi Milestone Terpisah
Berbeda sifat dari Milestone 5.3 — ini melibatkan dependency ke proses eksternal (scoring pipeline tim Data Scientist) yang berada di luar kendali langsung pekerjaan ini, sehingga perlu mekanisme sensor/trigger yang jelas, bukan sekadar transformasi SQL biasa. Baru relevan dikerjakan setelah kerangka `mart_aggregated` inti (Milestone 5.3) sudah berjalan.

### Output
- Mekanisme trigger scoring job eksternal dan sensor yang menunggu `ml_output` selesai ditulis, terintegrasi dengan orkestrator pipeline utama.
- Transformasi LEFT JOIN `ml_output` ke `mart_aggregated` final, dengan validasi kelengkapan `model_version` dan `feature_snapshot_at`.

### Kriteria Keberhasilan
- Simulasi siklus penuh (mart_cleaned refresh → trigger → sensor → join → mart_aggregated final) berhasil berjalan end-to-end tanpa intervensi manual.
- Baris hasil prediksi yang muncul di `mart_aggregated` selalu punya `model_version` dan `feature_snapshot_at` terisi — tidak ada baris ML yang tidak bisa ditelusuri asalnya.
- Jika `ml_output` gagal/telat ditulis, `mart_aggregated` tidak ikut gagal total — bagian non-ML tetap bisa ter-refresh (perlu dipastikan kegagalan feedback loop tidak menghambat seluruh mart).

---

## Milestone 5.5 — Reverse ETL Mart Aggregated ke PostgreSQL

### Lingkup
Membangun job reverse ETL yang mendorong seluruh `mart_aggregated` (full history) dari BigQuery ke PostgreSQL, menggunakan strategi full refresh dengan swap table, beserta validasi pasca-sync (row count parity check). Termasuk memastikan index di PostgreSQL (yang dibangun konsumen di atas tabel ini — lihat `04-serving-data-analyst.md` dan `05-serving-ai-chatbot.md`) tetap valid pasca-swap: karena tabel hasil swap tidak otomatis mewarisi statistik index dari tabel lama, job ini perlu memicu atau menyediakan mekanisme `REINDEX`/`ANALYZE` setiap kali swap terjadi, bukan mengasumsikan index tetap sehat dengan sendirinya.

### Kenapa Ini Jadi Milestone Terpisah
Sama seperti pola reverse ETL `mart_cleaned` — ini pekerjaan lintas sistem yang baru bisa dimulai setelah `mart_aggregated` (termasuk hasil join ML) stabil di BigQuery. Kaitan dengan REINDEX disatukan di sini (bukan di dokumen konsumen) karena swap table adalah proses yang dijalankan pekerjaan ini — pemilik proses yang paling tepat memastikan efek sampingnya (index basi) tertangani, bukan menyerahkannya ke konsumen yang tidak mengendalikan jadwal swap.

### Output
- Job reverse ETL `mart_aggregated` berjalan terjadwal, full refresh + swap table.
- Row count parity check otomatis pasca-sync.
- Mekanisme `REINDEX`/`ANALYZE` terpicu otomatis (atau tersedia sebagai langkah eksplisit) setiap kali swap table selesai.

### Kriteria Keberhasilan
- Seluruh tabel `mart_aggregated` tersedia di PostgreSQL dengan jumlah baris yang cocok dengan versi BigQuery pasca-sync.
- Swap table tidak mengganggu query yang sedang berjalan dari konsumen (Data Analyst maupun AI Chatbot) saat proses sync berlangsung.
- Statistik index pasca-swap terbukti ter-refresh (diverifikasi lewat `EXPLAIN ANALYZE` pada query representatif tidak menunjukkan degradasi performa dibanding sebelum swap).

---

## Milestone 5.6 — Mekanisme Pengajuan Perubahan Cakupan

### Lingkup
Menetapkan alur kerja yang jelas untuk menerima dan menindaklanjuti permintaan penambahan/perubahan agregasi dari tim konsumen (Data Analyst, AI Chatbot) setelah `mart_aggregated` berjalan — mengingat cakupan awal (Milestone 5.1) kemungkinan besar tidak akan menangkap 100% kebutuhan sejak hari pertama, terutama untuk AI Chatbot yang skema kebutuhannya masih ditandai bisa berubah.

### Kenapa Ini Jadi Milestone Terpisah
Ini bukan pekerjaan teknis, tapi pekerjaan proses — perlu eksplisit dibuat agar permintaan perubahan dari tim konsumen punya jalur yang jelas, bukan langsung berujung ke perubahan ad-hoc yang tidak terlacak pada aset bersama.

### Output
- Alur/kesepakatan kerja untuk pengajuan kebutuhan agregasi baru dari tim konsumen ke pemilik pekerjaan ini.
- Kriteria evaluasi sederhana untuk menilai permintaan (mis. apakah datanya tersedia, apakah berdampak ke konsumen lain, prioritas relatif).

### Kriteria Keberhasilan
- Ada jalur yang disepakati bersama (didokumentasikan) yang bisa dipakai tim Data Analyst dan AI Chatbot saat mengajukan kebutuhan agregasi baru.
- Sekurangnya satu siklus pengajuan-evaluasi-tindak lanjut berhasil dilakukan sebagai uji coba jalur ini.

---

## Catatan Serah Terima ke Pekerjaan Lain

`mart_aggregated` yang dihasilkan di sini menjadi fondasi bagi dua pekerjaan konsumen: `04-serving-data-analyst.md` dan `05-serving-ai-chatbot.md`. Kedua pekerjaan tersebut bergantung pada struktur dan isi `mart_aggregated` di PostgreSQL (hasil Milestone 5.5) — perubahan struktur di kemudian hari (penambahan/perubahan tabel, kolom, atau grain) perlu dikomunikasikan ke keduanya karena berdampak langsung pada view, index, dan API yang mereka bangun di atasnya.

Pekerjaan ini juga memperluas platform orchestrator bersama (fondasinya di-setup di Milestone 2.0, `02-serving-data-scientist.md`) dengan menambahkan langkah scoring trigger, sensor `ml_output`, transformasi `mart_aggregated`, dan reverse ETL-nya (Milestone 5.4-5.5) — bukan membangun instance terpisah. Pekerjaan monitoring Fase 2 (`06-monitoring-warehouse-serving-fase2.md`) akan mengamati seluruh langkah ini dari instance orchestrator yang sama.
