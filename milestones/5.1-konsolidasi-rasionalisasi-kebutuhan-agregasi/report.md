# Report — Milestone 5.1: Konsolidasi dan Rasionalisasi Kebutuhan Agregasi

Milestone ini berbasis **dokumen/desain**. Hasilnya adalah baseline kebutuhan mart agregat yang dipakai untuk menilai cakupan, grain, dan ketergantungan sebelum tabel dirancang.

## 1. Ringkasan Hasil

**Status akhir: Completed.** Kebutuhan dari enam domain dikonsolidasikan menjadi 94 entri: 77 masuk cakupan awal, satu kebutuhan khusus pace booking, dua pola kebutuhan khusus yang didokumentasikan, dan 16 kebutuhan di luar cakupan. Dua puluh persona chatbot juga telah dipetakan ke domain terkait.

Artefak utama adalah `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md`. Dokumen ini memberi M5.2 satu sumber untuk menentukan tabel, grain, sumber, dan catatan lintas-domain tanpa mencampur kebutuhan granular yang berisiko PII.

## 2. Kriteria Keberhasilan vs Bukti Nyata

| Kriteria | Bukti nyata |
| --- | --- |
| Kebutuhan agregasi dari seluruh domain terkonsolidasi | 94 entri mencakup enam domain, dengan status cakupan untuk tiap entri. |
| Kebutuhan dapat diterjemahkan menjadi desain fisik | Setiap entri menyebut grain, tabel sumber, dan catatan lintas-domain; menjadi masukan langsung M5.2. |
| Kebutuhan khusus dan batasan dicatat | Pace booking, watchlist HR antarperiode, serta parameter SLA/HR didokumentasikan terpisah dari kebutuhan umum. |
| Persona analitik dan chatbot terhubung ke domain data | 20 persona dipetakan sehingga kebutuhan konsumsi tidak hilang saat desain dimensi/fakta dibuat. |

## 3. Cara Kerja dan Arsitektur

Tidak ada komponen sistem baru pada milestone ini, sehingga tidak diperlukan diagram alur runtime. Prosesnya adalah membaca kebutuhan domain dan persona, mengelompokkan kebutuhan yang setara, lalu menetapkan status cakupan serta informasi minimum yang harus dibawa ke desain tabel.

Rasionalisasi ini juga mengungkap ketergantungan yang tidak boleh disembunyikan: capture rate F&B memerlukan `daily_occupancy`, sedangkan pricing ke GOP memerlukan `financial_summary`. Kebutuhan yang belum didukung sumber—misalnya rincian komisi—dipisahkan sebagai gap, bukan dipaksakan menjadi metrik semu.

## 4. Perubahan dari Plan

Rencana awal dipertahankan, namun hasil konsolidasi dibuat lebih eksplisit daripada daftar kebutuhan biasa: kebutuhan dipilah menurut prioritas, out-of-scope, pola khusus, dan dependensi sumber. Definisi watchlist HR dan parameter SLA sengaja tidak difinalkan tanpa bukti distribusi data; kalibrasi watchlist baru diselesaikan pada M5.6.

## 5. Keterbatasan dan Item Provisional

- Parameter ambang SLA masih terbuka karena belum memiliki definisi operasional yang tervalidasi.
- Rincian biaya/komisi tertentu tidak tersedia pada sumber saat ini.
- Kebutuhan pace booking memakai data sintetis statis, sehingga kelengkapannya perlu dibaca bersama batasan snapshot pada implementasi M5.3.

## 6. Follow-up

- M5.2 menerjemahkan baseline ini menjadi struktur fact dan dimension.
- M5.3 mengimplementasikan metrik yang memiliki sumber data memadai.
- Perubahan atau kebutuhan baru sesudah baseline harus masuk melalui mekanisme M5.6.
