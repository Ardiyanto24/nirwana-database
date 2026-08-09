# Milestone 5.7: Menindaklanjuti Pengajuan Perubahan Cakupan `dim_employee.property_id` — Report

**Status:** Completed
**Date completed:** 2026-08-09

## Latar Belakang

Menindaklanjuti 1 entri backlog nyata (bukan simulasi) di `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md`, diajukan oleh Data Analyst Serving (Milestone 3.2) lewat mekanisme resmi Milestone 5.6: `mart_aggregated.dim_employee` tidak punya kolom `property_id`, meski data itu sudah tersedia penuh di `mart_cleaned.employees` sejak M2.1-2.3. Milestone ini bukan berasal dari `docs/03-implementation-plans/` — "kontrak"-nya adalah entri backlog itu sendiri, dievaluasi dan ditindaklanjuti sesuai aturan mekanisme M5.6.

## Hasil — Diukur terhadap Apa yang Diminta Pengajuan

- [x] **Temuan pengaju diverifikasi benar sebelum dievaluasi.** Dicek langsung ke kode (bukan diterima begitu saja): `property_id` ada di produksi (`Metadata.md:134`), mengalir utuh ke `mart_cleaned.employees` (test `relationships` lolos), memang hilang di `dim_employee.sql`, dan ketiga fact table yang disebut (`fact_hr_employee_monthly`, `fact_hr_employee_performance_semester`, `fact_hr_watchlist_monthly`) memang cuma join lewat `employee_id` tanpa jalur ke properti. Dikonfirmasi juga ini bukan celah kecil wajar — `milestones/5.2-.../decisions.md` KK#2 eksplisit mewajibkan `property_id` sebagai kolom filter wajib di seluruh skema.
- [x] **`mart_aggregated.dim_employee.property_id` live di BigQuery, terverifikasi langsung.** `dbt run`+`test --select dim_employee` — 7/7 PASS (termasuk test `relationships` baru ke `dim_property`). `promote.py --select dim_employee` — sukses. Query langsung: `mart_aggregated.dim_employee` = 755 baris, 755 non-null `property_id` (100%), cocok persis dengan `mart_cleaned__employees` (755/755). Distribusi per properti: P01=165, P02=270, P03=115, P04=100, P05=85, P06=20 (kantor pusat).
- [x] **Kolom yang sama live di serving PostgreSQL, terverifikasi langsung.** `sync.py --table dim_employee` — sukses, row-count parity BigQuery=Postgres=755. Query langsung ke Postgres mengonfirmasi kolom `property_id` ada dengan distribusi identik ke BigQuery. Tidak ada tabel orphan tersisa di state akhir.
- [x] **Entri backlog ditutup dengan bukti tindak lanjut nyata**, bukan cuma "disetujui lalu didiamkan" — lihat `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md`, status Selesai.

## Deliverables

- `warehouse/models/mart_aggregated/corporate_master/dim_employee.sql` — kolom `property_id` ditambahkan.
- `warehouse/models/mart_aggregated/_mart_aggregated_dimensions_tests.yml` — test `relationships` `dim_employee.property_id` → `dim_property.property_id`.
- `mart_aggregated.dim_employee` (BigQuery) dan tabel serving PostgreSQL — live dengan kolom baru, terverifikasi 755/755 baris kedua sisi.
- `scripts/reverse_etl_mart_aggregated/sync.py` — diperbaiki (lihat Deviations).
- `docs/07-mart-aggregated/DataSchema-mart-aggregated.md`, `Metadata-mart-aggregated.md` — didokumentasikan.
- `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` — entri ditutup.
- Cross-reference Known Gaps di `milestones/5.2-.../report.md` dan `milestones/3.2-.../report.md`.
- `docs/keputusan-tertunda.md` — 1 entri baru (otomasi reapply `analyst_views`).
- `milestones/5.7-perubahan-cakupan-dim-employee-property-id/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada deviasi pada keputusan inti (tambah kolom, scope promote/sync, test relationships). **1 temuan signifikan di luar cakupan minimal, ditemukan lewat verifikasi wajib checkpoint 2, diperbaiki dalam scope karena file yang terdampak (`scripts/reverse_etl_mart_aggregated/sync.py`) memang wilayah pemilik `mart_aggregated`:**

`sync.py --table dim_employee` percobaan pertama **crash** (`DependentObjectsStillExist`) — swap RENAME-based M5.5 ternyata bentrok dengan 5 view `analyst_views` (M3.2, dibangun setelah M5.5, mengasumsikan tabel dasar stabil) karena Postgres view mengikat tabel dasar lewat OID, bukan nama. Diagnosis lengkap + perbaikan (drop tabel lama jadi non-fatal warning, dibuktikan lewat 2 siklus reproduksi nyata) ada di `logs.md` Checkpoint 2. **Tidak mengurangi bukti KK manapun** — data akhir di kedua sisi (BigQuery, Postgres) tetap terverifikasi benar; yang diperbaiki murni supaya proses sync-nya sendiri tidak crash untuk tabel manapun yang punya view di atasnya (relevan untuk hampir semua dari 76 tabel `mart_aggregated` ke depan, bukan cuma `dim_employee`). Otomasi penuh reapply-view sengaja **tidak** diputuskan sepihak di sini — dicatat sebagai keputusan tertunda terpisah di `docs/keputusan-tertunda.md`, karena itu keputusan orkestrasi lintas-milestone (M5.5 + M3.2, beda owner).

## Known Gaps / Follow-ups

- **3 view `analyst_views` (`v_hr_employee_monthly`, `v_hr_employee_performance_semester`, `v_hr_watchlist_monthly`) belum men-SELECT `property_id`** — data-nya kini tersedia di `mart_aggregated.dim_employee`, tapi mengedit `scripts/data_analyst_views/*.sql` di luar kepemilikan M5.7. Follow-up untuk pemilik M3.2/M3.4 (join pattern sudah ada di file yang sama sebagai contoh — `LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id`).
- **Otomasi reapply `analyst_views` setelah reverse-etl-mart-aggregated.yml** — belum ada; tabel `__old` akan menumpuk (orphan, aman tapi makan storage) di setiap run terjadwal berikutnya sampai `apply_views.py --all` dijalankan manual atau diorkestrasi. Dicatat di `docs/keputusan-tertunda.md`, status Open.
- **48 view `analyst_views` lainnya belum diuji ulang** terhadap swap `sync.py --all` penuh setelah fix ini — hanya `dim_employee` yang diverifikasi langsung lewat siklus nyata di M5.7. Kemungkinan besar berperilaku sama (fix-nya generik, bukan spesifik `dim_employee`), tapi belum dibuktikan untuk seluruh 76 tabel sekaligus.

## Handoff Notes

- **Pemilik `mart_aggregated` berikutnya:** pola M5.7 (verifikasi klaim pengaju dari kode dulu → evaluasi 3 kriteria M5.6 → milestone kecil kalau disetujui → implementasi + verifikasi infrastruktur sungguhan → tutup backlog + cross-reference) bisa dipakai lagi persis sama untuk pengajuan berikutnya.
- **Siapa pun yang menjalankan `reverse-etl-mart-aggregated.yml` terjadwal berikutnya:** kemungkinan besar akan melihat banyak WARNING "kept -- analyst_views still depend on it" di log run — ini EXPECTED sekarang (tidak lagi bikin run gagal), bukan regresi. Jalankan `scripts/data_analyst_views/apply_views.py --all` secara berkala untuk membersihkan tabel `__old` yang menumpuk, sampai keputusan tertunda soal otomasi ini diambil.
- **Pemilik M3.2/M3.4 (Data Analyst Serving):** gap `dim_employee.property_id` yang diblokir M3.2 kini sudah dibuka — 3 view HR bisa diupdate kapan pun untuk filter per-properti, tidak perlu menunggu apa pun lagi dari sisi `mart_aggregated`.
