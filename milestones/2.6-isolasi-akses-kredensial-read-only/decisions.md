# Milestone 2.6 — Isolasi Akses dan Kredensial Read-Only — Decisions

**Sumber:** `docs/03-implementation-plans/02-serving-data-scientist.md`, baris 160-176.
**Prasyarat:** Milestone 2.5 (API Akses Data Scientist) — Completed, kedua KK terpenuhi.

## Lingkup Sumber

Mengonfigurasi service account/kredensial terpisah khusus Data Scientist, least-privilege (read-only, terbatas ke `mart_cleaned` saja). Dua Kriteria Keberhasilan sumber:
1. Kredensial yang diberikan ke Data Scientist terbukti tidak bisa mengakses dataset raw maupun `mart_aggregated`.
2. Kredensial terbukti hanya bisa membaca (tidak bisa menulis/mengubah) `mart_cleaned`.

## Konteks Kritis: Sebagian Besar Scope Ini Sudah Selesai di M2.5

`milestones/2.5-api-akses-data-scientist/decisions.md` Decision 2 sudah mengunci: **M2.5 membangun kredensial `data-scientist-reader` yang SUDAH teruji penuh** (bukan sementara) — read-only dibuktikan empiris (`CREATE TABLE` ditolak `Forbidden`), isolasi dari `raw_production`/`staging` diuji langsung, isolasi dari `mart_aggregated` dijelaskan by-construction. **Kedua KK M2.6 secara literal sudah terpenuhi oleh pekerjaan M2.5** untuk kredensial ini — M2.6 TIDAK membangun ulang service account atau uji teknis dari nol.

## Keputusan (via AskUserQuestion, dikonfirmasi user)

### 1. Cakupan kebijakan: project-wide, mencakup seluruh 6 kredensial scoped

**Keputusan:** Dokumen kebijakan M2.6 mencakup SELURUH kredensial scoped yang sudah dibuat sepanjang Fase 2 — `extract_reader` (M2.1), `extract-writer` (M2.1), `dbt-transform` (M2.2/2.3), `reverse_etl_writer` (M2.4), `reverse-etl-reader` (M2.4), `data-scientist-reader` (M2.5) — bukan cuma `data-scientist-reader`.

**Kenapa:** Dokumen sumber eksplisit bilang RBAC lapis kedua ini "menjadi tanggung jawab pemilik infrastruktur data di **seluruh sistem ini**", bukan cuma soal 1 kredensial. Nilai tambah: 1 tempat rujukan untuk semua kredensial scoped yang ada, bukan tersebar di 5 `decisions.md` berbeda.

**Ditolak:** Kebijakan sempit cuma `data-scientist-reader` — lebih setia ke posisi milestone dalam urutan dokumen, tapi mengabaikan frasa "seluruh sistem" di dokumen sumber.

### 2. Lokasi dokumen: `docs/06-akses-kredensial/` (folder baru)

**Keputusan:** `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`.

**Kenapa:** Pola sama `docs/05-orchestrator/konvensi-job-dependency.md` (M2.0) — dokumen konvensi/kebijakan project-wide yang dirujuk lintas milestone layak folder `docs/` sendiri, bukan terkubur di 1 milestone folder atau nebeng ke `docs/02-requirements/` yang isinya spesifik per-konsumen (RBAC chatbot, pemetaan data mart), bukan kebijakan operasional kredensial.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 3. Re-verifikasi Task 1: non-destruktif saja, TIDAK rotasi password

Untuk kredensial yang punya mekanisme verifikasi re-runnable: `reverse-etl-reader`/`data-scientist-reader` (BigQuery, `verify_dataset_isolation.py` — murni SELECT, tanpa efek samping) di-re-run langsung. `extract_reader`/`reverse_etl_writer` (Postgres) diverifikasi ulang dengan query read-only pakai connection string YANG SUDAH ADA di `.env` (bukan menjalankan ulang `setup_extract_role.py`/`setup_writer_role.py`, yang me-ROTASI password dan akan mematahkan GitHub Secret yang sudah dipakai workflow terjadwal tanpa update manual). `extract-writer`/`dbt-transform` (project-level, bukan dataset-scoped sempit) tidak diuji ulang otomatis — dikutip dari bukti manual M2.1/M2.2 sebagaimana adanya, dicatat eksplisit sebagai "verifikasi manual, bukan otomatis" di dokumen kebijakan (bukan diklaim setara dengan yang punya script).

## Task Breakdown

4 task, 2 fase, 2 checkpoint (commit + push + log tiap checkpoint, pola sama M2.5).

### Fase 1 — Audit + Re-verifikasi
1. Audit 6 kredensial scoped (nama, sistem, scope, milestone asal, bukti isolasi) — cross-check ke `decisions.md`/`logs.md` tiap milestone, bukan dari ingatan.
2. Re-verifikasi non-destruktif: `verify_dataset_isolation.py` untuk `reverse-etl-reader`/`data-scientist-reader`; query read-only pakai `.env` existing untuk `extract_reader`/`reverse_etl_writer`.

**Checkpoint 1**

### Fase 2 — Kebijakan + Penutupan
3. Tulis `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` (inventaris 6 kredensial, siapa boleh pakai/minta baru, proses rotasi/pencabutan, prinsip least-privilege wajib untuk kredensial baru ke depan).
4. Verifikasi 2 Kriteria Keberhasilan sumber (merujuk bukti M2.5 + audit Task 1-2) + tulis `report.md`.

**Checkpoint 2 (final)**
