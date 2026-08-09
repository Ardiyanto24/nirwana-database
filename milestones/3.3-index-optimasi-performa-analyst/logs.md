# Milestone 3.3: Index dan Optimasi Performa untuk Pola Akses Analyst — Logs

## 2026-08-09 — Mulai kerja

- Plan disetujui via Plan Mode (setelah revisi task breakdown dari template 9/5 M3.1-M3.2 menjadi 8/8 yang diturunkan ulang dari bentuk kerja M3.3 sebenarnya — 6 domain independen menulis ke 2 file bersama, bukan file terpisah per domain seperti M3.2).
- `decisions.md` ditulis: 1 keputusan AskUserQuestion (cakupan mart_aggregated + mart_cleaned) + 7 keputusan teknis.
- Folder dibuat: `milestones/3.3-index-optimasi-performa-analyst/`.
- Mulai Task 1 (Fase 0 — bangun mekanisme reindex kedua schema).

## 2026-08-09 — Checkpoint 1

- `scripts/reverse_etl/{mart_cleaned_indexes.py,reindex_analyze.py}` dibuat (clone persis pola `reverse_etl_mart_aggregated`, target schema `mart_cleaned`, 23 tabel dari `serving_tables.py`).
- `scripts/reverse_etl_mart_aggregated/example_indexes.py` dihapus, diganti `mart_aggregated_indexes.py` (docstring PROVISIONAL dihapus, sekarang menyatakan diri sebagai desain M3.3). `reindex_analyze.py` (mart_aggregated) diupdate importnya.
- Step baru ditambahkan ke `.github/workflows/reverse-etl-mart-cleaned.yml`: "Milestone 3.3 -- REINDEX/ANALYZE pasca-swap" setelah `sync.py --all`, mengikuti persis pola step 2 di `reverse-etl-mart-aggregated.yml`.
- Verifikasi: `reindex_analyze.py --all` dijalankan langsung terhadap serving PostgreSQL sungguhan untuk kedua schema — 76 tabel `mart_aggregated` dan 23 tabel `mart_cleaned` semuanya sukses (no-op reindex karena daftar index masih kosong, `ANALYZE` tetap jalan). Tidak ada error privilege pada `reverse_etl_writer`/`reverse_etl_mart_aggregated_writer` untuk `CREATE INDEX`/`REINDEX`/`ANALYZE`.

## 2026-08-09 — Checkpoint 2: Index Revenue

- Row count live sisa tabel Revenue: `fact_revenue_channel_daily` 26.697, `fact_revenue_gop_impact_monthly` 180 (dikeluarkan — terlalu kecil, Keputusan #2), `fact_revenue_pricing_deviation` 5.490, `fact_revenue_loyalty_daily` 21.413, `fact_revenue_nationality_daily` 10.970, `fact_revenue_property_daily` 5.485.
- **Baseline (sebelum index)**, query "laporan bulanan P01" (filter `property_id`+`period_date` 1 bulan): `fact_revenue_room_type_daily` Seq Scan 88.2ms (19.622/19.746 baris dibuang filter); `fact_revenue_channel_daily` Seq Scan 130.7ms; `fact_revenue_los_daily` Seq Scan 276.6ms; `mart_cleaned.bookings` (investigasi cancellation) Parallel Seq Scan 82.1ms; `mart_cleaned.pricing_history` Seq Scan 2.7ms (sudah cepat, tabel kecil).
- Index dipasang: 7 tabel `mart_aggregated` (`fact_revenue_room_type_daily`, `channel_daily`, `los_daily`, `property_daily`, `pricing_deviation`, `loyalty_daily`, `nationality_daily`, semua composite `(property_id, period_date)`) + 2 tabel `mart_cleaned` (`bookings` → `(property_id, check_in_date)`, `pricing_history` → `(property_id, date)`).
- **Verifikasi setelah index**: seluruh 9 query `EXPLAIN ANALYZE` beralih ke Index Scan/Bitmap Index Scan (tidak ada Seq Scan tersisa). Waktu eksekusi: room_type_daily 88.2ms→2.2ms, channel_daily 130.7ms→1.8ms, los_daily 276.6ms→0.48ms, bookings 82.1ms→3.3ms. `pg_stat_user_indexes.idx_scan` dikonfirmasi ≥1 untuk seluruh 9 index — KK2 terbukti dua arah (query plan + runtime usage), bukan cuma index ada di skema.

**✅ Checkpoint 2 selesai.**
