# Milestone 1.1 — Execution Log

## 2026-08-07 (start)
Did: Menyelesaikan breakdown Milestone 1.1 dengan `planning-and-task-breakdown`, mengonfirmasi 4 keputusan teknis bersama user (rubrik prioritas, sumber baseline, cakupan business rule, lokasi deliverable), menulis `decisions.md`.
Result: worked.

## 2026-08-07 — Verifikasi live Supabase (Task 3)
Did: Jalankan script read-only (`psycopg2`, `SUPABASE_DB_URL`) untuk (1) list semua base table di luar schema sistem, (2) row count 23 tabel domain, (3) sampling NULL-rate kolom kritis, (4) distinct value `employees.department`.
Result: worked. Temuan:
- 6 schema Postgres persis sama dengan 6 database logis di `Metadata.md`/`DataSchema.md` (`corporate_master`, `reservation_revenue`, `fnb_operations`, `facility_maintenance`, `spa_event`, `hr_finance`) — tiap tabel didokumentasikan sebagai `schema.table`.
- Total baris live: **2.534.072** di 23 tabel — sangat dekat dengan `DataSchema.md` (~2,53 juta), selisih wajar (data terus bertambah, sesuai catatan dokumen).
- Ada 1 tabel tambahan di luar 23 tabel terdokumentasi: `public._sim_state` (1 baris: `id`, `sim_date`, `last_run_at`) — jelas tabel internal generator simulasi data, **bukan** tabel bisnis. Dikecualikan dari inventaris 23 tabel, dicatat di sini untuk transparansi.
- `guests.email` null/empty 3.97% (24.893 baris), `guests.phone` 3.01% — konsisten dengan dokumentasi (~4%, ~3%).
- `employees.department` masih menunjukkan variasi penulisan (19 nilai untuk 8 departemen sebenarnya) — persis seperti diklaim `Metadata.md`, terverifikasi bukan klaim usang.
- `fnb_transactions.guest_id` null 31.06% (walk-in anonim) — konsisten dokumentasi (~31%).
- `spa_bookings.guest_id` null 21.16% — sedikit di bawah dokumentasi (~21%, cocok).
- `maintenance_tickets.room_id` null 27.54% (fasilitas umum), `parts_replaced` null 52.21% — konsisten dokumentasi (~28% non-Room, ~52% tanpa ganti part).
- `staff_shifts.clock_in` NULL 100% konsisten pada status `absent` & `leave`, terisi penuh pada `present`/`late` — sesuai desain (bukan data hilang, tapi makna status).

## 2026-08-07 — Error/Temuan Penting
Encountered: Tabel RBAC yang didokumentasikan sebagai `role_permissions_chatbot_v2` (77 baris, 10 data_domain, v0.6) **tidak ada di database live** dengan nama tersebut. Nama tabel aktual di Supabase adalah `corporate_master.role_permissions`.
Cause: Bukan masalah data — isinya sudah versi v0.6 yang benar (diverifikasi: 77 baris, 10 nilai `data_domain` granular termasuk `guests_pii`/`guests_profile`/`properties_ref`/`employees_directory`, kolom `permission_type` semua `read`). Hanya **penamaan tabel** yang belum disinkronkan ke skema live — kemungkinan proses rename saat migrasi v0.5→v0.6 tidak diterapkan ke database production, hanya di dokumentasi.
Fix: Deliverable Milestone 1.1 (`docs/04-monitoring/baseline-inventaris-produksi.md`) memakai nama tabel **live** (`corporate_master.role_permissions`) sebagai rujukan utama, dengan catatan eksplisit soal ketidakcocokan nama vs dokumentasi arsitektur. Tidak mengubah nama tabel di Supabase (di luar scope Milestone 1.1 yang murni observasional) — direkomendasikan sebagai temuan untuk ditindaklanjuti pemilik dokumen arsitektur/tim yang berwenang atas skema production.

## 2026-08-07 — Priority scoring & deliverable (Task 4-7)
Did: Terapkan rubrik skor gabungan ke 23 tabel, isi kolom kritis bisnis & kolom kotor/nullable per tabel (gabungan `Metadata.md` + hasil query live), susun katalog kandidat business rule per schema, rakit `docs/04-monitoring/baseline-inventaris-produksi.md`, cek terhadap Kriteria Keberhasilan.
Result: worked. Hasil klasifikasi: 7 tabel Tinggi (`employees`, `guests`, `role_permissions`, `bookings`, `fnb_transactions`, `staff_shifts`, `payroll`), 12 Sedang, 4 Rendah. 4 dari 7 tabel Tinggi punya volume kecil-menengah (`role_permissions` 77 baris, `employees` 755 baris, `payroll` 23.383 baris) — mengonfirmasi keputusan memakai skor gabungan, bukan volume saja.

## 2026-08-07 — Script sementara
Catatan: Script verifikasi (`explore_schema.py`, `row_counts.py`, `dirty_data_check.py`) dijalankan dari scratchpad sesi, bersifat sekali-pakai (read-only, tidak ada mutasi), tidak disimpan ke repository. Jika Milestone 1.2 butuh mekanisme serupa secara terjadwal, itu perlu dibangun ulang sebagai bagian dari scope 1.2 (monitoring volume/freshness), bukan reuse script sekali-pakai ini.
