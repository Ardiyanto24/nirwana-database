# Milestone 2.5 — API Akses Data Scientist — Decisions

**Sumber:** `docs/03-implementation-plans/02-serving-data-scientist.md`, baris 142-157.
**Prasyarat:** Milestone 2.4 (Reverse ETL ke serving PostgreSQL) — Completed, kedua KK terpenuhi.

## Lingkup Sumber

Menyediakan jalur akses terprogram bagi Data Scientist ke `mart_cleaned` — dokumen arsitektur (Bagian 7.4) menegaskan Data Scientist **tetap di BigQuery langsung**, bukan Postgres (butuh scan data historis skala besar, kekuatan alami BigQuery). Dua Kriteria Keberhasilan sumber:
1. Tim Data Scientist berhasil mengambil data dari `mart_cleaned` secara terprogram, tanpa memerlukan akses langsung ke kredensial admin/service account inti.
2. Akses yang diberikan bersifat read-only dan terisolasi dari layer raw maupun `mart_aggregated`.

## Keputusan (via AskUserQuestion, dikonfirmasi user)

### 1. Bentuk akses: BigQuery client langsung + kredensial scoped, TANPA REST API perantara

**Keputusan:** Data Scientist memakai BigQuery client (Python/R/CLI) sendiri, autentikasi lewat service account key yang di-scope ke `mart_cleaned` saja. Tidak ada layer REST API tambahan.

**Kenapa:** Selaras dengan arsitektur Bagian 7.4 (Data Scientist tetap di BigQuery untuk scan besar — REST API di depan BigQuery berisiko jadi bottleneck, beda karakteristik dari API Postgres M1.6 yang melayani snapshot kecil) dan pola precedent project ini (`extract-writer`, `reverse-etl-reader` keduanya begini).

**Ditolak:** REST API perantara (mirip pola M1.6 `api/`) — menambah kerumitan signifikan dan berlawanan dengan alasan arsitektur kenapa Data Scientist tetap di BigQuery.

### 2. Pembagian M2.5 vs M2.6

**Konteks:** M2.5 (Output: "mekanisme akses + kredensial") dan M2.6 (Output: "service account read-only, terisolasi, teruji") tumpang tindih di teks sumbernya sendiri — KK M2.5 sendiri sudah minta "read-only dan terisolasi". Dokumen sumber cuma bilang isolasi "jangan menyatu diam-diam ke M2.5" tanpa merinci lebih jauh.

**Keputusan:** M2.5 membangun kredensial least-privilege yang SUDAH teruji penuh (bukan sementara) — pakai pola persis `extract-writer`/`reverse-etl-reader` (service account scoped + uji isolasi di milestone yang sama), sekaligus memenuhi KK M2.5 secara literal tanpa celah keamanan sementara. M2.6 nantinya fokus ke dokumentasi kebijakan akses (siapa boleh pakai kredensial ini, batasannya) yang MERUJUK ke kredensial & bukti isolasi yang sudah dibangun M2.5 — bukan membangun ulang service account/uji isolasi dari nol.

**Ditolak:** M2.5 cuma putuskan bentuk akses + kredensial sementara/longgar, M2.6 baru bangun & uji isolasi sungguhan — lebih setia ke kalimat literal dokumen sumber, tapi menyisakan celah keamanan sementara antara M2.5 selesai dan M2.6 dimulai.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 3. Nama service account: `data-scientist-reader`

Dataset ACL READER di `mart_cleaned` SAJA + `roles/bigquery.jobUser` project-level, pola identik `extract-writer`/`reverse-etl-reader`. Key file dibuat manual user kalau diblokir classifier (pola berulang M2.1-2.4, meski di M2.4 ternyata tidak diblokir sesi itu).

### 4. Isolasi dari `mart_aggregated` (KK#2) dibuktikan by construction, bukan uji langsung

Dataset `mart_aggregated` belum ada di project ini (scope kerja terpisah, lihat catatan "Tidak termasuk" di dokumen sumber). Karena model akses BigQuery adalah dataset-scoped ACL whitelist (kredensial cuma granted eksplisit ke `mart_cleaned`), kredensial ini TIDAK BISA membaca `mart_aggregated` begitu dataset itu dibuat nanti — bukan karena diuji, tapi karena tidak pernah diberi akses sama sekali. Dicatat eksplisit di `report.md`, bukan diklaim "sudah diuji" secara menyesatkan.

### 5. Refactor: generalisasi `verify_reader_isolation.py` jadi helper reusable

Dipakai ulang untuk `data-scientist-reader` (bukan copy-paste ke-3 kalinya) — DRY improvement murah karena pola sudah identik 2x sebelumnya (`extract-writer` diuji manual, `reverse-etl-reader` via script).

### 6. Dokumentasi cara pakai co-located dengan kode

`scripts/data_scientist_access/README.md` (bukan folder `docs/` baru) — pola sama `warehouse/README.md` yang co-located dengan project dbt-nya.

## Task Breakdown

5 task, 2 fase, 2 checkpoint (commit + push + log tiap checkpoint, pola sama M2.1-2.4).

### Fase 1 — Kredensial Least-Privilege
1. Buat service account `data-scientist-reader` (dataset ACL READER `mart_cleaned` + `bigquery.jobUser`).
2. Generalisasi `verify_reader_isolation.py` jadi helper reusable, pakai untuk verifikasi Task 1.

**Checkpoint 1**

### Fase 2 — Demonstrasi Akses + Dokumentasi
3. Tulis contoh/demo script (`scripts/data_scientist_access/example_query.py`) yang membuktikan akses terprogram end-to-end HANYA pakai kredensial `data-scientist-reader`.
4. Tulis `scripts/data_scientist_access/README.md` (autentikasi, contoh query/panggilan).
5. Verifikasi 2 Kriteria Keberhasilan sumber + tulis `report.md`.

**Checkpoint 2 (final)**
