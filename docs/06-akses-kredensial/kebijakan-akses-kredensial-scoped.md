# Kebijakan Akses Kredensial Scoped (RBAC Lapis 2)

**Ditulis untuk:** Milestone 2.6 — Isolasi Akses dan Kredensial Read-Only (`milestones/2.6-isolasi-akses-kredensial-read-only/decisions.md`).
**Cakupan:** Project-wide — seluruh kredensial scoped (service account BigQuery, role Postgres) yang dibuat sepanjang Fase 2, bukan cuma satu konsumen. Sesuai dokumen sumber (`docs/03-implementation-plans/02-serving-data-scientist.md` Milestone 2.6): RBAC lapis kedua ini "menjadi tanggung jawab pemilik infrastruktur data di seluruh sistem ini".

Dokumen ini beda dari `docs/02-requirements/rancangan-rbac-ai-chatbot.md` (Lapis 1 — RBAC level aplikasi chatbot, matriks `role_permissions`) — di sini murni soal **Lapis 2: isolasi kredensial di level database/warehouse**.

## Prinsip

Setiap kredensial baru yang dibuat untuk konsumen/job baru **wajib** least-privilege secara default:
- **BigQuery**: dataset ACL scoped ke SATU dataset (via `bq update` access list), bukan role project-level (`bigquery.dataEditor`/`bigquery.admin` di seluruh project) — kecuali ada alasan eksplisit yang didokumentasikan (lihat pengecualian `dbt-transform` di bawah).
- **PostgreSQL**: role dengan `NOSUPERUSER NOCREATEDB NOCREATEROLE`, grant eksplisit per skema/tabel (whitelist), bukan akses default yang lebih luas dari yang dibutuhkan.
- **Key file/password** dibuat manual oleh pemegang akses project (bukan disimpan di tempat yang bisa diakses otomatis oleh pihak lain), dan **tidak pernah** di-commit ke git (lihat `.gitignore` — `scripts/extract/*.json`).
- **Isolasi diverifikasi lewat uji coba nyata** (connect-as-role, cek query yang seharusnya diizinkan DAN yang seharusnya ditolak) — bukan diasumsikan benar dari niat desain saja. Pakai `scripts/bigquery_common/verify_dataset_isolation.py` untuk kredensial BigQuery baru (CLI generik, tidak perlu file baru per kredensial).

## Inventaris Kredensial (per 2026-08-08)

| Kredensial | Sistem | Scope | Milestone Asal | Bukti Isolasi | Least-Privilege? |
|---|---|---|---|---|---|
| `extract_reader` | PostgreSQL (production Supabase) | SELECT-only, whitelist 23 tabel eksplisit | M2.1 | `scripts/extract/setup_extract_role.py` (inline, verified saat dibuat) + re-verified M2.6 (query ad-hoc, tanpa rotasi password) | Ya |
| `extract-writer` | BigQuery (`nirwana-database-elt`) | Dataset ACL WRITER `raw_production` saja + `bigquery.jobUser` | M2.1 | Manual, dicatat di `milestones/2.1.../decisions.md` — tidak ada script re-runnable | Ya |
| `dbt-transform` | BigQuery (`nirwana-database-elt`) | **Project-level** `bigquery.dataEditor` + `bigquery.jobUser` | M2.2/2.3 | Manual, dicatat di `milestones/2.2.../decisions.md` | **Tidak** — pengecualian sadar (lihat di bawah) |
| `reverse_etl_writer` | PostgreSQL (serving project baru) | Schema-scoped `mart_cleaned` saja (CREATE/DROP/ALTER/RENAME table), `REVOKE ALL ON SCHEMA public` eksplisit | M2.4 | `scripts/reverse_etl/setup_writer_role.py` (inline) + re-verified M2.6 (query ad-hoc, tanpa rotasi password) | Ya |
| `reverse-etl-reader` | BigQuery (`nirwana-database-elt`) | Dataset ACL READER `mart_cleaned` saja + `bigquery.jobUser` | M2.4 | `scripts/reverse_etl/verify_reader_isolation.py` (re-runnable) + re-verified M2.6 | Ya |
| `data-scientist-reader` | BigQuery (`nirwana-database-elt`) | Dataset ACL READER `mart_cleaned` saja + `bigquery.jobUser` | M2.5 | `scripts/bigquery_common/verify_dataset_isolation.py` (re-runnable) + read-only dibuktikan (`CREATE TABLE` ditolak) + re-verified M2.6 | Ya |
| `ml-scoring-writer` | BigQuery (`nirwana-database-elt`) | Dataset ACL WRITER `ml_output` saja + `bigquery.jobUser` | M5.4 | Service account + dataset ACL dibuat via `gcloud`/`bq` (dicatat `milestones/5.4-.../logs.md`); isolasi diverifikasi lewat `scripts/bigquery_common/verify_dataset_isolation.py` begitu key file dibuat user | Ya |

### Pengecualian: `dbt-transform`

`dbt-transform` sengaja **bukan** dataset-scoped sempit — dbt-bigquery memanggil `bigquery.datasets.create` sebelum menulis model apa pun (idempotent, tapi tetap butuh izin ini dipanggil sama sekali), dan dbt di project ini mengelola **banyak dataset dari waktu ke waktu** (`staging`, `mart_cleaned_staging`, `mart_cleaned`, dan dataset baru di masa depan seiring pipeline bertambah) — scoped ke 1 dataset akan berarti mengedit ulang izinnya setiap kali ada dataset baru, bertentangan dengan alasan dbt dipilih (declarative, self-managing). Ini **trade-off sadar**, bukan kelalaian — dicatat eksplisit di `milestones/2.2-layer-staging-cleaning-per-tabel/decisions.md`.

## Siapa Boleh Memegang Kredensial Ini

- **Kredensial per-job** (`extract_reader`, `extract-writer`, `dbt-transform`, `reverse_etl_writer`, `reverse-etl-reader`, `ml-scoring-writer`): hanya dipakai oleh GitHub Actions workflow terjadwal (`extract-production.yml`, `transform-mart-cleaned.yml`, `reverse-etl-mart-cleaned.yml`, `scoring-occupancy-forecast.yml`) via GitHub Secrets, atau dijalankan manual oleh pemilik infrastruktur data untuk debugging/setup. **Tidak** dibagikan ke konsumen data (Data Analyst/Data Scientist/AI Chatbot) — mereka bukan pengguna akhir kredensial ini.
- **`data-scientist-reader`**: satu-satunya kredensial di daftar ini yang memang ditujukan untuk dipegang konsumen akhir (tim Data Scientist) — lihat `scripts/data_scientist_access/README.md` untuk cara pakai. Karena `mart_cleaned` memuat data sensitif penuh (PII, payroll — lihat `docs/03-implementation-plans/02-serving-data-scientist.md` "Prinsip Kunci"), permintaan salinan key file baru untuk anggota tim baru harus lewat pemilik infrastruktur data, bukan diteruskan bebas antar anggota tim.

## Proses Meminta Kredensial Baru

1. Tentukan scope minimum yang benar-benar dibutuhkan (dataset/schema mana, read atau write).
2. Ikuti pola di atas: `bq update` dataset ACL (BigQuery) atau `CREATE ROLE` + grant eksplisit per schema (Postgres) — bukan role project-level/superuser kecuali ada alasan sekuat `dbt-transform` di atas, dan itu pun harus didokumentasikan eksplisit di `decisions.md` milestone terkait.
3. Verifikasi isolasi lewat uji coba nyata sebelum kredensial dipakai produksi — pakai `scripts/bigquery_common/verify_dataset_isolation.py` untuk BigQuery, atau pola inline `setup_*_role.py` untuk Postgres (lihat `scripts/extract/setup_extract_role.py`/`scripts/reverse_etl/setup_writer_role.py` sebagai contoh).
4. Key file/password dibuat manual oleh pemilik infrastruktur data (atau via `gcloud`/SQL langsung), tidak pernah di-commit — tambahkan pattern-nya ke `.gitignore` kalau path baru.
5. Tambahkan 1 baris ke tabel inventaris di atas.

## Rotasi dan Pencabutan

**Gap yang diketahui (belum diselesaikan milestone manapun sejauh ini):** tidak ada rotasi terjadwal otomatis untuk key file/password kredensial mana pun di daftar ini — sama seperti dicatat di `milestones/2.5-api-akses-data-scientist/report.md` Known Gaps. Rotasi manual sejauh ini hanya terjadi insidental (mis. re-run `setup_extract_role.py` yang otomatis rotasi password tiap kali dijalankan ulang — efek samping yang **harus disertai update GitHub Secret terkait**, atau workflow terjadwal akan gagal koneksi).

Untuk mencabut akses (mis. anggota tim Data Scientist keluar): pemilik infrastruktur data membuat key baru (`gcloud iam service-accounts keys create`) dan **menghapus** key lama (`gcloud iam service-accounts keys delete <KEY_ID>`) — bukan menghapus service account itu sendiri (akan mematahkan workflow lain yang mungkin ikut memakainya, kalau ada).
