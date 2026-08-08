# Milestone 2.4 — Reverse ETL Mart Cleaned ke PostgreSQL — Decisions

**Sumber:** `docs/03-implementation-plans/02-serving-data-scientist.md`, baris 124-140.
**Prasyarat:** Milestone 2.3 (`mart_cleaned`, 23 tabel BigQuery, DQ gate) — Completed (Partially, 1 KK gap billing, lihat `milestones/2.3-layer-intermediate-mart-cleaned/report.md`).

## Lingkup Sumber

Job reverse ETL yang mendorong seluruh `mart_cleaned` (full history, 23 tabel) dari BigQuery ke PostgreSQL sebagai serving layer, strategi **full refresh + swap table**, plus mekanisme validasi pasca-sync (row count parity). Dua Kriteria Keberhasilan sumber:
1. Seluruh 23 tabel `mart_cleaned` tersedia di PostgreSQL dengan jumlah baris cocok BigQuery pasca-sync.
2. Swap table berjalan tanpa downtime yang mengganggu akses berjalan.

Dari master architecture doc (Bagian 7): PostgreSQL "serving layer" secara konsep terpisah dari Production DB (Supabase, sumber M2.1) — pipeline: Production DB → BigQuery → `mart_cleaned` → Reverse ETL → **Postgres serving layer** → consumers.

## Keputusan (via AskUserQuestion, dikonfirmasi user)

### 1. Lokasi serving PostgreSQL: project Supabase baru, terpisah dari production

**Keputusan:** Provision project Supabase baru khusus serving layer — bukan schema baru di project production yang sama, bukan provider lain (Neon/Render/Railway).

**Kenapa:** Project ini belum punya instance serving sama sekali. Opsi ini paling sesuai diagram arsitektur (Production DB dan Serving Layer digambarkan sebagai dua box terpisah) dan tetap gratis (Supabase free tier) — jadi "gratis" di sini dicapai TANPA harus mencampur source production dan hasil reverse-ETL dalam satu instance fisik, konsisten dengan kebiasaan project ini memilih opsi termurah/tersimple (GitHub Actions, BigQuery Sandbox) tanpa mengorbankan kejujuran arsitektur.

**Ditolak:** Schema baru di project Supabase production yang sama (nol setup tapi mencampur source dan serving secara fisik — menyimpang dari dokumen arsitektur); provider Postgres gratis lain (menambah vendor baru tanpa manfaat jelas dibanding Supabase baru).

### 2. M2.4 juga menutup gap orkestrasi transform yang belum terjadwal

**Keputusan:** Task pertama M2.4 adalah membuat `.github/workflows/transform-mart-cleaned.yml` — menjalankan dbt run+test staging (M2.2) → `promote.py --select mart_cleaned` (M2.3) → `renew_expiration.py` untuk `staging`/`mart_cleaned`/`mart_cleaned_staging`, terjadwal harian + `workflow_dispatch`.

**Kenapa:** `.github/workflows/` saat ini tidak punya job terjadwal untuk transform M2.2/M2.3 — keduanya masih dijalankan manual, sudah diflag prioritas tinggi di `milestones/2.3-layer-intermediate-mart-cleaned/report.md` (Known Gaps). Menutup gap ini sekarang menyelesaikan **2 known gap M2.3 sekaligus** (transform belum terjadwal + renewal 3 dataset belum terjadwal), dan membuat `workflow_run` chaining reverse-etl→transform (konvensi M2.0, `docs/05-orchestrator/konvensi-job-dependency.md`) benar-benar bermakna — bukan dua jadwal independen yang kebetulan berurutan.

**Ditolak:** M2.4 tetap ketat reverse-etl saja dengan jadwal sendiri tanpa dependency nyata — risiko mem-push data BigQuery yang stale ke Postgres tanpa terdeteksi.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 3. Kredensial least-privilege

Service account BigQuery baru `reverse-etl-reader` (read-only, dataset-scoped ke `mart_cleaned` SAJA + `bigquery.jobUser` project-level, pola sama `extract-writer`). Role Postgres baru di serving project (`reverse_etl_writer`) yang cuma bisa CREATE/DROP/ALTER/RENAME table di schema `mart_cleaned`, bukan superuser. Key file service account dibuat manual oleh user (pola berulang M2.1-2.3 — session classifier memblokir pembuatan key oleh assistant).

### 4. Bulk load via COPY, bukan row-by-row INSERT

Tabel terbesar (`fnb_transactions` ~902k, `staff_shifts` ~610k baris) butuh bulk path: baca BigQuery paginated (`list_rows`), tulis ke tabel staging Postgres via `psycopg2.copy_expert` dari buffer in-memory per batch — bukan load penuh ke pandas DataFrame sekaligus untuk tabel besar.

### 5. Row-count-parity check sebagai GATE sebelum swap

Hitung `COUNT(*)` BigQuery vs tabel staging Postgres SEBELUM proses RENAME — kalau tidak cocok, staging table dibuang dan live table TIDAK disentuh sama sekali.

**Deviasi sadar** dari bacaan literal "validasi pasca-sync" di dokumen sumber (bisa dibaca sebagai "cek setelah swap selesai") — dibuat lebih ketat, konsisten dengan filosofi DQ gate M2.3 ("jangan pernah biarkan versi salah jadi live").

### 6. Log sync ke `monitoring.reverse_etl_sync_log` (production Supabase, bukan serving project)

Tabel baru, additive, di schema `monitoring` yang sama (production Supabase) — bukan di serving project baru. Konsisten dengan backbone monitoring bersama project ini (lihat CLAUDE.md "monitoring schema — the shared backbone") — monitoring tetap terpusat terlepas dari di mana serving layer secara fisik berada.

## Catatan Out-of-Scope

Role Postgres **read-only** untuk konsumen (Data Analyst) di serving project baru ini belum ada milestone eksplisit yang menaunginya di `02-serving-data-scientist.md` (M2.5/2.6 fokus ke akses BigQuery untuk Data Scientist, bukan akses Postgres untuk Data Analyst). M2.4 hanya membangun role WRITER untuk job reverse-etl itu sendiri. Ini kemungkinan gap dokumentasi yang perlu diangkat terpisah setelah M2.4 selesai — kandidat entri baru `docs/keputusan-tertunda.md`, bukan diasumsikan otomatis tertutup milestone lain.

## Task Breakdown

15 task, 4 fase, 5 checkpoint (commit + push + log tiap checkpoint, pola sama M2.3).

### Fase 1 — Fondasi Infrastruktur Serving + Orkestrasi
1. Provision project Supabase baru untuk serving layer, buat schema `mart_cleaned`, tambahkan `SERVING_DB_URL` ke `.env`/`.env.example`.
2. Buat role Postgres `reverse_etl_writer` (scoped ke schema `mart_cleaned`, bukan superuser).
3. Buat service account BigQuery `reverse-etl-reader` (read-only, dataset-scoped `mart_cleaned`) + `bigquery.jobUser`.
4. Buat `.github/workflows/transform-mart-cleaned.yml`.

**Checkpoint 1**

### Fase 2 — Mekanisme Sync + Swap + Uji Coba 1 Tabel
5. Tulis `scripts/reverse_etl/sync.py` generic per-tabel, uji di 1 tabel kecil.
6. Uji coba terkontrol "no-downtime swap".
7. Tabel `monitoring.reverse_etl_sync_log` + logging tiap sync.

**Checkpoint 2**

### Fase 3 — Rollout ke 23 Tabel
8. `corporate_master` (4 tabel)
9. `reservation_revenue` (3 tabel)
10. `fnb_operations` (6 tabel, termasuk `fnb_transactions` 902k baris)

**Checkpoint 3** (13/23)

11. `facility_maintenance` (3 tabel)
12. `spa_event` (3 tabel)
13. `hr_finance` (4 tabel, termasuk `payroll`)

**Checkpoint 4** (23/23)

### Fase 4 — Wiring Orchestrator + Penutupan
14. Buat `.github/workflows/reverse-etl-mart-cleaned.yml`, trigger `workflow_run` menunggu `transform-mart-cleaned.yml`.
15. Verifikasi 2 Kriteria Keberhasilan + tulis `report.md`.

**Checkpoint 5 (final)**
