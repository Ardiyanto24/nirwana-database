# Rekam Implementasi per Milestone

Folder ini adalah catatan kejadian Level 3 untuk setiap milestone. Ia menjawab pertanyaan **apa yang benar-benar dikerjakan, keputusan apa yang dibuat saat itu, bagaimana hasilnya diverifikasi, dan gap apa yang masih tersisa**.

## Struktur setiap milestone

Setiap folder milestone menggunakan tiga artefak yang saling melengkapi:

| Artefak | Fungsi | Waktu dibaca |
| --- | --- | --- |
| `decisions.md` | konteks teknis, alternatif, dan batas scope | saat memahami *mengapa* implementasi berbentuk demikian |
| `logs.md` | jurnal peristiwa, temuan, error, dan checkpoint | saat melacak urutan kerja atau diagnosis |
| `report.md` | hasil akhir terhadap kriteria keberhasilan, known gap, dan handoff | sebagai sumber pertama untuk status aktual |

Jangan menyimpulkan milestone selesai hanya dari keberadaan source code. Bila ada `decisions.md` dan `logs.md` tanpa `report.md`, pekerjaan tersebut belum memiliki closure formal.

## Urutan pembacaan yang disarankan

1. Baca `report.md` untuk mengetahui status, bukti, dan gap.
2. Baca `decisions.md` untuk alasan desain yang tidak terlihat dari source code.
3. Baca `logs.md` bila perlu merekonstruksi temuan atau perubahan arah.
4. Ikuti cross-reference ke dokumen teknis dan implementasi yang disebutkan.

## Indeks milestone

### Fase 1 — Monitoring data produksi

| Milestone | Fokus | Referensi hasil |
| --- | --- | --- |
| 1.1 | inventaris baseline dan prioritas data produksi | [report](1.1-inventarisasi-baseline-produksi/report.md) |
| 1.2 | snapshot volume dan freshness | [report](1.2-monitoring-volume-freshness/report.md) |
| 1.3 | data quality dan value anomaly | [report](1.3-kualitas-data-anomali/report.md) |
| 1.4 | schema drift | [report](1.4-monitoring-schema-drift/report.md) |
| 1.5 | dashboard dan alerting awal | [report](1.5-dashboard-alerting-terpadu/report.md) |
| 1.6 | API monitoring read-only | [report](1.6-public-monitoring-api/report.md) |
| 1.7 | web monitoring | belum memiliki `report.md`; periksa `decisions.md` dan `logs.md` untuk status terbaru |

### Fase 2 — Warehouse, `mart_cleaned`, dan akses Data Scientist

| Milestone | Fokus | Referensi hasil |
| --- | --- | --- |
| 2.0 | fondasi orchestrator bersama | [report](2.0-fondasi-orchestrator-bersama/report.md) |
| 2.1 | extraction production ke raw warehouse | [report](2.1-extraction-production-raw-warehouse/report.md) |
| 2.2 | staging dan cleaning per tabel | [report](2.2-layer-staging-cleaning-per-tabel/report.md) |
| 2.3 | `mart_cleaned` dan promotion gate | [report](2.3-layer-intermediate-mart-cleaned/report.md) |
| 2.4 | reverse ETL ke PostgreSQL serving | [report](2.4-reverse-etl-postgresql/report.md) |
| 2.5 | akses Data Scientist | [report](2.5-api-akses-data-scientist/report.md) |
| 2.6 | isolasi dan kebijakan kredensial | [report](2.6-isolasi-akses-kredensial-read-only/report.md) |

### Fase 3 — Serving Data Analyst

| Milestone | Fokus | Referensi hasil |
| --- | --- | --- |
| 3.1 | pemetaan pola akses analyst | [report](3.1-pemetaan-pola-akses-analyst/report.md) |
| 3.2 | views dan query pattern | [report](3.2-view-dan-query-pattern-per-domain/report.md) |
| 3.3 | index dan baseline performa | [report](3.3-index-optimasi-performa-analyst/report.md) |
| 3.4 | API per domain | [report](3.4-multi-endpoint-api-analyst/report.md) |
| 3.5 | isolasi role PostgreSQL | [report](3.5-isolasi-akses-kredensial-analyst/report.md) |
| 3.6 | akses BigQuery melalui BI tool | [report](3.6-akses-bigquery-bi-tool/report.md) — partially completed; integrasi GUI BI belum diverifikasi |

### Fase 4 — Boundary akses AI Chatbot

| Milestone | Fokus | Referensi hasil |
| --- | --- | --- |
| 4.1 | pemetaan RBAC ke struktur data | [report](4.1-pemetaan-rbac-struktur-akses-teknis/report.md) |
| 4.2 | view granular per domain | [report](4.2-view-akses-granular-per-domain/report.md) |
| 4.3 | kredensial read-only per domain | [report](4.3-kredensial-read-only-per-kelompok-akses/report.md) |
| 4.4 | query API dan authorization boundary | [report](4.4-api-query-interface-chatbot/report.md) |
| 4.5 | audit log query | [report](4.5-audit-log-query-chatbot/report.md) |
| 4.6 | verifikasi ketahanan RBAC | [report](4.6-uji-ketahanan-rbac-lintas-persona/report.md) |

### Fase 5 — `mart_aggregated` dan feedback loop ML

| Milestone | Fokus | Referensi hasil |
| --- | --- | --- |
| 5.1 | konsolidasi kebutuhan agregasi | [report](5.1-konsolidasi-rasionalisasi-kebutuhan-agregasi/report.md) |
| 5.2 | desain star schema | [report](5.2-desain-struktur-tabel-mart-aggregated/report.md) |
| 5.3 | implementasi dan promotion mart | [report](5.3-implementasi-transformasi-mart-aggregated/report.md) |
| 5.4 | feedback loop ML provisional | [report](5.4-integrasi-feedback-loop-ml/report.md) |
| 5.5 | reverse ETL `mart_aggregated` | [report](5.5-reverse-etl-mart-aggregated/report.md) |
| 5.6 | mekanisme pengajuan perubahan | [report](5.6-mekanisme-pengajuan-perubahan-cakupan/report.md) |
| 5.7 | perubahan `dim_employee.property_id` | [report](5.7-perubahan-cakupan-dim-employee-property-id/report.md) |

### Fase 6 — Monitoring warehouse dan serving

| Milestone | Fokus | Referensi hasil |
| --- | --- | --- |
| 6.1 | inventaris titik pengamatan | [report](6.1-inventarisasi-titik-pengamatan/report.md) |
| 6.2 | monitoring log proses pipeline | [report](6.2-monitoring-log-proses-pipeline/report.md) |
| 6.3 | kesalahan dan anomali warehouse | [report](6.3-monitoring-kesalahan-anomali-warehouse/report.md) |
| 6.4 | health feedback loop ML | [report](6.4-monitoring-drift-feedback-loop-ml/report.md) |
| 6.5 | performa query Chatbot | [report](6.5-monitoring-performa-query-chatbot/report.md) |
| 6.6 | kesehatan reverse ETL dan serving | [report](6.6-monitoring-reverse-etl-serving-layer/report.md) |
| 6.7 | dashboard dan root-cause alerting | [report](6.7-dashboard-alerting-terpadu/report.md) |

## Hubungan dengan dokumentasi lain

- [Referensi teknis `docs/`](../docs/README.md) menjelaskan kontrak sistem yang relatif stabil.
- [System Guides](../docs/guides/README.md) menjelaskan narasi lintas komponen dan keputusan utama.
- [Script catalog](../scripts/README.md) mengarahkan ke implementasi operasional.
- [Workflow catalog](../.github/workflows/README.md) menjelaskan bagaimana proses dijalankan dan dihubungkan.
