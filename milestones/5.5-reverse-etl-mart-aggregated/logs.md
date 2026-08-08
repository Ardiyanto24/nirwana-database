# Milestone 5.5: Reverse ETL Mart Aggregated ke PostgreSQL — Logs

## 2026-08-08 -- Checkpoint 1: kredensial + schema Postgres + migrasi sync log (Fase 0)

`decisions.md` ditulis (10 keputusan: 3 via AskUserQuestion, 7 teknis dikunci mengikuti preseden M2.4/M5.3/M5.4).

**Migrasi `monitoring.reverse_etl_sync_log`** (Keputusan #9): `ALTER TABLE ... ADD COLUMN IF NOT EXISTS dataset_name text NOT NULL DEFAULT 'mart_cleaned'` dijalankan live terhadap production Supabase, diverifikasi via `information_schema.columns` -- kolom baru ada, backward-compatible (baris M2.4 lama otomatis `'mart_cleaned'`). `scripts/reverse_etl/schema_monitoring.sql` diupdate mencantumkan kolom ini di `CREATE TABLE` juga (fresh-deploy tidak perlu langkah `ALTER` terpisah).

**Schema + role Postgres** (`scripts/reverse_etl_mart_aggregated/`, Keputusan #4/#5/#6): `connections.py`, `schema.sql`, `setup_serving_schema.py` ditulis (copy pola M2.4, bukan diimpor) -- dijalankan, `mart_aggregated` schema berhasil dibuat di serving project yang sama (M2.4). `setup_writer_role.py` ditulis dan dijalankan -- role `reverse_etl_mart_aggregated_writer` dibuat, 4 verifikasi isolasi PASS: CREATE/RENAME/DROP di `mart_aggregated` diizinkan, CREATE di `public`/`CREATE SCHEMA` ditolak, **dan SELECT ke `mart_cleaned` (kredensial M2.4) juga ditolak** (dicek eksplisit untuk membuktikan isolasi antar-kredensial, bukan cuma isolasi dari `public`). `REVERSE_ETL_MART_AGGREGATED_WRITER_DB_URL` tertulis ke `.env`.

**Kredensial BigQuery**: `gcloud iam service-accounts create` untuk reader baru -- **nama awal `reverse-etl-mart-aggregated-reader` (35 char) ditolak GCP** (`INVALID_ARGUMENT`, limit 30 karakter) -- dipersingkat jadi `reverse-etl-mart-agg-reader` (27 char), sukses dibuat. `bigquery.jobUser` di-grant project-level. Dataset ACL `mart_aggregated`: tambah entry READER via `bq show`/`bq update` round-trip (pola sama M5.4 Checkpoint 1/2). Key file **belum dibuat** -- assistant tidak membuat key file kredensial mentah (prinsip project), user perlu jalankan sendiri:

```bash
gcloud iam service-accounts keys create scripts/extract/gcp-reverse-etl-mart-agg-reader-key.json --iam-account=reverse-etl-mart-agg-reader@nirwana-database-elt.iam.gserviceaccount.com
```

lalu isi `.env`:
```
REVERSE_ETL_MART_AGGREGATED_READER_CREDENTIALS=scripts/extract/gcp-reverse-etl-mart-agg-reader-key.json
```

`.env.example` diupdate dengan 2 baris baru (reader BigQuery, writer Postgres).