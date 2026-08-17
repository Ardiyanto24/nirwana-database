# Report — Milestone 1.1: Inventarisasi dan Baseline Sumber Data Production

Milestone ini berjenis **berbasis dokumen**. Hasilnya adalah baseline dan kesepakatan operasional untuk pekerjaan monitoring berikutnya; tidak ada sistem berjalan yang perlu didiagramkan secara rinci.

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai sesuai rencana.

Milestone 1.1 menghasilkan baseline operasional untuk 23 tabel di enam schema production dalam `docs/04-monitoring/baseline-inventaris-produksi.md`. Setiap tabel memiliki volume aktual, kolom bisnis penting, kondisi kosong/kotor yang sah, skor prioritas monitoring, serta kandidat business rule. Baseline tidak sekadar menyalin rancangan: seluruh hitungan volume dan sampel kondisi data diverifikasi langsung dengan query `SELECT` read-only ke Supabase.

Hasil verifikasi mencatat total 2.534.072 baris, klasifikasi tujuh tabel prioritas Tinggi, 12 Sedang, dan empat Rendah. Milestone juga menemukan perbedaan nama `corporate_master.role_permissions` di database live terhadap `role_permissions_chatbot_v2` pada dokumentasi, tanpa mengubah skema produksi karena pekerjaan ini bersifat observasional.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari dokumen sumber) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| Setiap 23 tabel di 6 database punya klasifikasi prioritas dan catatan karakteristik yang jelas. | `baseline-inventaris-produksi.md` memetakan 23/23 tabel dengan jumlah baris live, skor dan label prioritas, kolom kritis, serta kondisi nullable/kotor yang sah. Log verifikasi mencatat seluruh tabel ditemukan di enam schema dan total volume live 2.534.072 baris. | Ya |
| Dokumen bisa dipakai sebagai rujukan langsung oleh milestone-milestone berikutnya (1.2–1.4) tanpa perlu analisis ulang dari nol. | Dokumen menyediakan rubrik prioritas, baseline volume, pemetaan kondisi dirty-by-design, dan katalog kandidat business rule. M1.2 memakai prioritas serta pemetaan tersebut untuk konfigurasi volume/freshness, M1.3 untuk suite kualitas data, dan M1.4 untuk daftar 23 tabel baseline struktur. | Ya |

## Bagian 3 — Cara Kerja dan Arsitektur

Milestone ini menghasilkan dokumen dan kesepakatan, tidak ada sistem yang berjalan untuk didiagramkan — lihat Bagian 1 untuk ringkasan hasil.

## Bagian 4 — Perubahan dari Plan

Satu penyesuaian proses terjadi: checkpoint review klasifikasi prioritas tidak dijalankan sebagai jeda terpisah. Klasifikasi 23 tabel beserta rasionalisasi skor disampaikan bersama deliverable final sehingga tetap dapat ditinjau dan dikoreksi tanpa mengulang pekerjaan. Tidak ada perubahan terhadap lingkup atau hasil yang dijanjikan.

## Bagian 5 — Keterbatasan dan Item Provisional

- Baseline adalah snapshot pada 7 Agustus 2026. Volume perlu diolah sebagai baseline rolling oleh mekanisme M1.2, bukan diperlakukan sebagai angka tetap.
- `event_bookings` tidak memiliki tanggal pembuatan booking yang cocok sebagai sinyal freshness; keterbatasan ini diteruskan ke M1.2.
- Penamaan tabel RBAC berbeda antara dokumentasi dan database live: `role_permissions_chatbot_v2` versus `corporate_master.role_permissions`. Isinya tervalidasi setara, tetapi dokumentasi/skema belum diselaraskan.
- `public._sim_state` teridentifikasi sebagai tabel internal generator data, sehingga sengaja dikecualikan dari inventaris 23 tabel bisnis.

## Bagian 6 — Follow-up

- Volume, prioritas, dan kondisi dirty-by-design menjadi input M1.2 untuk monitoring volume/freshness.
- Katalog kandidat business rule menjadi input M1.3 untuk pengujian kualitas data; kolom dirty-by-design tidak boleh diperlakukan sebagai anomali semata.
- Daftar 23 tabel dan temuan perbedaan tipe/penamaan perlu diverifikasi lagi oleh M1.4 saat membangun baseline schema drift.
- Pemilik dokumentasi arsitektur perlu memutuskan penyelarasan nama tabel RBAC; pekerjaan ini berada di luar cakupan M1.1.
