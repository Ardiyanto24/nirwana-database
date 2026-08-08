# Milestone 2.5: API Akses Data Scientist — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Tim Data Scientist berhasil mengambil data dari `mart_cleaned` secara terprogram, tanpa memerlukan akses langsung ke kredensial admin/service account inti.** — Terpenuhi. `scripts/data_scientist_access/example_query.py` menjalankan query nyata (single-table, sample, DAN agregasi `GROUP BY` yang butuh scan penuh — bukan cuma `SELECT *` sederhana) memakai **hanya** kredensial `data-scientist-reader` (`DATA_SCIENTIST_READER_CREDENTIALS`), tidak pernah menyentuh `dbt-transform`/`extract-writer`/kredensial admin/pemilik project.
- [x] **Akses yang diberikan bersifat read-only dan terisolasi dari layer raw maupun `mart_aggregated`.** — Terpenuhi, dua bagian:
  - **Read-only**: dibuktikan empiris — percobaan `CREATE TABLE` di `mart_cleaned` memakai kredensial ini ditolak (`google.api_core.exceptions.Forbidden`), bukan cuma diasumsikan dari "kita cuma grant READER".
  - **Terisolasi dari raw/staging**: dibuktikan lewat `scripts/bigquery_common/verify_dataset_isolation.py --allow mart_cleaned.* --deny raw_production.* --deny staging.*` — 3/3 OK.
  - **Terisolasi dari `mart_aggregated`**: dataset ini **belum ada** di project (scope kerja terpisah, lihat catatan "Tidak termasuk" di `docs/03-implementation-plans/02-serving-data-scientist.md`) — tidak bisa diuji langsung. Dibuktikan **by construction**: model akses BigQuery adalah dataset-scoped ACL whitelist, `data-scientist-reader` cuma pernah di-grant eksplisit ke `mart_cleaned` — begitu `mart_aggregated` dibuat nanti, kredensial ini otomatis tidak punya akses ke situ kecuali digrant eksplisit lagi (yang tidak akan dilakukan tanpa keputusan sadar terpisah). Dicatat eksplisit di sini supaya tidak diklaim "sudah diuji" secara menyesatkan.

## Deliverables

- Service account `data-scientist-reader@nirwana-database-elt.iam.gserviceaccount.com` — dataset ACL READER `mart_cleaned` SAJA + `roles/bigquery.jobUser`.
- `scripts/bigquery_common/verify_dataset_isolation.py` — helper isolasi generik (extracted dari `scripts/reverse_etl/verify_reader_isolation.py`), dipakai untuk 2 service account sekaligus (`reverse-etl-reader` dan `data-scientist-reader`), siap dipakai untuk kredensial BigQuery scoped berikutnya tanpa file baru.
- `scripts/data_scientist_access/example_query.py` — demo end-to-end (query tunggal, sample, agregasi) memakai kredensial `data-scientist-reader` saja.
- `scripts/data_scientist_access/README.md` — dokumentasi cara pakai (autentikasi, contoh query, daftar tabel, batas kebijakan yang dirujuk ke M2.6).
- `milestones/2.5-api-akses-data-scientist/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada. Seluruh keputusan di `decisions.md` (bentuk akses BigQuery langsung, pembagian M2.5/M2.6, nama service account, argumen isolasi `mart_aggregated` by-construction, refactor helper isolasi, README co-located) diimplementasikan persis seperti direncanakan.

## Known Gaps / Follow-ups

- **Kebijakan akses (siapa boleh pakai kredensial ini, batasannya) belum didokumentasikan formal** — sesuai pembagian kerja M2.5/M2.6 yang dikunci di `decisions.md`, ini scope M2.6, bukan gap M2.5. `scripts/data_scientist_access/README.md` sudah merujuk ke M2.6 untuk ini secara eksplisit.
- **Isolasi dari `mart_aggregated` belum diuji langsung** (dataset belum ada) — argumen by-construction di atas cukup kuat untuk sekarang, tapi begitu `mart_aggregated` benar-benar dibuat (pekerjaan pemilik `03-mart-aggregated-owner.md`), sebaiknya isolasi diuji ulang secara langsung (tambahkan 1 `--deny mart_aggregated.*` ke `verify_dataset_isolation.py` saat itu) untuk verifikasi eksplisit, bukan cuma andalkan argumen struktural.
- **Belum ada rotasi/expiry policy untuk key file** `data-scientist-reader` — sama seperti seluruh service account lain di project ini (`extract-writer`, `dbt-transform`, `reverse-etl-reader`), key file statis tanpa rotasi terjadwal. Bukan gap baru khusus M2.5, konsisten dengan pola project secara keseluruhan.

## Handoff Notes

- **Untuk Milestone 2.6 (Isolasi Akses dan Kredensial Read-Only)**: kredensial `data-scientist-reader` sudah dibangun dan teruji penuh (read-only + isolasi raw/staging + argumen isolasi mart_aggregated) di sini — M2.6 tidak perlu membangun ulang service account atau uji teknis dari nol, fokus ke dokumentasi kebijakan (siapa berwenang pakai, proses permintaan/pencabutan akses) yang MERUJUK bukti di milestone ini.
- **`scripts/bigquery_common/verify_dataset_isolation.py`** sekarang jadi helper standar project ini untuk verifikasi kredensial BigQuery scoped baru — pakai ini dulu sebelum menulis script `verify_*.py` baru di milestone mendatang.
