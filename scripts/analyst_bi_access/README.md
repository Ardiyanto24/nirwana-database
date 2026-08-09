# Akses BigQuery Langsung untuk Data Analyst (Milestone 3.6)

Data Analyst mengakses `mart_cleaned` dan `mart_aggregated` **langsung di BigQuery** (bukan lewat serving PostgreSQL M3.1-3.5) untuk kebutuhan analitis lanjutan yang tidak tersedia di serving layer — mis. kombinasi tabel/agregasi yang belum tentu terwakili di struktur PostgreSQL, atau eksplorasi skala besar yang secara alami lebih murah dijalankan di BigQuery (lihat `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` §2.2/§8.1). Jalur ini **pelengkap**, bukan pengganti, endpoint API (M3.4) dan view PostgreSQL (M3.2).

> **Status jujur (per M3.6 `report.md`)**: kredensial dan bukti akses terprogram di dokumen ini **sudah** diverifikasi penuh terhadap BigQuery sungguhan. Koneksi BI tool GUI sungguhan (Metabase/Looker Studio/dst) **belum** benar-benar dijalankan di sesi ini — Docker Desktop tidak aktif saat milestone ini dikerjakan. Panduan di bawah adalah instruksi teknis yang benar untuk tiap kelas BI tool, tapi belum dibuktikan end-to-end oleh operator sungguhan. Lihat Known Gaps di `milestones/3.6-akses-bigquery-bi-tool/report.md`.

## 1. Kredensial

Kamu diberi key file service account `analyst-readonly@nirwana-database-elt.iam.gserviceaccount.com` — **read-only**, dan **hanya bisa membaca dataset `mart_cleaned` dan `mart_aggregated`** (tidak bisa `raw_production` atau `ml_output`, diverifikasi lewat `scripts/bigquery_common/verify_dataset_isolation.py` — lihat bukti di `decisions.md`/`logs.md` milestone ini).

Simpan key file di lokasi aman, lalu set environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/ke/gcp-analyst-readonly-key.json
```

**Jangan** minta atau pakai kredensial lain (`data-scientist-reader`, `dbt-transform`, atau kredensial admin) untuk kebutuhan ini — kalau `analyst-readonly` tidak cukup, minta scope ditambahkan lewat pemilik infrastruktur data.

## 2. Contoh Query Terprogram (Python)

```python
from google.cloud import bigquery

client = bigquery.Client(project="nirwana-database-elt")

df = client.query("""
    SELECT booking_id, property_id, check_in_date, total_amount
    FROM `mart_cleaned.mart_cleaned__bookings`
    LIMIT 100
""").to_dataframe()
```

Jalankan `python scripts/analyst_bi_access/example_query.py` (dari repo ini) untuk contoh lengkap yang jalan end-to-end — query row-level `mart_cleaned` DAN agregat `mart_aggregated` sekaligus, membuktikan kredensial menjangkau kedua dataset.

## 3. Koneksi BI Tool (panduan generik, belum diuji end-to-end — lihat catatan status di atas)

Tidak ada 1 BI tool yang ditetapkan wajib dipakai (dokumen sumber sengaja generik: "BI tool yang dipakai tim analyst"). Dua pola koneksi paling umum untuk BigQuery:

### a. Tool yang menerima upload JSON key langsung (mis. Metabase, Redash, DBeaver)

Kebanyakan tool kelas ini punya form setup koneksi BigQuery yang minta: **Project ID** (`nirwana-database-elt`) + **Service Account JSON key file** (upload `gcp-analyst-readonly-key.json` langsung). Setelah tersambung, dataset yang terlihat otomatis terbatas ke `mart_cleaned`/`mart_aggregated` (ACL-enforced di sisi BigQuery, bukan di sisi tool) — analyst tidak perlu konfigurasi tambahan untuk isolasi.

### b. Tool berbasis OAuth akun Google (mis. Looker Studio, Google Sheets Connected Sheets)

Tool kelas ini biasanya login pakai akun Google pribadi, bukan upload key file — supaya request BigQuery-nya memakai izin `analyst-readonly` (bukan izin akun pribadi analyst yang mungkin lebih luas atau malah tidak punya akses sama sekali), perlu **service account impersonation**: akun Google analyst diberi role `roles/iam.serviceAccountTokenCreator` pada `analyst-readonly@nirwana-database-elt.iam.gserviceaccount.com`, lalu pilih "impersonate service account" saat setup data source di tool tersebut. Langkah IAM tambahan ini **belum dikonfigurasi** — di luar cakupan yang sudah diverifikasi milestone ini, catat sebagai langkah lanjutan kalau tim benar-benar memakai jalur OAuth.

## 4. Daftar Tabel

- `mart_cleaned.mart_cleaned__<nama_tabel>` — 23 tabel row-level, daftar lengkap `docs/02-requirements/pemetaan-kebutuhan-konsumen-data-mart.md`.
- `mart_aggregated.<fact/dim_...>` — 46 tabel agregat, daftar lengkap `docs/07-mart-aggregated/DataSchema-mart-aggregated.md`.

## 5. Kebijakan Akses

Dicatat formal di `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` (inventaris project-wide) dan `docs/08-serving-data-analyst/bi-tool-analyst.md` (Output resmi M3.6).
