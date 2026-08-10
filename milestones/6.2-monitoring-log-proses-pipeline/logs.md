# Milestone 6.2 — Execution Log

## 2026-08-10 — Plan mode: breakdown awal ditolak, diskusi mendalam
Did: `/planning-and-task-breakdown` dipanggil, breakdown pertama dikunci sepihak tanpa `AskUserQuestion` sama sekali. User bertanya "apakah tidak ada bagian yang perlu didiskusikan?" — 3 fork arsitektur material (sumber data observasi vs instrumentasi, cakupan titik 3/7, struktur workflow) diajukan ulang via `AskUserQuestion`. User minta dijelaskan lebih detail dulu (2 putaran), lalu ditanya "mana yang paling dekat standar industri?" — dijawab dengan analisis konkret (observasi API = padanan Airflow/Dagster metadata DB; coarse+granularity flag = pola dbt artifacts/Great Expectations; 1 workflow gabungan = idiom asli `workflow_run.workflows` array GitHub). User setuju kunci ketiganya.
Result: worked. Plan final ditulis dengan section "Keputusan (dari diskusi sesi ini)" terpisah dari "Keputusan Teknis Lain".

## 2026-08-10 — Checkpoint 1: decisions.md + schema
Did: Tulis `decisions.md` (kontrak, temuan riset 6 workflow nyata, 12 keputusan). Tulis `scripts/monitoring_warehouse/{schema.sql,apply_schema.py,db.py}` — tabel `monitoring.pipeline_run_log` + view `pipeline_run_status`. Jalankan `apply_schema.py` terhadap Supabase sungguhan.
Result: worked. Ditemukan saat menulis DDL (tidak direncanakan eksplisit di plan): `UNIQUE (titik_id, run_id, step_name)` biasa tidak cukup untuk idempotency karena Postgres menganggap tiap NULL berbeda — diperbaiki pakai `CREATE UNIQUE INDEX ... COALESCE(step_name, '')`. Diverifikasi lewat query `information_schema` — tabel + view + 13 kolom benar. Commit `2b718aa`.

## 2026-08-10 — Checkpoint 2: titik_config.py
Did: Tulis 9 baris konfigurasi (titik 1-9, titik 10 dikecualikan — sinyalnya `reverse_etl_sync_log`). Verifikasi terprogram: script Python membaca isi `.github/workflows/*.yml` langsung dan mencocokkan `workflow_name`/`step_name_substring` di config terhadap isi file asli.
Result: worked. 9/9 titik cocok persis (0 typo). Commit `bab4e61`.

## 2026-08-10 — Checkpoint 3: snapshot_pipeline_run.py, diuji terhadap run nyata
Did: Tulis script, uji manual terhadap `run_id` GitHub Actions yang sudah ada sebelum workflow baru dibuat (31356508495 extract, 31361224267 transform-mart-cleaned, 31361454474/475 transform-mart-aggregated+scoring, 31361866737 reverse-etl-mart-aggregated, 31361454443 reverse-etl-mart-cleaned). Cocokkan hasil `SELECT` terhadap `gh run view`/`gh api` sebagai ground truth.
Result: worked. Seluruh 9 titik cocok persis (status, started_at, completed_at, duration_seconds). Titik 9 kebetulan dapat 1 run gagal nyata (`status='failure'`) — bukti awal mekanisme menangkap kegagalan, bukan cuma sukses. Idempotency diuji: re-run `run_id` sama menghasilkan `COUNT(*)=1` (tidak duplikat). Commit `60922d9`.

## 2026-08-10 — Checkpoint 4: workflow listener + push + verifikasi KK1
Did: Tulis `.github/workflows/monitoring-warehouse-pipeline-log.yml` (1 file gabungan, `workflow_run.workflows` array 6 workflow). **Blocker teridentifikasi**: `workflow_run` cuma dievaluasi GitHub terhadap versi file di default branch — perlu push. Ditanyakan eksplisit ke user (`AskUserQuestion`) karena user sebelumnya minta tahan push; user setuju push sekarang. Push `git push origin main` (40 commit, termasuk seluruh M6.1 + M6.2 checkpoint 1-4).
Trigger manual `extract-production.yml` (run 31387711191) via `gh workflow run`, tunggu selesai (`gh run watch`), konfirmasi `monitoring-warehouse-pipeline-log.yml` otomatis terpicu (run 31387872288) via `workflow_run` — TANPA intervensi manual apa pun setelah trigger awal.
Result: worked. Query `pipeline_run_status WHERE titik_id=1` menunjukkan run baru, `ran_today=true`, `duration_seconds=121` — KK1 M6.2 terpenuhi dengan bukti langsung. Commit `2159dc8` (workflow file, sebelum push).

## 2026-08-10 — Checkpoint 5: verifikasi KK2 + cakupan titik 2/3 & 6/7 lewat cascade nyata
Did: Trigger `transform-mart-cleaned.yml` manual (run 31388022750) — memicu fan-out otomatis nyata ke 3 workflow paralel (`reverse-etl-mart-cleaned.yml`, `scoring-occupancy-forecast.yml`, `transform-mart-aggregated.yml`) + listener M6.2 sendiri, persis pola dependency yang dipetakan M6.1. `transform-mart-aggregated.yml` sukses lalu mencascade lagi ke `reverse-etl-mart-aggregated.yml` — total 4 tahap cascade tervalidasi dalam 1 rangkaian trigger.
**Temuan operasional nyata (bukan simulasi)**: `reverse-etl-mart-cleaned.yml` gagal `psycopg2.errors.DuplicateTable: relation "employees__old" already exists` (pre-existing dari sebelum sesi ini, dikonfirmasi dari `gh run list` — bukan disebabkan perubahan M6.2). `reverse-etl-mart-aggregated.yml` juga gagal `relation "dim_property__old" already exists` — persis pola M5.7 (`docs/keputusan-tertunda.md` "Otomasi reapply analyst_views"), sekarang terjadi juga di `mart_cleaned` (sebelumnya cuma didokumentasikan untuk `mart_aggregated`). Kedua kegagalan tertangkap otomatis oleh `pipeline_run_log` (titik 8 & 9, `status='failure'`).
Result: worked, lebih lengkap dari target minimal plan. `COUNT(*) GROUP BY titik_id` menunjukkan **seluruh 9 titik punya tepat 2 baris** (bukan cuma ≥1 titik seperti target minimal Task 7). Titik 2&3 dan titik 6&7 dikonfirmasi ulang dari run OTOMATIS (bukan manual test Checkpoint 3): `step_name`/`status`/timing identik, `granularity` beda (`detailed` vs `coarse`) — Keputusan #2/#7 terbukti benar di jalur produksi sungguhan.
Tidak ada commit baru (murni verifikasi, tidak ada file berubah).

## 2026-08-10 — Checkpoint 6: update peta M6.1 + logs.md + report.md
Did: Update `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` — titik 1-9 dapat catatan sinyal `pipeline_run_log`/`pipeline_run_status` baru, titik 3/7 eksplisit ditegaskan gap detail TETAP terbuka (prasyarat M6.3 tidak berubah), titik 8/9 dapat konfirmasi nyata insiden orphan table. Commit `759c805`.
Result: worked. Milestone ditutup — lihat `report.md`.
