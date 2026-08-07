# Milestone 1.4 — Execution Log

## 2026-08-07 (start)
Did: Breakdown Milestone 1.4 dengan `planning-and-task-breakdown`, cek privilege koneksi (read-only: `rolsuper=False` untuk role `postgres`, relevan untuk keputusan metode deteksi). Konfirmasi 4 keputusan teknis bersama user (metode deteksi + waktu pemicu, cakupan, model baseline, heuristik sensitif). Tulis `decisions.md`.
Result: worked.

## 2026-08-07 — Schema, baseline, keyword classifier (Task 1-3)
Did: Terapkan `scripts/schema_drift/schema.sql` (`monitoring.schema_column_baseline`, `monitoring.schema_drift_events`, additive). `baseline_columns.py` mengambil baseline awal dari `information_schema.columns` untuk 23 tabel (reuse daftar tabel dari `scripts/monitoring/tables_config.py` lewat `tables_list.py` supaya tidak ada 3 sumber kebenaran berbeda). `sensitive_keywords.py` — keyword list + `classify_severity()`.
Result: worked. Baseline: 23/23 tabel, 165 kolom, terverifikasi via `COUNT(DISTINCT (schema_name, table_name))`. Manual test classifier: `password_hash`→high, `guest_email`→high, `salary_bonus`→high, `nik_number`→high, `total_amount`/`notes`/`room_type`→normal — sesuai ekspektasi.

## 2026-08-07 — Diff engine terhadap 23 tabel production nyata (Task 4)
Did: Jalankan `snapshot_and_diff.py` terhadap 23 tabel production sesaat setelah baseline diambil.
Result: "Tidak ada drift baru terdeteksi" — sesuai ekspektasi (baseline baru saja diambil dari kondisi yang sama).

## 2026-08-07 — Alur acknowledgment (Task 5)
Did: Tulis `acknowledge.py` — generic per drift_type (column_added → insert ke baseline, column_removed → delete dari baseline, type_changed → update data_type di baseline), lalu tandai event `acknowledged`.
Result: worked, diverifikasi lewat uji coba terkontrol (lihat entri berikutnya) bukan diuji terpisah.

## 2026-08-07 — Uji coba terkontrol (Task 6)
Did: `simulate_test.py` — buat `_simulation.staging_table` (bukan salah satu dari 23 tabel production), jalankan 4 `ALTER TABLE` beneran (ADD kolom biasa, ADD kolom bernama `password_hash`, DROP kolom, ALTER TYPE), lalu diff 3x dengan 1 acknowledge di tengah.
Result: **5/5 skenario PASS**:
1. Run diff #1: 4 drift terdeteksi dengan severity benar (`password_hash` → high, 3 lainnya → normal).
2. Run diff #2 (tanpa acknowledge): tetap 4 event pending yang sama persis — bukan 8 (tidak duplikat) dan bukan 0 (tidak "lupa" seperti day-over-day akan terjadi). Ini pembuktian langsung Kriteria Keberhasilan #2 dan keputusan model baseline tetap.
3. Acknowledge event `notes` (column_added): baseline ter-update, event itu hilang dari daftar pending, 3 lainnya tetap ada.
4. Run diff #3 (setelah acknowledge): `notes` permanen tidak muncul lagi sebagai drift baru (karena sudah masuk baseline), 3 event lain tetap pending.

Tidak ada bug ditemukan di run ini — kemungkinan karena desain schema (baseline terpisah dari snapshot, idempotency check via `_has_pending_event`) sudah mengantisipasi masalah yang biasanya baru ketahuan saat implementasi (beda dari M1.2/M1.3 yang menemukan beberapa bug saat dijalankan pertama kali).
