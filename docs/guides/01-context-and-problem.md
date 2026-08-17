# 01 — Konteks dan Masalah

## Ringkasan

Nirwana Data Platform dirancang untuk mengubah data operasional Nirwana Hospitality Group—sebuah grup hotel fiktif dengan lima properti—menjadi data yang dapat dipakai secara aman oleh Data Analyst, Data Scientist, dan AI Chatbot. Sistem ini tidak berhenti pada pemindahan data: ia harus menjaga konteks bisnis, membatasi akses menurut kebutuhan, dan menyediakan jejak saat data atau pipeline bermasalah.

Platform ini mencakup enam domain operasional: corporate master, reservation & revenue, F&B, facility maintenance, spa & event, serta HR & finance. Data sumber bersifat sintetis dan sengaja memuat pola data kotor yang realistis untuk menguji mekanisme kualitas data.

## Masalah yang perlu dipecahkan

### Satu sumber, tiga pola konsumsi

Kebutuhan konsumen tidak dapat dipenuhi dengan satu salinan data yang sama.

| Konsumen | Kebutuhan utama | Risiko jika diberi akses generik |
| --- | --- | --- |
| Data Scientist | data granular dan histori penuh untuk analisis serta feature engineering | agregasi dini menghilangkan sinyal; data sensitif dapat terbuka terlalu luas |
| Data Analyst | analisis cepat dan eksplorasi data historis melalui view, API, atau BI tool | logic bisnis berulang dan query dapat salah memahami grain |
| AI Chatbot | respons cepat dengan data yang relevan terhadap peran pengguna | akses berlebihan, PII terbuka, serta jawaban berbasis data yang tidak dapat ditelusuri |

Keputusan inti yang lahir dari perbedaan ini adalah memisahkan `mart_cleaned` untuk data granular dari `mart_aggregated` untuk metrik siap konsumsi. Pemisahan tersebut bukan optimasi teknis semata; ia membatasi siapa dapat melihat data apa dan mencegah konsumen menghitung ulang logic bisnis sendiri.

### Data tidak boleh "dibersihkan" tanpa konteks

Sebagian nilai kosong dan duplikat adalah keadaan bisnis yang bermakna, bukan kesalahan yang boleh dihapus otomatis. Contohnya termasuk transaksi F&B dari walk-in tanpa `guest_id`, tiket maintenance untuk area umum tanpa `room_id`, serta duplikat tamu yang sengaja dipertahankan untuk eksperimen Data Scientist.

Karena itu, proses cleaning hanya melakukan perubahan yang dapat dipertanggungjawabkan—misalnya normalisasi format dan tipe data—sementara data yang sengaja kotor atau bermakna tetap dipertahankan dan didokumentasikan.

### Kecepatan akses tidak boleh mengorbankan kontrol

BigQuery sesuai untuk transformasi dan pembacaan skala besar, tetapi pola query interaktif yang kecil dan sering—terutama dari AI Chatbot—lebih sesuai dilayani PostgreSQL. Platform menggunakan reverse ETL untuk menyajikan data ke PostgreSQL tanpa memberi aplikasi akses langsung ke warehouse.

Konsekuensinya, proses perpindahan data perlu memiliki quality gate, pemeriksaan kesetaraan jumlah baris, dan mekanisme swap tabel agar pembaca tidak mengalami downtime selama refresh.

### Sistem data perlu dapat dioperasikan, bukan hanya dibangun

Pipeline yang berhasil sekali belum tentu dapat dipercaya terus-menerus. Sistem harus menjawab pertanyaan operasional berikut tanpa membuka log mentah satu per satu:

- Tahap mana yang berjalan, gagal, atau lebih lambat dari normal?
- Apakah data lolos quality gate sebelum dipublikasikan?
- Apakah hasil reverse ETL sesuai dengan warehouse?
- Apakah output ML tersedia, lengkap, dan masih relevan?
- Apakah satu kegagalan upstream sedang menghasilkan banyak gejala downstream?

Jawaban atas pertanyaan tersebut membentuk lapisan observability yang terpusat pada schema `monitoring` dan disajikan lewat Grafana maupun endpoint agregat read-only.

## Prinsip yang mengarahkan desain

1. **Pisahkan data menurut tujuan konsumsi, bukan hanya lokasi penyimpanan.**
2. **Pertahankan konteks bisnis saat cleaning.** Tidak semua nilai kosong atau duplikat adalah defect.
3. **Publikasikan data melalui gate.** Build, test, parity check, lalu swap; bukan langsung mengganti tabel live.
4. **Terapkan least privilege secara berlapis.** Kredensial dan view dibatasi menurut domain, sementara kontrol aplikasi menangani konteks request.
5. **Catat trade-off sebagai bagian dari desain.** Constraint BigQuery Sandbox dan komponen ML provisional tidak diperlakukan sebagai fakta yang disembunyikan.

## Pertanyaan berikutnya

Bab berikutnya menjelaskan bagaimana prinsip di atas diterjemahkan menjadi alur data, batas komponen, dan jalur konsumsi yang berbeda.

## Referensi lanjutan

- [Rancangan arsitektur ELT](../01-architecture/rancangan-arsitektur-data-platform-elt.md)
- [Kebutuhan Data Scientist dan batas `mart_cleaned`](../02-requirements/pemetaan-kebutuhan-konsumen-data-mart.md)
- [Metadata dan pola data bermakna](../01-architecture/Metadata.md)
- [DataSchema dan alasan pola data sintetis](../01-architecture/DataSchema.md)
- [Catatan cleaning yang sengaja tidak dilakukan](../../warehouse/README.md)
