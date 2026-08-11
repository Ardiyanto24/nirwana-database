# Milestone 6.6: Monitoring Reverse ETL dan Serving Layer PostgreSQL — Decisions

**Source:** `docs/03-implementation-plans/06-monitoring-warehouse-serving-fase2.md` (baris 150-166)
**Status:** In Progress
**Date started:** 2026-08-11

## Contract (from source doc)

- **Lingkup:** Memantau kesehatan PostgreSQL sebagai serving layer secara umum (di luar spesifik chatbot) — storage growth, table bloat/status vacuum, dan kesehatan proses full refresh + swap table (dipakai `mart_aggregated` maupun `mart_cleaned`). Termasuk memastikan swap table tidak menyebabkan downtime baca yang tidak disengaja.
- **Output:** (1) Pemantauan storage growth dan table bloat/status vacuum PostgreSQL. (2) Pemantauan kesehatan proses swap table pasca-reverse ETL (durasi, keberhasilan, dampak ke query yang sedang berjalan).
- **Kriteria Keberhasilan:**
  - KK1: Tim bisa melihat tren pertumbuhan storage dan kondisi vacuum tanpa perlu login manual ke PostgreSQL setiap kali.
  - KK2: Proses swap table (uji coba terkontrol) yang berjalan lambat atau gagal terdeteksi dan dibedakan dari masalah query biasa.

## Temuan Riset

Riset dilakukan lewat pembacaan langsung `sync.py`/`reindex_analyze.py`/`test_no_downtime_swap.py` (kedua versi, `scripts/reverse_etl/` dan `scripts/reverse_etl_mart_aggregated/`) + verifikasi READ-ONLY langsung ke project serving PostgreSQL (`pg_stat_user_tables`, `pg_depend`, `pg_total_relation_size`) + `gh run list` untuk histori workflow.

1. **`docs/keputusan-tertunda.md` entri "Otomasi reapply `analyst_views` setelah swap reverse ETL `mart_aggregated`" (ditemukan M5.7, Status: Open) wajib direvisit di awal breakdown M6.6** (konvensi project) — dan ternyata jauh lebih parah dari catatan yang ada.

2. **72 dari 76 tabel `mart_aggregated` punya orphan `__old` SEKARANG** (112MB — LEBIH BESAR dari live schema-nya sendiri, 91MB), plus 1 di `mart_cleaned` (`employees__old`, 176KB). Dikonfirmasi query langsung `pg_stat_user_tables WHERE relname LIKE '%__old'`.

3. **`dim_property__old` diikat oleh SELURUH 42 view `analyst_views` DAN 44 view `chatbot_views`** yang dicek lewat `pg_depend`/`pg_rewrite` cross-reference — praktis seluruh lapisan konsumsi Data Analyst dan AI Chatbot terikat ke tabel `__old` untuk dimensi yang kena bug ini, bukan cuma "beberapa view" seperti kesan catatan lama.

4. **Dampak praktis SAAT INI nihil** — dibandingkan langsung `live` vs `__old` untuk 4 tabel (`fact_revenue_property_daily`, `fact_hr_attendance_daily`, `fact_fnb_outlet_daily`, `dim_employee`): row count IDENTIK semua. Konsisten dengan fakta project ini yang sudah berulang kali dicatat — dataset production adalah **snapshot statis**, tidak pernah berubah antar run BigQuery, jadi "baca dari snapshot lama" = "baca dari snapshot sekarang" secara kebetulan. Ini TETAP bug struktural nyata (view terikat ke OID yang salah) yang akan jadi masalah data-correctness sungguhan begitu data production berubah — bukan alasan untuk mengabaikannya.

5. **`reverse_etl_sync_log` (mart_aggregated) SUDAH MENGHITUNG `old_table_status`** (`'dropped'` / `'kept (...)'`) di `sync_table()` (`scripts/reverse_etl_mart_aggregated/sync.py:169-185`) **tapi TIDAK PERNAH menulisnya ke log** — `log_sync_result()` (baris 188-201) cuma menulis `table_name, bq_row_count, pg_row_count, status, dataset_name`. Nilai yang sudah dihitung dibuang, cuma `print()` yang hilang begitu CI selesai — kelas gap yang persis sama dengan yang M6.3 tutup untuk hasil dbt test.

6. **`scripts/reverse_etl/sync.py` (mart_cleaned, M2.4) TIDAK PUNYA try/except graceful-degradation** yang sudah dibangun `scripts/reverse_etl_mart_aggregated/sync.py` (M5.5, fix M5.7) — versi mart_cleaned akan CRASH TOTAL (bukan warning) kalau `DROP TABLE __old` kena `DependentObjectsStillExist`, PERSIS histori nyata M6.2 (`employees__old already exists` bikin `reverse-etl-mart-cleaned.yml` gagal total sebagai job, bukan cuma warning-tapi-lanjut seperti mart_aggregated).

7. **Tidak ada kolom durasi swap sama sekali** di kedua versi `sync.py`/`reverse_etl_sync_log` — hanya row-count parity dan status yang tercatat.

8. **`scripts/reverse_etl/test_no_downtime_swap.py` DAN `scripts/reverse_etl_mart_aggregated/test_no_downtime_swap.py` SUDAH ADA dan re-runnable** — bukti "0 downtime" M2.4 (274 query)/M5.5 (250 query) dibuat lewat script ini: polling `SELECT COUNT(*)` di background thread (interval 0.02s) sambil `sync_table()` dipanggil berulang (8 siklus) di foreground, pakai `get_serving_connection(readonly=True)` — koneksi ADMIN, bukan role scoped baru.

9. **Mekanisme perbaikan aman & terbukti**: `apply_views.py` (baik `scripts/data_analyst_views/` maupun `scripts/chatbot_views/`) pakai `CREATE OR REPLACE VIEW` (dikonfirmasi `grep` langsung ke `.sql` file) — reapply akan mengikat ulang view ke tabel live yang benar (Postgres re-resolve nama tabel saat `CREATE OR REPLACE`), baru setelah itu `DROP TABLE __old` bisa sukses tanpa `DependentObjectsStillExist`. Persis rekomendasi yang sudah tertulis di `docs/keputusan-tertunda.md` sejak M5.7.

10. **`reindex_analyze.py` (kedua versi) SUDAH otomatis jalan tiap workflow terjadwal**, langsung setelah `sync.py --all` (dikonfirmasi baca `.github/workflows/reverse-etl-mart-aggregated.yml`) — REINDEX + ANALYZE, BUKAN VACUUM (autovacuum Postgres jalan otomatis di background secara default; M6.6 cuma perlu membuat STATUS vacuum terlihat/queryable, bukan men-trigger vacuum).

11. **`pg_stat_user_tables` (n_live_tup, n_dead_tup, last_vacuum, last_autovacuum) terbukti bisa dibaca TANPA grant SELECT tabel apa pun** — dites lewat `chatbot_perf_reader` (M6.5, cuma punya `pg_monitor`, TIDAK ada akses `mart_aggregated` sama sekali) — tetap berhasil membaca statistik tabel di schema itu. `pg_total_relation_size()` BUTUH `USAGE` schema minimal — dikonfirmasi gagal `permission denied for schema mart_aggregated` saat dicoba tanpa itu via kredensial yang sama.

12. **Histori `reverse-etl-mart-aggregated.yml` (7 run terakhir sejak 2026-08-08)**: campuran success/failure/skipped — orphan sudah terakumulasi lintas beberapa siklus scheduled run, bukan dari 1 kejadian tunggal.

## Diskusi dengan User (2 keputusan material, dikunci lewat AskUserQuestion — 2 putaran, putaran pertama diminta riset lebih dalam dulu)

### Putaran 1 — user minta riset lebih spesifik sebelum memutuskan
Diajukan 2 pertanyaan awal (instrumentasi sync.py, cleanup orphan). User: "saya ingin anda cek lagi lebih spesifik soal masalah ini" dan "kita diskusikan lebih lanjut" — TIDAK langsung memutuskan. Riset tambahan dilakukan (temuan #3, #4 di atas — cakupan dependency view + verifikasi dampak data-correctness aktual) dan disampaikan lengkap ke user sebelum bertanya ulang.

### Putaran 2 — setelah riset tambahan, user memutuskan
- Q1 (instrumentasi sync.py): **User pilih instrumentasi penuh** (bukan observasi eksternal murni, bukan skip).
- Q2 (cleanup 73 orphan): **User pilih cleanup sekali** (bukan biarkan sebagai bukti saja).

## Technical Decisions

### Decision: Instrumentasi penuh `sync.py` (kedua versi) — commit `fix:`
- **Context:** `old_table_status` sudah dihitung tapi dibuang; `scripts/reverse_etl/sync.py` (mart_cleaned) tidak punya fix M5.7 yang sudah ada di versi mart_aggregated; tidak ada kolom durasi swap sama sekali.
- **Decision:** (1) Tangkap `old_table_status` (mart_aggregated) ke `reverse_etl_sync_log` — bukan logic baru, cuma menyimpan nilai yang sudah dihitung. (2) Port try/except graceful-degradation yang sama (proven M5.7) ke `scripts/reverse_etl/sync.py`. (3) Tambah `swap_duration_ms` — timer di sekitar blok RENAME+DROP saja (bukan seluruh `sync_table()` yang didominasi fetch+COPY BigQuery), di kedua versi.
- **Alternatives considered:** Observasi eksternal murni (0 sentuhan sync.py, deteksi orphan dari `pg_stat_user_tables` langsung, durasi dari `pipeline_run_log` run-level M6.2 yang kurang presisi) — user tidak pilih ini, meski tetap dipakai sebagai Keputusan C (mekanisme deteksi UTAMA tetap query eksternal, terpisah dari soal apakah sync.py diinstrumentasi).
- **Catatan commit:** Ditandai `fix:` — pola sama M6.5 (menutup gap nyata milestone lama: M2.4/M5.5/M5.7), bukan fitur baru M6.6.

### Decision: Cleanup sekali 73 tabel orphan
- **Context:** 112MB tabel orphan MASIH ADA sekarang, mekanisme perbaikan (`apply_views.py --all` x2) sudah terbukti aman.
- **Decision:** Reapply `scripts/data_analyst_views/apply_views.py --all` + `scripts/chatbot_views/apply_views.py --all`, lalu `DROP TABLE` LANGSUNG 73 tabel `__old` (TIDAK perlu rerun `sync.py --all` penuh — begitu dependency OID terlepas via reapply, `DROP TABLE` langsung cukup, tidak perlu re-fetch 76 tabel dari BigQuery lagi). Verifikasi before/after (jumlah orphan, ukuran, live table row count tidak berubah).
- **TIDAK mengubah keputusan otomasi** — `docs/keputusan-tertunda.md` entri M5.7 TETAP Status: Open (dicatat cleanup sekali M6.6 dilakukan, tapi solusi permanen untuk siklus berikutnya tetap keputusan orkestrasi lintas-milestone terpisah, sesuai reasoning entri itu sendiri).

### Decision (derived): Deteksi orphan table via query live `pg_stat_user_tables`, BUKAN cuma baca `old_table_status` log
- **Context:** `old_table_status` cuma menangkap kejadian BARU ke depan setelah kolom ditambahkan — 73 orphan yang sudah ada duluan tidak akan pernah muncul di situ (mereka sudah "synced" sebelum kolom ini ada).
- **Decision:** Detector utama (`detect_orphan_tables.py`) query snapshot storage (`relname LIKE '%__old'`) sebagai sumber kebenaran tunggal — robust terhadap kapan pun orphan itu muncul, tidak bergantung histori log. `old_table_status` di `reverse_etl_sync_log` tetap berguna sebagai jejak audit "sync run mana yang menyebabkannya" ke depan, bukan mekanisme deteksi utama.

### Decision (derived): Storage/vacuum murni dashboard (snapshot), TANPA alert threshold
- **Context:** KK1 minta "tren terlihat" (kata kerja pasif/observasional), beda dari KK2 yang eksplisit minta "terdeteksi" (aktif).
- **Decision:** Snapshot `pg_stat_user_tables` (size, live/dead tuple, last_vacuum/autovacuum) ke `monitoring.serving_storage_snapshot`, TIDAK push `monitoring.alerts` — sama filosofi KK1 M6.5 (latency/slow-query juga murni dashboard, bukan alert-based).

### Decision (derived): Swap health — 2 sub-deteksi, alert_type terpisah
- **Decision:** `serving_swap_orphan_table` (orphan `__old` terdeteksi, critical — sudah terbukti nyata & berdampak luas) dan `serving_swap_slow` (rolling-baseline identik algoritma M6.3 atas `swap_duration_ms`, tanpa filter day-of-week — sama alasan "sensor duration anomaly" M6.3, durasi swap tidak punya pola mingguan berarti).
- **Kenapa 2 alert_type terpisah:** KK2 eksplisit minta "dibedakan dari masalah query biasa" — 2 signature berbeda (orphan vs lambat) perlu tetap terlihat berbeda satu sama lain juga, bukan digabung jadi 1 generic "swap_issue".

### Decision (derived): Kredensial baru `serving_storage_reader`
- **Decision:** `pg_monitor` (baca `pg_stat_user_tables`/`pg_stat_activity`) + `USAGE` schema `mart_cleaned`+`mart_aggregated` (dibutuhkan `pg_total_relation_size()`, dikonfirmasi empiris). SELECT tabel TIDAK digrant di awal (kemungkinan tidak perlu untuk size/stats function) — ditambah kalau ternyata perlu saat implementasi, pola sama gotcha `extensions` schema M6.5.

### Decision (derived): Uji coba terkontrol KK2 — kombinasi bukti nyata + terkontrol
- **Decision:** (1) Orphan detection: 73 orphan yang SUDAH ADA dipakai sebagai bukti NYATA — jalankan detector SEBELUM cleanup, buktikan terdeteksi tepat, BARU cleanup, buktikan ulang hasilnya bersih (0 orphan). (2) Slow swap: uji coba terkontrol NYATA — tahan lock di 1 tabel via transaksi terpisah, trigger sync untuk tabel itu, `swap_duration_ms` naik signifikan (RENAME menunggu lock beneran, bukan angka sintetis), detector rolling-baseline memicu alert. (3) Re-run `test_no_downtime_swap.py` (sudah ada, kedua versi) sebagai bukti tambahan instrumentasi baru tidak mengubah perilaku no-downtime yang sudah terbukti M2.4/M5.5.

### Decision (derived): Folder baru `scripts/serving_layer_monitor/` + workflow terjadwal baru
- **Context:** Tema berbeda dari `monitoring_warehouse` (BigQuery) dan `chatbot_perf_monitor` (chatbot-spesifik) — serving layer PostgreSQL secara umum, relevan Data Analyst DAN AI Chatbot.
- **Decision:** Folder baru. BEDA dari M6.5 (yang sengaja TIDAK bikin workflow terjadwal karena `chatbot_api` manual-only) — sistem reverse ETL PUNYA traffic terjadwal nyata (cron chain sungguhan), jadi snapshot terjadwal genuinely bermakna. Workflow baru `monitoring-serving-layer-health.yml`, `workflow_run` listener ke `"Reverse ETL Mart Aggregated to Serving PostgreSQL"` (titik akhir pipeline, trigger sama M6.3).

## Open Questions Resolved with User

- Q: Bagaimana instrumentasi sync.py, mengingat `old_table_status` sudah dihitung tapi dibuang dan mart_cleaned tidak punya fix M5.7? → A: Instrumentasi penuh (setelah riset tambahan soal cakupan dampak & keamanan mekanisme perbaikan).
- Q: Apakah 73 tabel orphan yang sudah ada dibersihkan sekali sebagai bagian M6.6? → A: Ya, cleanup sekali, terpisah dari keputusan otomasi yang tetap ditunda.

## Task Breakdown

### Checkpoint 1 — Fondasi: decisions.md + kredensial + schema
- [x] Task 1: `decisions.md` — dokumen ini.
- [x] Task 2: Kredensial `serving_storage_reader` (serving) — `pg_monitor` + `USAGE` `mart_cleaned`+`mart_aggregated`. **Selesai** — 8/8 isolation checks OK, dikonfirmasi USAGE-only (tanpa SELECT) cukup untuk `pg_total_relation_size()`.
- [x] Task 3: `scripts/serving_layer_monitor/{connections.py, verify_role_isolation.py, db.py}` + schema baru. **Selesai** — diverifikasi `information_schema`.

### Checkpoint 2 — Instrumentasi sync.py — commit `fix:`
- [ ] Task 4: `scripts/reverse_etl_mart_aggregated/sync.py` — capture `old_table_status`+`swap_duration_ms`.
- [ ] Task 5: `scripts/reverse_etl/sync.py` — port graceful-degradation + `swap_duration_ms` + capture `old_table_status`.
- [ ] Task 6: Verifikasi live.

### Checkpoint 3 — KK1: storage growth + vacuum
- [ ] Task 7: `snapshot_serving_storage.py`.
- [ ] Task 8: Verifikasi live.

### Checkpoint 4 — KK2: swap health detection
- [ ] Task 9: `detect_orphan_tables.py` — SEBELUM cleanup.
- [ ] Task 10: `detect_swap_duration_anomaly.py`.
- [ ] Task 11: Uji coba terkontrol slow-swap nyata (lock).
- [ ] Task 12: Re-run `test_no_downtime_swap.py`.

### Checkpoint 5 (final) — Cleanup + konsolidasi
- [ ] Task 13: Cleanup 73 orphan.
- [ ] Task 14: Re-run `detect_orphan_tables.py` pasca-cleanup.
- [ ] Task 15: `simulate_test.py`.
- [ ] Task 16: Workflow `monitoring-serving-layer-health.yml`.
- [ ] Task 17: Update peta M6.1 + `keputusan-tertunda.md`.
- [ ] Task 18: `logs.md` + `report.md`.
