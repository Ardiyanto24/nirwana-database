# Milestone 3.6: Akses BigQuery Langsung via BI Tool — Decisions

**Sumber:** `docs/03-implementation-plans/04-serving-data-analyst.md`, baris 140-155.
**Prasyarat:** `mart_cleaned` dan `mart_aggregated` sudah tersedia di BigQuery (M2.3/M5.3, selesai). Independen dari Milestone 3.1-3.5 (jalur PostgreSQL) per dokumen sumber sendiri.
**Status:** In Progress
**Date started:** 2026-08-10

## Lingkup Sumber / Contract

- **Lingkup:** Menyediakan jalur akses BigQuery langsung (bukan lewat PostgreSQL) bagi Data Analyst untuk kebutuhan analitis lanjutan — menghubungkan BI tool ke BigQuery dengan kredensial `analyst-readonly` yang di-scope terpisah sesuai `rancangan-arsitektur-data-platform-elt.md` §8.3.
- **Output:**
  1. Kredensial `analyst-readonly` di BigQuery, read-only, di-scope ke `mart_cleaned` dan `mart_aggregated` saja.
  2. Koneksi BI tool ke BigQuery memakai kredensial itu, terdokumentasi.
- **Kriteria Keberhasilan:**
  1. Tim Data Analyst berhasil menjalankan query eksploratif langsung dari BI tool ke `mart_cleaned`/`mart_aggregated` memakai kredensial yang disediakan.
  2. Kredensial `analyst-readonly` terbukti tidak bisa mengakses `raw_production` atau `ml_output` saat diuji coba.
  3. Kredensial terbukti hanya bisa membaca (tidak bisa menulis/mengubah) data.

## Temuan Eksplorasi (sebelum breakdown)

- `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` §8.3 sudah menamai eksplisit `analyst-readonly` sebagai salah satu dari "minimal 4 service account berbeda" sejak desain awal — bukan nama yang perlu diputuskan lagi.
- Preseden pola pembuatan: `data-scientist-reader` (M2.5) — dibuat via `gcloud`/`bq` langsung (bukan script Python baru), key file `scripts/extract/gcp-data-scientist-reader-key.json`, diverifikasi via `scripts/bigquery_common/verify_dataset_isolation.py` (CLI generik, sudah dipakai 4× kredensial sebelumnya: `reverse-etl-reader`, `data-scientist-reader`, `ml-scoring-writer`, `reverse-etl-mart-agg-reader`).
- **Docker Desktop tidak berjalan** di environment ini (dicek langsung, daemon tidak aktif) — opsi menyalakan BI tool sungguhan (mis. Metabase) butuh aksi user yang tidak bisa dipastikan.
- Tidak ada BI tool spesifik yang sudah diputuskan di dokumen manapun (`keputusan-tertunda.md` cuma membahas Metabase/Superset untuk kebutuhan M1.5 monitoring dashboard yang beda kasus, ditolak karena alasan alerting — tidak relevan langsung ke kebutuhan BI eksploratif Data Analyst).

## Keputusan (via AskUserQuestion, dikonfirmasi user)

### 1. Verifikasi KK1: dokumentasi + script Python, bukan koneksi BI tool sungguhan

**Keputusan:** KK1 dibuktikan sejauh yang bisa dicapai tanpa BI tool sungguhan — kredensial dibangun+diverifikasi isolasinya, dibuktikan bisa query lewat script Python (`example_query.py`, pola M2.5), dan panduan koneksi BI tool didokumentasikan generik. **Tidak ada koneksi BI tool sungguhan yang benar-benar dijalankan** — dicatat eksplisit sebagai Known Gap/status Partially Met di `report.md`, bukan diklaim selesai penuh.

**Kenapa:** Docker Desktop tidak berjalan di environment ini, alternatif (Looker Studio via OAuth) tidak benar-benar menguji kredensial `analyst-readonly` yang sama (OAuth pakai identitas berbeda dari service account key). Opsi paling jujur pada implementasi dengan constraint ini: bukti sejauh yang bisa dibuktikan, catat gap-nya eksplisit — pola sama M1.5 (Partially Completed untuk kanal notifikasi eksternal).

**Ditolak:** Metabase via Docker (paling literal memenuhi KK1, tapi butuh Docker Desktop menyala — di luar kendali sesi ini saat ini).

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 2. Pola pembuatan service account: direct `gcloud`/`bq`

Replikasi persis `data-scientist-reader` (M2.5): `gcloud iam service-accounts create analyst-readonly`, dataset ACL READER lewat `bq update` (2× — `mart_cleaned` dan `mart_aggregated`), `roles/bigquery.jobUser` project-level, key file `scripts/extract/gcp-analyst-readonly-key.json`.

### 3. Verifikasi isolasi: reuse `verify_dataset_isolation.py`

CLI generik M2.5, tidak perlu file `verify_*.py` baru.

### 4. Bukti akses terprogram: `scripts/analyst_bi_access/example_query.py`

Pola persis `scripts/data_scientist_access/example_query.py`, query sample ke `mart_cleaned` DAN `mart_aggregated` (M2.5 cuma 1 dataset).

### 5. Dokumentasi koneksi BI tool: generik

Karena tidak ada tool yang benar-benar disambungkan — jelaskan pola koneksi untuk kelas BI tool relevan (Metabase key-upload, Looker Studio OAuth/impersonation), bukan instruksi 1 tool yang diklaim sudah diuji.

### 6. `.env`/`.env.example`

`ANALYST_READONLY_CREDENTIALS=scripts/extract/gcp-analyst-readonly-key.json`, pola sama `DATA_SCIENTIST_READER_CREDENTIALS`.

## Task Breakdown

**Kenapa 3 task / 3 checkpoint:** M3.6 adalah 1 kredensial tunggal menjangkau 2 dataset secara seragam — tidak ada split domain. Bentuk kerja alaminya 3 unit berurutan: (1) kredensial+isolasi, (2) bukti akses terprogram, (3) dokumentasi+tutup.

### Fase 0 — Kredensial + Isolasi
1. Buat service account + ACL 2 dataset + key file. Verifikasi `verify_dataset_isolation.py` (allow `mart_cleaned`/`mart_aggregated`, deny `raw_production`/`ml_output`, deny write). Update `.env`/`.env.example` — S

**✅ Checkpoint 1** — commit + log.

### Fase 1 — Bukti Akses Terprogram
2. `scripts/analyst_bi_access/example_query.py` + `README.md` (dokumentasi koneksi BI tool generik) — S

**✅ Checkpoint 2** — commit + log.

### Fase 2 — Finalisasi
3. `docs/08-serving-data-analyst/bi-tool-analyst.md`, verifikasi ulang KK2+KK3, `report.md` dengan KK1 Partially Met — S

**✅ Checkpoint 3 (final)** — commit; tanya user sebelum push.
