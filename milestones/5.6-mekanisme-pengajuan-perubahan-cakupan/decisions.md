# Milestone 5.6: Mekanisme Pengajuan Perubahan Cakupan — Decisions

**Source:** `docs/03-implementation-plans/03-mart-aggregated-owner.md`, baris 142-157.
**Status:** In Progress
**Date started:** 2026-08-08

## Contract (from source doc)

- **Lingkup:** Menetapkan alur kerja yang jelas untuk menerima dan menindaklanjuti permintaan penambahan/perubahan agregasi dari tim konsumen (Data Analyst, AI Chatbot) setelah `mart_aggregated` berjalan.
- **Output:**
  1. Alur/kesepakatan kerja untuk pengajuan kebutuhan agregasi baru dari tim konsumen ke pemilik pekerjaan ini.
  2. Kriteria evaluasi sederhana untuk menilai permintaan (mis. apakah datanya tersedia, apakah berdampak ke konsumen lain, prioritas relatif).
- **Kriteria Keberhasilan:**
  1. Ada jalur yang disepakati bersama (didokumentasikan) yang bisa dipakai tim Data Analyst dan AI Chatbot saat mengajukan kebutuhan agregasi baru.
  2. Sekurangnya satu siklus pengajuan-evaluasi-tindak lanjut berhasil dilakukan sebagai uji coba jalur ini.

## Temuan Eksplorasi

Milestone ini **beda sifat** dari M5.1-5.5 — pekerjaan proses, bukan teknis (per "Kenapa Ini Jadi Milestone Terpisah" dokumen sumber). Riset (1 Explore agent) menemukan:

- **4 kandidat "pengajuan" otentik sudah tercatat berulang** di laporan M5.1→M5.5 (bukan perlu dikarang untuk kebutuhan uji coba):
  - **Threshold watchlist HR** — `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md` §Kebutuhan Khusus Kategori C: "Threshold 'di luar kebiasaan' untuk early warning watchlist pra-resign | Dokumen arsitektur induk (Bagian 10 No. 3) eksplisit menandai ambang batas drift/anomali sebagai area yang perlu didiskusikan terpisah". Diulang di `milestones/5.2-.../report.md` dan `milestones/5.3-.../report.md` Known Gaps — kolom mentah (`absence_deviation_ratio`, `late_deviation_ratio`) sudah ada di `fact_hr_watchlist_monthly` sejak M5.3, tinggal keputusan bisnis.
  - **Threshold SLA breach Facility/Ops** — pola sama (kolom `avg_sla_duration_hours` dll sudah ada), tercatat berulang M5.1→M5.3.
  - **Breakdown `undistributed_expense`** — gap data sumber murni (`financial_summary` cuma 1 kolom total), tercatat M5.1→M5.3, tidak bisa diimplementasikan tanpa perubahan skema produksi.
  - **Perubahan skema tabel ML** (`fact_ml_occupancy_forecast_property_room_type`, M5.4) — `milestones/5.4-.../report.md` DAN `milestones/5.5-.../report.md` **sama-sama eksplisit menyebut Milestone 5.6 sebagai kanal yang dituju** untuk perubahan ini begitu tim ML Engineer punya skema final, tapi belum ada skema konkret untuk dievaluasi sekarang.
- **Tidak ada CONTRIBUTING.md atau template issue/PR** di repo ini (`.github/` cuma berisi `workflows/`). Pola paling dekat untuk ditiru gayanya: `docs/keputusan-tertunda.md` (per-entri: Date/What was deferred/Why deferred/Alternatives considered/Revisit when/Status — dicek ulang di awal tiap milestone baru) dan konvensi `decisions.md`/`logs.md`/`report.md` milestone itu sendiri.
- `docs/02-requirements/pemetaan-kebutuhan-*.md` (Data Analyst + 3 layer chatbot) tidak menyebut proses pengajuan apa pun — murni kebutuhan awal, konsisten alasan M5.6 perlu jadi milestone terpisah.
- `warehouse/models/mart_aggregated/hr_finance/hr/fact_hr_watchlist_monthly.sql` dibaca langsung: grain `employee_id x period_date`, kolom `absence_deviation_ratio`/`late_deviation_ratio` = rasio rate bulan berjalan dibanding rata-rata seluruh bulan SEBELUMNYA (expanding window, within-entity). Komentar di file sendiri: "Hanya rasio mentah, TIDAK ADA kolom flag 'masuk watchlist' — threshold belum ditentukan (Keputusan #7 decisions.md)" — mengonfirmasi gap ini masih terbuka persis sampai sekarang.

## Keputusan (via AskUserQuestion)

### 1. Trial cycle: threshold watchlist HR — dipilih karena bisa DITUTUP PENUH

**Keputusan:** Uji coba KK2 memakai gap threshold watchlist HR. Siklus ditutup dengan tindak lanjut nyata: threshold diputuskan + 1 kolom flag baru ditambahkan ke `fact_hr_watchlist_monthly`.

**Kenapa:** Kolom mentah sudah ada, tinggal 1 keputusan bisnis sederhana — bisa diimplementasikan sungguhan sebagai bukti siklus lengkap (submit→evaluasi→tindak lanjut nyata→tertutup), bukan cuma "diajukan lalu didiamkan."

**Ditolak:**
- Breakdown `undistributed_expense` — akan berakhir ditolak/diteruskan ke pemilik sistem produksi (gap data sumber murni), bukan siklus yang selesai dengan perubahan nyata di `mart_aggregated`.
- Perubahan skema tabel ML M5.4 — belum ada skema konkret dari tim ML Engineer untuk dievaluasi, siklusnya akan berakhir "ditunda" bukan tertutup. (Tetap dicatat di backlog sebagai entri terpisah, status "Menunggu skema dari ML Engineer" — bukan trial KK2, tapi contoh nyata bagaimana backlog menampung pengajuan yang belum bisa dievaluasi tuntas.)
- Threshold SLA breach Facility/Ops — pola sama watchlist HR, tidak dipilih sebagai trial KK2 supaya scope tetap 1 contoh fokus (bisa jadi entri backlog kedua kalau relevan, tapi bukan trial wajib).

### 2. Role-play siklus: simulasi penuh, ditandai jelas

**Keputusan:** Assistant menulis pengajuan ala persona (HR Manager) berdasarkan gap yang sudah tercatat di dokumen sebelumnya, lalu mengevaluasi + menindaklanjuti sebagai "pemilik `mart_aggregated`". Seluruh simulasi ditandai eksplisit.

**Kenapa:** Project solo — tidak ada tim Data Analyst/AI Chatbot terpisah sungguhan. Konsisten pola "provisional/simulasi ditandai jelas" (M5.4 mock scorer, M5.5 index contoh).

### 3. File backlog/tracking terpisah: `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md`

**Keputusan:** Backlog terpisah dari dokumen proses, pola sama persis `docs/keputusan-tertunda.md`.

**Kenapa:** Supaya ada tempat terpusat mencatat pengajuan berikutnya (bukan cuma trial ini) — `docs/keputusan-tertunda.md` sudah terbukti dipakai konsisten sepanjang project dan dicek ulang di awal tiap milestone baru.

## Keputusan Teknis Lain (dikunci tanpa AskUserQuestion)

### 4. Lokasi & isi dokumen proses: `docs/07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md`

Folder sama seperti seluruh deliverable M5.1-5.5. Isi: alur kerja (submit → evaluasi → keputusan → tindak lanjut → log ke backlog), template pengajuan, 3 kriteria evaluasi sesuai contoh dokumen sumber (ketersediaan data, dampak ke konsumen lain, prioritas relatif), peran evaluator ("pemilik mart_aggregated").

### 5. Nilai threshold watchlist HR: rasio deviasi > 1.5x baseline individu (absence ATAU late)

`in_watchlist = coalesce(absence_deviation_ratio > 1.5, false) OR coalesce(late_deviation_ratio > 1.5, false)` — aturan sederhana, defensible, konsisten filosofi "within-entity-over-time" yang sudah dikunci sejak M5.1/M5.2 (deviasi dari baseline individu sendiri, bukan rate absolut lintas-karyawan). `coalesce(..., false)` supaya bulan pertama karyawan (baseline `NULL`, belum ada histori) tidak ikut ter-flag `NULL`/error, melainkan `false` (belum bisa dinilai = tidak masuk watchlist).

### 6. Implementasi tindak lanjut: edit `fact_hr_watchlist_monthly.sql` + `_hr_facts_tests.yml`, promote ulang, verifikasi via GitHub Actions sungguhan

Reuse `scripts/mart_aggregated/promote.py` (M5.3) dan `scripts/reverse_etl_mart_aggregated/sync.py` (M5.5, otomatis ambil kolom baru tanpa perubahan kode — `sync.py` selalu baca skema BigQuery tabel secara dinamis via `bq_client.get_table()`). Trigger `transform-mart-aggregated.yml` lalu `reverse-etl-mart-aggregated.yml` untuk buktikan kolom baru mengalir BigQuery→Postgres tanpa intervensi manual tambahan — pola pembuktian end-to-end yang sama seperti M5.4/M5.5.

### 7. Update dokumentasi terkait

Kolom baru didokumentasikan di `DataSchema-mart-aggregated.md` dan `Metadata-mart-aggregated.md`. Known Gaps M5.1/M5.2/M5.3 yang menyebut threshold watchlist HR belum diputuskan ditandai "Diselesaikan via M5.6" dengan referensi silang — supaya jejak keputusan tidak terputus (konsisten pola cross-reference yang sudah dipakai `docs/keputusan-tertunda.md`).

## Task Breakdown

7 fase, 7 checkpoint.

### Fase 0 — Setup
1. Tulis `decisions.md` (dokumen ini).

**Checkpoint 1**

### Fase 1 — Dokumen proses
2. `docs/07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md`.

**Checkpoint 2**

### Fase 2 — Backlog + pengajuan trial (simulasi)
3. `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` — backlog + entri trial (persona HR Manager, status "Diajukan").

**Checkpoint 3**

### Fase 3 — Evaluasi + keputusan threshold
4. Update entri backlog: evaluasi 3 kriteria + keputusan threshold 1.5x.

**Checkpoint 4**

### Fase 4 — Tindak lanjut: implementasi kolom `in_watchlist`
5. Edit model + test dbt, promote, verifikasi via GitHub Actions sungguhan (transform + reverse ETL).

**Checkpoint 5**

### Fase 5 — Tutup siklus + update dokumentasi
6. Update entri backlog jadi selesai, update DataSchema/Metadata, cross-reference Known Gaps M5.1/M5.2/M5.3.

**Checkpoint 6**

### Fase 6 — Finalisasi
7. Verifikasi 2 KK sumber, tulis `report.md`.

**Checkpoint 7 (final)** — commit + push.
