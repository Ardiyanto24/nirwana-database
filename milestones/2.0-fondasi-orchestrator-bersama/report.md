# Milestone 2.0: Fondasi Orchestrator Bersama (Fase 2) — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Job percobaan sederhana berhasil dijadwalkan dan dijalankan melalui platform ini.** — Terpenuhi. `orchestrator-demo-extract.yml` punya trigger `schedule` (cron harian, 02:00 UTC) dan `workflow_dispatch`. Dipicu manual via `gh workflow run` untuk verifikasi cepat (tidak perlu menunggu jadwal harian): run [`31226809039`](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31226809039), status `success`, selesai dalam 7 detik.
- [x] **Pemilik pekerjaan lain (diverifikasi lewat uji coba akses) bisa menambahkan job baru ke instance yang sama tanpa perlu membangun instance terpisah.** — Terpenuhi. `orchestrator-demo-monitoring.yml` ditambahkan sebagai file baru (mensimulasikan pekerjaan monitoring Fase 2 sebagai "pemilik lain"), mengikuti konvensi di `docs/05-orchestrator/konvensi-job-dependency.md`, **tanpa mengubah satu baris pun** di `orchestrator-demo-extract.yml`/`orchestrator-demo-transform.yml` yang sudah ada (dicek lewat commit diff — hanya 1 file baru, bukan modifikasi). Job ini ter-trigger otomatis lewat `workflow_run` (run [`31226825790`](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31226825790), sukses) di repo/instance GitHub Actions yang sama persis dengan 2 job sebelumnya — tidak ada repo, project, atau service orchestrator baru yang dibuat.

## Bukti Rantai Dependency (run history sungguhan)

| Job | Run ID | Trigger | Waktu mulai (UTC) | Status |
|---|---|---|---|---|
| Orchestrator Demo - Extract | 31226809039 | manual (`workflow_dispatch`) | 23:20:12 | success |
| Orchestrator Demo - Transform | 31226817633 | otomatis (`workflow_run`, 9 detik setelah extract sukses) | 23:20:21 | success |
| Orchestrator Demo - Monitoring (Simulated Other Owner) | 31226825790 | otomatis (`workflow_run`, 9 detik setelah transform sukses) | 23:20:30 | success |

Urutan waktu run membuktikan dependency chain berjalan sesuai desain (bukan ketiganya jalan paralel/independen) — hanya trigger job pertama secara manual sudah cukup memicu seluruh rantai sampai job ketiga.

## Deliverables

- `CLAUDE.md` — Project Scope diupdate: Fase 2 kini dikerjakan di repo ini mulai Milestone 2.0 (file ini gitignored, perubahan tersimpan lokal, tidak muncul di histori commit — konsisten dengan konvensi repo yang sudah ada sebelum milestone ini).
- `docs/keputusan-tertunda.md` — entri baru "Orchestrator sungguhan (Airflow/Dagster/Prefect self-hosted) untuk Fase 2" (Open, revisit di masa depan).
- `docs/05-orchestrator/konvensi-job-dependency.md` — konvensi penamaan file/job, dua mekanisme dependency (`needs` vs `workflow_run`), cara menambah job baru tanpa mengedit job existing, dan batasan eksplisit platform (tidak ada sensor native, tidak ada UI dependency graph).
- `.github/workflows/orchestrator-demo-extract.yml`, `orchestrator-demo-transform.yml`, `orchestrator-demo-monitoring.yml` — 3 job demo membuktikan mekanisme, self-contained (tanpa koneksi GCP/BigQuery, karena provisioning itu di luar lingkup M2.0).
- `milestones/2.0-fondasi-orchestrator-bersama/{decisions,logs}.md`.

## Deviations from decisions.md

- **Provisioning GCP/BigQuery sempat direncanakan sebagai task M2.0 di draft awal breakdown, lalu dikoreksi keluar dari scope** setelah re-baca source doc (M2.0 eksplisit "tidak mencakup mendefinisikan seluruh 10 langkah dependency" — provisioning `raw_production` adalah output Milestone 2.1). Dicatat di `decisions.md` sebagai catatan serah terima ke M2.1, bukan dikerjakan di sini. Ini koreksi terhadap draft breakdown awal, bukan deviasi dari `decisions.md` final (yang sudah menulis versi terkoreksi).
- Tidak ada deviasi lain — seluruh 6 task di `decisions.md` final selesai sesuai rencana.

## Known Gaps / Follow-ups

- **Job demo bersifat sementara/ilustratif**, bukan job produksi. Begitu Milestone 2.1 punya workflow ekstraksi sungguhan, `orchestrator-demo-*.yml` sebaiknya dihapus atau diberi catatan eksplisit "referensi, bukan aktif" supaya tidak membingungkan pemilik pekerjaan lain yang membaca `.github/workflows/`.
- **Batasan GitHub Actions sebagai orchestrator** (tidak ada sensor native untuk kondisi arbitrer, tidak ada UI dependency graph, retry granular per-task terbatas) sudah didokumentasikan di `docs/05-orchestrator/konvensi-job-dependency.md` dan `docs/keputusan-tertunda.md` — akan jadi masalah nyata begitu Milestone 2.5+ (feedback loop scoring, Bagian 6.4 arsitektur) butuh sensor menunggu `ml_output` selesai ditulis. Perlu direvisit sebelum sampai ke sana, bukan ditunda sampai mendesak.
- **Belum ada pemilik pekerjaan lain sungguhan** — Kriteria Keberhasilan #2 diverifikasi lewat simulasi (job dummy berperan sebagai pekerjaan monitoring Fase 2), bukan uji coba dengan orang/tim sungguhan yang berbeda, karena project ini dikerjakan solo. Konvensi di `docs/05-orchestrator/konvensi-job-dependency.md` tetap jadi acuan tertulis untuk kapan pun kebutuhan itu jadi nyata.

## Handoff Notes

- **Untuk Milestone 2.1**: mulai dengan provisioning GCP project + dataset `raw_production` (lihat catatan serah terima di `milestones/2.0-fondasi-orchestrator-bersama/decisions.md`), lalu bangun workflow ekstraksi sungguhan mengikuti pola penamaan `extract-<tahap>.yml` dari `docs/05-orchestrator/konvensi-job-dependency.md` (bukan melanjutkan prefix `orchestrator-demo-`).
- **Rerun manual job demo**: `gh workflow run orchestrator-demo-extract.yml --repo Ardiyanto24/nirwana-database` — akan memicu seluruh rantai (transform lalu monitoring) otomatis.
- **Kredensial**: belum ada secret baru ditambahkan di milestone ini (job demo tidak butuh koneksi eksternal) — Milestone 2.1 akan jadi yang pertama menambah secret terkait GCP (pola nama: `GCP_<TUJUAN>`, konsisten dengan `SUPABASE_DB_URL`/`GRAFANA_SERVICE_ACCOUNT_TOKEN`).
- Dengan selesainya Milestone 2.0, Milestone 2.1 (Extraction Production ke Raw Warehouse) sudah bisa dimulai — prasyarat "bisa berjalan terjadwal" sudah terbukti.
