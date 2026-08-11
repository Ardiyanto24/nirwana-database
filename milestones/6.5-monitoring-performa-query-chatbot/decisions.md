# Milestone 6.5: Monitoring Performa Query AI Chatbot — Decisions

**Source:** `docs/03-implementation-plans/06-monitoring-warehouse-serving-fase2.md` (baris 130-147)
**Status:** In Progress
**Date started:** 2026-08-11

## Contract (from source doc)

- **Lingkup:** Membangun pemantauan performa query AI Chatbot terhadap PostgreSQL — prinsip monitoring ketiga (setelah M6.2 "lihat apa yang terjadi" dan M6.3 "deteksi kesalahan/anomali"). Memanfaatkan audit log query chatbot (M4.5) + metrik performa PostgreSQL langsung (`pg_stat_statements`, latency, connection pool usage).
- **Output:** (1) Dashboard performa query chatbot: latency (p50/p95/p99), volume query per satuan waktu, query gagal/ditolak, query paling lambat/paling sering. (2) Pemantauan `pg_stat_statements` dan `EXPLAIN ANALYZE` berkala terhadap pola query representatif chatbot. (3) Pemantauan connection pool usage di depan PostgreSQL.
- **Kriteria Keberhasilan:**
  - KK1: Tim bisa melihat latency end-to-end (sejauh data ini tersedia dari audit log) dan mengidentifikasi query paling lambat tanpa investigasi manual ke `pg_stat_statements` langsung.
  - KK2: Persentase query gagal/ditolak terlihat sebagai tren, bukan hanya angka harian sesaat.
  - KK3: Lonjakan penggunaan connection pool (uji coba terkontrol) terdeteksi.

## Temuan Riset

Riset dilakukan lewat 2 Explore agent paralel (chatbot audit log system M4.5; infra serving PostgreSQL/`pg_stat_statements`/pooler) + verifikasi READ-ONLY langsung ke project serving PostgreSQL (query `pg_extension`, `information_schema.columns`, `pg_roles`, `pg_stat_activity`, `pg_stat_statements`).

1. **`monitoring.chatbot_query_log` (M4.5, production Supabase) TIDAK punya kolom latency/durasi apa pun.** Kolom: `id, role_title, domain, view_name, employee_id, access_scope, resolved_property_id, status, denial_reason, row_count, requested_at`. Writer `chatbot_audit_writer` (M4.5) INSERT-only murni (`GRANT INSERT` + `GRANT USAGE` sequence, TIDAK ADA `GRANT SELECT`) — **tidak ada kredensial baca sama sekali** untuk tabel ini. Sudah diantisipasi eksplisit: `report.md` M4.5 ("kredensial baca terpisah `chatbot_audit_reader` kemungkinan perlu dibuat M6.5 sendiri") dan `report.md`/`logs.md` M6.1 (titik 11 out-of-scope, gap latency dicatat).
2. **Delivery `chatbot_query_log` best-effort** — `audit.py::log_query()` swallow exception (print ke stderr, tidak pernah raise), dipanggil via FastAPI `BackgroundTasks` SETELAH response terkirim (tidak menambah latency respons). Bug nyata M4.5 (background task didiamkan FastAPI kalau handler `raise` bukan `return`) sudah diperbaiki — 3 jalur denial di `main.py` pakai `JSONResponse(..., background=background_tasks)`.
3. **`pg_stat_statements` SUDAH aktif di project serving** (v1.11, dikonfirmasi `SELECT extname, extversion FROM pg_extension` — tidak perlu `CREATE EXTENSION`). **2649 baris data nyata** per verifikasi langsung, termasuk query `chatbot_views.*` sungguhan dari traffic uji coba M4.6 (`stats_since=2026-08-08 04:45:20 UTC`, belum pernah di-reset). Sample nyata: `SELECT property_id FROM chatbot_views.v_employees_directory WHERE employee_id = $1` — 96 calls, mean_exec_time=0.45ms.
4. **`pg_stat_statements` TIDAK PUNYA kolom percentile sama sekali** — dikonfirmasi `information_schema.columns`: cuma `total/min/max/mean/stddev_exec_time` (+ setara utk `plan_time`). Tidak ada `p50`/`p95`/`p99`/histogram apa pun. KK1 minta literal "p50/p95/p99" — secara matematis TIDAK BISA dihitung jujur dari mean+stddev tanpa asumsi distribusi.
5. **Admin `SERVING_DB_URL` (role `postgres`, dikonfirmasi `rolsuper=false`) SUDAH menjadi member `pg_monitor`** (predefined role Postgres yang mencakup `pg_read_all_stats`+`pg_read_all_settings`+`pg_stat_scan_tables`) — dikonfirmasi query `pg_auth_members` langsung. `pg_stat_activity` juga sudah terbukti bisa dibaca penuh lintas role (13 sesi: `supabase_admin`, `authenticator`, `postgres`, `pgbouncer`, dst) — bukan cuma sesi milik sendiri.
6. **Tidak ada role LAIN manapun di project ini (10 chatbot reader, 7 analyst reader, dst) yang punya `pg_monitor`/`pg_read_all_stats`** — grep `pg_monitor`/`pg_read_all_stats` di seluruh repo 0 match selain temuan baru ini. Kredensial baru wajib dibuat untuk scoped access, konsisten precedent M2.5-M6.4.
7. **Serving project pakai Supabase (Supavisor pooler)**, sama seperti production — dikonfirmasi `.env.example` (format URL Session Pooler) + `milestones/2.4-reverse-etl-postgresql/decisions.md` Keputusan #1 (provider lain — Neon/Render/Railway — ditolak eksplisit). `scripts/chatbot_audit/connections.py` juga mengonfirmasi `SUPABASE_DB_URL` (production) ternyata Supavisor pooler URL juga, bukan direct connection seperti asumsi awal `.env.example`.
8. **`scripts/chatbot_api/` manual-only, tidak pernah dideploy** (`docs/09-serving-ai-chatbot/api-chatbot.md`) — dijalankan `uvicorn main:app --reload` lokal saja. **Tidak punya connection pooling sendiri** — tiap request buka koneksi Postgres baru (`connections.py::query_as_domain`). Temuan M4.6: 240 HTTP call (200 Layer A + 30 Layer B RBAC matrix) makan >120 detik justru karena pola ini — data point konkret untuk desain uji coba terkontrol KK3 (burst request lokal = burst koneksi nyata di `pg_stat_activity`, tidak perlu infra tambahan).
9. **Row count `chatbot_query_log` saat ini**: ~5 baris (M4.5 sendiri) + hingga 240 (M4.6 RBAC test, tidak diverifikasi ulang post-hoc) — seluruhnya dari tanggal 2026-08-10. Tidak ada proses berkelanjutan yang menambah data harian (sama pola "static snapshot" seperti dataset production Fase 1).

## Diskusi dengan User (1 keputusan material, dikunci lewat AskUserQuestion)

### Q1 — Bagaimana menangani ketiadaan kolom percentile di `pg_stat_statements`?
Diajukan 3 opsi: (A) tambah instrumentasi `duration_ms` ke `chatbot_api` (percentile sungguhan, sentuhan kecil ke kode M4.4/M4.5), (B) aproksimasi dari `mean/max/stddev` pg_stat_statements (nol sentuhan kode, tapi bukan percentile sungguhan), (C) skip metrik percentile, catat sebagai gap (Partially Completed). **User memilih (A)**, dengan instruksi eksplisit tambahan: commit yang menyentuh `main.py`/`audit.py`/`schema.sql` untuk instrumentasi ini ditandai sebagai **fix** (bukan feat/feature) di pesan commit — mengakui ini menutup gap nyata M4.5, bukan sekadar fitur baru M6.5.

## Technical Decisions

### Decision: Latency — instrumentasi `duration_ms` ke `chatbot_api` (Keputusan A)
- **Context:** `pg_stat_statements` tidak punya kolom percentile; `chatbot_query_log` tidak punya kolom durasi. KK1 minta p50/p95/p99 yang literal tidak bisa dipenuhi tanpa data per-request nyata.
- **Decision:** `scripts/chatbot_api/main.py::handler()` (baris 123-169) — `start = time.perf_counter()` di awal, `duration_ms = round((time.perf_counter()-start)*1000, 2)` sebelum tiap pemanggilan `log_query(...)` (jalur denied baris 143, jalur success baris 158), diteruskan sebagai parameter baru. `audit.py::log_query()` (baris 36-46) — parameter baru `duration_ms=None`, masuk ke kolom INSERT. `scripts/chatbot_audit/schema.sql` — `ALTER TABLE monitoring.chatbot_query_log ADD COLUMN IF NOT EXISTS duration_ms NUMERIC` (additive). `chatbot_audit_writer` tidak perlu re-grant (INSERT sudah mencakup seluruh kolom, bukan column-level). Percentile dihitung SQL sungguhan: `percentile_cont(0.5/0.95/0.99) WITHIN GROUP (ORDER BY duration_ms)`.
- **Alternatives considered:** Aproksimasi `pg_stat_statements` (nol sentuhan kode, tapi tidak jujur diklaim "percentile"); skip metrik (KK1 Partially Completed).
- **Rejected because:** User memilih A setelah dijelaskan konstrain teknisnya secara eksplisit.
- **Catatan commit:** commit checkpoint yang menyentuh 3 file ini WAJIB ditandai `fix:` sesuai instruksi eksplisit user.

### Decision (derived): 2 kredensial baru, pola scoped-reader konsisten M2.5-M6.4
- **`chatbot_perf_reader`** (Postgres, project **serving**) — grant `pg_monitor` (satu-satunya cara baca `pg_stat_statements`/`pg_stat_activity` tanpa superuser) + `SELECT` pada **seluruh schema `chatbot_views`** (dibutuhkan `EXPLAIN ANALYZE` representative query lintas 10 domain — lebih luas dari kredensial `*_chatbot_reader` M4.3 yang per-domain, precedent sama `analyst-readonly` M3.6: 1 kredensial lintas cakupan untuk kebutuhan cross-cutting, tetap read-only murni).
- **`chatbot_audit_reader`** (Postgres, **production Supabase**) — SELECT-only `monitoring.chatbot_query_log`, nama sudah diantisipasi M4.5/M6.1.
- **Context:** Tidak ada role existing dengan privilege ini (temuan riset #6). Least-privilege konsisten seluruh precedent M2.5-M6.4 — reuse admin `SERVING_DB_URL`/`SUPABASE_DB_URL` untuk READ scoped ditolak, sama alasan berulang project ini.

### Decision (derived): Folder baru `scripts/chatbot_perf_monitor/`
- **Context:** M6.1-6.4 tinggal di `scripts/monitoring_warehouse/` karena tema BigQuery warehouse pipeline. M6.5 secara tematik masuk keluarga `chatbot_*` (`chatbot_views`, `chatbot_credentials`, `chatbot_api`, `chatbot_audit`, `chatbot_rbac_test`).
- **Decision:** Folder baru, bukan dipaksakan ke `monitoring_warehouse`. Tulisan ke `monitoring.*` (production Supabase) tetap lewat pola admin `SUPABASE_DB_URL` yang mapan (`db.py` di-copy, bukan di-import, konsisten anti-pattern `sys.path` yang sudah didokumentasikan CLAUDE.md).

### Decision (derived): `EXPLAIN ANALYZE` — daftar query representatif dikurasi manual
- **Context:** `pg_stat_statements.query` menyimpan teks ternormalisasi berisi placeholder (`$1, $2`) — tidak langsung dieksekusi ulang tanpa substitusi nilai nyata.
- **Decision:** Kurasi manual ~10 query (1 per domain chatbot), pola sama persis `scripts/chatbot_api/whitelist_*.py`, dengan parameter sampel nyata (property_id/employee_id dari data yang sudah ada).
- **Alternatives considered:** Ekstraksi dinamis + substitusi placeholder otomatis — ditolak, jauh lebih kompleks/fragile untuk manfaat marginal dibanding kurasi manual sekali.

### Decision (derived): TIDAK ada workflow GitHub Actions terjadwal baru (beda dari M6.1-6.4)
- **Context:** `chatbot_api` manual-only/tidak pernah dideploy — bukan keputusan M6.5 untuk diubah. Job terjadwal harian yang snapshot sistem tanpa traffic baru cuma mengulang angka statis, tidak memberi nilai riil.
- **Decision:** Script dibuat re-runnable (pola `scripts/chatbot_rbac_test/`), dijalankan manual/on-demand. Tren KK2 dibuktikan dari traffic uji coba milestone ini sendiri (mirror cara M4.6 diverifikasi), bukan traffic produksi berkelanjutan yang memang tidak ada.

### Decision (derived): Connection pool spike — rolling-baseline sama algoritma M6.3, tanpa filter day-of-week
- **Context:** Sama alasan "sensor duration anomaly" M6.3 — jumlah koneksi aktif tidak punya pola mingguan berarti.
- **Decision:** Snapshot `pg_stat_activity` count (role chatbot-related) ke `monitoring.chatbot_connection_snapshot`, deteksi pakai algoritma existing (`WINDOW=8, MIN_HISTORY=3`, sigma warning=2/critical=3), push `monitoring.alerts` (`alert_type='chatbot_connection_pool_spike'`). Uji coba terkontrol: burst request paralel lokal (`concurrent.futures`) ke `chatbot_api`, snapshot sebelum/sesudah.

## Open Questions Resolved with User

- Q: Bagaimana menangani ketiadaan kolom percentile di `pg_stat_statements`/`chatbot_query_log`? → A: Tambah instrumentasi `duration_ms` ke `chatbot_api` (Keputusan A), commit ditandai `fix:`.

## Task Breakdown

### Checkpoint 1 — Fondasi: decisions.md + 2 kredensial + schema
- [x] Task 1: `decisions.md` — dokumen ini.
- [x] Task 2: Kredensial `chatbot_perf_reader` (serving) — `pg_monitor` + `SELECT` schema `chatbot_views`. **Selesai** — 8/8 isolation checks OK. 1 hambatan ditemukan+diperbaiki: `pg_stat_statements` view ada di schema `extensions` (konvensi Supabase), bukan `public`/`pg_catalog` — perlu `GRANT USAGE ON SCHEMA extensions` + qualified `extensions.pg_stat_statements` di semua query (search_path role baru tidak otomatis include `extensions`).
- [x] Task 3: Kredensial `chatbot_audit_reader` (production) — SELECT-only `monitoring.chatbot_query_log`. **Selesai** — 6/6 isolation checks OK.
- [x] Task 4: `scripts/chatbot_perf_monitor/{db.py, serving_pg.py}` + schema baru (`chatbot_query_perf_snapshot`, `chatbot_connection_snapshot`, `chatbot_explain_analyze_log`, extend `alerts.alert_type`). **Selesai** — diverifikasi `information_schema`.

### Checkpoint 2 — KK1 bagian 1: instrumentasi durasi + latency percentile
- [x] Task 5: Edit `main.py`/`audit.py`/`schema.sql` — **commit fix**. **Selesai**.
- [x] Task 6: Verifikasi HTTP nyata. **Selesai** — 3 request nyata (200 sukses, 403+404 denied), `duration_ms` terisi benar, baris lama tetap NULL.
- [x] Task 7: `compute_latency_percentiles.py`. **Selesai** — p50/p95/p99 sungguhan (n=3), tren volume/denied lintas 2 hari (2026-08-10: 239 total/127 denied; 2026-08-11: 3/2).

### Checkpoint 3 — KK1 bagian 2: pg_stat_statements snapshot + EXPLAIN ANALYZE
- [ ] Task 8: `snapshot_query_perf.py`.
- [ ] Task 9: `explain_representative_queries.py`.

### Checkpoint 4 — KK3: connection pool spike
- [ ] Task 10: `snapshot_connection_pool.py` + `detect_connection_pool_spike.py`.
- [ ] Task 11: Uji coba terkontrol burst paralel.

### Checkpoint 5 (final) — Konsolidasi
- [ ] Task 12: `simulate_test.py`.
- [ ] Task 13: Update peta M6.1 (Titik 11).
- [ ] Task 14: `logs.md` + `report.md`.
