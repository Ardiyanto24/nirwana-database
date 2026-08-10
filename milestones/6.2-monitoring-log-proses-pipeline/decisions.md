# Milestone 6.2: Monitoring Log Proses Pipeline — Decisions

**Source:** `docs/03-implementation-plans/06-monitoring-warehouse-serving-fase2.md`, baris 68-83.
**Prasyarat:** Milestone 6.1 (`docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md`) — Completed, peta 10 titik pengamatan pipeline Fase 2, konsumen langsung milestone ini.
**Status:** Done
**Date started:** 2026-08-10

## Contract (from source doc)

- **Lingkup:** Membangun kemampuan **melihat apa yang terjadi** di sepanjang pipeline — status tiap job (berjalan/berhasil/gagal), durasi eksekusi, riwayat historisnya. Prinsip monitoring pertama fase ini (bukan cuma tahu ada masalah, tapi bisa menelusuri proses apa yang sedang/sudah terjadi).
- **Output:** (1) Mekanisme pencatatan status dan durasi tiap job/tahap dalam pipeline (10 titik Milestone 6.1). (2) Kemampuan menelusuri riwayat eksekusi (kapan suatu tahap terakhir berjalan, berapa lama, apa hasilnya) tanpa perlu masuk ke sistem orkestrator secara manual.
- **Kriteria Keberhasilan:**
  1. Untuk setiap titik pengamatan, tim bisa menjawab "apakah tahap ini sudah berjalan hari ini, kapan, dan berapa lama" tanpa query manual ke log mentah.
  2. Riwayat eksekusi tersimpan cukup lama untuk keperluan investigasi tren (bukan hanya snapshot hari ini).

## Temuan Riset

Dibaca langsung dari `.github/workflows/*.yml` 6 workflow Fase 2 nyata (`extract-production.yml`, `transform-mart-cleaned.yml`, `reverse-etl-mart-cleaned.yml`, `scoring-occupancy-forecast.yml`, `transform-mart-aggregated.yml`, `reverse-etl-mart-aggregated.yml`):

- Setiap workflow sudah punya step name yang deskriptif dan konsisten (`"Milestone X.X -- <deskripsi>"`), 1 job per workflow. GitHub Actions REST API (`GET .../actions/runs/{run_id}/jobs`) mengembalikan array `steps` dengan `name`/`conclusion`/`started_at`/`completed_at` per step — granularitas per-langkah sudah tersedia gratis dari infrastruktur yang ada.
- Titik 1 (extract), titik 4 (trigger scoring), titik 8/9 (reverse ETL) masing-masing punya 1 step yang cleanly 1:1 dengan titik-nya sendiri.
- Titik 5 (sensor `ml_output`) punya step tersendiri yang terpisah jelas di dalam `transform-mart-aggregated.yml`.
- Titik 2 dan titik 3 berbagi 1 step yang sama (`promote.py` yang membundel dbt run+test+swap). Titik 6 dan titik 7 juga berbagi 1 step yang sama. Ini mengonfirmasi ulang temuan M6.1 (`docs/keputusan-tertunda.md`): granularitas GitHub Actions cukup untuk tahu "apakah step ini sukses/gagal" (menjawab KK1), tapi tidak cukup membedakan "gagal karena transform" vs "gagal karena DQ test spesifik" (tetap scope M6.3).
- Titik 10 (post-sync parity) sudah punya sinyal lebih granular dari GitHub Actions manapun: `monitoring.reverse_etl_sync_log` (per-tabel, ditulis `sync.py`) — M6.2 tidak menyentuhnya, cukup dirujuk.
- Tidak ada precedent pemanggilan GitHub API di Python manapun di repo ini (0 match `GITHUB_TOKEN`/`api.github.com`/`PyGithub`). `requests==2.33.1` sudah jadi dependency (M4.6).
- Pola konfigurasi list-of-tuple (`scripts/monitoring/tables_config.py`) dan pola schema `monitoring.*` (snapshot append-only + `UNIQUE` constraint idempotency) sudah established kuat — direplikasi untuk M6.2.
- `docs/05-orchestrator/konvensi-job-dependency.md` baris 14 sudah mengantisipasi domain `monitoring-warehouse` untuk pekerjaan ini.

## Task Breakdown

6 checkpoint, commit tiap checkpoint.

- [x] **Checkpoint 1** — `decisions.md` (dokumen ini) + `scripts/monitoring_warehouse/{schema.sql,apply_schema.py,db.py}` — Acceptance: `monitoring.pipeline_run_log`+`pipeline_run_status` live di Supabase — Verify: query `information_schema` konfirmasi tabel+view+kolom benar — S
- [x] **Checkpoint 2** — `scripts/monitoring_warehouse/titik_config.py` (9 baris titik 1-9) — Acceptance: workflow filename + step-name-substring cocok persis isi YAML — Verify: grep silang — S
- [x] **Checkpoint 3** — `scripts/monitoring_warehouse/snapshot_pipeline_run.py` — Acceptance: insert benar dari run GitHub Actions nyata yang sudah ada — Verify: cocokkan hasil query vs `gh run view` — M
- [x] **Checkpoint 4** — `.github/workflows/monitoring-warehouse-pipeline-log.yml` + verifikasi KK1 — Acceptance: listener otomatis terpicu, `pipeline_run_status` benar — Verify: trigger nyata + query — S
- [x] **Checkpoint 5** — Verifikasi KK2 (riwayat terakumulasi) + cakupan titik 2/3 & 6/7 (granularity benar) — Verify: trigger berulang + query — XS
- [x] **Checkpoint 6** — Update peta M6.1 + `logs.md` + `report.md` — Verify: cocokkan KK1/KK2 dengan bukti Checkpoint 4/5 — S

## Technical Decisions

Seluruh keputusan (3 via diskusi `AskUserQuestion` sesi ini dengan analisis standar industri, 9 keputusan teknis lain dikunci tanpa tanya) dicatat lengkap di plan mode session ini dan direplikasi di sini untuk arsip permanen:

### 1. Sumber data: Observasi GitHub Actions REST API, bukan instrumentasi langsung ke workflow/script pipeline

**Context:** 2 opsi arsitektur untuk mendapatkan status/durasi per titik — observasi pasif via API GitHub Actions, atau instrumentasi aktif (step logging baru di 6 workflow YAML, atau modifikasi `promote.py`/`sync.py`/`extract.py` supaya menulis status sendiri).
**Decision:** Observasi API — `github.event.workflow_run` payload (run-level, gratis) + `GET .../runs/{id}/jobs` (step-level). Nol baris kode di 6 workflow pipeline existing atau script pipeline manapun disentuh.
**Alternatives considered:** Instrumentasi langsung — ditolak. Padanan paling dekat standar industri untuk platform tanpa orchestrator sungguhan adalah observasi via API CI/CD (pola sama Datadog CI Visibility, Grafana GitHub Actions datasource) — instrumentasi langsung dianggap anti-pattern observability modern (mencampur logic monitoring ke logic bisnis) dan berisiko nyata: `promote.py`/`sync.py` sudah diverifikasi lewat fault-injection nyata (M2.3, M5.3) dan zero-downtime test (M2.4, M5.5), menambah logic ke situ berarti re-test ulang seluruh jaminan itu untuk manfaat granularitas yang sebenarnya tetap jadi scope M6.3.

### 2. Titik 3 & 7: dicatat sebagai sinyal, ditandai eksplisit `granularity='coarse'` di level data

**Context:** Titik 3 dan 7 berbagi step GitHub Actions yang sama dengan titik 2 dan 6 (dari `promote.py` yang membundel build+test+swap) — datanya identik, cuma "dipinjam".
**Decision:** Tetap dicatat (bukan dikecualikan), kolom `granularity` (`'coarse'|'detailed'`) menandai titik 3/7 sebagai `'coarse'`, beda dari titik 1,2,4,5,6,8,9 yang `'detailed'`.
**Alternatives considered:** Kecualikan total dari M6.2 — ditolak, 2/10 titik kosong sama sekali bertentangan literal KK1 "untuk setiap titik pengamatan". Catat coarse tanpa penanda granularitas — ditolak, risiko disalahartikan "sudah selesai" di kemudian hari (preseden serupa: diskrepansi nama tabel `role_permissions` M1.1). Pola observability data quality matang (Great Expectations, dbt artifacts, Monte Carlo/Bigeye) selalu mulai dari sinyal kasar yang ditandai eksplisit levelnya, detail menyusul bertahap — persis ritme project ini sendiri (M1.2→M1.3, M5.5→M3.3).

### 3. Struktur workflow: 1 file gabungan memakai `workflow_run.workflows:` array 6 nama workflow

**Context:** Workflow listener baru bisa 1 file gabungan, 6 file terpisah 1:1 (konvensi existing), atau reusable workflow (`workflow_call`).
**Decision:** 1 file gabungan, `on.workflow_run.workflows: [6 nama workflow pipeline]`.
**Alternatives considered:** 6 file terpisah 1:1 — ditolak, konsisten konvensi existing tapi 6× duplikasi boilerplate (checkout/setup-python/write-env identik). Reusable workflow — ditolak, menambah 1 lapisan abstraksi yang belum pernah dipakai di project ini, berlebihan untuk skala 6 workflow. `workflow_run.workflows:` menerima array secara sengaja didesain GitHub untuk use-case persis ini (1 listener pusat bereaksi ke banyak workflow upstream — status aggregator, bukan dependency chain linear) — penggunaan fitur sesuai desain platform, bukan penyimpangan.

### 4. Trigger: `workflow_run` event-driven, bukan periodic batch pull

Konsisten pola `workflow_run` yang sudah dipakai di seluruh pipeline Fase 2. Payload event sudah membawa data run-level tanpa API call tambahan. Event-driven menjamin tidak ada run yang terlewat (beda dari batch pull yang butuh window lookback).

### 5. Autentikasi: `GITHUB_TOKEN` bawaan Actions untuk run terjadwal, PAT lokal (`GITHUB_API_TOKEN`) cuma untuk uji coba manual

`GITHUB_TOKEN` otomatis tersedia tiap run Actions dengan scope baca `actions` — tidak perlu kredensial baru (least-privilege M2.6, milestone ini tidak menambah 1 pun baris ke `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`).

### 6. Tulis ke Postgres pakai `SUPABASE_DB_URL` admin langsung, bukan kredensial scoped baru

Mengikuti pola `scripts/monitoring/`, `scripts/dq/`, `scripts/schema_drift/` (batch/scheduled monitoring writer) — beda kategori dari `chatbot_audit_writer` yang scoped karena live-traffic API process, bukan batch job internal.

### 7. Schema: 1 tabel gabungan `monitoring.pipeline_run_log`, kolom `granularity`, UNIQUE index pakai `COALESCE(step_name, '')`

Kolom: `id, titik_id, titik_label, workflow_name, run_id, step_name (nullable), granularity, status, started_at, completed_at, duration_seconds, trigger_event, logged_at`. **Temuan implementasi** (tidak direncanakan eksplisit di plan awal, ditemukan saat menulis DDL): `UNIQUE (titik_id, run_id, step_name)` biasa TIDAK cukup untuk idempotency karena Postgres menganggap tiap NULL berbeda satu sama lain — 2 baris titik run-level (`step_name IS NULL`) dengan `titik_id`+`run_id` sama tetap dianggap unik oleh constraint biasa. Diperbaiki pakai `CREATE UNIQUE INDEX ... (titik_id, run_id, COALESCE(step_name, ''))` — idempotency benar untuk titik run-level maupun step-level.

### 8. View `monitoring.pipeline_run_status` — pola sama `monitoring.current_status` (M1.2)

`SELECT DISTINCT ON (titik_id) ... ORDER BY titik_id, completed_at DESC` — 1 baris terbaru per titik, termasuk kolom `granularity`. Kolom `ran_today` valid dipakai (timestamp run GitHub Actions wall-clock nyata, beda dari freshness-lag Fase 1 yang terikat data production statis).

### 9. Tidak ada backfill historis — capture forward mulai milestone ini selesai

Pipeline Fase 2 baru berjalan sejak ~2026-08-08 (M2.0) — jendela backfill cuma ~2 hari, manfaatnya kecil dibanding kerumitan tambahan.

### 10. Retensi unbounded, tidak ada pruning

Konsisten seluruh tabel snapshot `monitoring.*` lain.

### 11. Konfigurasi mapping titik→sumber sinyal: `scripts/monitoring_warehouse/titik_config.py`

Replikasi pola `scripts/monitoring/tables_config.py` — satu tempat kebenaran.

### 12. Folder baru `scripts/monitoring_warehouse/`

`scripts/monitoring/` eksklusif Fase 1 — folder terpisah mengikuti nama `docs/10-monitoring-warehouse-serving/`.

## Open Questions Resolved with User

- Q: Apakah tidak ada bagian yang perlu didiskusikan dengan user (semua dikunci tanpa tanya)? → A: Ada 3 fork arsitektur material yang sempat terlewat dikunci sepihak — diajukan ulang via `AskUserQuestion`, didiskusikan mendalam (2 putaran, termasuk penjelasan detail tiap opsi dan analisis "mana yang paling dekat standar industri"), dikonfirmasi user.
- Q: Sumber data observasi API vs instrumentasi? → A: Observasi API (Keputusan #1).
- Q: Titik 3/7 dicatat coarse, dikecualikan, atau coarse+penanda granularitas? → A: Coarse + kolom `granularity` eksplisit (Keputusan #2).
- Q: 1 workflow gabungan vs 6 terpisah vs reusable workflow? → A: 1 gabungan pakai `workflow_run.workflows:` array (Keputusan #3).
