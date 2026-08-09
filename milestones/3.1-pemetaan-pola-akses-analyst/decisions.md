# Milestone 3.1: Pemetaan Pola Akses per Peran Analyst — Decisions

**Sumber:** `docs/03-implementation-plans/04-serving-data-analyst.md`, baris 49-63.
**Prasyarat:** Milestone 5.1-5.6 (`mart_aggregated` selesai, 46 fact + 27 dimension table) dan Milestone 2.1-2.4 (`mart_cleaned` selesai) — keduanya status Completed.
**Status:** In Progress
**Date started:** 2026-08-09

## Lingkup Sumber / Contract

- **Lingkup:** Menerjemahkan 6 pola domain dari `docs/02-requirements/pemetaan-kebutuhan-data-analyst.md` menjadi pemetaan konkret: tabel `mart_aggregated`/`mart_cleaned` mana yang relevan untuk peran mana, filter wajib apa yang berlaku, dan kebutuhan row-level mana yang perlu dijembatani ke `mart_cleaned`.
- **Output:**
  1. Tabel pemetaan: peran → tabel sumber (`mart_aggregated`/`mart_cleaned`) → filter wajib → kebutuhan row-level.
  2. Daftar business rule kritis yang wajib diterapkan di level query/view.
- **Kriteria Keberhasilan:**
  1. Setiap 6 pola peran (plus Property/GM Analyst sebagai union) punya pemetaan akses yang jelas dan bisa langsung dipakai sebagai acuan Milestone 3.2 tanpa perlu membuka ulang dokumen kebutuhan dari nol.

## Temuan Eksplorasi (sebelum breakdown)

- Milestone numbering "3.x" dikonfirmasi merujuk `docs/03-implementation-plans/04-serving-data-analyst.md` (mendefinisikan Milestone 3.1-3.6 secara internal) — cross-reference eksplisit ditemukan di `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` ("milestone konsumen M3.x/M4.x"). Milestone 4.x = `05-serving-ai-chatbot.md`.
- `docs/02-requirements/pemetaan-kebutuhan-data-analyst.md` (576 baris) sudah berisi 6 section "Kebutuhan Final" per domain (§1.3 Revenue, §2.3 F&B, §3.3 Facility/Ops, §4.3 Spa & Event, §5.3 HR, §6.3 Corporate/Financial) di level kebutuhan bisnis (dimensi/metrik naratif) — belum dipetakan ke nama tabel/kolom aktual.
- `docs/07-mart-aggregated/DataSchema-mart-aggregated.md` adalah sumber kebenaran skema aktual (46 fact + 27 dimension table, pasca-koreksi grain M5.3) — dipakai sebagai basis pemetaan, bukan dokumen draft M5.1 yang sudah diketahui punya beberapa grain salah di draft awal.
- Serving PostgreSQL (M2.4/M5.5) belum punya role read-only untuk Data Analyst — itu cakupan Milestone 3.5, bukan 3.1. M3.1 murni pemetaan tabel/filter, tidak menyentuh kredensial.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 1. Lokasi dokumen output: `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md`

**Keputusan:** Folder baru bernomor urut `docs/08-serving-data-analyst/` (lanjutan `07-mart-aggregated`), isinya dokumen pemetaan ini (berpotensi dokumen desain view/API milestone 3.2+ berikutnya).

**Kenapa:** Preseden identik Keputusan #1 Milestone 5.1 — deliverable inti adalah dokumen substantif, folder `milestones/<id>-*/` dibatasi 3 file (`decisions.md`/`logs.md`/`report.md`), dan pola penomoran folder `docs/` (`01-architecture` ... `07-mart-aggregated`) sudah konsisten dipakai untuk tiap area kerja substantif.

**Ditolak:** Menaruh sebagai section baru di `04-serving-data-analyst.md` (dokumen itu rancangan implementasi coarse-grained, bukan tempat data pemetaan detail); menaruh sebagai file ke-4 di folder milestone (menyimpang dari konvensi "exactly 3 files").

### 2. Skema kolom tabel pemetaan

`Peran | Cakupan Properti | Tabel mart_aggregated Relevan | Tabel mart_cleaned Relevan (row-level) | Filter Wajib | Business Rule Kritis Terkait | Catatan Gap`

Dipilih langsung karena mengikuti literal 2 poin Output dokumen sumber (baris 57-59) — tidak ada desain alternatif yang bersaing di titik ini, sama alasan Keputusan #2 M5.1.

### 3. Metode pengerjaan: pembacaan langsung, tanpa delegasi sub-agent

`pemetaan-kebutuhan-data-analyst.md` dan `DataSchema-mart-aggregated.md` sudah dibaca lengkap saat eksplorasi plan mode sesi ini. Volume per-domain kecil dan butuh judgment silang antara kebutuhan bisnis naratif dan nama tabel/kolom teknis — delegasi sub-agent berisiko kehilangan konteks silang, sama alasan Keputusan #3 M5.1.

### 4. Sumber kebenaran nama tabel: `DataSchema-mart-aggregated.md`, bukan `konsolidasi-agregasi-mart-aggregated.md`

`DataSchema-mart-aggregated.md` sudah final pasca-koreksi M5.3 (grain, nama kolom, tabel yang dipecah/digabung sudah dikoreksi dari draft M5.1/M5.2). Memetakan langsung ke dokumen ini memastikan M3.1 akurat terhadap skema yang benar-benar diimplementasikan.

### 5. Penamaan tabel `mart_cleaned` row-level

Dirujuk dengan nama tabel produksi asli (mis. `bookings`, `maintenance_tickets`), konsisten dengan penamaan `mart_cleaned__<table>` yang dipakai di seluruh `DataSchema-mart-aggregated.md`. Tidak perlu re-dokumentasi skema `mart_cleaned` di sini — sudah ada di `warehouse/README.md`/`docs/01-architecture/Metadata.md`.

## Task Breakdown

7 task, 5 fase, 5 checkpoint (commit + log tiap checkpoint, sama pola M5.1 — seluruh task analitis/dokumentasi, tidak ada kode).

### Fase 0 — Fondasi
1. Setup `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md` (skeleton skema kolom terkunci) + 1 tabel referensi "domain → fact/dim table relevan" dari `DataSchema-mart-aggregated.md` — Acceptance: 6 domain + tabel lintas-domain tercakup — Verify: hitung fact table per domain cocok dengan `DataSchema-mart-aggregated.md` — S

**✅ Checkpoint 1** — commit + log.

### Fase 1 — Revenue + F&B
2. Pemetaan Revenue Analyst (§1.3 × fact/dim Revenue aktual) — Acceptance: 11 metrik §1.3 terpetakan, gap data sumber tercatat — Verify: cross-check jumlah metrik — S
3. Pemetaan F&B Analyst (§2.3 × fact/dim F&B aktual) — pola sama — S

**✅ Checkpoint 2** — commit + log.

### Fase 2 — Facility/Ops + Spa & Event
4. Pemetaan Facility/Ops Analyst (§3.3 × fact/dim Facility aktual), termasuk business rule `pending_count` SLA — S
5. Pemetaan Spa & Event Analyst (§4.3.1 + §4.3.2 × fact/dim aktual) — S

**✅ Checkpoint 3** — commit + log.

### Fase 3 — HR + Corporate/Financial
6. Pemetaan HR Analyst + Corporate/Financial Analyst (1 task, domain saling terkait via payroll exclusion) — Acceptance: business rule payroll-exclusion dan filter `Overall`-vs-departemen tercatat eksplisit — Verify: cross-check §5.3 dan §6.3 — M

**✅ Checkpoint 4** — commit + log.

### Fase 4 — Property/GM Analyst (union) + Finalisasi
7. Pemetaan Property/GM Analyst (union peran #1-5) + daftar business rule konsolidasi + verifikasi KK + `report.md` — Acceptance: 7 peran lengkap, tidak ada rule tercecer — Verify: baca ulang dokumen penuh — M

**✅ Checkpoint 5 (final)** — commit + push, tutup milestone.
