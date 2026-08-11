# Milestone 6.6: Monitoring Reverse ETL dan Serving Layer PostgreSQL — Report

**Status:** Completed
**Date completed:** 2026-08-11

## Kriteria Keberhasilan — Hasil

- [x] **KK1 — Tim bisa melihat tren pertumbuhan storage dan kondisi vacuum tanpa perlu login manual ke PostgreSQL setiap kali.** — Terpenuhi. `snapshot_serving_storage.py` (via kredensial `serving_storage_reader`, `pg_monitor`+`USAGE`, TANPA SELECT tabel apa pun) snapshot SEMUA tabel `mart_cleaned`+`mart_aggregated` (size, live/dead tuple, `last_vacuum`/`last_autovacuum`) ke `monitoring.serving_storage_snapshot`, dijadwalkan harian. Diverifikasi data live: 173 tabel awal (531.6MB), turun ke 100 tabel (409.7MB) setelah cleanup — tren storage langsung terlihat dari 1 query, tanpa login manual.
- [x] **KK2 — Proses swap table (uji coba terkontrol) yang berjalan lambat atau gagal terdeteksi dan dibedakan dari masalah query biasa.** — Terpenuhi, dengan 2 mekanisme bersinyal berbeda (Keputusan E): `detect_orphan_tables.py` (`alert_type='serving_swap_orphan_table'`, terbukti dari **73 orphan NYATA** yang sudah ada di database — bukan sintetis) dan `detect_swap_duration_anomaly.py` (`alert_type='serving_swap_slow'`, terbukti dari **uji coba terkontrol nyata**: lock `ACCESS EXCLUSIVE` 20 detik menahan RENAME sungguhan, `swap_duration_ms=10518.7ms` tertangkap vs baseline ~914ms, detector CRITICAL `z=71.43`). Keduanya jelas berbeda signature dari "masalah query biasa" (bukan `pg_stat_activity` lambat atau query timeout generik) — 2 `alert_type` terpisah secara eksplisit menyebutkan kelasnya di nama sendiri.

## Deliverables

- `scripts/serving_layer_monitor/{connections.py, verify_role_isolation.py, db.py, schema.sql, apply_schema.py}` — fondasi dual-instance (serving + production).
- Kredensial baru `serving_storage_reader` (serving) — `pg_monitor` + `USAGE` 2 schema, **kredensial paling sempit di project ini** (0 akses data baris apa pun).
- **`fix:` scripts/reverse_etl/sync.py + scripts/reverse_etl_mart_aggregated/sync.py** — `old_table_status`+`swap_duration_ms` ditangkap ke `reverse_etl_sync_log` (nilai yang sebelumnya dihitung tapi dibuang); `scripts/reverse_etl/sync.py` (mart_cleaned) dapat port try/except graceful-degradation yang sebelumnya cuma ada di `mart_aggregated` (M5.7) — diverifikasi NYATA (bukan cuma port kode) lewat skenario dependency-conflict sungguhan.
- `scripts/serving_layer_monitor/{snapshot_serving_storage.py, detect_orphan_tables.py, detect_swap_duration_anomaly.py, cleanup_orphan_tables.py, simulate_test.py}` — baru.
- `.github/workflows/monitoring-serving-layer-health.yml` — baru, diverifikasi jalan penuh hijau di CI sungguhan (run `31454420692`).
- **Cleanup satu kali**: 73 tabel orphan `__old` (112.1MB) dibersihkan — reapply `data_analyst_views`+`chatbot_views`, `DROP TABLE` langsung. Verifikasi before/after: live table row count utuh, view masih berfungsi lewat tabel yang benar.
- `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`, `.env.example`, `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md`, `docs/keputusan-tertunda.md` — diperbarui.
- **Tidak disentuh:** `authz.py`, `role_permissions`, isi `apply_views.py` itu sendiri (dijalankan, tidak diedit), `reindex_analyze.py` (sudah otomatis benar sejak awal).

## Deviations from decisions.md

Tidak ada deviasi pada Keputusan A-B (dikunci user, setelah 2 putaran diskusi + riset tambahan). **3 hal ditemukan & diperbaiki saat implementasi** (dicatat eksplisit di `logs.md`):

1. **Task 6 (Checkpoint 2)**: tabel dengan orphan existing tidak bisa dipakai untuk verifikasi biasa (RENAME collision) — dipilih tabel bebas orphan untuk happy-path, PLUS ditambahkan verifikasi jalur warning yang lebih lengkap dari rencana (skenario dependency-conflict nyata untuk mart_cleaned).
2. **Task 11 (Checkpoint 4)**: percobaan pertama lock pakai kredensial admin gagal (`permission denied` — admin tidak punya privilege ke tabel yang tidak dimilikinya, temuan M3.5 terbukti lagi) — diperbaiki pakai kredensial OWNER tabel.
3. **Task 14 (Checkpoint 5)**: `detect_orphan_tables.py` awalnya pakai `datetime.now().date()` — snapshot sebelum/sesudah cleanup di hari yang sama membuat baris stale tidak pernah "hilang" dari query "hari ini". Diperbaiki pakai `MAX(snapshot_date)` dari tabel.

**1 gap BARU ditemukan, DI LUAR scope yang disetujui** (Task 12 lanjutan, Checkpoint 5): RENAME step (beda dari DROP step yang diperbaiki Keputusan A) masih rentan crash `DuplicateTable` kalau nama `__old` sudah dipakai orphan dari siklus sebelumnya. Direproduksi nyata (`test_no_downtime_swap.py` mart_aggregated crash di cycle 2/8). Didokumentasikan lengkap, di-flag sebagai follow-up terpisah (task spawn `task_f2313778`), entri baru `docs/keputusan-tertunda.md`.

## Known Gaps / Follow-ups

- **RENAME step belum diproteksi dari tabrakan nama dengan orphan lama** (temuan baru M6.6, lihat di atas) — di luar Keputusan A yang disetujui, perlu keputusan/persetujuan terpisah untuk memperluas scope graceful-degradation.
- **`test_no_downtime_swap.py` mart_aggregated tidak sempat di-re-run PENUH 8 siklus** pasca-instrumentasi (terhalang gap RENAME di atas) — KK2 "zero downtime" tetap dianggap valid lewat penalaran tidak langsung (mart_cleaned re-run penuh sukses + mekanisme RENAME/DROP byte-identik di kedua file, cuma dibungkus timer) plus bukti asli M5.5, bukan re-run baru mart_aggregated secara langsung.
- **Otomasi pencegahan orphan-table (reapply view otomatis) TETAP Open** di `docs/keputusan-tertunda.md` — cleanup M6.6 murni satu kali, orphan baru akan menumpuk lagi di siklus berikutnya tanpa intervensi manual (tapi sekarang minimal LANGSUNG TERDETEKSI harian via `detect_orphan_tables.py`, tidak lagi didiamkan sampai ditemukan tidak sengaja).
- **`detect_swap_duration_anomaly.py` mode terjadwal cuma cek tabel yang sync HARI ITU** — tabel yang jarang berubah/tidak pernah re-sync dalam beberapa hari tidak akan pernah baseline-nya terbangun dari mode terjadwal saja (baseline `dim_shift_type` di milestone ini dibangun manual, 8 run berturut-turut) — wajar untuk mekanisme rolling-baseline, bukan bug, tapi baseline baru akan genuinely representatif setelah beberapa hari run terjadwal nyata.

## Handoff Notes

- **Milestone 6.7 (Dashboard Terpadu):** `monitoring.alerts` sekarang punya 13 `alert_type` (11 sebelumnya + `serving_swap_orphan_table` + `serving_swap_slow`). `monitoring.serving_storage_snapshot` adalah sumber BARU informational (TIDAK lewat `monitoring.alerts`, sama pola staleness M6.4/latency M6.5) — kalau M6.7 ingin menampilkan storage growth/vacuum di dashboard, query langsung ke tabel ini.
- **Pemilik infrastruktur reverse ETL**: 2 hal untuk ditindaklanjuti — (1) gap RENAME-step baru (`docs/keputusan-tertunda.md`, task follow-up sudah di-spawn); (2) keputusan otomasi reapply-view yang sudah lama Open (M5.7), sekarang dengan bukti dampak jauh lebih besar dari perkiraan awal (73 tabel, bukan "beberapa").
- **Kalau orphan menumpuk lagi di masa depan**: `scripts/serving_layer_monitor/cleanup_orphan_tables.py --dry-run` untuk preview, tanpa `--dry-run` untuk eksekusi — re-runnable, sama pola dipakai M6.6 untuk 73 tabel pertama. WAJIB reapply `data_analyst_views`+`chatbot_views` dulu sebelum menjalankannya.
