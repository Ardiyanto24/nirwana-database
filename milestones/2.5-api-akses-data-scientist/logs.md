# Milestone 2.5 -- Execution Log

## 2026-08-08 (start)
Did: Baca lingkup sumber Milestone 2.5 (`docs/03-implementation-plans/02-serving-data-scientist.md` baris 142-157) dan Bagian 7.4 master architecture doc (Data Scientist tetap di BigQuery). Breakdown via skill `planning-and-task-breakdown` (dalam plan mode), dibantu 1 Explore agent untuk riset precedent (`scripts/reverse_etl/verify_reader_isolation.py` sebagai template isolasi, `docs/02-requirements/rancangan-rbac-ai-chatbot.md` dikonfirmasi tidak relevan -- cuma Lapis 1 chatbot). Ditemukan M2.5 vs M2.6 tumpang tindih di teks sumbernya sendiri (KK M2.5 sudah minta "read-only dan terisolasi", padahal itu scope inti M2.6). Diajukan 2 keputusan ke user via `AskUserQuestion`: (1) bentuk akses -- dipilih BigQuery client langsung + kredensial scoped, TANPA REST API perantara; (2) pembagian M2.5/M2.6 -- dipilih M2.5 bangun kredensial least-privilege yang SUDAH teruji penuh, M2.6 jadi lapis dokumentasi kebijakan/governance.
Result: worked. Plan disetujui user (`ExitPlanMode`). `decisions.md` ditulis lengkap (6 keputusan).

## 2026-08-08 -- Task 1 (Fase 1: service account data-scientist-reader)
Did: `gcloud iam service-accounts create data-scientist-reader`, dataset ACL `mart_cleaned` = READER (`bq update` pola sama M2.1/M2.4), `roles/bigquery.jobUser` project-level, key file (`gcp-data-scientist-reader-key.json`). Ketiganya berhasil dijalankan langsung tanpa diblokir classifier (konsisten pola M2.4, bukan M2.1/M2.2/M2.3 yang selalu perlu user manual).
Result: worked. Key file terverifikasi gitignored (`git check-ignore`). Task 1 selesai.

## 2026-08-08 -- Task 2 (Fase 1: generalisasi verify_reader_isolation.py)
Did: Tulis `scripts/bigquery_common/verify_dataset_isolation.py` -- fungsi generik `verify_isolation(keyfile, project, checks)` + CLI (`--keyfile --project --allow --deny`, bisa banyak kali) supaya kredensial BigQuery scoped berikutnya tidak perlu file `verify_*.py` baru sama sekali. `scripts/reverse_etl/verify_reader_isolation.py` diubah jadi thin wrapper (tetap ada sebagai file, karena `decisions.md`/`report.md` M2.4 merujuk path ini sebagai deliverable) yang delegate ke helper baru.
Result: worked. Re-run `verify_reader_isolation.py` -- 3/3 OK, **tidak ada regresi** dari refactor. Verifikasi `data-scientist-reader` langsung lewat CLI generik (`--allow mart_cleaned.mart_cleaned__properties --deny raw_production.* --deny staging.*`) -- 3/3 OK. Task 2 selesai, 1 helper dipakai 2 service account seperti direncanakan.

## Checkpoint 1 -- selesai
Task 1-2 selesai dan terverifikasi.

## 2026-08-08 -- Task 3 (Fase 2: demo script example_query.py)
Did: Tulis `scripts/data_scientist_access/example_query.py` -- query tunggal (`properties`), sample (`bookings` LIMIT 5), dan agregasi `GROUP BY` (rata-rata `total_amount` per property, butuh scan penuh) pakai HANYA `DATA_SCIENTIST_READER_CREDENTIALS`. Sempat error kolom (`checkin_date` vs nama asli `check_in_date`) -- dicek lewat `bq show --schema`, diperbaiki. Tambahkan `pandas==3.0.2` ke `requirements.txt` (belum pernah dipin sebelumnya).
Result: worked. Ketiga query jalan sukses (`properties` 6 baris, `bookings` sample 5, agregasi 5 property dengan `n_bookings`/`avg_amount` masuk akal). Task 3 selesai, KK#1 sumber terbukti end-to-end.

## 2026-08-08 -- Task 4 (Fase 2: README)
Did: Tulis `scripts/data_scientist_access/README.md` -- autentikasi, contoh query Python, daftar tabel (rujuk `pemetaan-kebutuhan-konsumen-data-mart.md`), catatan kebijakan dirujuk ke M2.6 (bukan didobel di sini).
Result: worked. Task 4 selesai.

## 2026-08-08 -- Task 5 (Fase 2: verifikasi KK + report.md)
Did: Sebelum tulis report.md, tambah 1 verifikasi lagi yang belum eksplisit diuji: percobaan `CREATE TABLE` di `mart_cleaned` pakai kredensial `data-scientist-reader` -- untuk membuktikan "read-only" secara empiris, bukan cuma diasumsikan dari "kita cuma grant READER". Cek 2 KK sumber satu-satu. Tulis `report.md`.
Result: `CREATE TABLE` ditolak (`Forbidden`) -- read-only terbukti. **Kedua KK terpenuhi**. Status: Completed. 1 catatan penting: isolasi dari `mart_aggregated` dibuktikan by-construction (dataset belum ada), bukan uji langsung -- dicatat eksplisit di report.md, bukan diklaim "sudah diuji" secara menyesatkan.

## Checkpoint 2 (final) -- selesai
Milestone 2.5 selesai. Kedua Kriteria Keberhasilan sumber terpenuhi.
