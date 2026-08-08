# Milestone 5.5: Reverse ETL Mart Aggregated ke PostgreSQL — Decisions

**Source:** `docs/03-implementation-plans/03-mart-aggregated-owner.md`, baris 122-140.
**Status:** Done
**Date started:** 2026-08-08

## Contract (from source doc)

- **Lingkup:** Membangun job reverse ETL yang mendorong seluruh `mart_aggregated` (full history) dari BigQuery ke PostgreSQL, strategi full refresh dengan swap table, validasi pasca-sync (row count parity), dan mekanisme `REINDEX`/`ANALYZE` pasca-swap (karena tabel hasil swap tidak otomatis mewarisi statistik index dari tabel lama).
- **Output:**
  1. Job reverse ETL `mart_aggregated` berjalan terjadwal, full refresh + swap table.
  2. Row count parity check otomatis pasca-sync.
  3. Mekanisme `REINDEX`/`ANALYZE` terpicu otomatis (atau tersedia sebagai langkah eksplisit) setiap kali swap table selesai.
- **Kriteria Keberhasilan:**
  1. Seluruh tabel `mart_aggregated` tersedia di PostgreSQL, jumlah baris cocok dengan versi BigQuery pasca-sync.
  2. Swap table tidak mengganggu query konsumen (Data Analyst maupun AI Chatbot) yang sedang berjalan.
  3. Statistik index pasca-swap terbukti ter-refresh (`EXPLAIN ANALYZE` pada query representatif tidak menunjukkan degradasi dibanding sebelum swap).

## Temuan Eksplorasi

- `scripts/reverse_etl/sync.py` (M2.4) sudah pola lengkap yang langsung reusable: baca BigQuery paginated (`bq_client.list_rows`), bulk load ke Postgres staging table via `psycopg2.copy_expert` (COPY text-format, batch 50.000 baris — bukan INSERT baris-per-baris, tabel besar seperti `fnb_transactions` M2.4 ~902k baris jadi alasannya), gate row-count-parity **sebelum** swap (kalau BigQuery `COUNT(*)` ≠ Postgres staging `COUNT(*)`, staging di-drop, tabel live tidak tersentuh), swap via `ALTER TABLE ... RENAME` (tabel live → `__old`, staging → nama live, `__old` di-drop).
- `scripts/reverse_etl/connections.py`: 3 helper koneksi — `get_serving_connection` (admin, `SERVING_DB_URL`, setup-only), `get_serving_writer_connection` (least-privilege, `REVERSE_ETL_WRITER_DB_URL`, dipakai `sync.py` sehari-hari), `get_production_connection` (re-export dari `scripts/monitoring/db.py`, sengaja dinamai beda dari `db.py` untuk hindari collision import — pelajaran M2.1).
- `scripts/reverse_etl/setup_writer_role.py`: buat/rotate role Postgres `reverse_etl_writer` (`NOSUPERUSER NOCREATEDB NOCREATEROLE`), `REVOKE ALL ON SCHEMA public`, `GRANT USAGE, CREATE ON SCHEMA mart_cleaned`, verifikasi isolasi empiris (CREATE/RENAME/DROP di schema itu diizinkan, CREATE di `public`/`CREATE SCHEMA` ditolak), tulis `REVERSE_ETL_WRITER_DB_URL` ke `.env`.
- `scripts/reverse_etl/test_no_downtime_swap.py`: thread background poll `SELECT COUNT(*)` tiap 20ms via koneksi readonly, sementara 8 siklus `sync_table()` penuh dijalankan foreground terhadap tabel yang sama — hasil M2.4: 274 query konkuren, 0 error. Bukti empiris `RENAME` cepat & aman, bukan cuma klaim teori locking Postgres.
- **Tidak ada mekanisme REINDEX/ANALYZE di manapun di repo ini** — genuinely ground baru untuk M5.5. `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` Bagian 9.3.2 sudah dokumentasikan *kenapa*-nya ("tabel baru hasil swap tidak otomatis mewarisi statistik index dari tabel lama"). Index sungguhan (Milestone 3.3, `04-serving-data-analyst.md`) **belum dibangun** — dokumen itu sendiri sudah punya catatan ketergantungan eksplisit ke M5.5.
- `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`: `reverse-etl-reader` (BigQuery) dan `reverse_etl_writer` (Postgres) scoped hanya ke `mart_cleaned` — tidak bisa dipakai ulang untuk `mart_aggregated` tanpa melanggar prinsip least-privileged-per-dataset yang sudah konsisten dipakai project ini.
- `monitoring.reverse_etl_sync_log` (`scripts/reverse_etl/schema_monitoring.sql`): kolom `table_name, bq_row_count, pg_row_count, status, synced_at` — **tidak ada kolom pembeda dataset**. Nama tabel `mart_cleaned` (mis. `bookings`) dan `mart_aggregated` (mis. `fact_revenue_room_type_daily`) sudah pasti tidak akan tabrakan secara nilai, tapi query "seluruh sync M5.5 sejauh ini" tidak bisa langsung difilter tanpa kolom pembeda — perlu migrasi additive kecil.
- `mart_aggregated` BigQuery: tabel **tanpa prefix domain** di nama tabelnya (`dim_property`, `fact_revenue_room_type_daily`, dst) — beda dari `mart_cleaned` yang tabelnya diprefix `mart_cleaned__` mengikuti pola `ref()` dbt. Jadi tidak perlu logic strip-prefix seperti `sync.py` M2.4.
- Terhitung ulang langsung dari `warehouse/models/mart_aggregated/` (bukan cuma dari dokumentasi): **76 model** di luar `ml_feedback/` (27 dimension + 49 fact), persis cocok jumlah resmi M5.3.

## Keputusan (via AskUserQuestion)

### 1. Discovery tabel: hardcoded list (konsisten M2.4)

**Keputusan:** `scripts/reverse_etl_mart_aggregated/mart_aggregated_tables.py` — daftar 76 tabel eksplisit, dikelompokkan per folder dbt (`corporate_master`, `reservation_revenue`, `fnb_operations`, `facility_maintenance`, `spa_event`, `hr`, `corporate_financial` — 2 grup terakhir dari pemecahan `hr_finance/` M5.3) untuk keperluan `--domain`.

**Kenapa:** Konsisten preseden M2.4 (`serving_tables.py`) dan filosofi eksplisit-di-mana-mana project ini.

**Ditolak:** Dynamic discovery dari `INFORMATION_SCHEMA.TABLES` — bisa otomatis menyinkronkan tabel yang belum sengaja stabil kalau `promote.py` gagal sebagian.

### 2. Tabel ML provisional (M5.4): DITUNDA, tidak disinkronkan — dengan catatan eksplisit

**Keputusan:** `fact_ml_occupancy_forecast_property_room_type` **tidak** masuk `mart_aggregated_tables.py`. Konsekuensi ini dicatat eksplisit di `report.md` sebagai deviasi sadar dari kata "seluruh `mart_aggregated`" di KK1 sumber, plus 1 baris tambahan di addendum M5.4 `docs/07-mart-aggregated/DataSchema-mart-aggregated.md` menandai status "belum disinkronkan ke serving layer, menunggu skema final ML Engineer."

**Kenapa:** Skema tabel itu sendiri belum final — menyinkronkan sesuatu yang strukturnya bisa berubah kapan saja ke serving layer berisiko konsumen membangun kontrak di atas skema yang belum stabil.

### 3. REINDEX/ANALYZE: mekanisme generik (aman tanpa index) + index contoh untuk verifikasi mekanisme

**Keputusan:** `scripts/reverse_etl_mart_aggregated/reindex_analyze.py` — 3 langkah pasca setiap swap: (1) `CREATE INDEX IF NOT EXISTS` untuk tiap index yang terdaftar di `example_indexes.py`, (2) `REINDEX TABLE`, (3) `ANALYZE`. Ditambah 1-2 index contoh di 1-2 tabel representatif (kandidat: `fact_revenue_property_daily` pada `(property_id, period_date)`, sesuai kolom yang disebut arsitektur Bagian 9.3.2 untuk pola akses chatbot) khusus untuk membuktikan mekanisme `EXPLAIN ANALYZE` before/after bekerja nyata.

**Koreksi saat implementasi:** draf awal cuma menyebut "`REINDEX TABLE`+`ANALYZE`" — ternyata **tidak cukup sendirian**. Tabel staging di `sync.py` dibuat baru tiap sync (`DROP TABLE IF EXISTS` + `CREATE TABLE` cuma kolom, tanpa index apa pun), lalu di-RENAME jadi tabel live. Artinya tiap swap, tabel live yang baru **kehilangan seluruh index** (bukan sekadar index basi/stale statistik) — `REINDEX` (yang cuma membangun ulang index yang SUDAH ADA) tidak bisa mengembalikan index yang hilang total. Mekanisme yang benar: **`CREATE INDEX IF NOT EXISTS` dulu** (mengembalikan index yang hilang akibat swap) baru `REINDEX`+`ANALYZE` (higienis untuk kasus non-swap/index yang sudah ada). Ini persis alasan `03-mart-aggregated-owner.md` menugaskan mekanisme ini ke pemilik `mart_aggregated`, bukan konsumen — konsumen tidak akan tahu index mereka hilang total tiap swap kalau tidak ada mekanisme eksplisit ini.

**Kenapa:** Index sungguhan (Milestone 3.3) belum ada — KK3 sumber tidak bisa diverifikasi bermakna tanpa satu pun index untuk dites. Index contoh **eksplisit ditandai provisional/contoh**, bukan desain index final M3.3 (pola sama "provisional" M5.4).

**Ditolak:** Menunda verifikasi KK3 sepenuhnya sampai M3.3 dibangun.

## Keputusan Teknis Lain (dikunci tanpa AskUserQuestion — mengikuti preseden project)

### 4. Folder baru `scripts/reverse_etl_mart_aggregated/` — copy penuh dari `scripts/reverse_etl/`, bukan diparameterisasi

Mengikuti preseden `scripts/mart_aggregated/promote.py` (copy dari `scripts/mart_cleaned/promote.py`, M5.3). Isi: `connections.py`, `schema.sql`, `setup_serving_schema.py`, `setup_writer_role.py`, `mart_aggregated_tables.py`, `sync.py`, `test_no_downtime_swap.py`, `reindex_analyze.py`.

### 5. Serving Postgres: schema baru `mart_aggregated` di project serving yang SUDAH ADA

Reuse project Supabase serving M2.4 (sudah terpisah dari production) — cukup `CREATE SCHEMA IF NOT EXISTS mart_aggregated`, bukan project baru lagi.

### 6. Kredensial baru, scoped `mart_aggregated` — bukan memperluas kredensial M2.4

- `reverse-etl-mart-agg-reader` (BigQuery, dataset ACL READER `mart_aggregated` + `bigquery.jobUser`) — **nama dipersingkat saat implementasi**: GCP service account ID dibatasi maks 30 karakter, `reverse-etl-mart-aggregated-reader` (35 char) ditolak (`INVALID_ARGUMENT`). Env var tetap deskriptif penuh: `REVERSE_ETL_MART_AGGREGATED_READER_CREDENTIALS`, key file `scripts/extract/gcp-reverse-etl-mart-agg-reader-key.json` (pola sama semua key BigQuery lain, tetap di folder `scripts/extract/` yang sudah di-gitignore).
- `reverse_etl_mart_aggregated_writer` (Postgres, schema-scoped `mart_aggregated` saja, `REVOKE ALL ON SCHEMA public`). Env var: `REVERSE_ETL_MART_AGGREGATED_WRITER_DB_URL`.

Konsisten prinsip least-privilege `kebijakan-akses-kredensial-scoped.md` — kredensial terpisah per dataset supaya rotasi/pencabutan salah satu tidak memengaruhi yang lain.

### 7. Row-count-parity: gate SEBELUM swap (identik M2.4 Keputusan #5)

Sama persis pola M2.4 — staging table di-COUNT, dibandingkan ke BigQuery COUNT, swap cuma jalan kalau cocok.

### 8. No-downtime swap: adaptasi `test_no_downtime_swap.py` (poll baca 20ms + N siklus swap konkuren)

Pola sama M2.4.

### 9. `monitoring.reverse_etl_sync_log`: tambah kolom `dataset_name`, migrasi additive

**Keputusan:** `ALTER TABLE monitoring.reverse_etl_sync_log ADD COLUMN IF NOT EXISTS dataset_name text NOT NULL DEFAULT 'mart_cleaned'` — kolom baru, backward-compatible (baris M2.4 lama otomatis terisi `'mart_cleaned'`, `sync.py` M2.4 tidak perlu diubah). Script M5.5 (`log_sync_result` versi baru) menulis eksplisit `dataset_name='mart_aggregated'` tiap insert.

**Kenapa:** Tetap 1 tabel log terpusat (prinsip "monitoring tetap terpusat" — `CLAUDE.md`), bukan tabel baru terpisah, tapi butuh 1 kolom pembeda supaya query "sync M5.5 sejauh ini" bisa difilter eksplisit tanpa menerka dari nama tabel.

### 10. Workflow baru `reverse-etl-mart-aggregated.yml`, trigger `workflow_run` off `"Transform Mart Aggregated"`

Pola sama `reverse-etl-mart-cleaned.yml` — dependency data nyata (`mart_aggregated` harus fresh dulu sebelum disinkronkan), bukan time-buffer.

## Task Breakdown

7 fase, 7 checkpoint (commit tiap checkpoint, push begitu ada yang butuh verifikasi CI sungguhan — pelajaran M5.4: jangan cuma baca sintaks, trigger run nyata).

### Fase 0 — Setup: kredensial + schema Postgres + migrasi sync log
1. Cek/apply migrasi `dataset_name` ke `reverse_etl_sync_log` (Keputusan #9). `setup_serving_schema.py` (schema `mart_aggregated`) + `setup_writer_role.py` (role `reverse_etl_mart_aggregated_writer`). Buat service account BigQuery `reverse-etl-mart-aggregated-reader` (dataset ACL READER, `bigquery.jobUser`) — key file dibuat manual oleh user.

**Checkpoint 1**

### Fase 1 — Copy & adaptasi script reverse ETL
2. `scripts/reverse_etl_mart_aggregated/` — `connections.py`, `mart_aggregated_tables.py` (76 tabel per folder dbt), `sync.py` (BQ_DATASET/PG_SCHEMA=`mart_aggregated`, tanpa prefix `mart_cleaned__`, log ke `reverse_etl_sync_log` dengan `dataset_name`).

**Checkpoint 2**

### Fase 2 — Sync manual pertama + row-count parity
3. Jalankan `sync.py --all` manual, verifikasi row count 76 tabel cocok BigQuery vs Postgres.

**Checkpoint 3**

### Fase 3 — REINDEX/ANALYZE + index contoh
4. `reindex_analyze.py` (Keputusan #3). 1-2 index contoh, ditandai provisional. Verifikasi `EXPLAIN ANALYZE` before/after.

**Checkpoint 4**

### Fase 4 — No-downtime test
5. Adaptasi `test_no_downtime_swap.py`, buktikan 0 error selama N siklus swap konkuren.

**Checkpoint 5**

### Fase 5 — Workflow terjadwal
6. `.github/workflows/reverse-etl-mart-aggregated.yml` — trigger off `transform-mart-aggregated.yml`. Push, trigger, verifikasi run sukses di GitHub Actions sungguhan.

**Checkpoint 6**

### Fase 6 — Dokumentasi + Finalisasi
7. Update `kebijakan-akses-kredensial-scoped.md`, `DataSchema-mart-aggregated.md` (catatan tabel ML ditunda). Verifikasi 3 KK sumber (dengan catatan deviasi 76/77), tulis `report.md`.

**Checkpoint 7 (final)** — commit + push.
