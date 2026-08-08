# Milestone 5.2: Desain Struktur Tabel Mart Aggregated — Decisions

**Source:** `docs/03-implementation-plans/03-mart-aggregated-owner.md`, baris 63-81.
**Status:** Done
**Date started:** 2026-08-08

## Contract (from source doc)

- **Lingkup:** Menentukan struktur tabel `mart_aggregated` (nama tabel, granularitas/grain per tabel, kolom dimensi, kolom metrik, partitioning dan clustering key) berdasarkan hasil konsolidasi Milestone 5.1. Termasuk keputusan desain untuk kasus khusus (pace booking, metrik lintas domain) dan audit eksplisit kolom PII yang berpotensi masuk `mart_aggregated`.
- **Output:**
  1. Skema tabel `mart_aggregated` (nama tabel, grain, kolom) untuk seluruh cakupan hasil Milestone 5.1.
  2. Keputusan desain terdokumentasi untuk kasus khusus (snapshot, cross-domain join).
  3. Rencana partitioning dan clustering key per tabel besar.
  4. Daftar eksplisit kolom PII yang masuk `mart_aggregated` apa adanya vs yang di-mask/dianonimkan, beserta alasannya per kolom.
- **Kriteria Keberhasilan:**
  1. Skema mencakup seluruh metrik prioritas Milestone 5.1 tanpa ambiguitas granularitas (tiap tabel punya definisi grain yang jelas).
  2. Skema mempertimbangkan filter wajib konsumen (`property_id`, `department`, rentang waktu) sebagai kolom mudah difilter/di-cluster, bukan tersembunyi di dalam kalkulasi.
  3. Setiap kolom yang berpotensi PII punya keputusan eksplisit (diteruskan apa adanya dengan alasan, atau di-mask dengan metode jelas) — tidak ada kolom PII masuk skema tanpa keputusan sadar.

## Input Utama

`docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md` (Milestone 5.1, Completed) — 94 baris metrik terkonsolidasi lintas 6 domain (Revenue 15, F&B 17, Facility/Ops 17, Spa & Event 16, HR 13, Corporate/Financial 16), 3 kasus "Kebutuhan Khusus" (pace booking, watchlist HR, 2 threshold pending), 16 item "Eksplisit Luar Cakupan" (tidak perlu masuk skema).

## Temuan Eksplorasi

- `warehouse/dbt_project.yml` + contoh model `mart_cleaned__*.sql`: `mart_aggregated` mewarisi constraint yang sama dari BigQuery Sandbox mode (full-refresh table, DML diblokir total — lihat `docs/keputusan-tertunda.md` "Aktivasi billing GCP"), dan pola penamaan `mart_cleaned__<source>` sudah ada sebagai preseden penamaan.
- Dokumen arsitektur induk Bagian 8.3: "Data sensitif (PII) yang mungkin ada di `raw_production` tidak diteruskan ke `mart_aggregated` tanpa proses masking/anonymization yang eksplisit."
- `04-serving-data-analyst.md` dan `05-serving-ai-chatbot.md` (dibaca untuk diskusi lokasi metadata — lihat Keputusan #10): keduanya murni konsumen `mart_aggregated`, tidak menyebut pembuatan metadata/data dictionary sebagai output milik mereka.

## Keputusan (via AskUserQuestion, dikonfirmasi user — 2 putaran diskusi)

### 1. Pendekatan skema: star schema (Kimball) dengan conformed dimension tables

**Keputusan:** Fact table dikelompokkan per grain yang sama dalam 1 domain (bisa >1 tabel per domain kalau grain berbeda), dengan foreign key ke dimension table yang dipakai bersama lintas domain (conformed dimensions).

**Kenapa:** Alternatif "1 tabel lebar per domain" berisiko ambiguitas grain (baris harian tercampur baris bulanan dalam 1 tabel) — bertentangan langsung dengan KK#1. Alternatif "base table per sumber tanpa pre-join, biarkan konsumen join sendiri" menambah beban query berulang ke tiap konsumen (Data Analyst API, AI Chatbot) — bertentangan dengan tujuan `mart_aggregated` sebagai lapisan "siap pakai".

**Ditolak:** Kedua alternatif di atas.

### 2. Seluruh kategori/referensi jadi dimension table tersendiri (bukan degenerate/inline)

**Keputusan:** `dim_channel`, `dim_department`, `dim_issue_type`, `dim_priority`, `dim_spa_service`, `dim_customer_type`, `dim_fnb_category`, `dim_outlet_type`, `dim_venue_type`, `dim_event_type`, `dim_access_level`, dst — semua jadi dimension table, bukan kolom string inline di fact table.

**Kenapa:** Alasan eksplisit user — ke depan kalau ada kebutuhan atribut tambahan dalam kategori yang sama (mis. `dim_channel` perlu kolom komisi per channel di kemudian hari), tinggal tambah kolom ke dimension table yang sudah ada, tidak perlu bikin dimension table baru dari nol atau migrasi skema besar.

**Ditolak:** Degenerate dimension (kolom inline) — praktik Kimball standar untuk kategori beratribut tunggal, tapi user memprioritaskan extensibility jangka panjang di atas kesederhanaan jumlah tabel saat ini.

## Keputusan Teknis Lain (dikunci tanpa AskUserQuestion — mengikuti preseden/prinsip project)

### 3. Lokasi output: `docs/07-mart-aggregated/desain-skema-mart-aggregated.md`

Folder sama dengan output M5.1, sesuai Handoff Notes eksplisit di `milestones/5.1-.../report.md`.

### 4. Partitioning: kolom `DATE` asli per fact table, bukan `dim_date` terpisah

Tiap fact table pakai kolom `DATE` asli (`period_date`/`snapshot_date`/dst) sebagai partition key BigQuery — BigQuery partition-by butuh kolom native di fact table itu sendiri, join ke `dim_date` terpisah tidak bisa dipakai untuk partitioning. `dim_date` tidak dibangun karena tidak ada kebutuhan kalender fiskal/custom di 94 metrik M5.1.

### 5. Clustering: `property_id` + 1-2 dimensi sekunder relevan per fact table

Memenuhi KK#2 — filter wajib konsumen jadi kolom clustered, bukan tersembunyi di kalkulasi.

### 6. Metrik cross-domain di-precompute saat transformasi M5.3, disimpan sebagai kolom measure

Capture rate F&B, dampak pricing→GOP, service charge vs okupansi, delayed rate vs okupansi — semua dihitung sekali saat transformasi (M5.3) dan disimpan sebagai kolom measure di fact table domain pemiliknya, tidak dihitung ulang saat query oleh konsumen. Tidak bertentangan dengan Keputusan #1 (star schema mengatur normalisasi dimensi, bukan kapan measure dihitung).

### 7. SLA breach & threshold watchlist HR: simpan nilai mentah, bukan flag

Skema hanya menyimpan nilai mentah (durasi `resolved−reported` dalam jam; rate absen/telat individu vs baseline) — tidak menyimpan kolom breach/flag yang bergantung ke threshold yang belum diputuskan (dicatat di M5.1 sebagai "Kebutuhan Khusus kategori C"). Klasifikasi breach/flag ditunda ke saat threshold diputuskan, di luar scope M5.2.

### 8. Cakupan audit PII diperluas ke `employees_directory`

Bukan cuma `guests_pii`/`guests_profile` (penekanan literal dokumen sumber), tapi juga `dim_employee.full_name` — employee name-resolution eksplisit diminta beberapa persona chatbot (HR Staff, dll), tetap data personal meski levelnya beda dari PII tamu.

### 9. Pace booking dan watchlist HR dapat fact table tersendiri

Terpisah dari fact table utama domainnya — grain/karakter fundamental berbeda (snapshot harian vs within-entity-over-time) dari metrik agregat historis biasa.

### 10. Metadata/data dictionary kolom: dipisah, bukan menyatu di dokumen M5.2

**Keputusan:** M5.2 hanya menulis skema **struktural** (nama tabel, nama/tipe kolom, FK ke dimension, partition/cluster key, 1 baris keterangan singkat per kolom). Data dictionary lengkap (cara hitung detail, unit, contoh nilai) ditulis **di Milestone 5.3**, setelah SQL transformasi selesai dan teruji.

**Kenapa:** Mengikuti pola produksi — `Metadata.md` mendeskripsikan skema yang sudah nyata berjalan (bukan yang baru didesain di atas kertas), beda dari `DataSchema.md` yang mendokumentasikan histori/keputusan desain (peran itu yang diisi dokumen M5.2 ini). Dikonfirmasi user setelah membaca `04-serving-data-analyst.md` dan `05-serving-ai-chatbot.md` — keduanya murni konsumen `mart_aggregated`, tidak menyebut pembuatan metadata sebagai output milik mereka, sehingga metadata tetap harus ada sebelum kedua pekerjaan itu mulai (di M5.3, bukan ditunda sampai ke 04/05).

**Ditolak:** Metadata penuh ditulis sekaligus di M5.2 (digabung ke dokumen struktur) — berisiko mendeskripsikan cara hitung yang belum tentu persis sama dengan implementasi SQL final di M5.3, dan menambah beban M5.2 di luar scope literalnya (Output M5.2 hanya minta "skema", bukan data dictionary).

**Dicatat di `docs/keputusan-tertunda.md`** sebagai entri baru (lihat commit terpisah) — keputusan yang sengaja ditunda ke milestone tertentu tetap perlu tercatat di backlog project-wide walau sudah punya rumah yang jelas di M5.3.

## Task Breakdown

10 task, 6 fase, 6 checkpoint (commit + log tiap checkpoint, pola sama M5.1).

### Fase 0 — Fondasi Dimensional Model
1. Inventarisasi seluruh dimension table lintas domain dari 94 metrik — Acceptance: setiap dimension table punya nama, atribut, natural key vs surrogate key, tabel produksi sumber — Verify: setiap kategori/referensi yang muncul di 94 baris M5.1 punya dimension table yang mewakilinya — S

**Checkpoint 1**

### Fase 1 — Fact Table Revenue + F&B
2. Desain fact table(s) Revenue dari 15 baris metrik §1 M5.1 — Acceptance: setiap metrik Cakupan Awal/Khusus punya kolom, grain tidak ambigu — Verify: cross-check 15 baris — S
3. Desain fact table(s) F&B dari 17 baris metrik §2 — sama pola — S

**Checkpoint 2**

### Fase 2 — Fact Table Facility/Ops + Spa & Event
4. Desain fact table(s) Facility/Ops dari 17 baris §3 (termasuk kolom SLA mentah tanpa flag breach) — S
5. Desain fact table(s) Spa & Event dari 16 baris §4 (2 sub-grain: spa vs event/MICE) — S

**Checkpoint 3**

### Fase 3 — Fact Table HR + Corporate/Financial
6. Desain fact table(s) HR dari 13 baris §5 (fact table department/periode + fact table employee/periode terpisah) — S
7. Desain fact table(s) Corporate/Financial dari 16 baris §6 — S

**Checkpoint 4**

### Fase 4 — Kasus Khusus Lintas Domain
8. Desain fact table snapshot pace booking + fact table watchlist HR — Acceptance: kedua tabel terpisah dari fact table utama, grain eksplisit — S

**Checkpoint 5**

### Fase 5 — Audit PII + Finalisasi
9. Audit seluruh kolom berpotensi PII (`dim_employee.full_name`; kolom dari domain `guests_pii`/`guests_profile` bila ada di skema final) — Acceptance: tiap kolom punya keputusan eksplisit — Verify: daftar lengkap di dokumen — S
10. Verifikasi 3 KK sumber + tulis `report.md` — S

**Checkpoint 6 (final)**
