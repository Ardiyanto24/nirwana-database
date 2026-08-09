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
