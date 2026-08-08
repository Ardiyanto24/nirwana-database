# Milestone 2.6 -- Execution Log

## 2026-08-08 (start)
Did: Baca lingkup sumber Milestone 2.6 (`docs/03-implementation-plans/02-serving-data-scientist.md` baris 160-176). Breakdown via skill `planning-and-task-breakdown`. Ditemukan sebagian besar scope M2.6 (service account read-only + uji isolasi) sudah selesai di M2.5 (sesuai pembagian kerja yang dikunci di `milestones/2.5.../decisions.md` Decision 2) -- satu-satunya item Output yang benar-benar baru adalah dokumentasi kebijakan akses. Diajukan 2 keputusan ke user via `AskUserQuestion`: (1) cakupan kebijakan -- dipilih project-wide (6 kredensial scoped, bukan cuma data-scientist-reader), sesuai frasa sumber "seluruh sistem ini"; (2) lokasi dokumen -- dipilih folder baru `docs/06-akses-kredensial/`, pola sama `docs/05-orchestrator/`.
Result: worked. `decisions.md` ditulis lengkap (2 keputusan via AskUserQuestion + 1 keputusan teknis soal re-verifikasi non-destruktif tanpa rotasi password).

## 2026-08-08 -- Task 1-2 (Fase 1: audit + re-verifikasi 6 kredensial)
Did: Audit 6 kredensial scoped lewat cross-check `decisions.md` tiap milestone asal (bukan dari ingatan): `extract_reader` (M2.1, Postgres, SELECT-only whitelist 23 tabel), `extract-writer` (M2.1, BigQuery, dataset ACL WRITER `raw_production` saja), `dbt-transform` (M2.2/2.3, BigQuery, **project-level** `dataEditor` -- sengaja lebih luas, bukan dataset-scoped sempit, karena dbt kelola banyak dataset dari waktu ke waktu), `reverse_etl_writer` (M2.4, Postgres, schema-scoped `mart_cleaned` saja), `reverse-etl-reader` (M2.4, BigQuery, dataset ACL READER `mart_cleaned` saja), `data-scientist-reader` (M2.5, BigQuery, dataset ACL READER `mart_cleaned` saja). Re-verifikasi non-destruktif: `verify_dataset_isolation.py` untuk 2 kredensial BigQuery reader (re-run langsung, murni SELECT); untuk 2 role Postgres (`extract_reader`, `reverse_etl_writer`), tulis query ad-hoc read-only pakai connection string YANG SUDAH ADA di `.env` (`EXTRACT_DB_URL`, `REVERSE_ETL_WRITER_DB_URL`) -- sengaja TIDAK menjalankan ulang `setup_extract_role.py`/`setup_writer_role.py` karena itu akan rotasi password dan mematahkan GitHub Secret yang dipakai workflow terjadwal. `extract-writer`/`dbt-transform` tidak diuji ulang otomatis (tidak ada script reusable, scope project-level bukan dataset-scoped sempit) -- dikutip dari bukti manual milestone asal apa adanya.
Result: worked. Seluruh 4 kredensial yang punya mekanisme non-destruktif terverifikasi ulang, **tidak ada drift** dari perilaku yang didokumentasikan di milestone asalnya (`reverse-etl-reader`/`data-scientist-reader`: isolasi BigQuery OK; `extract_reader`: SELECT whitelisted OK, SELECT `monitoring.alerts` ditolak, INSERT ditolak; `reverse_etl_writer`: CREATE TABLE `mart_cleaned.*` OK, CREATE TABLE `public.*` ditolak). Task 1-2 selesai.

## Checkpoint 1 -- selesai
Audit + re-verifikasi 6 kredensial selesai, tidak ada drift ditemukan.

## 2026-08-08 -- Task 3 (Fase 2: dokumen kebijakan)
Did: Tulis `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` -- prinsip least-privilege wajib untuk kredensial baru, inventaris 6 kredensial (tabel lengkap dengan bukti isolasi per baris), pengecualian `dbt-transform` didokumentasikan eksplisit (bukan disembunyikan sebagai "sudah least-privilege" padahal tidak), siapa boleh pegang tiap kredensial, proses minta kredensial baru (5 langkah, merujuk pola existing), proses rotasi/pencabutan.
Result: worked. Task 3 selesai.

## 2026-08-08 -- Task 4 (Fase 2: verifikasi KK + report.md)
Did: Cek 2 KK sumber -- keduanya sudah dibuktikan di M2.5, ditegaskan lagi lewat re-verifikasi non-destruktif M2.6 tanpa drift. Tulis `report.md`.
Result: **Kedua KK terpenuhi**. Status: Completed. 2 Known Gap dicatat (rotasi otomatis belum ada -- diwariskan bukan baru; `extract-writer` belum punya script verifikasi re-runnable -- gap kecil, di luar scope M2.6).

## Checkpoint 2 (final) -- selesai
Milestone 2.6 selesai. Kedua Kriteria Keberhasilan sumber terpenuhi.
