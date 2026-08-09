# Milestone 3.6: Akses BigQuery Langsung via BI Tool — Report

**Status:** Partially Completed — KK2 dan KK3 terpenuhi penuh, KK1 Partially Met (lihat detail di bawah).
**Date completed:** 2026-08-10

## Kriteria Keberhasilan — Hasil

- [~] **KK1 — Tim Data Analyst berhasil menjalankan query eksploratif langsung dari BI tool ke `mart_cleaned`/`mart_aggregated` di BigQuery menggunakan kredensial yang disediakan.** **Partially Met.** Yang terbukti: kredensial `analyst-readonly` bekerja penuh secara terprogram — `scripts/analyst_bi_access/example_query.py` dijalankan sungguhan, berhasil query row-level `mart_cleaned` (`mart_cleaned__properties` 6 baris, `mart_cleaned__bookings` sample) DAN agregat `mart_aggregated` (`fact_revenue_room_type_daily`, 18 baris hasil `GROUP BY`) sekaligus, hanya memakai kredensial ini. Panduan koneksi 2 kelas BI tool (upload-key: Metabase/Redash/DBeaver; OAuth+impersonation: Looker Studio) didokumentasikan teknis benar di `scripts/analyst_bi_access/README.md`. **Yang belum terbukti**: koneksi BI tool GUI sungguhan tidak benar-benar dijalankan — Docker Desktop tidak aktif di lingkungan pengerjaan (dicek langsung sebelum breakdown), dan jalur OAuth (Looker Studio) butuh setup service account impersonation tambahan yang belum dikonfigurasi. Keputusan diambil sadar bersama user sebelum breakdown (`decisions.md` Keputusan #1), bukan terlewat tanpa disadari.
- [x] **KK2 — Kredensial `analyst-readonly` terbukti tidak bisa mengakses `raw_production` atau `ml_output` saat diuji coba.** Terpenuhi. `scripts/bigquery_common/verify_dataset_isolation.py --allow mart_cleaned.mart_cleaned__properties --allow mart_aggregated.dim_property --deny raw_production.properties --deny ml_output.predictions` → 4/4 OK, dijalankan sungguhan terhadap BigQuery `nirwana-database-elt`.
- [x] **KK3 — Kredensial terbukti hanya bisa membaca (tidak bisa menulis/mengubah) data.** Terpenuhi. Percobaan `CREATE TABLE mart_cleaned.__test_write_denied_analyst_readonly` memakai kredensial `analyst-readonly` → `403 Forbidden` (`google.api_core.exceptions.Forbidden`), dijalankan sungguhan (pola sama M2.5).

## Deliverables

- `docs/08-serving-data-analyst/bi-tool-analyst.md` — Output resmi #2 (kebijakan + status jujur KK1).
- `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` — diupdate, 1 baris inventaris baru + bagian "Siapa Boleh Memegang".
- `scripts/analyst_bi_access/{example_query.py,README.md}`.
- `scripts/extract/gcp-analyst-readonly-key.json` (gitignored) — key file service account.
- `.env`/`.env.example` — `ANALYST_READONLY_CREDENTIALS`.
- `milestones/3.6-akses-bigquery-bi-tool/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada deviasi dari keputusan inti. **1 bug operasional signifikan ditemukan dan diperbaiki di luar scope asli** (didokumentasikan eksplisit, bukan disembunyikan): `.env` ternyata sudah rusak sejak Milestone 3.5 Checkpoint 2 — `write_env_var()` menambahkan entri baru ke baris terakhir file yang kebetulan tidak diakhiri newline, membuat 2 variabel (`REVERSE_ETL_MART_AGGREGATED_READER_CREDENTIALS` dan `REVENUE_ANALYST_READER_DB_URL`) tergabung jadi 1 baris korup. Ditemukan saat menambahkan `ANALYST_READONLY_CREDENTIALS`, diperbaiki langsung (baris `.env` dibetulkan + akar masalah di `write_env_var()` diperbaiki supaya tidak terulang untuk kredensial berikutnya). Dikonfirmasi tidak ada baris lain yang kena masalah sama.

## Known Gaps / Follow-ups

- **Koneksi BI tool GUI sungguhan belum dijalankan** (KK1 Partially Met, lihat detail di atas). Follow-up eksplisit: begitu Docker Desktop bisa dinyalakan, jalankan Metabase (`docker run -d -p 3000:3000 metabase/metabase`), hubungkan ke BigQuery pakai `gcp-analyst-readonly-key.json` langsung di UI setup, jalankan 1 query eksploratif nyata — akan menyelesaikan KK1 sepenuhnya tanpa perlu perubahan desain kredensial apa pun (kredensial sudah siap pakai).
- **Service account impersonation untuk jalur OAuth (Looker Studio dkk) belum dikonfigurasi** — kalau tim memang memilih jalur ini, perlu `roles/iam.serviceAccountTokenCreator` diberikan ke akun Google analyst pada `analyst-readonly`, dicatat sebagai langkah IAM tambahan terpisah.
- **Bug `.env` yang diperbaiki** (lihat Deviations) — perlu diperiksa ulang kalau ada milestone lain yang sempat menulis ke `.env` di antara M3.5 dan M3.6 tanpa terdeteksi (dicek: tidak ada, cuma 1 baris kena, sudah dikonfirmasi lewat `_load_env()` parse ulang 25 key benar).

## Handoff Notes

- **Kalau KK1 mau diselesaikan penuh nanti**: tidak perlu ulang dari nol — kredensial, isolasi, dan bukti akses terprogram semuanya sudah siap. Tinggal jalankan Metabase (atau BI tool lain) dan hubungkan pakai `gcp-analyst-readonly-key.json`.
- **Pemilik `mart_cleaned`/`mart_aggregated` berikutnya**: kalau ada dataset BigQuery baru untuk Data Analyst, tambahkan ACL READER ke `analyst-readonly` lewat pola `bq show`/`bq update --source` yang sama (dicatat di `logs.md` Checkpoint 1) — `bq add-iam-policy-binding` level-dataset gagal butuh allowlisting, jangan dicoba lagi.
- **Siapa pun yang menulis ke `.env` via script Python ke depan**: pastikan pola append aman terhadap baris terakhir tanpa newline — `write_env_var()` di `scripts/data_analyst_credentials/connections.py` sudah diperbaiki dan bisa dipakai sebagai referensi kalau ada helper serupa di folder lain.
