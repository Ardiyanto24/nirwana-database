# Rancangan Implementasi — Monitoring Data Production (Fase 1)

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Monitoring & Dashboard) |
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` (Bagian 9) |
| **Cakupan fase ini** | Monitoring sisi **database production** (PostgreSQL/MySQL, 6 database logis, 23 tabel) — **sebelum** data menyentuh `raw_production` di BigQuery |
| **Tidak termasuk** | Titik landing `raw_production` di BigQuery dan seterusnya — itu cakupan Fase 2 (dokumen terpisah, dikerjakan belakangan oleh orang yang sama) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Dokumen ini berisi **milestone**, bukan task list atomic. Setiap milestone:
- Mencakup satu lingkup kerja yang koheren (bukan satu tugas kecil)
- Jika dihentikan/pause di tengah jalan, tidak merusak atau memblokir bagian sistem lain yang sudah berjalan
- Punya **output** yang jelas dan **kriteria keberhasilan** yang bisa diverifikasi
- **Tidak** menentukan tool, script, atau langkah teknis persis — itu keputusan implementasi di lapangan, tergantung tool yang dipilih tim (lihat Bagian 12 dokumen arsitektur induk untuk kategori tool ilustratif)

Urutan milestone di bawah adalah urutan yang disarankan, bukan urutan kaku. Temuan di satu milestone (misalnya volume data yang ternyata jauh lebih besar dari perkiraan, atau pola dirty data yang tidak terduga) boleh dan wajar mengubah prioritas atau detail milestone sesudahnya — itu bagian dari sifat pekerjaan ini, bukan penyimpangan dari rencana.

Rujukan kebutuhan: `Metadata.md` dan `DataSchema.md` (data dictionary & skema 6 database), serta Bagian 9.2–9.4 `rancangan-arsitektur-data-platform-elt.md` (lima pilar monitoring, deteksi perubahan data). Dokumen ini tidak mengutip ulang isinya secara detail — rujuk langsung ke sumber saat dibutuhkan.

---

## Konteks Singkat

6 database production yang perlu dimonitor: `corporate_master`, `reservation_revenue`, `fnb_operations`, `facility_maintenance`, `spa_event`, `hr_finance` — total 23 tabel, ~2,53 juta baris pada kondisi saat ini, dan akan terus bertambah seiring operasional berjalan.

Beberapa karakteristik yang relevan untuk dipertimbangkan sejak awal:
- Sebagian tabel punya kolom yang **memang dirancang tidak sempurna** (dirty data terkontrol: format telepon tidak konsisten, email kosong, typo nama, dsb.) — ini bukan anomali yang perlu dialarm, tapi kondisi dasar yang sudah diketahui. Monitoring perlu bisa membedakan antara "dirty data yang memang diharapkan ada" dan "penyimpangan baru di luar pola yang sudah diketahui".
- Beberapa kolom bersifat **nullable secara bermakna** (misalnya `guest_id` kosong untuk walk-in anonim) — bukan data hilang yang bermasalah.
- Ada tabel-tabel besar dengan volume tinggi (`fnb_transactions` ~900rb baris, `staff_shifts` ~609rb baris, `housekeeping_log` ~425rb baris) yang kemungkinan jadi prioritas monitoring volume karena paling sensitif terhadap gangguan operasional.

---

## Milestone 1.1 — Inventarisasi dan Baseline Sumber Data Production

### Lingkup
Membangun pemahaman menyeluruh dan terdokumentasi atas apa yang akan dimonitor, sebelum membangun mekanisme monitoring apa pun. Ini termasuk memetakan karakteristik tiap tabel (volume normal, pola pertumbuhan, kolom kritis bisnis, kolom yang memang dirancang "kotor") dan menentukan skala prioritas — tidak semua 23 tabel butuh kedalaman monitoring yang sama.

### Kenapa Ini Jadi Milestone Terpisah
Membangun monitoring tanpa baseline yang jelas menghasilkan alert yang tidak bisa dipercaya (terlalu sensitif atau terlalu tumpul). Pekerjaan ini murni observasional/analitis, tidak memasang sistem apa pun, sehingga aman untuk dihentikan sewaktu-waktu tanpa risiko ke komponen lain.

### Output
- Dokumen/tabel pemetaan 23 tabel: volume baseline, kolom kritis bisnis, kolom yang boleh kosong/kotor secara sah, dan prioritas monitoring (tinggi/sedang/rendah) per tabel.
- Daftar business rule yang relevan untuk validasi nilai (contoh: `revenue >= 0`, format email, rentang tanggal yang masuk akal).

### Kriteria Keberhasilan
- Setiap 23 tabel di 6 database punya klasifikasi prioritas dan catatan karakteristik yang jelas.
- Dokumen ini bisa dipakai sebagai rujukan langsung oleh milestone-milestone berikutnya tanpa perlu analisis ulang dari nol.

---

## Milestone 1.2 — Monitoring Volume dan Freshness Data Masuk

### Lingkup
Membangun kemampuan untuk menjawab: data apa yang masuk, berapa jumlahnya, dan apakah datang tepat waktu — untuk seluruh tabel production sesuai prioritas dari Milestone 1.1. Termasuk mekanisme baseline historis (rolling, bukan angka statis) agar volume yang dianggap "wajar" mengikuti pola bisnis riil (musiman, hari kerja vs akhir pekan, dsb).

### Kenapa Ini Jadi Milestone Terpisah
Ini kapabilitas paling dasar dan paling sering dibutuhkan lebih dulu — sebelum bisa bicara soal anomali nilai atau schema drift, tim harus lebih dulu tahu "apakah data yang seharusnya datang, benar-benar datang". Independen dari Milestone 1.3 dan 1.4 — bisa berjalan lebih dulu tanpa menunggu keduanya selesai.

### Output
- Mekanisme pemantauan volume harian per tabel (dibandingkan baseline rolling).
- Mekanisme pemantauan freshness (kapan data terakhir masuk/berubah per tabel).
- Alert untuk penyimpangan volume signifikan atau keterlambatan data.

### Kriteria Keberhasilan
- Untuk setiap tabel prioritas tinggi, tim bisa menjawab "berapa baris masuk hari ini dibanding biasanya" dan "kapan data terakhir update" tanpa query manual.
- Simulasi penurunan/lonjakan volume buatan (uji coba terkontrol) berhasil memicu alert sesuai ekspektasi.

---

## Milestone 1.3 — Monitoring Kualitas Data dan Anomali Nilai

### Lingkup
Membangun validasi kualitas data (nilai tidak boleh kosong pada kolom kritis, keunikan, relasi antar tabel, nilai yang diperbolehkan, business rule custom) dan deteksi anomali nilai (outlier ekstrem, proporsi NULL yang tiba-tiba melonjak pada kolom yang biasanya lengkap, nilai negatif yang seharusnya tidak ada).

Bagian tersulit dari milestone ini: memastikan mekanisme ini **tidak** mengalarm dirty data yang memang sudah diketahui by design (lihat konteks di atas) — perlu pemisahan yang jelas antara "pola kotor yang sudah dikenal dan stabil proporsinya" vs "penyimpangan baru yang belum pernah terlihat".

### Kenapa Ini Jadi Milestone Terpisah
Berbeda sifat dari Milestone 1.2 — ini bicara soal **kebenaran nilai**, bukan sekadar ada/tidaknya data. Butuh baseline dari Milestone 1.1 sebagai rujukan mana kolom yang punya toleransi kotor dan mana yang tidak. Bisa dikerjakan paralel dengan 1.2 karena tidak saling bergantung secara teknis, meski keduanya sama-sama butuh hasil Milestone 1.1.

### Output
- Rangkaian pengujian kualitas data (not_null, unique, relationships, accepted_values) untuk kolom-kolom kritis di tabel prioritas.
- Mekanisme deteksi anomali nilai dengan baseline rolling per kolom kunci bisnis.
- Dokumentasi eksplisit: daftar pola dirty data yang dikecualikan dari alert karena memang sah secara desain.

### Kriteria Keberhasilan
- Pengujian kualitas data berjalan terjadwal dan hasilnya bisa ditelusuri (lolos/gagal per tabel per waktu).
- Anomali nilai buatan (uji coba terkontrol, di luar pola dirty data yang sudah dikenal) berhasil terdeteksi.
- Proporsi dirty data yang sudah diketahui (missing value, format tidak konsisten, dsb.) **tidak** memicu false alert pada kondisi normal.

---

## Milestone 1.4 — Monitoring Perubahan Struktur (Schema Drift)

### Lingkup
Membangun deteksi ketika struktur tabel production berubah tanpa pemberitahuan — kolom baru ditambahkan, kolom dihapus, atau tipe data berubah. Termasuk menentukan alur notifikasi (bukan otomatis diteruskan tanpa review), khususnya untuk kolom baru yang berpotensi memuat data sensitif.

### Kenapa Ini Jadi Milestone Terpisah
Sifatnya berbeda dari volume/freshness maupun anomali nilai — ini soal **bentuk**, bukan isi, data. Frekuensi kejadian jauh lebih jarang tapi dampaknya bisa lebih besar (bisa mematahkan pipeline downstream). Independen dari Milestone 1.2 dan 1.3 sepenuhnya.

### Output
- Mekanisme deteksi perubahan skema (kolom baru/hilang, perubahan tipe data) di level production.
- Alur notifikasi ke tim yang tepat saat perubahan terdeteksi.

### Kriteria Keberhasilan
- Perubahan skema buatan (uji coba terkontrol: tambah kolom baru pada tabel non-produktif atau environment staging) berhasil terdeteksi dan memicu notifikasi.
- Tidak ada perubahan skema yang otomatis diteruskan tanpa jejak/notifikasi.

---

## Milestone 1.5 — Dashboard dan Alerting Terpadu (Fase 1)

### Lingkup
Menyatukan hasil Milestone 1.2, 1.3, dan 1.4 ke dalam satu tampilan yang bisa dipakai tim untuk memantau kesehatan data production secara keseluruhan, beserta jalur alerting yang jelas (siapa menerima alert apa, lewat kanal apa).

### Kenapa Ini Jadi Milestone Terpisah
Ini murni pekerjaan konsolidasi dan presentasi — sengaja diletakkan terakhir karena baru bisa dikerjakan dengan baik setelah komponen-komponen monitoring individualnya (1.2–1.4) sudah menghasilkan data yang bisa ditampilkan. Menunda milestone ini tidak menghambat milestone lain karena sifatnya downstream murni.

### Output
- Dashboard yang menampilkan status volume, freshness, kualitas data, dan schema drift untuk seluruh tabel prioritas.
- Konfigurasi alerting dengan tujuan/kanal yang jelas per jenis kejadian.

### Kriteria Keberhasilan
- Dashboard dapat diakses tim dan mencerminkan kondisi terkini (bukan data basi).
- Setiap jenis alert dari Milestone 1.2–1.4 muncul di dashboard dan terkirim ke kanal yang benar saat diuji coba.

---

## Catatan Serah Terima ke Fase 2

Fase 1 berhenti tepat sebelum data menyentuh `raw_production` di BigQuery. Hasil kerja fase ini (baseline, pola dirty data yang dikenal, mekanisme deteksi anomali/drift) relevan sebagai referensi untuk Fase 2, karena masalah yang berasal dari sisi production akan terlihat gejalanya lagi di layer warehouse — pemilik pekerjaan yang sama disarankan membawa temuan dari Fase 1 sebagai konteks saat memulai Fase 2, bukan memulai dari nol.
