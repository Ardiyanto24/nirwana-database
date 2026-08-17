# Referensi Teknis Nirwana Data Platform

Folder `docs/` adalah Level 3 dokumentasi: rujukan teknis yang menjelaskan kontrak sistem, batas desain, kebutuhan consumer, dan keputusan yang tetap berlaku. Gunakan [System Guides](guides/README.md) untuk alur baca naratif; gunakan halaman ini ketika perlu menelusuri detail hingga dokumen sumber.

## Cara menentukan sumber yang berwenang

| Pertanyaan | Sumber pertama | Sumber pendukung |
| --- | --- | --- |
| Sistem ini seharusnya bekerja seperti apa? | [Arsitektur ELT](01-architecture/rancangan-arsitektur-data-platform-elt.md) | requirements dan implementation plan terkait |
| Apa arti data dan pola nilainya? | [Metadata](01-architecture/Metadata.md) | [DataSchema](01-architecture/DataSchema.md) |
| Apa kebutuhan consumer dan boundary aksesnya? | `02-requirements/` | serving reference pada `08-` atau `09-` |
| Apa yang benar-benar terjadi saat implementasi? | [Milestone records](../milestones/README.md) | source code dan workflow terkait |
| Apakah sebuah gap memang belum diputuskan? | [Keputusan Tertunda](keputusan-tertunda.md) | report milestone yang menemukan gap |

Jika rancangan awal dan laporan milestone berbeda, perlakukan laporan milestone serta implementasi yang dirujuknya sebagai keadaan **as-built**. Rancangan awal tetap penting untuk memahami tujuan dan alasan perubahan.

## Peta referensi berdasarkan area

### 01 — Arsitektur dan data sumber

- [Rancangan Arsitektur Data Platform ELT](01-architecture/rancangan-arsitektur-data-platform-elt.md) — alur dari production hingga consumer, beserta keputusan lintas layer.
- [Metadata](01-architecture/Metadata.md) — data dictionary dan nilai yang bermakna.
- [DataSchema](01-architecture/DataSchema.md) — sejarah skema dan rationale pola data sintetis.
- [Diagram database](01-architecture/database_architecture.mmd) — visual model database sumber.

### 02 — Kebutuhan consumer dan RBAC

- [Kebutuhan Data Scientist / `mart_cleaned`](02-requirements/pemetaan-kebutuhan-konsumen-data-mart.md)
- [Kebutuhan Data Analyst](02-requirements/pemetaan-kebutuhan-data-analyst.md)
- [Rancangan RBAC AI Chatbot](02-requirements/rancangan-rbac-ai-chatbot.md)
- [Kebutuhan Chatbot layer Staff](02-requirements/pemetaan-kebutuhan-chatbot-layer-staff.md), [Manager](02-requirements/pemetaan-kebutuhan-chatbot-layer-manager.md), dan [Korporat](02-requirements/pemetaan-kebutuhan-chatbot-layer-korporat.md)

### 03–06 — Kontrak implementasi, monitoring awal, dan akses

- [Implementation plans](03-implementation-plans/) — lingkup dan kriteria keberhasilan tiap keluarga milestone.
- [Baseline monitoring produksi](04-monitoring/baseline-inventaris-produksi.md) — prioritas dan karakteristik 23 tabel sumber.
- [Konvensi dependency orchestrator](05-orchestrator/konvensi-job-dependency.md) — pola `needs` dan `workflow_run`.
- [Kebijakan kredensial scoped](06-akses-kredensial/kebijakan-akses-kredensial-scoped.md) — inventory credential, pemberian, rotasi, dan revokasi.

### 07 — `mart_aggregated`

- [Konsolidasi kebutuhan agregasi](07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md)
- [Data schema](07-mart-aggregated/DataSchema-mart-aggregated.md) dan [metadata](07-mart-aggregated/Metadata-mart-aggregated.md)
- [ERD](07-mart-aggregated/ERD-mart-aggregated.md)
- [Mekanisme pengajuan perubahan](07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md) dan [backlog perubahan](07-mart-aggregated/pengajuan-perubahan-cakupan.md)

### 08–09 — Serving consumer

- [Serving Data Analyst](08-serving-data-analyst/) — access mapping, views, index, API, BI, dan credential.
- [Serving AI Chatbot](09-serving-ai-chatbot/) — access mapping, view contract, credential, API, audit, dan rancangan pengujian RBAC.

### 10 — Monitoring warehouse dan serving

- [Pemetaan titik pengamatan pipeline](10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md) — titik observasi, dependency, dan prioritas sinyal.

## Referensi implementasi langsung

| Jika ingin memeriksa… | Mulai dari |
| --- | --- |
| keputusan, event, dan hasil per tahap | [milestones/README.md](../milestones/README.md) |
| source code operasional | [scripts/README.md](../scripts/README.md) |
| warehouse dbt dan test | [warehouse/README.md](../warehouse/README.md) |
| jadwal dan dependency pipeline | [.github/workflows/README.md](../.github/workflows/README.md) |

## Batas referensi

Dokumen Level 3 berisi detail yang dapat berubah bersama sistem. Jangan menyalin isinya ke Level 1 atau Level 2. Jika sebuah konsep perlu diperkenalkan di sana, tautkan ke sumber ini dan pertahankan detail normatifnya di satu lokasi.
