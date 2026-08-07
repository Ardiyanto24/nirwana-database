# Milestone 1.3: Monitoring Kualitas Data dan Anomali Nilai — Report

**Status:** Completed
**Date completed:** 2026-08-07

## Kriteria Keberhasilan — Hasil

- [x] **Pengujian kualitas data berjalan terjadwal dan hasilnya bisa ditelusuri (lolos/gagal per tabel per waktu).** — Sebagian: mekanismenya bisa dijalankan kapan saja dan hasilnya jelas bisa ditelusuri (evidence: query `monitoring.dq_test_results GROUP BY schema_name, table_name, run_date` menunjukkan histori lolos/gagal untuk 23/23 tabel, lihat `logs.md`). **"Terjadwal" secara otomatis belum** — konsisten dengan keputusan Milestone 1.2 yang ditunda (`docs/keputusan-tertunda.md`, `pg_cron` belum diaktifkan), sekarang mencakup juga runner Milestone 1.3.
- [x] **Anomali nilai buatan (uji coba terkontrol, di luar pola dirty data yang sudah dikenal) berhasil terdeteksi.** — Evidence: `scripts/dq/simulate_test.py`, skenario `dq_failure_case`, `dirty_drift_case` (z=256), `value_spike_case` (z=158) — ketiganya memicu alert critical sesuai ekspektasi.
- [x] **Proporsi dirty data yang sudah diketahui (missing value, format tidak konsisten, dsb.) TIDAK memicu false alert pada kondisi normal.** — Evidence ganda: (1) simulasi `dirty_normal_case`, `dirty_bootstrap_normal`, `value_normal_case`, `dq_normal_case` — semua benar TIDAK memicu alert; (2) **data production nyata**: `detect_dq_failures`/`detect_dirty_drift`/`detect_value_anomalies` dijalankan terhadap 23 tabel real, dan seluruh 8 kolom dirty-by-design (`guests.email` 3,97%, `fnb_transactions.guest_id` 31,06%, dst — semuanya dalam rentang M1.1) **tidak memicu satu pun alert palsu**.

## Deliverables

- `requirements.txt` (baru) — `psycopg2-binary`, `great_expectations[postgresql]`.
- `scripts/dq/ge_context.py` — Data Context GE + datasource Postgres (Fluent API), kredensial via substitusi `${SUPABASE_DB_URL}` (bukan mentah di file yang di-commit).
- `scripts/dq/schema.sql` — perluasan schema `monitoring`: `dq_test_results`, `dirty_proportion_snapshot`, `value_anomaly_snapshot`, plus `alerts.alert_type` diperluas 3 jenis baru.
- `scripts/dq/rules_config.py` — 31 custom business rule (26 dari 27 katalog M1.1, disesuaikan setelah 3 ditemukan salah asumsi; +5 basic sanity check tambahan untuk tabel di luar katalog) + not_null/unique/accepted_values dasar untuk seluruh 23 tabel.
- `scripts/dq/build_and_run.py` — bangun & jalankan expectation suite, tulis hasil ke `monitoring.dq_test_results`.
- `scripts/dq/dirty_columns_config.py` + `snapshot_dirty_proportion.py` — snapshot & evaluasi drift 8 kolom dirty-by-design (mode bootstrap → rolling).
- `scripts/dq/value_anomaly_config.py` + `snapshot_value_anomaly.py` — snapshot IQR & evaluasi drift outlier 6 kolom nilai bisnis kritis.
- `scripts/dq/dq_alerts.py` — gabungkan 3 sumber deteksi ke `monitoring.alerts`.
- `scripts/dq/simulate_test.py` — uji coba terkontrol, 7 skenario, 7/7 PASS.
- `milestones/1.3-kualitas-data-anomali/{decisions,logs}.md` — keputusan & jurnal lengkap.
- `docs/keputusan-tertunda.md` — entri `pg_cron` diperbarui, cakupan bertambah ke Milestone 1.3.

## Deviations from decisions.md

- **Rule `staff_shifts.clock_out > clock_in` dihapus total dari suite** (bukan dikoreksi seperti rule lain) — ditemukan bahwa kolom `time`-only (tanpa tanggal) secara fundamental tidak bisa membedakan shift yang sah lewat tengah malam dari durasi negatif yang salah. Bukan penyimpangan dari keputusan (masih dalam semangat "GE untuk rule tetap"), tapi hasil akhirnya rule ini tidak ada di suite final — beda dari rencana awal yang mengasumsikan semua 27 rule katalog M1.1 langsung terpakai.
- Tidak ada deviasi lain dari `decisions.md`.

## Known Gaps / Follow-ups

- **Penjadwalan otomatis masih tertunda** (lihat `docs/keputusan-tertunda.md`) — sama seperti Milestone 1.2, cakupannya sekarang juga meliputi seluruh runner Milestone 1.3.
- **`staff_shifts` tidak punya validasi urutan clock_in/clock_out** — keterbatasan skema nyata (kolom `time` tanpa tanggal), bukan sesuatu yang bisa diperbaiki di level query monitoring. Kalau butuh validasi ini di masa depan, perlu perubahan skema production (tambah tanggal ke kolom, atau kolom durasi terpisah) — di luar scope Milestone 1.3.
- **Temuan data quality nyata yang belum diperbaiki** (di luar scope milestone ini untuk memperbaiki data, hanya mendeteksi):
  - `bookings.total_amount != room_rate × nights` pada 165/217.654 baris (0,076%) — kemungkinan artefak rounding saat generate data sintetis.
- **Cakupan 4 tabel prioritas Rendah lebih tipis** — sesuai keputusan cakupan penuh, tapi `fnb_outlets`, `fnb_inventory`, `venues` hanya punya basic checks (not_null/unique/accepted_values), belum ada business rule custom sedalam 19 tabel lainnya (katalog M1.1 memang tidak sedalam itu untuk keempatnya).
- **`event_bookings` freshness** (dari Milestone 1.2) masih volume-only — tidak berubah oleh Milestone 1.3.

## Handoff Notes

- **Untuk Milestone 1.4 (schema drift)**: temuan tipe kolom yang meleset dari deskripsi `Metadata.md` (`housekeeping_log.cleaning_start_time` sebenarnya `time` bukan `timestamp` di M1.2; `employees.hire_date` sebenarnya `text` bukan `date` di M1.2; `staff_shifts.clock_in`/`clock_out` juga `time` bukan `timestamp`, ditemukan di M1.3) relevan sebagai konteks — dokumentasi arsitektur (`Metadata.md`) tidak selalu presisi soal tipe data aktual, worth diverifikasi ulang lewat `information_schema.columns` sebagai bagian baseline Milestone 1.4, bukan diasumsikan dari deskripsi naratif.
- **Untuk Milestone 1.5 (dashboard)**: `monitoring.dq_test_results`, `dirty_proportion_snapshot`, `value_anomaly_snapshot` siap jadi sumber data pilar "kualitas data" dashboard, melengkapi volume/freshness dari Milestone 1.2.
- **Untuk siapa pun yang menjalankan mekanisme ini**: urutan jalan harian (manual, sampai `pg_cron` diputuskan): `build_and_run.py` → `snapshot_dirty_proportion.py` → `snapshot_value_anomaly.py` → `dq_alerts.py`. Perlu ≥3 snapshot historis (hari berbeda) sebelum drift dirty-proportion/value-anomaly keluar dari mode bootstrap ke mode rolling penuh.
- **Peringatan penting**: alert `total_amount_matches_rate_x_nights` yang muncul sekarang adalah temuan nyata (165 baris), bukan false alarm — jangan diabaikan tanpa investigasi lanjut oleh pemilik data production jika ingin data dibersihkan.
