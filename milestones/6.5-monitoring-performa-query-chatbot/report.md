# Milestone 6.5: Monitoring Performa Query AI Chatbot — Report

**Status:** Completed
**Date completed:** 2026-08-11

## Kriteria Keberhasilan — Hasil

- [x] **KK1 — Tim bisa melihat latency end-to-end (sejauh data ini tersedia dari audit log) dan mengidentifikasi query paling lambat tanpa investigasi manual ke `pg_stat_statements` langsung.** — Terpenuhi PENUH, melebihi literal "sejauh data tersedia" karena M6.5 justru **menutup gap data itu sendiri** (Keputusan A): `pg_stat_statements` dikonfirmasi TIDAK punya kolom percentile sama sekali (cuma mean/min/max/stddev per bentuk query, bukan per-request) — tanpa instrumentasi, p50/p95/p99 secara literal tidak bisa dihitung jujur. Instrumentasi `duration_ms` ditambahkan ke `chatbot_api` (commit `fix:`), diverifikasi HTTP nyata (200/403/404). `compute_latency_percentiles.py` menghitung `percentile_cont(0.5/0.95/0.99)` SUNGGUHAN dari data live (p50=909.77ms, p95=1521.5ms, p99=1575.9ms, n=3). Query paling lambat/sering diidentifikasi via `snapshot_query_perf.py` (50 query nyata dari `pg_stat_statements`, tanpa investigasi manual — 1 query saja) — ditemukan `guests_contact_view` sebagai outlier nyata (max 2494ms).
- [x] **KK2 — Persentase query gagal/ditolak terlihat sebagai tren, bukan hanya angka harian sesaat.** — Terpenuhi. `compute_latency_percentiles.py` menghitung tren `GROUP BY requested_at::date` — dibuktikan lintas 2 hari NYATA (2026-08-10: 239 total/127 denied=53.1%; 2026-08-11: 3 total/2 denied=66.7%), bukan snapshot 1 hari.
- [x] **KK3 — Lonjakan penggunaan connection pool (uji coba terkontrol) terdeteksi.** — Terpenuhi lewat uji coba terkontrol NYATA (bukan simulasi): 20 request paralel sungguhan ke `chatbot_api` lokal, `pg_stat_activity` di-poll live selama burst (0 → 30 koneksi), `detect_connection_pool_spike.py` (rolling-baseline identik algoritma sensor-duration M6.3) memicu alert `CRITICAL` benar. Plus verifikasi ulang lewat `simulate_test.py` (data sintetis bertanda, re-runnable).

## Deliverables

- `scripts/chatbot_perf_monitor/{connections.py, verify_role_isolation.py, db.py, serving_pg.py, schema.sql, apply_schema.py}` — fondasi dual-instance (serving + production).
- `scripts/chatbot_perf_monitor/{setup_perf_reader.py, setup_audit_reader.py}` — 2 kredensial baru: `chatbot_perf_reader` (serving, `pg_monitor`+`SELECT chatbot_views`, 8/8 isolation checks), `chatbot_audit_reader` (production, SELECT-only `chatbot_query_log`, 6/6 isolation checks).
- `scripts/chatbot_api/main.py`, `scripts/chatbot_api/audit.py`, `scripts/chatbot_audit/schema.sql` — **fix** permanen: instrumentasi `duration_ms` per-request (menutup gap nyata M4.5).
- `scripts/chatbot_perf_monitor/compute_latency_percentiles.py` — p50/p95/p99 sungguhan + top-10 slowest + tren volume/denied.
- `scripts/chatbot_perf_monitor/{snapshot_query_perf.py, explain_representative_queries.py}` — `pg_stat_statements` snapshot (50 query nyata) + `EXPLAIN ANALYZE` 10 query representatif (1 per domain).
- `scripts/chatbot_perf_monitor/{snapshot_connection_pool.py, detect_connection_pool_spike.py}` — deteksi lonjakan koneksi, diverifikasi burst 20 request nyata + `simulate_test.py`.
- Schema baru `monitoring.*` (production): `chatbot_query_perf_snapshot`, `chatbot_explain_analyze_log`, `chatbot_connection_snapshot`, extend `alerts.alert_type` (+`chatbot_connection_pool_spike`), `chatbot_query_log.duration_ms`.
- `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`, `.env.example` — diperbarui (2 kredensial baru).
- `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` — Titik 11 (AI Chatbot) gap latency ditutup.
- **Tidak ada workflow GitHub Actions baru** (Keputusan E) — `chatbot_api` manual-only, scheduled job tidak memberi nilai untuk sistem tanpa traffic berkelanjutan.
- **Tidak disentuh:** `authz.py`, `connections.py`, whitelist manapun, `role_permissions`, `scripts/chatbot_views/`, `scripts/chatbot_credentials/` — seluruh logic RBAC/otorisasi steril.

## Deviations from decisions.md

Tidak ada deviasi pada Keputusan A (dikunci user) maupun 5 keputusan derived. **3 hal ditemukan & diperbaiki saat implementasi** (dicatat eksplisit di `logs.md`, bukan disembunyikan):

1. **Nama kredensial `chatbot-perf-reader` (hyphen) salah, diperbaiki SEBELUM eksekusi** jadi `chatbot_perf_reader` (underscore) — konsisten konvensi Postgres role project ini (hyphen cuma dipakai BigQuery service account).
2. **`pg_stat_statements` hidup di schema `extensions` Supabase**, bukan `public`/`pg_catalog` — butuh `GRANT USAGE ON SCHEMA extensions` + qualified reference eksplisit, tidak bergantung `search_path` role baru.
3. **`snapshot_query_perf.py`**: literal `'%chatbot_views%'` inline di SQL string bentrok dengan psycopg2 punya sendiri parameter substitution (`IndexError`) — diperbaiki, pattern dilewatkan sebagai bound parameter.
4. **`snapshot_connection_pool.py`**: `chatbot_perf_reader` (kredensial pemantau itu sendiri) namanya cocok pola `%chatbot%`, self-count koneksinya sendiri — diperbaiki dengan exclude eksplisit.

**Temuan operasional nyata di luar 4 bug di atas** (bukan gap M6.5, dicatat sebagai Known Gap/Handoff): burst 20 request paralel menyingkap **Supavisor session-mode `pool_size=15`** per role domain — 5/20 request gagal `HTTP 500` (`EMAXCONNSESSION`) karena `chatbot_api` tidak punya connection pooling sendiri (buka koneksi baru tiap request, temuan M4.6 terbukti konsekuensinya nyata di sini).

## Known Gaps / Follow-ups

- **`chatbot_api` tidak punya connection pooling sendiri** — di atas ~15 request bersamaan ke domain yang sama akan mulai gagal 500 (Supavisor session-mode limit). Di luar scope M6.5 untuk diperbaiki (M6.5 murni observasional, kecuali gap instrumentasi `duration_ms` yang eksplisit disepakati user). Perlu ditangani sebelum `chatbot_api` dipertimbangkan untuk traffic produksi sungguhan.
- **`guests_contact_view` execution_time jauh lebih lambat** (2354-2494ms) dari 66 view lain — ditemukan lewat `EXPLAIN ANALYZE`/`pg_stat_statements`, tidak diinvestigasi/diperbaiki lebih lanjut (di luar scope observasional M6.5).
- **Sample percentile KK1 kecil (n=3)** — traffic HTTP nyata terbatas ke uji coba milestone ini sendiri (`chatbot_api` manual-only, tidak ada traffic produksi berkelanjutan). Mekanisme sudah terbukti benar secara matematis dan teknis; angka akan jadi representatif begitu ada lebih banyak traffic nyata.
- **Baris `chatbot_query_log` pra-M6.5 (M4.5/M4.6, ~245 baris) permanen `duration_ms=NULL`** — tidak di-backfill (tidak mungkin direkonstruksi setelah fakta), dikecualikan otomatis oleh `percentile_cont()`.
- **`analyst_views`/tabel serving lain tidak diverifikasi lebih lanjut** — scope M6.5 murni `chatbot_views`.

## Handoff Notes

- **Milestone 6.6 (Reverse ETL/Serving Layer):** temuan Supavisor `pool_size=15` (Known Gap di atas) relevan langsung — kalau M6.6 memantau kesehatan serving layer secara umum, connection pool exhaustion ini layak masuk cakupannya (di luar M6.5 yang fokus spesifik ke chatbot).
- **Milestone 6.7 (Dashboard Terpadu):** `monitoring.alerts` sekarang punya 11 `alert_type` (10 sebelumnya + `chatbot_connection_pool_spike`). `monitoring.chatbot_query_perf_snapshot`/`chatbot_explain_analyze_log`/`chatbot_connection_snapshot` adalah 3 sumber BARU yang TIDAK selalu lewat `monitoring.alerts` (staleness-style informational untuk 2 yang pertama) — kalau M6.7 ingin menampilkan performa query chatbot di dashboard, harus query langsung ke tabel-tabel ini.
- **Kalau `chatbot_api` suatu saat dipertimbangkan untuk deploy sungguhan:** WAJIB menyelesaikan Known Gap connection pooling dulu (lihat di atas) — beban traffic AI chatbot nyata jauh melebihi 15 concurrent request per domain yang jadi batas saat ini.
- **Percentile/tren KK1-2 akan jadi lebih representatif begitu ada lebih banyak traffic uji coba** — jalankan `compute_latency_percentiles.py`/`snapshot_query_perf.py`/`explain_representative_queries.py` ulang kapan saja setelah sesi testing baru terhadap `chatbot_api` (semua re-runnable, tidak butuh setup ulang).
