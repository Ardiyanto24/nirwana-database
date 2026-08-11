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
