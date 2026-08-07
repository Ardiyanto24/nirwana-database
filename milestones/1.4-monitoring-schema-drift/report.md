# Milestone 1.4: Monitoring Perubahan Struktur (Schema Drift) — Report

**Status:** Completed
**Date completed:** 2026-08-07

## Kriteria Keberhasilan — Hasil

- [x] **Perubahan skema buatan (uji coba terkontrol: tambah kolom baru pada tabel non-produktif atau environment staging) berhasil terdeteksi dan memicu notifikasi.** — Evidence: `scripts/schema_drift/simulate_test.py`, 4 `ALTER TABLE` beneran (ADD kolom biasa, ADD kolom `password_hash`, DROP kolom, ALTER TYPE) di `_simulation.staging_table` — keempatnya terdeteksi dengan `drift_type` & `severity` benar (`password_hash` → `high`, 3 lainnya → `normal`). "Notifikasi" di sini berbentuk baris `pending` di `monitoring.schema_drift_events` yang bisa di-query sebagai antrian review (lihat query di `logs.md`) — bukan push notification (di luar scope repo ini, lihat `decisions.md` M1.2 soal precedent).
- [x] **Tidak ada perubahan skema yang otomatis diteruskan tanpa jejak/notifikasi.** — Evidence: run diff kedua (tanpa acknowledge apa pun) menghasilkan 4 event pending yang **identik** dengan run pertama — bukan 8 (tidak duplikat) dan bukan 0 (tidak "lupa" seperti risiko day-over-day yang dihindari lewat keputusan model baseline tetap). Drift tetap `pending` sampai eksplisit di-`acknowledge`.

## Deliverables

- `scripts/schema_drift/schema.sql` — `monitoring.schema_column_baseline` (baseline tetap/approved), `monitoring.schema_drift_events` (antrian drift, status pending/acknowledged).
- `scripts/schema_drift/tables_list.py` — reuse daftar 23 tabel dari `scripts/monitoring/tables_config.py`.
- `scripts/schema_drift/baseline_columns.py` — ambil baseline awal (dijalankan sekali).
- `scripts/schema_drift/sensitive_keywords.py` — heuristik keyword untuk severity kolom baru.
- `scripts/schema_drift/snapshot_and_diff.py` — engine deteksi (idempotent, tidak menduplikasi event pending).
- `scripts/schema_drift/acknowledge.py` — satu-satunya jalur baseline diperbarui.
- `scripts/schema_drift/simulate_test.py` — uji coba terkontrol, 5/5 skenario PASS.
- `milestones/1.4-monitoring-schema-drift/{decisions,logs}.md`.
- `docs/keputusan-tertunda.md` — entri `pg_cron` diperbarui lagi, cakupan bertambah ke Milestone 1.4.

## Deviations from decisions.md

Tidak ada. Semua 8 task berjalan sesuai rencana di `decisions.md` tanpa perlu koreksi arah di tengah jalan — berbeda dari Milestone 1.2/1.3 yang masing-masing menemukan bug/koreksi signifikan saat implementasi (lihat `logs.md` untuk catatan soal ini).

## Known Gaps / Follow-ups

- **Penjadwalan otomatis masih tertunda** (lihat `docs/keputusan-tertunda.md`) — `snapshot_and_diff.py` perlu dijalankan manual/on-demand sampai `pg_cron` diaktifkan.
- **Metode deteksi seketika (event trigger) tidak dieksplorasi lebih lanjut** — sudah diverifikasi read-only bahwa role koneksi bukan superuser, jadi kemungkinan besar tidak feasible; tidak ada percobaan aktif `CREATE EVENT TRIGGER` yang dilakukan (di luar scope plan mode saat itu, dan snapshot-diff sudah dipilih sebagai keputusan final, bukan sekadar fallback sementara).
- **Cakupan hanya kolom di 23 tabel yang sudah dikenal** — tabel baru/hilang di 6 schema production tidak dipantau (keputusan eksplisit, lihat `decisions.md`). Kalau suatu saat tabel baru muncul di schema production tanpa masuk `tables_list.py`, itu tidak akan terdeteksi oleh mekanisme ini.
- **Data simulasi (`_simulation.staging_table`) sengaja dibiarkan ada** di database (bukan tabel production, tidak mengganggu) sebagai bukti kerja uji coba terkontrol — bisa dibersihkan kapan saja tanpa dampak ke tabel manapun yang dipantau.

## Handoff Notes

- **Untuk Milestone 1.5 (dashboard)**: `monitoring.schema_drift_events` (filter `status='pending'`, urutkan `severity DESC`) langsung jadi sumber data pilar "schema drift" dashboard — pola query sudah didemonstrasikan di `logs.md`.
- **Untuk siapa pun yang menjalankan mekanisme ini**: urutan kerja — `snapshot_and_diff.py` (jalankan kapan saja, aman diulang) → review `SELECT * FROM monitoring.schema_drift_events WHERE status='pending'` → `acknowledge.py <event_id> --note "..."` untuk tiap drift yang sudah direview (baik disetujui maupun ditolak — catat di `--note` kenapa).
- **Peringatan penting**: `acknowledge.py` akan memperbarui baseline `approved` begitu dijalankan — pastikan review sudah benar-benar dilakukan (terutama untuk severity `high`) sebelum acknowledge, karena setelah itu drift yang sama tidak akan terdeteksi lagi sebagai "baru".
