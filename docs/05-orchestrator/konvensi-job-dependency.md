# Konvensi Job dan Dependency — Orchestrator Bersama (Fase 2)

**Ditulis untuk:** Milestone 2.0 — Fondasi Orchestrator Bersama (`milestones/2.0-fondasi-orchestrator-bersama/decisions.md`).
**Dipakai oleh:** Pemilik pekerjaan `mart_cleaned`/`mart_aggregated` (Milestone 2.1-2.6, `03-mart-aggregated-owner.md`) dan pekerjaan monitoring Fase 2 (`06-monitoring-warehouse-serving-fase2.md`) saat menambahkan job baru ke instance orchestrator yang sama.

## Platform

GitHub Actions di repo `nirwana-database` ini — bukan orchestrator sungguhan (Airflow/Dagster/Prefect). Keputusan & alasan lengkap ada di `milestones/2.0-fondasi-orchestrator-bersama/decisions.md` dan `docs/keputusan-tertunda.md` ("Orchestrator sungguhan untuk Fase 2"). Satu repo = satu instance orchestrator; semua job Fase 2 hidup di `.github/workflows/` repo ini, sama seperti `monitoring.yml` (Fase 1).

## Penamaan File Workflow

`<domain>-<tahap>.yml`, semua huruf kecil, pemisah tanda hubung:

- `domain` = area kerja: `extract` (Milestone 2.1), `transform` (Milestone 2.2-2.3), `reverse-etl` (Milestone 2.4), `scoring` (feedback loop `mart_aggregated`), `monitoring-warehouse` (Fase 2 monitoring), dst.
- `tahap` = tahap spesifik di dalam domain itu bila lebih dari satu, mis. `extract-incremental.yml` vs `extract-full-load.yml`.

Job demo Milestone 2.0 (bukan pipeline sungguhan, murni bukti mekanisme) mengikuti pola ini dengan prefix `orchestrator-demo-`: `orchestrator-demo-extract.yml`, `orchestrator-demo-transform.yml`, `orchestrator-demo-monitoring.yml` — dihapus atau dijadikan referensi begitu Milestone 2.1 punya workflow produksi sungguhan yang menggantikannya.

## Penamaan Job di Dalam Workflow

`run-<domain>-<tahap>` (mis. `run-extract-incremental`) — konsisten dengan `run-monitoring` di `monitoring.yml`.

## Deklarasi Dependency Antar Tahap

Dua mekanisme, dipilih sesuai kebutuhan:

1. **Dalam satu workflow file** (tahap-tahap yang selalu jalan berurutan, tidak pernah berdiri sendiri): gunakan `jobs.<job_id>.needs: [<job_id_sebelumnya>]`. Ini pola dipakai kalau seluruh rantai dimiliki satu pekerjaan (mis. beberapa step di dalam Milestone 2.1 sendiri).
2. **Antar workflow file berbeda** (dependency lintas pemilik pekerjaan, mis. `transform` menunggu `extract` selesai, atau job monitoring menunggu job pipeline utama): gunakan trigger `on.workflow_run` yang menunjuk ke `workflows: ["<nama-workflow-yang-di-tunggu>"]` dengan `types: [completed]`, lalu cek `github.event.workflow_run.conclusion == 'success'` di awal job sebelum lanjut. Ini pola dipakai job demo Milestone 2.0 dan **wajib** dipakai pemilik pekerjaan lain saat job mereka bergantung pada output workflow yang bukan milik mereka — supaya tidak perlu mengedit workflow file orang lain untuk menambahkan dependency.

## Cara Menambahkan Job Baru (untuk pemilik pekerjaan lain)

1. Buat file workflow baru di `.github/workflows/`, ikuti pola penamaan di atas.
2. Kalau job baru bergantung ke job/workflow yang sudah ada, pakai `workflow_run` (poin 2 di atas) — **jangan** edit workflow file yang sudah ada untuk menambahkan dependency incoming, cukup daftarkan `workflow_run` di file baru yang mendengarkan.
3. Kredensial baru (kalau perlu koneksi ke sistem yang belum ada secret-nya) ditambahkan sebagai GitHub Secret baru dengan nama `<SISTEM>_<TUJUAN>` (pola sama seperti `SUPABASE_DB_URL`, `GRAFANA_SERVICE_ACCOUNT_TOKEN`) — tidak pernah hardcode, tidak menimpa secret milik pekerjaan lain.
4. Tidak perlu instance/repo/project orchestrator baru — satu repo ini menampung seluruh job Fase 2. Terbukti lewat job demo Task 4 Milestone 2.0 (`orchestrator-demo-monitoring.yml`), ditambahkan tanpa mengubah `orchestrator-demo-extract.yml`/`orchestrator-demo-transform.yml` yang sudah ada.

## Batasan yang Perlu Diketahui (warisan dari keputusan "GitHub Actions extended")

- Tidak ada sensor native untuk menunggu kondisi arbitrer (mis. "tunggu sampai baris tertentu muncul di tabel") — `workflow_run` hanya bereaksi ke *completion* workflow lain, bukan ke state data. Kalau butuh sensor sungguhan (mis. feedback loop scoring, Bagian 6.4 arsitektur), kemungkinan perlu polling step manual di dalam job (cek kondisi lewat query, retry dengan `sleep`) sebagai workaround sementara.
- Retry ada di level step (`continue-on-error` + manual retry logic) atau seluruh job (re-run dari UI/`gh workflow run`), bukan retry granular per-task dengan backoff otomatis seperti orchestrator sungguhan.
- Tidak ada UI dependency graph visual — dependency hanya bisa dibaca dari isi file YAML (`needs`/`workflow_run`). Dokumen ini adalah sumber kebenaran untuk memahami rantai dependency secara keseluruhan sampai ada migrasi ke orchestrator sungguhan.
