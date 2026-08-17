# Report — Milestone 5.6: Mekanisme Pengajuan Perubahan Cakupan

Milestone ini berbasis **dokumen/proses**. Ia menetapkan cara perubahan cakupan dinilai dan ditutup, lalu membuktikannya dengan satu perubahan nyata pada watchlist HR.

## 1. Ringkasan Hasil

**Status akhir: Completed.** Dokumen `mekanisme-pengajuan-perubahan-cakupan.md` menetapkan alur lima tahap—pengajuan, evaluasi, keputusan, tindak lanjut, dan penutupan—beserta lima field wajib, peran, dan kriteria availability, impact, serta priority. Backlog `pengajuan-perubahan-cakupan.md` menjadi catatan perubahan yang dapat ditelusuri.

Mekanisme diterapkan pada threshold watchlist HR. Ambang awal `1.5×` menandai 47% populasi, sehingga dikalibrasi menjadi `5×` berdasarkan `APPROX_QUANTILES` sekitar P95. Kolom `in_watchlist` kemudian tersedia pada `fact_hr_watchlist_monthly`, dengan hasil konsisten di BigQuery dan PostgreSQL: 1.122 dari 24.036 baris (`4,67%`) bernilai true.

## 2. Kriteria Keberhasilan vs Bukti Nyata

| Kriteria | Bukti nyata |
| --- | --- |
| Perubahan memiliki alur dan informasi minimum | Dokumen proses memuat lima tahap serta lima field pengajuan wajib. |
| Keputusan dapat dinilai dengan kriteria eksplisit | Availability sumber, dampak, dan prioritas digunakan sebagai dasar evaluasi. |
| Mekanisme dibuktikan pada perubahan nyata | Threshold HR diuji, ditolak dalam bentuk awal, dikalibrasi, diimplementasikan, lalu ditutup di backlog. |
| Hasil perubahan konsisten pada layer konsumsi | Nilai `in_watchlist` cocok antara BigQuery dan PostgreSQL. |

## 3. Cara Kerja dan Arsitektur

Tidak ada komponen runtime baru yang berdiri sendiri, sehingga tidak diperlukan diagram arsitektur. Mekanisme ini menjadi jalur pengendali di atas pipeline yang sudah ada: pemohon mencatat kebutuhan dan dampak, evaluator memeriksa sumber serta risiko, keputusan menentukan tindakan, lalu hasil implementasi dan validasi dicatat sebelum tiket ditutup.

Pemisahan ini penting agar perubahan seperti threshold tidak masuk sebagai edit ad-hoc. Parameter yang memiliki dampak analitik wajib memiliki bukti distribusi dan jejak keputusan yang dapat diperiksa kembali.

## 4. Perubahan dari Plan

Rencana mekanisme diwujudkan sekaligus sebagai simulasi perubahan pada proyek solo. Evaluasi tidak menerima ambang `1.5×` hanya karena mudah ditulis; bukti bahwa cakupannya terlalu lebar menghasilkan keputusan kalibrasi `5×`. Dengan demikian, proses menghasilkan perubahan data yang benar-benar diverifikasi, bukan sekadar template administrasi.

## 5. Keterbatasan dan Item Provisional

- Ambang SLA tetap open karena belum memiliki dasar data dan persetujuan operasional.
- Rincian undistributed expense masih merupakan gap sumber.
- Perubahan skema ML ditunda sampai mock contract diganti oleh kontrak ML final.
- Rantai CI penuh belum menjadi bukti untuk semua perubahan: sensor ML masih menunggu mock output, meskipun promosi dan sinkronisasi manual telah tervalidasi.

## 6. Follow-up

- Gunakan backlog ini untuk perubahan schema ML, threshold SLA, dan gap sumber berikutnya.
- Pertahankan keputusan, bukti data, dan status penutupan pada satu jejak yang sama.
- M5.7 memakai mekanisme ini untuk menyelesaikan penambahan `property_id` pada `dim_employee`.
