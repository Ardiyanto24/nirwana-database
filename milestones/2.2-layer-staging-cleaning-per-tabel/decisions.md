# Milestone 2.2: Layer Staging — Cleaning per Tabel (Fase 2)

**Source:** `docs/03-implementation-plans/02-serving-data-scientist.md` (baris 85-101, "Milestone 2.2 — Layer Staging: Cleaning per Tabel")
**Status:** Done (lihat `report.md` untuk verifikasi Kriteria Keberhasilan)
**Date started:** 2026-08-08

## Contract (from source doc)

- **Lingkup:** Membangun transformasi staging untuk seluruh 23 tabel, menerapkan aturan cleaning spesifik per tabel sesuai pemetaan di `docs/02-requirements/pemetaan-kebutuhan-konsumen-data-mart.md` — normalisasi format (telepon, kapitalisasi, tanggal), trim whitespace, type casting, sambil sadar mempertahankan missing value bermakna dan dirty data yang disengaja.
- **Output:** Model staging 23 tabel dengan aturan cleaning per tabel; dokumentasi eksplisit daftar kolom/tabel yang sengaja tidak dibersihkan.
- **Kriteria keberhasilan:**
  1. Untuk tabel dengan aturan normalisasi, hasil staging menunjukkan nilai yang sudah dinormalisasi.
  2. Untuk kolom/baris yang harus dipertahankan apa adanya, hasil staging identik dengan raw pada kolom/baris tersebut.
  3. Tidak ada kolom turunan/fitur hasil kalkulasi yang muncul di layer ini.

## Konteks: Pekerjaan Pra-Milestone

Sebelum breakdown & keputusan ini, dilakukan observability/profiling independen terhadap 23 tabel `raw_production` (`data-profiling-findings.md` di folder ini) — bukan sekadar mempercayai `docs/01-architecture/Metadata.md`. Hasilnya dikategorikan jadi 3 kelompok (Section 6 dokumen itu):
- **Kategori A** (dibersihkan): `employees.department` (19→8), `employees.full_name` (trim), `employees.hire_date` (parse tanggal), `guests.nationality` (case/whitespace), `guests.phone` (4→1 format).
- **Kategori B** (dibiarkan — bermakna/untuk Data Scientist): `guests` 367 duplikat, `guests.full_name` typo, seluruh missing value bermakna (walk-in, absent/leave, dst).
- **Kategori C** (bukan soal bersih/kotor, perlu didokumentasikan): `financial_summary` Corporate Overhead vs Overall, `payroll.thr`/`financial_summary.gop` zero-vs-null, `fnb_transactions.transaction_id` non-unique.

**Klarifikasi penting** (bukan deviasi): sempat ditemukan kontradiksi antara lingkup M2.2 (minta normalisasi telepon) vs "Prinsip Kunci" di `02-serving-data-scientist.md` baris 30 (menyebut "format telepon tidak konsisten" sebagai contoh dirty data yang dipertahankan). Setelah membaca `pemetaan-kebutuhan-konsumen-data-mart.md` (dokumen rujukan RESMI & lebih spesifik untuk M2.2), ternyata dokumen itu eksplisit menyuruh menormalisasi `guests.phone` (baris 46: *"phone: normalisasi 4 variasi format → 1 format standar"*). "Prinsip Kunci" generic sudah usang/kurang presisi dibanding pemetaan detail ini — bukan kontradiksi nyata, keputusan user untuk menormalisasi `phone` **sesuai** dokumen rujukan resmi, bukan berlawanan dengannya.

## Task Breakdown

- [x] Task 1: Setup project dbt-core (`dbt-core`, `dbt-bigquery`) + dataset `staging` di BigQuery — Acceptance: `dbt debug` sukses konek — Verify: `dbt debug` "All checks passed!" — service account baru `dbt-transform` (project-level `bigquery.dataEditor`+`jobUser`, terpisah dari `extract-writer`)
- [x] Task 2: Model dbt `stg_corporate_master__properties`/`role_permissions` (passthrough, view) — Acceptance: row count = raw — Verify: query pembanding — properties 6=6, role_permissions 77=77
- [x] Task 3: Definisikan mapping `employees.department` 19→8 eksplisit — Acceptance: 19 nilai asli termapping ke 8 nilai baku, didokumentasikan — Verify: query `GROUP BY department` langsung ke `raw_production` — **koreksi temuan profiling sebelumnya**: seluruh 19 variasi ternyata murni beda kapitalisasi/whitespace (bukan singkatan/ejaan berbeda seperti diduga) — `LOWER(TRIM())` + mapping 1:1 ke 8 nilai baku (`Corporate`, `F&B`, `Facility`, `Finance`, `Housekeeping`, `HR`, `Revenue`, `Spa&Event`) sudah cukup, tidak perlu fuzzy matching
- [x] Task 4: Model dbt `stg_corporate_master__employees` (trim `full_name`, mapping `department`, parse `hire_date`, preserve null `role_title`) — Acceptance: row count = raw, distinct `department`=8, `hire_date` bertipe DATE — Verify: 755=755, distinct department 19→8, hire_date DATE, role_title null=15 (preserved)
- [x] Task 5: Model dbt `stg_corporate_master__guests` (normalisasi `phone`, `nationality` case/trim, preserve typo/null/duplikat) — Acceptance: row count = raw, distinct format `phone`=1 — Verify: 24893=24893, null phone=750 (preserved), distinct nationality 466→243, phone domestik (4 variasi: `+62 xxx-xxxx-xxx`, `62xxxxxxxxxx`, `0xxx-xxxx-xxx`, `0xxxxxxxxxx`) semua jadi `0xxxxxxxxxx`, nomor asing tidak disentuh. **Bug ditemukan & diperbaiki**: nama CTE sama dengan nama kolom di dalamnya (`phone_normalized`) menyebabkan BigQuery salah resolve jadi STRUCT satu baris penuh alih-alih kolom tunggal -- CTE di-rename `with_phone_normalized`
- [x] Task 6: Model dbt `stg_reservation_revenue__*` (3 tabel, passthrough) — Acceptance: row count = raw — Verify: 217654/19746/19746 semua cocok
- [x] Task 7: Model dbt `stg_fnb_operations__*` (6 tabel, passthrough, `fnb_transactions` didokumentasikan non-unique key) — Acceptance: row count = raw — Verify: 17/120/32910/902574/108733/457 semua cocok
- [x] Task 8: Model dbt `stg_facility_maintenance__*` (3 tabel, passthrough + preserve null) — Acceptance: row count = raw — Verify: 549/425172/13514 semua cocok
- [x] Task 9: Model dbt `stg_spa_event__*` (3 tabel, passthrough) — Acceptance: row count = raw — Verify: 20/127890/1333 semua cocok
- [x] Task 10: Model dbt `stg_hr_finance__*` (4 tabel, passthrough + dokumentasi Kategori C di komentar SQL `payroll`/`financial_summary`) — Acceptance: row count = raw — Verify: 610019/3748/23383/756 semua cocok
- [x] Task 11: Dokumentasi eksplisit "kolom yang sengaja tidak dibersihkan" per tabel — Acceptance: daftar lengkap — Verify: `warehouse/README.md` (11 baris tabel, cross-check Kategori B)
- [x] Task 12: dbt test dasar (`not_null`, `unique`, `accepted_values`) — Acceptance: test jalan — Verify: `dbt test` — **31/31 PASS** (unique+not_null 15 tabel ber-PK tunggal, accepted_values `department`=8 nilai)
- [x] Task 13: Verifikasi Kriteria Keberhasilan + `logs.md`/`report.md` — Acceptance: 3 KK dicek eksplisit — Verify: `report.md`

**Checkpoint** setelah Task 5: validasi pola kerja & tooling dbt di 2 tabel tersulit (`employees`, `guests`) dulu sebelum 18 tabel passthrough lain.

## Technical Decisions

### Decision: Tooling transformasi — dbt-core

- **Context:** Project belum pernah pakai tool transformasi SQL terstruktur. M2.0/M2.1 konsisten memilih opsi ringan (GitHub Actions, custom Python) karena pertimbangan biaya/infra tambahan.
- **Decision:** dbt-core (`dbt-core` + `dbt-bigquery`, dijalankan via CLI, tidak perlu hosting — beda dari alasan penolakan orchestrator penuh di M2.0 yang butuh service 24/7).
- **Alternatives considered:** Custom Python + SQL manual (lanjutkan pola M2.1); Dataform (native GCP, ekosistem lebih kecil); SQLMesh (lebih baru, komunitas lebih kecil).
- **Rejected because:** dbt-core gratis dan strukturnya (staging→marts, test bawaan `not_null`/`unique`/`relationships`/`accepted_values`) persis kebutuhan M2.2 **dan** M2.3 (data quality gate) — custom Python berarti membangun mekanisme test dari nol lagi di M2.3 (pengulangan effort Great Expectations M1.3). Dataform/SQLMesh tidak dipertimbangkan mendalam karena dbt lebih matang & dokumentasinya lebih luas untuk kasus umum seperti ini.

### Decision: Materialisasi staging — view

- **Context:** Insiden M2.1 (partitioning tabel fisik + BigQuery Sandbox mode 60 hari expirasi) menyebabkan kehilangan data sementara.
- **Decision:** Seluruh model staging `materialized: view` di dbt — tidak menyimpan data sendiri, query live ke `raw_production`.
- **Alternatives considered:** Tabel fisik (materialized table).
- **Rejected because:** tabel fisik butuh strategi refresh + risiko berulang soal partition expiration Sandbox mode. View sepenuhnya menghindari kelas masalah itu, dan volume 23 tabel ini tidak cukup besar untuk BigQuery keberatan query live tanpa materialisasi.

### Decision: Dokumentasi temuan Kategori C — cukup di `decisions.md`, tidak update dokumen master

- **Context:** 3 temuan (financial_summary Corporate Overhead vs Overall, payroll/financial_summary zero-vs-null, fnb_transactions key non-unique) tidak tercatat di `Metadata.md`/`pemetaan-kebutuhan-konsumen-data-mart.md`.
- **Decision:** Dicatat di `decisions.md`/`data-profiling-findings.md` milestone ini saja.
- **Alternatives considered:** Juga usulkan koreksi ke `Metadata.md`/`pemetaan-kebutuhan-konsumen-data-mart.md`.
- **Rejected because:** user memilih membatasi scope ke milestone ini untuk saat ini — mengubah dokumen master adalah keputusan terpisah yang bisa direvisit nanti.

### Decision: Normalisasi `nationality` — case/whitespace saja

- **Context:** 466 nilai distinct, 156 grup case-variant (bisa dibereskan `LOWER(TRIM())`), sisanya kemungkinan typo/singkatan yang tidak bisa dinormalisasi via rule sederhana.
- **Decision:** Normalisasi `LOWER(TRIM())` saja, tidak membangun mapping ke daftar negara baku.
- **Alternatives considered:** Mapping menyeluruh ke daftar negara baku (fuzzy matching).
- **Rejected because:** konsisten dengan prinsip "typo tidak diperbaiki via rule" yang sudah berlaku untuk `guests.full_name` (`pemetaan-kebutuhan-konsumen-data-mart.md` baris 46) — dan variasi di luar case/whitespace belum eksplisit dikonfirmasi sebagai dirty data yang harus dibersihkan vs sengaja disuntikkan, jadi tidak dipaksakan.

### Decision: Service account `dbt-transform` terpisah dari `extract-writer`, dengan role project-level

- **Context:** `dbt run` gagal dengan `extract-writer` (scoped ke dataset `raw_production` saja, sesuai keputusan least-privilege M2.1) — dbt-bigquery selalu memanggil create-dataset (idempotent, tapi tetap butuh izin `bigquery.datasets.create` untuk dipanggil sama sekali) sebelum menulis model.
- **Decision:** Service account baru `dbt-transform@nirwana-database-elt.iam.gserviceaccount.com`, dengan `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` di **level project** (bukan scoped ke satu dataset seperti `extract-writer`).
- **Alternatives considered:** Perluas scope `extract-writer` yang sudah ada (grant dataset ACL tambahan per dataset baru); tetap satu service account project-level untuk semua kebutuhan BigQuery.
- **Rejected because:** dbt akan mengelola beberapa dataset ke depannya (`staging` sekarang, `intermediate`/`mart_cleaned` di M2.3) — meminta approve dataset ACL satu-satu tiap kali dbt butuh dataset baru tidak praktis, dan mencampur service account ekstraksi (M2.1, scope sempit by design) dengan service account transformasi (butuh scope lebih luas) melanggar prinsip pemisahan akun per keperluan yang sudah konsisten dipakai project ini (`extract_reader` vs role admin Postgres, `monitoring_api_reader` vs role admin). Trade-off diterima: `dbt-transform` punya akses lebih luas ke BigQuery (bisa buat dataset baru) tapi tetap tidak menyentuh apa pun di luar BigQuery.
- **Catatan:** kedua role grant (project-level) diblokir otomatis oleh classifier keamanan sesi AI, begitu juga pembuatan key file — ketiganya dijalankan manual oleh user, bukan oleh assistant.

### Decision: Jangan set `+schema` di `dbt_project.yml` — cukup `dataset` di `profiles.yml`

- **Context:** Percobaan awal set `+schema: staging` di `dbt_project.yml` (mengira ini cara menentukan nama dataset tujuan) menghasilkan dataset salah bernama `staging_staging` — perilaku default dbt: `generate_schema_name` menggabungkan `<target_schema>_<custom_schema>` kalau model punya `+schema` custom, bukan menggantikannya.
- **Decision:** `profiles.yml` (`dataset: staging`) sudah cukup jadi target schema default. `dbt_project.yml` cukup set `+materialized: view` tanpa `+schema`.
- **Alternatives considered:** Override macro `generate_schema_name` custom di `macros/`.
- **Rejected because:** tidak perlu kerumitan tambahan untuk kasus sederhana (1 schema target untuk seluruh staging) — override macro baru relevan kalau nanti butuh multiple schema custom per grup model.

## Open Questions Resolved with User

- Q: Tooling transformasi? → A: dbt-core.
- Q: Materialisasi staging? → A: View.
- Q: Dokumentasi temuan Kategori C? → A: Cukup di `decisions.md` milestone ini.
- Q: Kedalaman normalisasi `nationality`? → A: Case/whitespace saja.
