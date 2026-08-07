# Milestone 1.1: Inventarisasi dan Baseline Sumber Data Production

**Source:** docs/03-implementation-plans/01-monitoring-data-production-fase1.md (baris 40-55)
**Status:** Done
**Date started:** 2026-08-07

## Contract (from source doc)

- **Lingkup:** Membangun pemahaman menyeluruh dan terdokumentasi atas apa yang akan dimonitor — memetakan karakteristik tiap tabel (volume normal, pola pertumbuhan, kolom kritis bisnis, kolom yang memang dirancang "kotor") dan menentukan skala prioritas (tidak semua 23 tabel butuh kedalaman monitoring yang sama).
- **Output:** (1) Dokumen/tabel pemetaan 23 tabel — volume baseline, kolom kritis bisnis, kolom yang boleh kosong/kotor secara sah, prioritas monitoring (tinggi/sedang/rendah). (2) Daftar business rule yang relevan untuk validasi nilai.
- **Kriteria keberhasilan:** Setiap 23 tabel di 6 database punya klasifikasi prioritas dan catatan karakteristik yang jelas; dokumen bisa dipakai sebagai rujukan langsung oleh milestone-milestone berikutnya (1.2-1.4) tanpa perlu analisis ulang dari nol.
- **Sifat:** Murni observasional/analitis — tidak memasang sistem monitoring apa pun.

## Task Breakdown

- [x] Task 1: Skeleton inventaris 23 tabel (6 DB) dari `Metadata.md`/`DataSchema.md` — Acceptance: semua 23 tabel terdaftar dengan nama DB & tabel — Verify: cocok dengan `DataSchema.md` bagian "Realisasi Volume Data"
- [x] Task 2: Tulis rubrik skor prioritas (bobot volume + kekritisan bisnis + jumlah konsumen downstream) — Acceptance: rubrik terformalisasi dengan bobot eksplisit — Verify: bisa diterapkan konsisten ke seluruh 23 tabel tanpa penilaian ad-hoc
- [x] Task 3: Verifikasi live ke Supabase (row count + NULL-rate sampling kolom kritis, read-only) — Acceptance: setiap tabel punya row count aktual — Verify: query hanya SELECT, tidak ada mutasi
- [x] Task 4: Isi per tabel — baseline volume aktual, pola pertumbuhan, kolom kritis bisnis, kolom kotor/nullable sah + pola & proporsi — Acceptance: 23/23 tabel terisi lengkap — Verify: silang cek dengan `Metadata.md` per tabel
- [x] Task 5: Terapkan skor prioritas per tabel pakai rubrik Task 2 + angka Task 4 — Acceptance: setiap tabel dapat label tinggi/sedang/rendah + skor — Verify: checkpoint review dengan user
- [x] Task 6: Katalog kandidat business rule per kolom kritis (bahasa natural, bukan syntax tool) — Acceptance: setiap kolom kritis di tabel prioritas tinggi/sedang punya minimal satu aturan kandidat — Verify: tidak menyebut tool/dbt/Great Expectations
- [x] Task 7: Rakit `docs/04-monitoring/baseline-inventaris-produksi.md` final — Acceptance: dokumen tunggal memuat semua hasil Task 1-6 — Verify: cek satu per satu terhadap Kriteria Keberhasilan
- [x] Task 8: Tulis `report.md` — Acceptance: setiap Kriteria Keberhasilan dicek eksplisit — Verify: review manual

## Technical Decisions

### Decision: Rubrik skor prioritas monitoring (tinggi/sedang/rendah)

- **Context:** Dokumen sumber menyebut "tidak semua 23 tabel butuh kedalaman monitoring yang sama" tapi tidak mendefinisikan kriteria penentuan prioritas.
- **Decision:** Skor gabungan dari 3 komponen, masing-masing dinilai 1-3 (rendah/sedang/tinggi) lalu dijumlah (rentang skor 3-9):
  1. **Volume/frekuensi perubahan** — tabel besar & sering berubah (transaksional) dapat skor tinggi; tabel referensi statis dapat skor rendah.
  2. **Kekritisan bisnis** — dampak ke revenue/operasional/kepatuhan (RBAC, data personal, laporan keuangan) jika datanya salah/telat.
  3. **Jumlah & sensitivitas konsumen downstream** — berapa milestone/domain RBAC/tabel lain yang bergantung pada tabel ini (mis. `properties`/`employees`/`guests` dipakai hampir semua database lain sebagai FK; `role_permissions_chatbot_v2` adalah jantung RBAC meski hanya 77 baris).
  - Skor 7-9 → **Tinggi**, 5-6 → **Sedang**, 3-4 → **Rendah**.
- **Alternatives considered:** (a) Semata volume baris; (b) Semata kekritisan bisnis.
- **Rejected because:** (a) melewatkan tabel kecil tapi kritis seperti `role_permissions_chatbot_v2` (77 baris, tapi jantung RBAC — kesalahan di sini bisa membocorkan data lintas role) dan `venues`/`properties` (master data kecil tapi jadi FK di banyak tabel lain). (b) berisiko membuat monitoring volume/freshness undersized untuk tabel besar berisiko tinggi (`fnb_transactions`, `staff_shifts`) yang "aman" secara kekritisan individual tapi rentan gangguan operasional akibat volumenya.

### Decision: Sumber baseline volume — live Supabase, bukan hanya dokumentasi

- **Context:** `DataSchema.md` (v0.6) mendokumentasikan volume data sintetis per tabel (~2,53 juta baris/23 tabel), tapi ini snapshot saat dokumen ditulis. Kredensial Supabase (`SUPABASE_DB_URL` di `.env`) sudah diberikan user pada sesi ini.
- **Decision:** Baseline volume final Milestone 1.1 diverifikasi langsung lewat query read-only (`SELECT COUNT(*)`) ke Supabase untuk seluruh 23 tabel, dibandingkan terhadap angka `DataSchema.md`. Selisih dicatat eksplisit di `logs.md`, bukan diam-diam ditimpa.
- **Alternatives considered:** (a) Pakai angka `DataSchema.md` saja tanpa verifikasi; (b) Tunda Milestone 1.1 sampai ada kepastian data production "final".
- **Rejected because:** (a) berisiko baseline sudah basi kalau data production sudah berubah sejak dokumen ditulis (dokumen eksplisit menyebut "akan terus bertambah seiring operasional berjalan"), dan sekarang aksesnya sudah tersedia sehingga tidak ada alasan teknis untuk tidak memverifikasi. (b) tidak realistis untuk sistem yang datanya terus tumbuh — baseline monitoring memang harus berbasis rolling, bukan menunggu kondisi "final" yang tidak akan pernah tercapai.

### Decision: Cakupan katalog business rule — daftar kandidat saja

- **Context:** Output Milestone 1.1 termasuk "daftar business rule yang relevan untuk validasi nilai". Implementasi test aktual (dbt/Great Expectations/dst) belum ditentukan tool-nya.
- **Decision:** Milestone 1.1 hanya mendaftar aturan kandidat per kolom kritis dalam bahasa natural/tabel (mis. "revenue >= 0", "format email valid", "check_out_date > check_in_date"). Tidak ada syntax test tool.
- **Alternatives considered:** Sekalian menuliskan draft syntax test (mis. dbt YAML) di Milestone 1.1.
- **Rejected because:** dokumen sumber eksplisit menyatakan Milestone 1.1 "tidak memasang sistem apa pun" (murni observasional). Menulis syntax tool tertentu mendahului keputusan tooling platform yang belum difinalkan, berisiko harus ditulis ulang di Milestone 1.3 kalau tool yang dipilih berbeda.

### Decision: Lokasi deliverable — `docs/04-monitoring/`

- **Context:** Perlu tempat permanen untuk pemetaan 23 tabel yang bisa dirujuk Milestone 1.2-1.4 tanpa membongkar `milestones/1.1-.../decisions.md` (yang fokus ke keputusan, bukan data).
- **Decision:** `docs/04-monitoring/baseline-inventaris-produksi.md` — folder baru, lanjutan penomoran `01-architecture`/`02-requirements`/`03-implementation-plans`. Folder ini akan menampung hasil kerja monitoring (bukan rancangan) dari Milestone 1.1-1.5 dan Fase 2.
- **Alternatives considered:** (a) Taruh di dalam `report.md` milestone; (b) Taruh di `docs/01-architecture/`.
- **Rejected because:** (a) `report.md` jadi terlalu panjang dan kurang nyaman dirujuk sebagai tabel data oleh milestone lain. (b) `docs/01-architecture/` isinya dokumen rancangan/arsitektur (`Metadata.md`, `DataSchema.md`), sedangkan baseline inventory adalah hasil kerja operasional Milestone 1.1 — mencampur keduanya bikin ambigu mana yang "rancangan" vs "hasil kerja aktual".

## Open Questions Resolved with User

- Q: Rubrik prioritas berbasis apa? → A: Skor gabungan (volume + kekritisan bisnis + konsumen downstream).
- Q: Baseline volume pakai dokumen atau tunggu akses live? → A: User memberikan `.env` Supabase; baseline diverifikasi live.
- Q: Katalog business rule sejauh mana? → A: Katalog saja, implementasi test di Milestone 1.3.
- Q: Deliverable disimpan di mana? → A: `docs/04-monitoring/` (folder baru).
