# Milestone 3.6: Akses BigQuery Langsung via BI Tool — Logs

## 2026-08-10 — Mulai kerja

- Plan disetujui via Plan Mode. `decisions.md` ditulis, mengunci 1 keputusan via AskUserQuestion (verifikasi KK1 lewat dokumentasi+script, bukan koneksi BI tool sungguhan — Docker Desktop tidak berjalan di environment ini) + 5 keputusan teknis.
- Folder dibuat: `milestones/3.6-akses-bigquery-bi-tool/`, `scripts/analyst_bi_access/`.
- Mulai Task 1 (Fase 0 — kredensial + isolasi).

## 2026-08-10 — Checkpoint 1: kredensial + isolasi

- `gcloud iam service-accounts create analyst-readonly` sukses. Dataset ACL READER ditambahkan ke `mart_cleaned` dan `mart_aggregated` lewat `bq show`/`bq update --source` (pola `bq add-iam-policy-binding` level-dataset gagal "requires allowlisting", sama temuan M2.1). `roles/bigquery.jobUser` ditambahkan project-level. Key file `scripts/extract/gcp-analyst-readonly-key.json` dibuat sukses (tidak diblokir classifier sesi ini) — dikonfirmasi gitignored (`git check-ignore`).
- **Bug nyata ditemukan dan diperbaiki**: `.env` punya 1 baris tercampur tanpa newline (`REVERSE_ETL_MART_AGGREGATED_READER_CREDENTIALS=...jsonREVENUE_ANALYST_READER_DB_URL=...`) — akibat `write_env_var()` (M3.5, `scripts/data_analyst_credentials/connections.py`) menambahkan entri baru ke baris terakhir file yang kebetulan tidak diakhiri newline, alih-alih memulai baris baru. Diperbaiki: (a) `.env` yang sudah rusak dibetulkan langsung (sisip newline yang hilang), dikonfirmasi ulang lewat `_load_env()` — 25 key terparse benar; (b) akar masalah di `write_env_var()` diperbaiki (pastikan baris terakhir diakhiri `\n` sebelum append) supaya tidak terulang untuk kredensial berikutnya.
- `ANALYST_READONLY_CREDENTIALS` ditambahkan ke `.env` dan `.env.example`.
- **Verifikasi KK2**: `verify_dataset_isolation.py --allow mart_cleaned.mart_cleaned__properties --allow mart_aggregated.dim_property --deny raw_production.properties --deny ml_output.predictions` → 4/4 OK.
- **Verifikasi KK3**: percobaan `CREATE TABLE mart_cleaned.__test_write_denied_analyst_readonly` memakai kredensial `analyst-readonly` → `403 Forbidden` (pola sama M2.5, uji terpisah dari CLI karena `verify_dataset_isolation.py` tidak punya flag write-check bawaan).

## 2026-08-10 — Checkpoint 2: bukti akses terprogram + dokumentasi BI tool

- `scripts/analyst_bi_access/example_query.py` ditulis (pola `example_query.py` M2.5) — beda dari M2.5, di sini query mencakup **kedua** dataset (`mart_cleaned.mart_cleaned__properties`/`mart_cleaned__bookings` row-level + `mart_aggregated.fact_revenue_room_type_daily` agregat), bukan cuma 1.
- **Dijalankan sungguhan**: seluruh 3 query sukses — `properties` (6 baris), `bookings` sample 5 baris, agregasi `mart_aggregated` per property/room_type (18 baris) — memakai HANYA `ANALYST_READONLY_CREDENTIALS`, tidak pernah menyentuh kredensial lain.
- `README.md` ditulis — dokumentasi koneksi BI tool generik (2 pola: upload key langsung untuk tool seperti Metabase/Redash/DBeaver; OAuth+service account impersonation untuk tool seperti Looker Studio), dengan **catatan status jujur di paling atas** bahwa koneksi BI tool sungguhan belum dijalankan (Docker Desktop tidak aktif).

## 2026-08-10 — Checkpoint 3 (final) — Tutup milestone

- `docs/08-serving-data-analyst/bi-tool-analyst.md` ditulis — Output resmi M3.6, termasuk tabel status KK1/KK2/KK3 dan bagian "Status Jujur" untuk KK1.
- `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` diupdate — 1 baris inventaris `analyst-readonly`, bagian "Siapa Boleh Memegang" ditambah entri (dibedakan eksplisit dari 7 kredensial `*_analyst_reader` M3.5: `analyst-readonly` dipakai bersama seluruh tim, bukan per-peran).
- **KK2 dan KK3 diverifikasi ulang** — tetap konsisten hasil Checkpoint 1.
- `report.md` ditulis dengan **status milestone "Partially Completed"** (bukan "Completed") — KK1 ditandai Partially Met secara eksplisit dengan alasan dan rencana lanjutan, konsisten pola kejujuran M1.5.
- Milestone ditutup. Fase Serving Data Analyst (M3.1-3.6) selesai — 5 dari 6 milestone Completed penuh, 1 (M3.6) Partially Completed dengan gap yang jelas dan mudah diselesaikan kapan saja Docker tersedia.
