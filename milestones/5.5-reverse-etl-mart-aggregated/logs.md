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

## 2026-08-08 -- Checkpoint 2: copy & adaptasi sync.py (Fase 1)

User membuat key file `gcp-reverse-etl-mart-agg-reader-key.json` dan mengisi `.env` sendiri. `mart_aggregated_tables.py` ditulis -- 76 tabel (27 dim + 49 fact, dikelompokkan per folder dbt), **dicocokkan otomatis terhadap isi riil `warehouse/models/mart_aggregated/`** (bukan disalin dari dokumentasi) -- exact match, 0 selisih, 0 duplikat. `sync.py` ditulis (copy `scripts/reverse_etl/sync.py`, Keputusan #4) -- perbedaan dari versi M2.4: `BQ_DATASET`/`PG_SCHEMA="mart_aggregated"`, `bq_table_id` TANPA prefix `mart_cleaned__` (tabel `mart_aggregated` di BigQuery memang tidak diprefix), `log_sync_result` menulis kolom `dataset_name='mart_aggregated'` (Keputusan #9).

**Smoke test** `sync.py --table dim_property` -- sukses, `BigQuery=6 Postgres=6`.

## 2026-08-08 -- Checkpoint 3: sync penuh 76 tabel + verifikasi independen (Fase 2)

`sync.py --all` dijalankan (background, ~beberapa menit karena beberapa tabel besar) -- **76/76 tabel synced, 0 mismatch**. Diverifikasi independen (bukan cuma percaya log script sendiri):
- Query langsung `information_schema.tables` schema `mart_aggregated` di Postgres: **76 tabel**, cocok persis. **0 tabel `__staging`/`__old` tersisa** (swap bersih, tidak ada sampah).
- Spot-check `COUNT(*)` 3 tabel (`dim_property`=6, `fact_revenue_property_daily`=5485, `fact_hr_watchlist_monthly`=24036) -- cocok dengan yang dilaporkan `sync.py`.
- `monitoring.reverse_etl_sync_log`: 77 baris `dataset_name='mart_aggregated'` (76 dari `--all` + 1 dari smoke test Checkpoint 2 -- `dim_property` disync 2x, sesuai ekspektasi), semua `status='synced'`, 0 `mismatch_aborted`. Baris `mart_cleaned` (93, dari M2.4) tidak terganggu -- migrasi additive terbukti backward-compatible.

**KK1 sumber M5.5 (seluruh tabel tersedia, row count cocok) terbukti** untuk 76/77 tabel (1 tabel ML M5.4 sengaja dikecualikan, Keputusan #2 -- dicatat sebagai deviasi eksplisit di `report.md` nanti).

## 2026-08-08 -- Checkpoint 4: REINDEX/ANALYZE + index contoh + uji coba terkontrol (Fase 3)

`example_indexes.py` (1 index contoh, ditandai provisional eksplisit di docstring) + `reindex_analyze.py` ditulis, dengan koreksi Keputusan #3 sudah diterapkan sejak awal (`CREATE INDEX IF NOT EXISTS` dulu, baru `REINDEX`+`ANALYZE`).

**Baseline (SEBELUM index):** `EXPLAIN ANALYZE` terhadap `fact_revenue_property_daily WHERE property_id='P05' AND period_date='2023-12-03'` -> `Seq Scan`, **33.088 ms**, "Rows Removed by Filter: 5484" (full table scan literal).

`reindex_analyze.py --table fact_revenue_property_daily` dijalankan -> index `idx_fact_revenue_property_daily_property_period` dibuat.

**Setelah index:** `EXPLAIN ANALYZE` query sama -> `Index Scan using idx_fact_revenue_property_daily_property_period`, **2.386 ms** -- **~14x lebih cepat**, plan berubah dari Seq Scan ke Index Scan. Bukti konkret KK3 (bukan diasumsikan).

**Uji coba terkontrol tambahan (membuktikan mekanisme benar-benar DIPERLUKAN, bukan cuma dekoratif):** `sync.py --table fact_revenue_property_daily` dijalankan ulang (simulasi swap hari berikutnya) -> `pg_indexes` dicek: **index HILANG TOTAL** (`[]`), persis prediksi koreksi Keputusan #3 (staging table baru tidak pernah punya index). `reindex_analyze.py --table fact_revenue_property_daily` dijalankan lagi -> index **kembali ada**, `EXPLAIN ANALYZE` kembali `Index Scan` (0.743 ms). Siklus hilang->pulih dibuktikan nyata, bukan cuma teori "REINDEX aman dijalankan kapan saja."