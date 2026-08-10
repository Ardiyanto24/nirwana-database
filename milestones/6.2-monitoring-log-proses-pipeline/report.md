# Milestone 6.2: Monitoring Log Proses Pipeline — Report

**Status:** Completed
**Date completed:** 2026-08-10

## Kriteria Keberhasilan — Hasil

- [x] **Untuk setiap titik pengamatan, tim bisa menjawab "apakah tahap ini sudah berjalan hari ini, kapan, dan berapa lama" tanpa query manual ke log mentah.** — Terpenuhi untuk 9/10 titik (titik 10 sudah punya sinyal lebih granular sejak M2.4/M5.5 lewat `monitoring.reverse_etl_sync_log`, tidak disentuh M6.2). `SELECT * FROM monitoring.pipeline_run_status` — 1 view, 1 query — menjawab `status`/`started_at`/`completed_at`/`duration_seconds`/`ran_today` untuk seluruh 9 titik sekaligus. Dibuktikan lewat trigger nyata (bukan simulasi): `extract-production.yml` dipicu manual, `monitoring-warehouse-pipeline-log.yml` otomatis terpicu via `workflow_run` tanpa intervensi lanjutan, hasil query menunjukkan run baru dengan `ran_today=true`, `duration_seconds=121` — cocok persis `gh run view`.
- [x] **Riwayat eksekusi tersimpan cukup lama untuk keperluan investigasi tren (bukan hanya snapshot hari ini).** — Terpenuhi. `monitoring.pipeline_run_log` append-only (tidak ada UPDATE/overwrite), dibuktikan lewat trigger berulang: `transform-mart-cleaned.yml` dipicu manual, memicu cascade otomatis nyata ke 3 workflow paralel (`reverse-etl-mart-cleaned.yml`, `scoring-occupancy-forecast.yml`, `transform-mart-aggregated.yml`) yang lalu mencascade lagi ke `reverse-etl-mart-aggregated.yml` — total 4 tahap cascade, seluruhnya tertangkap otomatis. Hasil akhir: **seluruh 9 titik punya tepat 2 baris historis** (`COUNT(*) GROUP BY titik_id`), `pipeline_run_status` tetap menunjukkan run TERBARU per titik (`DISTINCT ON ... ORDER BY completed_at DESC` terbukti benar).

## Deliverables

- `scripts/monitoring_warehouse/{schema.sql,apply_schema.py,db.py}` — schema `monitoring.pipeline_run_log` (13 kolom, termasuk `granularity`) + view `monitoring.pipeline_run_status`, live di Supabase.
- `scripts/monitoring_warehouse/titik_config.py` — mapping 9 titik → workflow/step GitHub Actions, diverifikasi terprogram 100% cocok isi `.github/workflows/*.yml`.
- `scripts/monitoring_warehouse/snapshot_pipeline_run.py` — baca GitHub Actions REST API (run+step), tulis ke `pipeline_run_log`, idempotent.
- `.github/workflows/monitoring-warehouse-pipeline-log.yml` — 1 workflow listener gabungan (`workflow_run.workflows` array), murni observasional, 0 baris disentuh di 6 workflow pipeline existing.
- `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` — diperbarui, titik 1-9 dapat catatan sinyal baru.
- `milestones/6.2-monitoring-log-proses-pipeline/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada. Satu koreksi teknis ditemukan & diperbaiki saat menulis DDL (dicatat eksplisit di `decisions.md` Keputusan #7, bukan disembunyikan): `UNIQUE` constraint biasa di kolom nullable (`step_name`) tidak cukup untuk idempotency karena Postgres menganggap tiap `NULL` berbeda — diperbaiki pakai `UNIQUE INDEX` dengan `COALESCE(step_name, '')`.

## Known Gaps / Follow-ups

- **Gap titik 3/7 (detail per-test DQ) TIDAK tertutup oleh M6.2** — sesuai desain (`granularity='coarse'`), M6.2 cuma menambah sinyal pass/fail kasar. Prasyarat Milestone 6.3 tetap terbuka, dicatat eksplisit di `docs/keputusan-tertunda.md` dan peta M6.1 supaya tidak keliru dianggap selesai.
- **Titik 5 (sensor)**: hasil polling detail (percobaan ke berapa baru sukses) masih cuma di log run GitHub Actions mentah — M6.2 cuma mencatat hasil akhir step, bukan isi prosesnya.
- **Ditemukan 2 kegagalan operasional nyata selama verifikasi (bukan disebabkan M6.2)**: `reverse-etl-mart-cleaned.yml` gagal `employees__old already exists`, `reverse-etl-mart-aggregated.yml` gagal `dim_property__old already exists` — keduanya orphan table dari swap RENAME-based, persis pola yang sudah didokumentasikan M5.7 untuk `mart_aggregated` (`docs/keputusan-tertunda.md` "Otomasi reapply analyst_views") — sekarang terkonfirmasi juga terjadi di `mart_cleaned`. **Di luar scope M6.2 untuk diperbaiki** (M6.2 observasional, bukan pemilik `sync.py`/reverse ETL) — dicatat sebagai bukti nyata mekanisme M6.2 bekerja (menangkap kegagalan asli, bukan cuma skenario sukses), dan sebagai sinyal tambahan bahwa isu M5.7 makin mendesak untuk ditindaklanjuti pemilik infrastruktur data.
- **Belum ada mekanisme pruning/retensi** — konsisten keputusan sadar (`decisions.md` #10), sama seperti seluruh tabel `monitoring.*` lain.

## Handoff Notes

- **Milestone 6.3**: `pipeline_run_log`/`pipeline_run_status` siap dipakai langsung untuk sinyal job-status kasar, TAPI **wajib baca entri `docs/keputusan-tertunda.md` soal DQ gate sebelum breakdown** — gap detail per-test (titik 3/7) sama sekali belum tersentuh, M6.2 cuma menambah pass/fail kasar di atas gap yang sama.
- **Milestone 6.7 (dashboard terpadu)**: `pipeline_run_status` view siap jadi sumber data langsung untuk panel "status pipeline hari ini" — kolom `granularity` sudah tersedia untuk membedakan sinyal detail vs kasar di UI, kolom `ran_today` siap pakai tanpa perhitungan tambahan.
- **Siapa pun yang punya kewenangan mengedit `extract-production.yml`/`transform-mart-cleaned.yml`**: gap "titik 1→2 tidak digate" (`docs/keputusan-tertunda.md`, ditemukan M6.1) masih terbuka — `pipeline_run_log` sekarang bisa dipakai untuk membangun cross-check "titik 2 mulai tanpa titik 1 terkonfirmasi sukses" sebagai sinyal turunan (query `started_at` titik 1 vs titik 2), tapi tidak menutup akar masalahnya.
- **Pemilik infrastruktur `sync.py`/reverse ETL**: 2 kegagalan orphan-table nyata (`employees__old`, `dim_property__old`) ditemukan tanpa sengaja saat verifikasi milestone ini — layak ditindaklanjuti terpisah dari M6.2 (lihat Known Gaps), memperkuat urgensi entri M5.7 di `docs/keputusan-tertunda.md`.
- **Rerun manual**: `gh workflow run monitoring-warehouse-pipeline-log.yml -f run_id=<id> --repo Ardiyanto24/nirwana-database`, atau lokal `python scripts/monitoring_warehouse/snapshot_pipeline_run.py <run_id>`.
