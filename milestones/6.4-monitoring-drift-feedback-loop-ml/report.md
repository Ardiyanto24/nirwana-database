# Milestone 6.4: Monitoring Data Drift Feedback Loop ML — Report

**Status:** Completed
**Date completed:** 2026-08-11

## Kriteria Keberhasilan — Hasil

- [x] **KK1 — Tim bisa melihat kapan model terakhir di-retrain untuk tiap `model_version` yang aktif tanpa bertanya langsung ke tim Data Scientist.** — Terpenuhi, sebagai mekanisme **informational-only** sesuai keputusan eksplisit user (bukan alert-based — `model_version` di pipeline mock M5.4 adalah string konstan hardcoded, tidak ada cadence retrain sungguhan untuk dikalibrasi jadi threshold). `snapshot_ml_model_version.py` + view `monitoring.ml_model_staleness_status` menjawab pertanyaan literal KK1 langsung dari query: data live menunjukkan `model_version='occupancy_forecast_mock_v1'` aktif sejak `first_scored_at=2026-08-08`, `days_since_first_scored` terhitung benar, `is_most_recently_active=true`. Diverifikasi 2 jalur: data live nyata (Checkpoint 2) dan skenario sintetis di `simulate_test.py` (100 hari, cek angka & flag benar). Entri baru `docs/keputusan-tertunda.md` mencatat threshold retrain cadence masih perlu didiskusikan dengan tim Data Scientist — bukan diselesaikan sepihak oleh data engineering.
- [x] **KK2 — Entity yang gagal ter-score (ada di populasi tapi tidak muncul di `ml_output`) teridentifikasi otomatis.** — Terpenuhi. `check_ml_output_completeness.py` membandingkan populasi `mart_aggregated.fact_revenue_room_type_daily` (BUKAN `mart_cleaned` langsung — revisi teknis dipaksa temuan, lihat Deviations) vs `ml_output.predictions`, mengidentifikasi entity hilang baris per baris (bukan cuma angka). Diverifikasi baseline live (`expected=18 scored=18 missing=0`) DAN fault-injection nyata ke `mock_score.py` (1 property dikecualikan pada `feature_snapshot_at` yang belum pernah dipakai run manapun — `expected=18 scored=15 missing=3`, tepat `P03` dengan 3 room_type terdeteksi, alert `monitoring.alerts` + 3 baris `ml_output_missing_entity` benar). Satu-satunya dari 3 mekanisme M6.4 yang push ke `monitoring.alerts` (`ml_output_incomplete_scoring`) — sesuai keputusan bahwa ini temuan biner berbasis evidence, bukan threshold tebakan.
- [x] **KK3 — Tren drift (jika data drift sudah diekspos oleh pipeline scoring) tervisualisasi dan bisa dipantau dari waktu ke waktu.** — Terpenuhi **sebagai kapasitas deteksi ketersediaan** (canary), BUKAN visualisasi tren sungguhan — konsisten catatan ketergantungan dokumen sumber sendiri ("milestone ini menyediakan kapasitas pemantauan begitu data tersedia, bukan menentukan threshold-nya"). Tidak ada data/tabel drift apa pun di project saat ini (dikonfirmasi riset, dokumen arsitektur sendiri menandainya "area validasi terbuka"). `check_drift_data_availability.py` mendeteksi EKSISTENSI dataset yang cocok pola nama (`drift`/`ml_monitoring`, nol asumsi skema kolom) — begitu tim Data Scientist mempublikasikan data drift, canary ini akan otomatis mendeteksinya dan mencatatnya, memberi sinyal kapan visualisasi tren sungguhan (di luar scope M6.4) baru bisa mulai dibangun. Diverifikasi 2 jalur nyata: state sekarang (`found=false`) dan dataset throwaway BigQuery (`bq mk`/`bq rm`, `found=true` nama benar).

## Deliverables

- `scripts/monitoring_warehouse/schema.sql` — extend: `ml_model_version_snapshot` + view `ml_model_staleness_status`, `ml_output_completeness_snapshot`, `ml_output_missing_entity`, `ml_drift_data_availability_check`, extend `alerts.alert_type` (+`ml_output_incomplete_scoring`).
- `scripts/monitoring_warehouse/{snapshot_ml_model_version, check_ml_output_completeness, check_drift_data_availability}.py` — baru.
- `scripts/monitoring_warehouse/simulate_test.py` — extend (2 skenario baru: staleness view, drift canary; KK2 completeness sengaja tidak masuk, sama alasan KK1 M6.3).
- `.github/workflows/monitoring-warehouse-dq-anomaly.yml` — extend (3 step baru), diverifikasi jalan penuh hijau di CI sungguhan (run [`31443361931`](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31443361931)).
- Kredensial `warehouse-monitor-reader` — tambah `roles/bigquery.metadataViewer` project-level (IAM, dieksekusi manual oleh user karena diblokir classifier auto-mode). Terbukti dibutuhkan: sebelum grant ini, `list_datasets()` cuma melihat 4/7 dataset (yang sudah di-ACL M6.3); setelah grant + propagasi (~2-3 menit), 7/7 dataset terlihat. `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` diperbarui.
- `docs/keputusan-tertunda.md` — entri baru: threshold retrain cadence model staleness, Status Open.
- `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` — diperbarui (titik 4, 5).
- `milestones/6.4-monitoring-drift-feedback-loop-ml/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada deviasi pada 2 keputusan material yang dikunci lewat diskusi user (staleness informational-only, drift via canary). **2 hal ditemukan & diperbaiki saat implementasi** (dicatat eksplisit di `logs.md`, bukan disembunyikan):

1. **Bug nyata di `check_ml_output_completeness.py` (Checkpoint 3, Task 8)**: query awal salah asumsi `ml_output.predictions` punya kolom `property_id`/`room_type_id` terpisah — ternyata cuma `entity_id` komposit (`"property_id:room_type_id"`). Diperbaiki pakai `SPLIT(entity_id, ':')`, sama pola dbt model `fact_ml_occupancy_forecast_property_room_type.sql`.
2. **Desain uji coba KK2 (Checkpoint 3, Task 9)** perlu penyesuaian di tengah eksekusi: karena `mock_score.py` selalu memakai `last_date = MAX(period_date)` (statis) dan self-union (tidak pernah menghapus baris lama), sekadar exclude 1 property tanpa mengganti `last_date` tidak akan pernah terlihat "missing". Ditambahkan 2 CLI flag TEMPORARY ke `mock_score.py` (`--test-last-date`, `--test-exclude-property-id`) untuk memaksa `feature_snapshot_at` yang belum pernah dipakai — direvert penuh setelah test (`git checkout --`, dikonfirmasi bersih).

**1 penyesuaian scope kecil di Checkpoint 5**: `check_ml_output_completeness.py` awalnya cuma didesain untuk "snapshot terbaru", tapi selama implementasi ditambahkan CLI flag permanen `--feature-snapshot-at`/`--simulated` (bukan sementara) supaya bisa audit snapshot spesifik — dipakai langsung untuk uji coba terkontrol KK2, dan berguna untuk audit manual di masa depan.

## Known Gaps / Follow-ups

- **KK3 (drift) baru berupa kapasitas deteksi ketersediaan, bukan visualisasi tren sungguhan** — literally tidak bisa dipenuhi lebih jauh dari itu sampai tim Data Scientist mengekspos data drift nyata (dependency eksternal, bukan gap M6.4). Begitu canary mendeteksi `dataset_found=true` di masa depan, itu sinyal untuk memulai kerja lanjutan (di luar scope M6.4).
- **Threshold cadence retrain model staleness belum ditentukan** — dicatat eksplisit di `docs/keputusan-tertunda.md`, sengaja tidak diputuskan sepihak oleh data engineering (keputusan user, konsisten filosofi threshold drift di dokumen arsitektur).
- **Nama pola canary drift (`drift`, `ml_monitoring`) adalah usaha wajar, bukan jaminan penuh** — kalau tim Data Scientist memakai nama dataset yang sama sekali berbeda, canary ini tidak akan mendeteksinya. Didokumentasikan sebagai keterbatasan yang diketahui (`decisions.md`), bukan diam-diam diasumsikan sempurna.
- **Populasi "expected" completeness (KK2) mengasumsikan window scoring = 1 hari (`period_date` = `feature_snapshot_at`)** — cukup untuk desain `mock_score.py` saat ini (semua entity di-scan dalam 1 batch per run), tapi kalau pipeline scoring nyata nanti scoring bertahap/multi-batch per hari, definisi "expected" ini perlu ditinjau ulang.

## Handoff Notes

- **Milestone 6.5 (Performa Query Chatbot):** tidak terpengaruh langsung.
- **Milestone 6.6 (Reverse ETL/Serving Layer):** tidak terpengaruh langsung.
- **Milestone 6.7 (Dashboard Terpadu):** `monitoring.alerts` sekarang punya 10 `alert_type` (9 sebelumnya + `ml_output_incomplete_scoring`). `monitoring.ml_model_staleness_status` dan `monitoring.ml_drift_data_availability_check` adalah 2 sumber informational BARU yang TIDAK lewat `monitoring.alerts` (sengaja, lihat decisions.md) — kalau M6.7 ingin menampilkan staleness/drift-availability di dashboard, harus query langsung ke 2 tabel/view ini, bukan cuma `monitoring.alerts`.
- **Kalau tim Data Scientist akhirnya mempublikasikan data drift nyata:** cek dulu `monitoring.ml_drift_data_availability_check` (kalau canary sudah pernah mendeteksinya, `dataset_found=true` dengan `dataset_name` aktual akan langsung menunjukkan nama datasetnya) sebelum membangun mekanisme visualisasi tren baru dari nol.
- **Kalau `mock_score.py` diganti pipeline scoring sungguhan:** `model_version` diharapkan mulai benar-benar bervariasi antar retrain — saat itu terjadi, `docs/keputusan-tertunda.md` entri threshold staleness perlu direvisit (saat ini sengaja tanpa alert karena tidak ada cadence retrain sungguhan untuk dikalibrasi).
