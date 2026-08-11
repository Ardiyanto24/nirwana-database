# Milestone 6.5 — Execution Log

## 2026-08-11 — Plan mode: riset infra + 1 diskusi keputusan material
Did: 2 Explore agent paralel (chatbot audit log system M4.5; infra serving PostgreSQL/`pg_stat_statements`/pooler) + verifikasi READ-ONLY langsung ke project serving (query `pg_extension`, `information_schema.columns`, `pg_roles`, `pg_stat_activity`, `pg_stat_statements`) sebelum plan dikunci. Ditemukan: `pg_stat_statements` sudah aktif (v1.11, 2649 baris nyata) TAPI tidak ada kolom percentile sama sekali. Diajukan 3 opsi ke user (instrumentasi `duration_ms` / aproksimasi mean-max / skip+gap) — user pilih instrumentasi, plus instruksi eksplisit: commit yang menyentuh kode M4.4/M4.5 ditandai `fix:`.
Result: worked. Plan ditulis lengkap dengan Keputusan A (dikunci user) + 5 keputusan derived (kredensial, folder, EXPLAIN ANALYZE, no scheduled workflow, rolling-baseline pool spike).

## 2026-08-11 — Checkpoint 1 Task 1: decisions.md
Did: Tulis kontrak, 9 temuan riset, 1 diskusi user, 6 technical decisions.
Result: worked.

## 2026-08-11 — Checkpoint 1 Task 2: kredensial chatbot_perf_reader (serving)
Did: `scripts/chatbot_perf_monitor/{connections.py, verify_role_isolation.py, setup_perf_reader.py}` — copy pola `chatbot_credentials`/`chatbot_audit`, disesuaikan dual-instance (serving + production). Nama role awalnya salah ketik `chatbot-perf-reader` (hyphen, meniru konvensi BigQuery service account M6.3/M6.4) — **diperbaiki sebelum eksekusi** jadi `chatbot_perf_reader` (underscore), konsisten konvensi Postgres role project ini (`chatbot_audit_reader`, `chatbot_authz_reader`, dst — SEMUA underscore, hyphen cuma dipakai BigQuery service account).
Jalankan `setup_perf_reader.py` — **1 hambatan nyata ditemukan**: `SELECT count(*) FROM pg_stat_statements` gagal `UndefinedTable` meski extension terinstal dan `pg_monitor` sudah di-grant. Diagnosis: `pg_stat_statements` view Supabase hidup di schema `extensions` (bukan `public`), admin (`postgres`) kebetulan punya `extensions` di `search_path` default-nya, role baru TIDAK. Diperbaiki: `GRANT USAGE ON SCHEMA extensions` + qualified `extensions.pg_stat_statements` di ALLOW_CHECKS (dan seluruh script masa depan, tidak bergantung `search_path`).
Result: worked setelah perbaikan. 8/8 isolation checks OK (3 allow: stats + chatbot_views; 5 deny: mart_cleaned HR/role_permissions, analyst_views, INSERT/CREATE).

## 2026-08-11 — Checkpoint 1 Task 3: kredensial chatbot_audit_reader (production)
Did: `scripts/chatbot_perf_monitor/setup_audit_reader.py` — SELECT-only `monitoring.chatbot_query_log`, nama sudah diantisipasi M4.5/M6.1.
Result: worked, tanpa hambatan. 6/6 isolation checks OK (1 allow: SELECT; 5 deny: tabel monitoring lain, tabel production, INSERT/UPDATE).

## 2026-08-11 — Checkpoint 1 Task 4: schema
Did: `scripts/chatbot_perf_monitor/{db.py, serving_pg.py, schema.sql, apply_schema.py}` — 3 tabel baru (`chatbot_query_perf_snapshot` pakai `queryid` bawaan pg_stat_statements sebagai unique key bukan hash query_text sendiri; `chatbot_explain_analyze_log`; `chatbot_connection_snapshot` sengaja TANPA UNIQUE constraint karena uji coba terkontrol KK3 butuh snapshot berulang cepat), extend `alerts.alert_type` (+`chatbot_connection_pool_spike`). Jalankan `apply_schema.py`.
Result: worked. Verifikasi `information_schema`: 3 tabel baru live, CHECK constraint 11 nilai (10 lama + 1 baru).

## 2026-08-11 — Checkpoint 2 (Task 5-7): instrumentasi duration_ms + latency percentile
Did: `scripts/chatbot_audit/schema.sql` — `ALTER TABLE monitoring.chatbot_query_log ADD COLUMN IF NOT EXISTS duration_ms numeric` (additive, nullable, baris lama TIDAK di-backfill -- tidak mungkin direkonstruksi). `scripts/chatbot_api/main.py::handler()` -- `time.perf_counter()` di awal, `duration_ms` dihitung sebelum TIAP `log_query(...)` (jalur denied & success). `scripts/chatbot_api/audit.py::log_query()` -- parameter baru `duration_ms=None`, masuk kolom INSERT.
Result: worked, sesuai instruksi user commit ditandai `fix:`.

Task 6 verifikasi: `uvicorn main:app --port 8020` lokal, 3 request HTTP nyata via `curl` -- 404 (`v_properties_ref` bukan key whitelist sungguhan, ketahuan salah tebak nama saat testing), 403 (`Front Office Staff` -> domain `financial`, sesuai pola M4.4 "FO Staff ditolak domain lain"), 200 sukses (`properties_ref/properties`, key whitelist benar -- Corporate Revenue Director, `all_properties`). Query `chatbot_query_log` via `chatbot_audit_reader` mengonfirmasi: 3 baris baru `duration_ms` terisi (1589.5ms/909.77ms/803.21ms), baris lama M4.5/M4.6 tetap NULL persis sesuai desain (tidak di-backfill).

Task 7: `compute_latency_percentiles.py` -- `percentile_cont(0.5/0.95/0.99)` (otomatis skip NULL), top-10 slowest query, tren volume+denied per hari (`GROUP BY requested_at::date`). Dijalankan terhadap data live: p50=909.77ms p95=1521.5ms p99=1575.9ms (n=3, sample kecil tapi PERCENTILE SUNGGUHAN, bukan aproksimasi) -- KK1 terpenuhi. Tren 2 hari: 2026-08-10 (239 total/127 denied, 53.1%) vs 2026-08-11 (3 total/2 denied, 66.7%) -- KK2 terpenuhi (tren lintas hari, bukan cuma angka harian sesaat).

## 2026-08-11 — Checkpoint 3 (Task 8-9): pg_stat_statements snapshot + EXPLAIN ANALYZE
Did: `snapshot_query_perf.py` -- query `extensions.pg_stat_statements` (chatbot_perf_reader) filter `query ILIKE '%chatbot_views%'`, upsert `chatbot_query_perf_snapshot` (unique key `queryid` bawaan pg_stat_statements).
Result: **1 bug nyata ditemukan+diperbaiki** (percobaan pertama): `IndexError: tuple index out of range` saat `cur.execute()` -- literal `'%chatbot_views%'` inline di SQL string bentrok dengan psycopg2 punya sendiri `%s`-style parameter substitution (`%c` di tengah string ditafsirkan sebagai format conversion, bukan wildcard LIKE). Diperbaiki: pattern ILIKE dilewatkan sebagai bound parameter (`%s`), bukan inline literal. Setelah perbaikan: 50 query nyata tersimpan (top by `calls`), paling sering 96 calls (`v_employees_directory WHERE employee_id=$1`), paling lambat max_exec_time 2494ms (`guests_contact_view`).

`explain_representative_queries.py` -- 10 query kurasi manual (1 per domain, bentuk sama persis `_run_whitelisted_query`), `EXPLAIN (ANALYZE, FORMAT TEXT)` via `chatbot_perf_reader`, tulis `chatbot_explain_analyze_log`.
Result: worked, 10/10 tereksekusi & tersimpan. Temuan nyata (bukan bug, observasional): `guests_contact_view` execution_time=2354ms -- jauh lebih lambat dari 9 view lain (rentang 0.04-101ms) -- konsisten dengan `max_exec_time` tertinggi di `pg_stat_statements` (Task 8). Tidak diperbaiki di M6.5 (di luar scope -- M6.5 murni observasional, sama prinsip M6.1-6.4 "mengamati, bukan membangun/memperbaiki" kecuali gap instrumentasi yang eksplisit disepakati user seperti Task 5).
