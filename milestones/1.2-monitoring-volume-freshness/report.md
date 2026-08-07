# Milestone 1.2: Monitoring Volume dan Freshness Data Masuk — Report

**Status:** Completed
**Date completed:** 2026-08-07

## Kriteria Keberhasilan — Hasil

- [x] **Untuk setiap tabel prioritas tinggi, tim bisa menjawab "berapa baris masuk hari ini dibanding biasanya" dan "kapan data terakhir update" tanpa query manual.** — Evidence: `scripts/monitoring/views.sql` (`monitoring.current_status`) — satu view SQL, satu query, menjawab keduanya sekaligus untuk 7 tabel prioritas Tinggi (`employees`, `guests`, `role_permissions`, `bookings`, `fnb_transactions`, `staff_shifts`, `payroll`). Lihat hasil di `logs.md` entri "Verifikasi Kriteria Keberhasilan #1".
- [x] **Simulasi penurunan/lonjakan volume buatan (uji coba terkontrol) berhasil memicu alert sesuai ekspektasi.** — Evidence: `scripts/monitoring/simulate_test.py`, 5/5 skenario sesuai ekspektasi (2 normal → tidak alert, 3 anomali/delay → alert critical). Lihat `logs.md` entri "Uji coba terkontrol".

## Deliverables

- `scripts/monitoring/schema.sql` + `apply_schema.py` — schema `monitoring` (3 tabel: `volume_daily_snapshot`, `freshness_snapshot`, `alerts`), diterapkan ke Supabase.
- `scripts/monitoring/tables_config.py` — konfigurasi 23 tabel: prioritas (dari Milestone 1.1), kolom freshness, tipe kolom, kelas kadensi.
- `scripts/monitoring/snapshot_volume.py` — snapshot row count harian per tabel (upsert per hari).
- `scripts/monitoring/snapshot_freshness.py` — snapshot `MAX(kolom sinyal)` & lag per tabel, termasuk parsing kolom text kotor (`hire_date` mixed-format) dan kolom period (`YYYY-MM`/`YYYY-SN`).
- `scripts/monitoring/detect_alerts.py` — logic alert: volume (rolling per-hari-dalam-minggu, mean ± sigma) & freshness (threshold per kelas kadensi).
- `scripts/monitoring/simulate_test.py` — uji coba terkontrol, 5 skenario, terisolasi di `schema_name='_simulation'`.
- `scripts/monitoring/views.sql` — `monitoring.current_status`, satu view untuk menjawab Kriteria Keberhasilan #1.
- `milestones/1.2-monitoring-volume-freshness/decisions.md` — 4 keputusan teknis + pemetaan freshness 23 tabel + koreksi selama implementasi.
- `milestones/1.2-monitoring-volume-freshness/logs.md` — jurnal kerja lengkap.
- `docs/keputusan-tertunda.md` — entri baru: aktivasi `pg_cron` untuk penjadwalan otomatis (ditunda).

## Deviations from decisions.md

- **Koreksi kolom freshness `housekeeping_log`**: `decisions.md` awalnya menyebut `cleaning_start_time`, dikoreksi ke `date` setelah verifikasi tipe kolom menunjukkan `cleaning_start_time` bertipe `time without time zone` (tanpa komponen tanggal) — bukan `timestamp` seperti tersirat di `Metadata.md`. Dicatat & dikoreksi langsung di `decisions.md` (bukan disembunyikan), lihat `logs.md` Task 2.
- Tidak ada deviasi lain dari `decisions.md`.

## Known Gaps / Follow-ups

- **`event_bookings` tidak punya sinyal freshness yang valid** — hanya ada `event_date` (tanggal acara, bisa jauh di masa depan karena event MICE lazim dibooking berbulan-bulan sebelumnya), bukan tanggal booking dibuat. Dipantau volume-only. Kalau di masa depan `event_bookings` mendapat kolom `created_at`/`booking_created_date`, freshness bisa ditambahkan.
- **`employees.hire_date` sebagai proxy freshness kurang tepat** — kolom ini mencatat kapan karyawan itu direkrut, bukan kapan baris terakhir di-update (mis. perubahan `status`/`access_level` karyawan lama tidak mengubah `hire_date`). Ini keterbatasan yang melekat pada tidak adanya kolom audit di production (lihat `decisions.md`), bukan bug implementasi.
- **Data production adalah snapshot sintetis statis (berhenti 2026-07-01), bukan aliran live** — akibatnya, freshness check *saat ini* melaporkan status **CRITICAL** untuk 12 dari 15 tabel berkelas kadensi "daily" (lag 866-1706 jam). **Ini bukan bug** — mekanisme bekerja benar dan jujur melaporkan kondisi data yang sesungguhnya stale relatif terhadap `now()` wall-clock. Kalau/ketika data production menjadi aliran live sungguhan, angka ini akan otomatis turun ke rentang wajar tanpa perubahan kode apa pun.
- **Baseline volume rolling belum punya histori** — baru 1 titik snapshot (hari ini). `pct_diff_from_baseline` di `monitoring.current_status` akan tetap `NULL`/`histori belum cukup` sampai `snapshot_volume.py` dijalankan minimal 3x di hari-yang-sama-dalam-minggu. Ini konsekuensi wajar dari mekanisme baru dibangun hari ini, bukan cacat desain.
- **Penjadwalan otomatis harian (`pg_cron` atau alternatif lain) ditunda** — lihat `docs/keputusan-tertunda.md`. Saat ini `snapshot_volume.py`/`snapshot_freshness.py`/`detect_alerts.py` perlu dijalankan manual/on-demand.

## Handoff Notes

- **Untuk Milestone 1.3 (kualitas data/anomali)**: `monitoring` schema & pola snapshot-harian yang dibangun di sini bisa dipakai sebagai referensi pola (append-only snapshot + alert table), tapi Milestone 1.3 kemungkinan butuh tabel/skema terpisah untuk hasil pengujian kualitas data (beda bentuk data dari volume/freshness).
- **Untuk Milestone 1.4 (schema drift)**: sebaiknya independen dari `monitoring` schema di sini (murni soal struktur tabel, bukan snapshot metrik).
- **Untuk Milestone 1.5 (dashboard)**: `monitoring.current_status` sudah bisa langsung jadi sumber data dashboard untuk 3 dari 4 pilar (volume, freshness dari sini; kualitas data & schema drift menyusul dari 1.3/1.4).
- **Untuk siapa pun yang menjalankan mekanisme ini mulai sekarang**: jalankan `snapshot_volume.py` lalu `snapshot_freshness.py` lalu `detect_alerts.py` setiap hari (manual, sampai `docs/keputusan-tertunda.md` soal `pg_cron` diputuskan) supaya histori baseline terbentuk dan alert volume mulai bisa dievaluasi (butuh minimal 3 titik histori per hari-dalam-minggu).
- **Peringatan penting**: freshness CRITICAL yang muncul sekarang untuk 12 tabel adalah **temuan nyata tentang kondisi dataset** (berhenti 2026-07-01), bukan false alarm — jangan diabaikan sebagai "known issue" tanpa konteks ini saat melapor ke pihak lain.
