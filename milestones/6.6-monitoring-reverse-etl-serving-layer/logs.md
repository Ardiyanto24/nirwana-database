# Milestone 6.6 — Execution Log

## 2026-08-11 — Plan mode: riset + 2 diskusi keputusan material (2 putaran)
Did: Riset langsung ke kode (`sync.py` kedua versi, `reindex_analyze.py`, `test_no_downtime_swap.py`) + verifikasi read-only langsung ke serving project (`pg_stat_user_tables`, `pg_depend`, `pg_total_relation_size`, `gh run list`). Ditemukan: 72/76 tabel `mart_aggregated` orphan `__old` (112MB), diikat SELURUH `analyst_views`+`chatbot_views`, `old_table_status` sudah dihitung tapi dibuang, mart_cleaned tidak punya fix graceful-degradation M5.7.
2 pertanyaan diajukan putaran 1 — user minta riset lebih dalam dulu ("cek lagi lebih spesifik", "kita diskusikan lebih lanjut"), TIDAK langsung jawab. Riset tambahan: cakupan dependency (`pg_depend`, 42+44 view), verifikasi dampak data-correctness aktual (live vs `__old` row count identik di 4 tabel, konsisten dataset statis project ini). Disampaikan lengkap ke user, putaran 2: user pilih instrumentasi penuh + cleanup sekali.
Result: worked. Plan ditulis lengkap dengan Keputusan A-B (dikunci user) + 6 keputusan derived.

## 2026-08-11 — Checkpoint 1 (Task 1-3): decisions.md + kredensial + schema
Did: Tulis `decisions.md`. `scripts/serving_layer_monitor/{connections.py, verify_role_isolation.py, db.py, setup_storage_reader.py}` — kredensial baru `serving_storage_reader` (serving), `pg_monitor` + `USAGE` `mart_cleaned`+`mart_aggregated`, TANPA SELECT tabel (kredensial paling sempit di project ini — cuma metadata/stats). `schema.sql` — `monitoring.serving_storage_snapshot` (is_orphan dihitung saat insert, sumber kebenaran tunggal utk deteksi orphan), extend `reverse_etl_sync_log` (+`old_table_status`, +`swap_duration_ms`), extend `alerts.alert_type` (+`serving_swap_orphan_table`, +`serving_swap_slow`).
Result: worked. 8/8 isolation checks OK, `USAGE`-only (tanpa `SELECT`) dikonfirmasi cukup untuk `pg_total_relation_size()` (sesuai prediksi riset). Schema diverifikasi `information_schema`.
