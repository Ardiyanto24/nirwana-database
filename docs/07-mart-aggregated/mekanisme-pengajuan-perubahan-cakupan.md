# Mekanisme Pengajuan Perubahan Cakupan `mart_aggregated`

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 5.6 (`milestones/5.6-mekanisme-pengajuan-perubahan-cakupan/`) |
| **Dipakai oleh** | Tim konsumen `mart_aggregated` — Data Analyst (`04-serving-data-analyst.md`, belum dibangun), AI Chatbot (`05-serving-ai-chatbot.md`, belum dibangun) — begitu milestone mereka mulai dan menemukan kebutuhan agregasi yang belum tercakup |
| **Backlog terkait** | `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` — tiap pengajuan dicatat sebagai 1 entri di sana |
| **Status** | Selesai — 1 siklus uji coba (threshold watchlist HR) berhasil ditutup penuh, lihat backlog |

---

## Kenapa Dokumen Ini Ada

`mart_aggregated` adalah **aset bersama** (`docs/03-implementation-plans/03-mart-aggregated-owner.md`, "Kenapa Pekerjaan Ini Dipisah Sebagai Kepemilikan Tersendiri") — dikonsumsi Data Analyst dan AI Chatbot sekaligus lewat 1 struktur dan definisi tunggal. Cakupan awal (Milestone 5.1) hampir pasti tidak menangkap 100% kebutuhan sejak hari pertama — terutama untuk kebutuhan yang baru ketahuan setelah tim konsumen benar-benar mulai membangun di atas `mart_aggregated`.

Tanpa jalur yang jelas, risikonya adalah perubahan ad-hoc yang tidak terlacak pada aset bersama — definisi metrik yang berubah diam-diam, kolom baru ditambahkan tanpa evaluasi dampak ke konsumen lain, atau permintaan yang menumpuk tanpa keputusan. Dokumen ini menetapkan jalur satu-satunya untuk mengajukan perubahan: **lewat pemilik `mart_aggregated`, dicatat di backlog, dievaluasi dengan kriteria yang sama tiap kali** — bukan langsung mengedit model dbt atau meminta akses tulis ke `mart_aggregated`.

## Alur Kerja

```
1. SUBMIT     Tim konsumen mengisi template pengajuan (lihat di bawah),
              menambahkannya sebagai entri baru di backlog
              (pengajuan-perubahan-cakupan.md), status "Diajukan".
                    |
                    v
2. EVALUASI   Pemilik mart_aggregated menilai pengajuan terhadap
              3 kriteria (lihat di bawah), menulis hasil evaluasi
              langsung di entri backlog yang sama.
                    |
                    v
3. KEPUTUSAN  Salah satu dari:
              - DISETUJUI, akan diimplementasikan  -> lanjut ke 4
              - DITOLAK (data tidak tersedia)       -> ditutup, alasan dicatat
              - DITUNDA (butuh info lebih lanjut)    -> tetap di backlog, status "Ditunda"
                    |
                    v
4. TINDAK     Kalau disetujui: perubahan diimplementasikan (model dbt,
   LANJUT     test, promote ke mart_aggregated, cek reverse ETL kalau
              relevan) via checkpoint milestone seperti biasa (bukan
              hotfix langsung ke production).
                    |
                    v
5. TUTUP      Entri backlog diupdate status "Selesai", direferensikan
              ke commit/checkpoint yang mengimplementasikan perubahan.
```

Setiap pengajuan — apa pun hasilnya (disetujui/ditolak/ditunda) — **tetap dicatat permanen di backlog**, bukan dihapus begitu selesai diproses. Ini konsisten pola `docs/keputusan-tertunda.md` yang sudah terbukti dipakai project ini: entri "ditolak" atau "ditunda" tetap punya nilai sebagai jejak keputusan, dicek ulang kalau situasinya berubah.

## Template Pengajuan

Setiap entri baru di backlog wajib mengisi field berikut:

- **Tanggal**: kapan diajukan.
- **Pengaju**: nama/peran + tim (mis. "HR Manager, tim Data Analyst").
- **Kebutuhan**: deskripsi singkat apa yang dibutuhkan dan kenapa (konteks bisnis, bukan cuma "tambah kolom X").
- **Domain terdampak**: salah satu dari 6 domain `mart_aggregated` (Revenue, F&B, Facility/Ops, Spa & Event, HR, Corporate/Financial) atau lintas-domain.
- **Referensi (kalau ada)**: apakah ini kebutuhan yang sudah pernah tercatat sebagai gap di milestone/dokumen sebelumnya (mis. `konsolidasi-agregasi-mart-aggregated.md` §Eksplisit Luar Cakupan, atau Known Gaps milestone manapun) — kalau ada, sebutkan referensinya supaya tidak dievaluasi dari nol.

## Kriteria Evaluasi

3 kriteria sederhana (sesuai contoh di dokumen sumber M5.6), dinilai oleh pemilik `mart_aggregated` untuk tiap pengajuan:

| Kriteria | Pertanyaan | Nilai |
|---|---|---|
| **Ketersediaan data** | Apakah data untuk kebutuhan ini benar-benar ada di `mart_cleaned`/sumber lain? | Tersedia / Tersedia sebagian / Tidak tersedia |
| **Dampak ke konsumen lain** | Kalau diimplementasikan, apakah mengubah definisi/struktur yang sudah dipakai konsumen lain (Data Analyst maupun AI Chatbot)? | Tidak ada dampak (murni tambahan) / Dampak rendah (kolom baru, tidak mengubah yang sudah ada) / Dampak tinggi (mengubah definisi/grain existing) |
| **Prioritas relatif** | Seberapa mendesak dibanding pengajuan lain yang sedang menunggu di backlog? | Rendah / Sedang / Tinggi |

**Aturan keputusan sederhana**: "Tidak tersedia" pada ketersediaan data → **DITOLAK** langsung (tidak ada gunanya lanjut evaluasi dampak/prioritas kalau datanya memang tidak ada — diteruskan sebagai rekomendasi ke pemilik sistem produksi kalau relevan, bukan dipaksakan). Selain itu, kombinasi dampak rendah + data tersedia penuh → jalur cepat ke **DISETUJUI**. Dampak tinggi selalu butuh diskusi eksplisit dulu (tidak bisa auto-disetujui), konsisten prinsip project ini soal perubahan yang menyentuh infrastruktur/kontrak bersama.

## Peran

- **Pengaju**: tim konsumen (Data Analyst, AI Chatbot) — mengisi template, tidak mengedit `mart_aggregated` langsung.
- **Pemilik `mart_aggregated`**: mengevaluasi, memutuskan, dan (kalau disetujui) mengimplementasikan perubahan lewat proses milestone/checkpoint yang sama seperti M5.1-5.6 — bukan hotfix ad-hoc.

## Catatan tentang Uji Coba Siklus (Milestone 5.6)

Project ini dikerjakan solo — tidak ada tim Data Analyst/AI Chatbot terpisah sungguhan untuk menguji jalur ini secara otentik. Siklus uji coba KK2 M5.6 **disimulasikan penuh**: pengajuan ditulis ala persona (HR Manager) berdasarkan gap yang sudah tercatat berulang di M5.1→M5.3 (bukan dikarang), lalu dievaluasi dan ditindaklanjuti sebagai pemilik `mart_aggregated`. Lihat entri lengkap di `pengajuan-perubahan-cakupan.md` — ditandai eksplisit sebagai simulasi, konsisten pola provisional yang sudah dipakai M5.4 (mock scorer)/M5.5 (index contoh).
