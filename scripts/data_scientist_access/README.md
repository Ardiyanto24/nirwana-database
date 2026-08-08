# Akses `mart_cleaned` untuk Data Scientist (Milestone 2.5)

Data Scientist mengakses `mart_cleaned` **langsung di BigQuery** (bukan lewat serving PostgreSQL) — training model butuh pemindaian data historis skala besar, kekuatan alami BigQuery (lihat `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` Bagian 7.4). Tidak ada REST API perantara — kamu pakai BigQuery client (Python/R/CLI/notebook) sendiri, diautentikasi dengan kredensial yang sudah di-scope khusus untuk ini.

## 1. Kredensial

Kamu diberi key file service account `data-scientist-reader@nirwana-database-elt.iam.gserviceaccount.com` — **read-only**, dan **hanya bisa membaca dataset `mart_cleaned`** (tidak bisa `raw_production`, `staging`, atau dataset lain apa pun, termasuk `mart_aggregated` begitu dataset itu dibuat nanti — lihat `milestones/2.5-api-akses-data-scientist/decisions.md` Decision 4 untuk kenapa ini terjamin by construction, bukan sekadar diuji manual).

Simpan key file itu di lokasi aman, lalu set environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/ke/gcp-data-scientist-reader-key.json
```

**Jangan** minta atau pakai kredensial lain (`dbt-transform`, `extract-writer`, atau kredensial admin/pemilik project) untuk kebutuhan ini — kalau `data-scientist-reader` tidak cukup (mis. butuh dataset baru), minta scope ditambahkan lewat pemilik infrastruktur data, bukan pinjam kredensial yang lebih luas.

## 2. Contoh Query (Python)

```python
from google.cloud import bigquery

client = bigquery.Client(project="nirwana-database-elt")

df = client.query("""
    SELECT booking_id, property_id, check_in_date, total_amount
    FROM `mart_cleaned.mart_cleaned__bookings`
    LIMIT 100
""").to_dataframe()
```

Jalankan `python scripts/data_scientist_access/example_query.py` (dari repo ini) untuk contoh lengkap yang jalan end-to-end — termasuk query agregasi (`GROUP BY`) yang butuh scan penuh, membuktikan akses row-level tidak dibatasi sampling/windowing.

## 3. Daftar Tabel

Seluruh 23 tabel: `mart_cleaned.mart_cleaned__<nama_tabel>` — daftar lengkap & aturan cleaning per tabel ada di `docs/02-requirements/pemetaan-kebutuhan-konsumen-data-mart.md`. Ingat: `mart_cleaned` **cleaning-only**, tidak ada feature engineering (kolom turunan hasil kalkulasi) — itu tanggung jawab eksperimenmu sendiri. Beberapa dirty-data/missing-value memang sengaja dipertahankan (lihat `warehouse/README.md` untuk daftar lengkap) — bukan bug, itu bagian dari desain untuk fleksibilitas eksperimen kamu sendiri (mis. keputusan dedup 367 baris duplicate di `guests` diserahkan ke kamu, bukan platform).

## 4. Kebijakan Akses

Siapa yang boleh memegang kredensial ini dan batasannya akan didokumentasikan formal di Milestone 2.6 (`milestones/2.6-.../report.md`, belum ada saat dokumen ini ditulis). Dokumen ini (`README.md`) hanya soal **cara pakai** teknis, bukan **kebijakan** siapa yang berwenang.
