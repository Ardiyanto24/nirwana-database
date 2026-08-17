# Report — Milestone 6.1: Inventarisasi Titik Pengamatan dan Baseline Pipeline

Milestone ini berbasis **dokumen/desain**. Ia membuat peta observabilitas sebagai baseline untuk pekerjaan monitoring berikutnya, bukan membangun monitor atau alert baru.

## 1. Ringkasan Hasil

**Status akhir: Completed.** `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` memetakan 10 titik pengamatan arsitektur dengan sumber sinyal, ketergantungan, prioritas, dan evidence historis. Delapan titik sudah memiliki sinyal yang dapat dirujuk; dua titik—detail DQ gate—dicatat eksplisit sebagai gap yang menjadi prasyarat M6.3.

Peta juga mengidentifikasi fan-out tiga cabang dari transformasi `mart_cleaned` sebagai blast radius tertinggi, serta membedakan `workflow_run` dari buffer waktu cron agar ketergantungan tidak diasumsikan seragam. Klasifikasi Kritis, Tinggi, dan Sedang menjadi dasar deduplikasi alert M6.7.

## 2. Kriteria Keberhasilan vs Bukti Nyata

| Kriteria | Bukti nyata |
| --- | --- |
| Semua titik pengamatan memiliki sumber sinyal atau gap yang eksplisit | 10/10 titik dipetakan; titik 3 dan 7 menyebut prasyarat instrumentasi M6.3, bukan sekadar “belum ada”. |
| Ketergantungan cukup jelas untuk mencegah alert downstream berlebihan | Dependency YAML, cara pemicu, fan-out, dan prioritas tiga tingkat terdokumentasi. |
| Batas cakupan dijaga | Titik konsumsi Data Analyst/AI Chatbot dicatat sebagai titik ke-11 out-of-scope, beserta gap-nya. |
| Bukti dapat diteruskan ke milestone berikutnya | Peta menautkan tabel monitoring, workflow, dan report historis yang menjadi rujukan langsung M6.2–M6.7. |

## 3. Cara Kerja dan Arsitektur

Tidak ada komponen runtime baru sehingga diagram sistem tidak diperlukan. Prosesnya menelusuri tujuh lapis pipeline, menghubungkan setiap tahap ke sinyal yang sudah ada, lalu mencatat dependency dan kekosongan instrumentasi yang tidak boleh disamarkan sebagai monitoring aktif.

Baseline ini secara sengaja membedakan “sinyal tersedia” dari “sinyal sudah diverifikasi ulang”. Sebagian evidence diwarisi dari milestone terdahulu; milestone lanjutan menjadi tempat untuk mengonfirmasi data live dan membangun sinyal yang masih kosong.

## 4. Perubahan dari Plan

Lokasi deliverable dibuat sebagai folder `docs/10-monitoring-warehouse-serving/`, bukan satu file tunggal, agar konsisten dengan struktur dokumentasi proyek. Selain itu, temuan risiko dependency gate dan hasil DQ yang belum queryable ditulis ke `docs/keputusan-tertunda.md` alih-alih diperbaiki di milestone observasional ini.

## 5. Keterbatasan dan Item Provisional

- Verifikasi M6.1 mayoritas berbasis review dokumen dan evidence historis, bukan audit ulang semua tabel monitoring atau run CI.
- Detail hasil test DQ untuk titik 3 dan 7 belum tersedia sampai M6.3.
- Latensi chatbot dan audit log Data Analyst merupakan gap konsumsi yang berada di luar 10 titik utama.
- Tension pace booking dengan data sintetis statis tetap relevan meski bukan bagian dari peta 10 titik.

## 6. Follow-up

- M6.2 menambahkan riwayat dan status pipeline kasar untuk titik 1–9.
- M6.3 menutup gap detail DQ, volume, parity, dan freshness ML.
- M6.7 memakai prioritas dan graph dependency peta ini untuk root-cause grouping.
