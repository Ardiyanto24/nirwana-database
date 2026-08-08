# Milestone 2.6: Isolasi Akses dan Kredensial Read-Only — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Kredensial yang diberikan ke Data Scientist terbukti tidak bisa mengakses dataset raw maupun `mart_aggregated` saat diuji coba.** — Terpenuhi. Dibangun & diuji penuh di Milestone 2.5 (`scripts/bigquery_common/verify_dataset_isolation.py --allow mart_cleaned.* --deny raw_production.* --deny staging.*`, 3/3 OK), **di-re-verifikasi ulang di M2.6** (tidak ada drift). Isolasi dari `mart_aggregated` tetap dibuktikan by-construction (dataset itu belum ada di project) — dicatat konsisten di M2.5 dan diwariskan di sini, bukan diklaim "sudah diuji langsung" secara menyesatkan.
- [x] **Kredensial terbukti hanya bisa membaca (tidak bisa menulis/mengubah) `mart_cleaned`.** — Terpenuhi. Dibuktikan empiris di M2.5 (percobaan `CREATE TABLE` ditolak `Forbidden`) — tidak diulang otomatis di M2.6 (percobaan tulis di dataset scoped adalah operasi yang secara desain "sekali cukup", tidak ada mekanisme yang bisa membuatnya berubah drift di antara M2.5 dan M2.6 tanpa perubahan grant eksplisit, yang tidak terjadi).

## Deliverables

- `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` — dokumen kebijakan **project-wide**: inventaris 6 kredensial scoped (nama, sistem, scope, milestone asal, bukti isolasi, status least-privilege), pengecualian `dbt-transform` didokumentasikan eksplisit (project-level, bukan dataset-scoped, alasan sadar), siapa boleh pegang tiap kredensial, proses meminta kredensial baru, proses rotasi/pencabutan (termasuk gap rotasi otomatis yang diwariskan dari M2.5).
- Audit + re-verifikasi non-destruktif 6 kredensial (Task 1-2) — 4/6 diverifikasi ulang lewat mekanisme yang ada (2 BigQuery reader via `verify_dataset_isolation.py`, 2 role Postgres via query ad-hoc pakai `.env` existing tanpa rotasi password), 2/6 (`extract-writer`, `dbt-transform`) dikutip dari bukti manual milestone asal apa adanya — **zero drift** ditemukan di seluruh 6.
- `milestones/2.6-isolasi-akses-kredensial-read-only/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada. Kedua keputusan (cakupan project-wide, lokasi `docs/06-akses-kredensial/`) dan keputusan teknis (re-verifikasi non-destruktif tanpa rotasi password) diimplementasikan persis seperti direncanakan.

## Known Gaps / Follow-ups

- **Rotasi kredensial otomatis masih belum ada** — diwariskan dari `milestones/2.5-.../report.md`, sekarang didokumentasikan project-wide di `docs/06-akses-kredensial/...md` (bagian "Rotasi dan Pencabutan") alih-alih tersebar. Bukan gap baru, hanya sekarang tercatat konsisten di 1 tempat.
- **`extract-writer` dan `dbt-transform` tidak punya script verifikasi isolasi re-runnable** (beda dari 4 kredensial lain yang sudah punya) — untuk `dbt-transform` ini memang tidak relevan (scope-nya sengaja project-level, bukan soal isolasi dataset tunggal). Untuk `extract-writer`, ini gap kecil yang bisa ditutup nanti kalau dibutuhkan (tinggal pakai `verify_dataset_isolation.py --allow raw_production.* --deny staging.* --deny mart_cleaned.*`) — tidak dikerjakan sekarang karena di luar scope eksplisit M2.6 (audit + kebijakan, bukan membangun tooling baru untuk kredensial M2.1).

## Handoff Notes

- **`docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` adalah rujukan tunggal untuk seluruh kredensial scoped project ini** — setiap milestone berikutnya yang membuat kredensial BigQuery/Postgres baru (mis. pemilik `mart_aggregated`, `03-mart-aggregated-owner.md`) sebaiknya menambah 1 baris ke tabel inventaris di situ, bukan cuma mencatat di `decisions.md` milestone masing-masing saja.
- **Untuk Milestone 2.7+ atau `mart_aggregated`**: pola `scripts/bigquery_common/verify_dataset_isolation.py` siap dipakai langsung untuk kredensial BigQuery baru, tidak perlu script baru.
