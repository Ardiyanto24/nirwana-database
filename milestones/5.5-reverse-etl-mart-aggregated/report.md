# Milestone 5.5: Reverse ETL Mart Aggregated ke PostgreSQL — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Seluruh tabel `mart_aggregated` tersedia di PostgreSQL dengan jumlah baris yang cocok dengan versi BigQuery pasca-sync.** — Terpenuhi untuk 76/77 tabel (lihat Deviations di bawah untuk 1 tabel yang sengaja dikecualikan). Dibuktikan lokal (`sync.py --all`: 76/76 synced, 0 mismatch, diverifikasi independen via `information_schema.tables` — 76 tabel, 0 sisa `__staging`/`__old`) DAN terhadap GitHub Actions sungguhan ([run 31261974429](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31261974429), dipicu otomatis via `workflow_run` dari `transform-mart-aggregated.yml`, bukan `workflow_dispatch` manual pada workflow yang diuji itu sendiri) — pasca-run, query independen ke Postgres tetap menunjukkan 76 tabel dan 76 baris baru di `monitoring.reverse_etl_sync_log`.
- [x] **Swap table tidak mengganggu query yang sedang berjalan dari konsumen (Data Analyst maupun AI Chatbot) saat proses sync berlangsung.** — Terpenuhi. `test_no_downtime_swap.py` (adaptasi M2.4): thread background poll `SELECT COUNT(*)` tiap 20ms sementara 8 siklus swap penuh dijalankan foreground terhadap tabel yang sama — **250 query konkuren, 0 error**.
- [x] **Statistik index pasca-swap terbukti ter-refresh (diverifikasi lewat `EXPLAIN ANALYZE` pada query representatif tidak menunjukkan degradasi performa dibanding sebelum swap).** — Terpenuhi, dengan bukti lebih kuat dari yang diminta literal KK sumber. Baseline (sebelum index): `Seq Scan`, 33.088 ms. Setelah `reindex_analyze.py` (index contoh + REINDEX + ANALYZE): `Index Scan`, 2.386 ms (~14x lebih cepat) — bukan cuma "tidak degradasi", performa **membaik nyata**. Uji coba terkontrol tambahan membuktikan mekanisme ini **benar-benar diperlukan** (bukan dekoratif): re-sync tabel yang sama menghilangkan index **total** (`pg_indexes` kosong), `reindex_analyze.py` memulihkannya, `EXPLAIN ANALYZE` kembali `Index Scan`.

## Deliverables

- `scripts/reverse_etl_mart_aggregated/` — 7 file: `connections.py`, `schema.sql`, `setup_serving_schema.py`, `setup_writer_role.py`, `mart_aggregated_tables.py` (76 tabel, cross-checked otomatis terhadap `warehouse/models/mart_aggregated/`), `sync.py`, `example_indexes.py` + `reindex_analyze.py`, `test_no_downtime_swap.py`.
- `.github/workflows/reverse-etl-mart-aggregated.yml` — workflow terjadwal baru, trigger `workflow_run` off `transform-mart-aggregated.yml`, diverifikasi jalan otomatis end-to-end di GitHub Actions sungguhan.
- Schema Postgres `mart_aggregated` (baru, di serving project M2.4 yang sama) — 76 tabel live, teruji.
- Kredensial baru: `reverse-etl-mart-agg-reader` (BigQuery), `reverse_etl_mart_aggregated_writer` (Postgres) — didokumentasikan di `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`, GitHub Secrets ditambahkan.
- `monitoring.reverse_etl_sync_log` — migrasi additive (`dataset_name` column), backward-compatible dengan 93 baris M2.4 lama.
- 1 index contoh (`idx_fact_revenue_property_daily_property_period`), eksplisit ditandai provisional — bukan desain final Milestone 3.3.
- `docs/07-mart-aggregated/DataSchema-mart-aggregated.md` — addendum M5.4 ditambah 1 baris status ("belum disinkronkan, ditunda").
- `milestones/5.5-reverse-etl-mart-aggregated/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada deviasi pada 10 keputusan inti. **2 koreksi teknis ditemukan & diperbaiki saat implementasi**, didokumentasikan eksplisit (bukan diperbaiki diam-diam):
- **Nama service account BigQuery kepanjangan**: `reverse-etl-mart-aggregated-reader` (35 karakter) ditolak GCP (limit 30 karakter) — dipersingkat jadi `reverse-etl-mart-agg-reader`.
- **Keputusan #3 (REINDEX/ANALYZE) draf awal tidak lengkap**: `REINDEX TABLE` sendirian tidak cukup — tabel staging `sync.py` selalu dibuat baru tanpa index apa pun, jadi tabel live pasca-swap kehilangan **seluruh** index, bukan cuma index basi. Mekanisme diperbaiki jadi `CREATE INDEX IF NOT EXISTS` (mengembalikan index yang hilang) + `REINDEX` + `ANALYZE`, dibuktikan lewat uji coba terkontrol (index hilang setelah re-sync, dipulihkan mekanisme ini).

**1 deviasi terhadap KK1 sumber, disengaja dan didokumentasikan (Keputusan #2):** kata "seluruh `mart_aggregated`" secara literal berarti 77 tabel (termasuk `fact_ml_occupancy_forecast_property_room_type`, M5.4). M5.5 hanya menyinkronkan **76/77** — tabel ML provisional sengaja dikecualikan karena skemanya belum final (menunggu tim ML Engineer), demi menghindari konsumen membangun kontrak di atas skema yang bisa berubah kapan saja.

## Known Gaps / Follow-ups

- **Tabel ML provisional (M5.4) belum ada di serving PostgreSQL** — keputusan sadar (lihat Deviations), bukan kelalaian. Perlu direvisit begitu skema final dari tim ML Engineer tersedia.
- **Index contoh (`idx_fact_revenue_property_daily_property_period`) bukan desain index final** — Milestone 3.3 (`04-serving-data-analyst.md`) yang memiliki desain index sungguhan berdasarkan pola akses real, belum dibangun. Index ini murni bukti mekanisme.
- **`sync.py --domain`/`--table` tidak dipakai di workflow terjadwal** — sama seperti M2.4, workflow selalu `--all`. Opsi tersedia untuk debugging/sync parsial kalau volume bertambah signifikan.
- **Rotasi kredensial `reverse-etl-mart-agg-reader`/`reverse_etl_mart_aggregated_writer` belum otomatis** — gap yang sama seperti kredensial lain (`kebijakan-akses-kredensial-scoped.md` "Rotasi dan Pencabutan").
- **Tidak ada read-only role khusus konsumen** (Data Analyst/AI Chatbot) untuk mengakses `mart_aggregated` di Postgres — sama seperti gap M2.4 untuk `mart_cleaned`, ini scope milestone konsumen (M3.x/M4.x), bukan M5.5.

## Handoff Notes

- **Milestone 3.3 (Index dan Optimasi Performa, `04-serving-data-analyst.md`)**: `scripts/reverse_etl_mart_aggregated/example_indexes.py` adalah TEMPLATE, bukan desain final — tambahkan index sungguhan di sana (list `EXAMPLE_INDEXES`, format `{table, index_name, columns}`), `reindex_analyze.py` akan otomatis membuat/mempertahankannya tiap swap tanpa perlu perubahan mekanisme.
- **Milestone 5.6 (Mekanisme Pengajuan Perubahan Cakupan)**: kalau `mart_aggregated` bertambah tabel lagi ke depan, `scripts/reverse_etl_mart_aggregated/mart_aggregated_tables.py` perlu diupdate manual (hardcoded list, Keputusan #1) — jalur pengajuan M5.6 sebaiknya termasuk langkah ini secara eksplisit.
- **Tim ML Engineer (kalau/ketika terlibat)**: begitu skema `ml_output`/`fact_ml_occupancy_forecast_property_room_type` final, tambahkan ke `mart_aggregated_tables.py` untuk mulai disinkronkan — cek `docs/07-mart-aggregated/DataSchema-mart-aggregated.md` addendum M5.4 untuk status terkini.
- **`docs/04-serving-data-analyst.md`/`05-serving-ai-chatbot.md`**: `mart_aggregated` di Postgres sekarang live dan bisa dipakai membangun view/API — tapi baca `Metadata-mart-aggregated.md` dulu untuk konteks bisnis tiap kolom sebelum membangun apa pun di atasnya (sama pesan handoff M5.3).
