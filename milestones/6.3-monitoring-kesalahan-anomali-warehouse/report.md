# Milestone 6.3: Monitoring Kesalahan dan Anomali di Pipeline Warehouse — Report

**Status:** Completed
**Date completed:** 2026-08-11

## Kriteria Keberhasilan — Hasil

- [x] **KK1 — Kegagalan pengujian data `mart_cleaned`/`mart_aggregated` (uji coba terkontrol) terlihat di monitoring tanpa buka log mentah.** — Terpenuhi. Fault-injection nyata (bukan simulasi) ke `mart_cleaned__bookings.sql` (`UNION ALL` baris `total_amount=-500000`, pola persis M2.3), trigger `transform-mart-cleaned.yml` run `31436680183`: gate `promote.py` FAIL sesuai desain (swap dibatalkan), step capture baru (`if: always()`) tetap jalan dan menulis **37 baris detail** ke `monitoring.dbt_test_result` — **tepat 1** `status='fail'` (`assert_bookings_total_amount_non_negative`, `failures=1`), 36 sisanya `pass`. Query SQL langsung menjawab "test mana yang gagal", tanpa buka log CI mentah. `promote.py` sendiri tidak disentuh 1 baris pun.
- [x] **KK2 — Penyimpangan volume buatan (uji coba terkontrol) terdeteksi, bisa dibedakan tahap asalnya.** — Terpenuhi. `snapshot_warehouse_volume.py` (3 dataset BigQuery, `__TABLES__` metadata) + `detect_volume_anomaly.py` (replikasi algoritma `detect_alerts.py` Fase 1). Uji coba terkontrol: 2 tabel beda dataset (`mart_cleaned.mart_cleaned__employees`, `mart_aggregated.dim_access_level`), histori 3 minggu + outlier 10x — **2 alert `critical` terpisah**, masing-masing `schema_name`/`table_name` (dataset/tabel) teridentifikasi tepat, membuktikan "bisa dibedakan dari tahap mana asalnya".
- [x] **KK3 — Ketidakcocokan row count BigQuery vs PostgreSQL (uji coba terkontrol) terdeteksi + tabel teridentifikasi.** — Terpenuhi. `detect_parity_mismatch.py`, murni konsolidasi `monitoring.reverse_etl_sync_log` (M2.4/M5.5) yang sudah lengkap — 0 mekanisme baru, `sync.py` tidak disentuh. Uji coba terkontrol: 1 baris sintetis `mismatch_aborted` (`is_simulated=TRUE`) — alert `critical` muncul tepat 1, `table_name='mart_cleaned__bookings_SIM_TEST'` teridentifikasi benar dengan `bq_row_count`/`pg_row_count` sesuai. Run non-simulasi tetap 0 (isolasi tidak bocor).
- [x] **KK4 — Keterlambatan `ml_output` (uji coba terkontrol) terdeteksi sebagai freshness issue, bukan cuma kegagalan sensor.** — Terpenuhi, 2 sub-mekanisme independen dari `wait_for_ml_output.py` (tidak disentuh sama sekali): (a) `snapshot_ml_output_freshness.py` (`MAX(scored_at)` BigQuery, threshold daily 48h/96h dari Fase 1) — uji coba terkontrol lag=150h → alert `critical` detail eksplisit "lag=150.0h"; (b) `detect_ml_output_issues.py` sensor-duration sub-detection, reuse `monitoring.pipeline_run_log` titik 5 (M6.2) — uji coba terkontrol durasi 3600s vs baseline ~97s → alert `critical` (`z=63.27`) detail eksplisit menyebut durasi sensor. Keduanya secara eksplisit BUKAN "sensor gagal" generik — detail selalu spesifik penyebabnya.

## Deliverables

- `scripts/monitoring_warehouse/{schema.sql}` — extended: `dbt_test_result`, `warehouse_volume_snapshot`, `ml_output_freshness_snapshot`, view `warehouse_parity_status`, `reverse_etl_sync_log.is_simulated`, `alerts.alert_type` +4 nilai.
- `scripts/monitoring_warehouse/{bq.py, capture_dbt_test_results, snapshot_warehouse_volume, detect_volume_anomaly, detect_parity_mismatch, snapshot_ml_output_freshness, detect_ml_output_issues, simulate_test}.py` — baru.
- `.github/workflows/monitoring-warehouse-dq-anomaly.yml` — baru, terjadwal via `workflow_run` ke titik 8 (10 titik peta M6.1), diverifikasi 2 jalur (auto-skip saat upstream gagal, jalan penuh saat dispatch manual).
- `.github/workflows/{transform-mart-cleaned, transform-mart-aggregated}.yml` — edit, +1/+2 step (`if: always()`) — **satu-satunya sentuhan ke file pipeline existing di seluruh keluarga 6.x**, `promote.py` sendiri tidak disentuh.
- Kredensial baru `warehouse-monitor-reader` (BigQuery, READER 4 dataset) — isolasi 5/5 OK, write ditolak 403, terdokumentasi di `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`.
- `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` — diperbarui (titik 1,2,3,5,6,7,10).
- `docs/keputusan-tertunda.md` — entri DQ gate ditutup **Resolved**.
- `milestones/6.3-monitoring-kesalahan-anomali-warehouse/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada deviasi pada keputusan inti. **4 revisi teknis ditemukan & diperbaiki saat implementasi** (dicatat eksplisit di `decisions.md`, bukan disembunyikan — pola konsisten project ini):
1. **Keputusan #4** (row count via `INFORMATION_SCHEMA.TABLE_STORAGE`) — ternyata `Access Denied` (kemungkinan restriksi BigQuery Sandbox mode), diganti `__TABLES__` legacy pseudo-table, angka diverifikasi akurat.
2. **Keputusan #7** (view `warehouse_parity_status`) — hardcode `is_simulated=FALSE` membuat uji coba terkontrol KK3 mustahil lewat view; `detect_parity_mismatch.py` diubah query langsung ke tabel dengan parameter eksplisit.
3. **Keputusan #10** (sensor duration anomaly) — filter same-day-of-week dihapus (tidak ada pola mingguan berarti untuk metrik ini, beda dari volume bisnis).
4. **Bug timezone nyata**: `detect_ml_output_issues.py` awalnya pakai local date, mismatch dengan writer yang UTC eksplisit — diperbaiki sebelum sempat jadi masalah produksi (GitHub Actions runner UTC, tapi testing lokal WIB langsung menampakkan bug-nya).

Satu penambahan di luar breakdown Task asli (dicatat di `logs.md`, bukan deviasi keputusan): **`detect_parity_mismatch.py` ditambahkan ke workflow terjadwal** — Task 15 plan awal cuma menyebut Task 7→8 dan 12→13, oversight yang dikoreksi karena KK3 butuh deteksi otomatis harian juga.

## Catatan Pasca-Closure (2026-08-11)

Ditemukan user lewat GitHub Actions UI (bukan dari verifikasi saya) **setelah** milestone ini ditutup Completed: run `monitoring-warehouse-pipeline-log.yml` (workflow **Milestone 6.2**, bukan M6.3) sempat FAILED — dipicu sebagai efek samping uji coba fault-injection Checkpoint 2 Task 6 (`transform-mart-cleaned.yml` sengaja dibuat gagal, menyebabkan `transform-mart-aggregated.yml` skip diri sendiri, dan `snapshot_pipeline_run.py` milik M6.2 crash mengamati run yang di-skip itu). **Bug ini di file M6.2 (`scripts/monitoring_warehouse/snapshot_pipeline_run.py`), bukan di salah satu dari 8 script M6.3** — jalur kodenya sepenuhnya terpisah dari 4 KK yang dilaporkan Completed di atas, jadi hasil verifikasi KK1-4 tidak berubah/terpengaruh. Diperbaiki dan diverifikasi ulang di CI sungguhan (commit `b295338`, run [`31439829146`](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31439829146)) — detail lengkap di `milestones/6.2-monitoring-log-proses-pipeline/logs.md`. Dicatat di sini murni untuk jejak sejarah lengkap (uji coba M6.3 yang menyingkap bug M6.2), bukan revisi terhadap hasil M6.3 sendiri.

## Known Gaps / Follow-ups

- **Test count mart_aggregated re-verifikasi 190, bukan "244+1" di `report.md` M5.3** — drift kemungkinan dari M5.6/M5.7, akar penyebab tidak ditelusuri (di luar scope M6.3).
- **Timeout sensor realistis (~60 menit) masih belum pernah diuji habis** — carry-over dari M6.1/M6.2, tidak berubah oleh M6.3 (M6.3 memantau durasi APAPUN yang terjadi, tidak menguji ulang timeout itu sendiri).
- **2 kegagalan orphan-table nyata ditemukan tanpa sengaja saat verifikasi Checkpoint 6** (`reverse-etl-mart-aggregated.yml` gagal, listener baru terbukti benar self-skip) — konfirmasi lanjutan risiko M5.7 yang sudah tercatat di `docs/keputusan-tertunda.md`, bukan gap baru M6.3, di luar scope untuk diperbaiki di sini.
- **`simulate_test.py` sengaja tidak mencakup KK1** — butuh fault-injection nyata ke model dbt (sudah dibuktikan terpisah Checkpoint 2 Task 6), tidak bisa direplikasi lewat data snapshot sintetis karena yang diuji adalah pipa capture itu sendiri.
- **Rotasi kredensial `warehouse-monitor-reader` belum otomatis** — konsisten gap project-wide yang sudah dicatat untuk seluruh kredensial lain.

## Handoff Notes

- **Milestone 6.4 (Drift ML):** `monitoring.ml_output_freshness_snapshot` dan sensor-duration anomaly (titik 5) sudah tersedia sebagai fondasi — M6.4 bisa fokus ke model staleness/kelengkapan `ml_output` tanpa membangun ulang freshness dari nol.
- **Milestone 6.5 (Performa Query Chatbot):** tidak terpengaruh langsung, tapi pola `monitoring.alerts` extensible (`alert_type` CHECK) siap dipakai kalau M6.5 butuh alert query lambat/gagal.
- **Milestone 6.6 (Reverse ETL/Serving Layer):** `monitoring.warehouse_parity_status` + `detect_parity_mismatch.py` sudah mengonsolidasikan row-count parity — M6.6 bisa fokus ke storage growth/vacuum/swap-health tanpa mengulang parity check.
- **Milestone 6.7 (Dashboard Terpadu):** `monitoring.alerts` sekarang punya 9 `alert_type` (5 Fase 1 + 4 M6.3) sebagai 1 sumber konsolidasi — dashboard tinggal query 1 tabel untuk seluruh sinyal kesalahan/anomali. `monitoring.dbt_test_result.github_run_id` siap di-JOIN ke `pipeline_run_log.run_id` (M6.2) untuk drill-down dari status kasar ke detail per-test.
- **Pemilik infrastruktur `sync.py`/reverse ETL:** 2 kegagalan orphan-table nyata (Checkpoint 6) memperkuat urgensi entri M5.7 `docs/keputusan-tertunda.md` — pertimbangkan diangkat sebelum M6.7 menyusun dashboard final, supaya tidak muncul sebagai alert berulang yang membingungkan.
