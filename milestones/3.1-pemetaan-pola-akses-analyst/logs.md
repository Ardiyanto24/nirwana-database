# Milestone 3.1: Pemetaan Pola Akses per Peran Analyst — Logs

## 2026-08-09 — Mulai kerja

- Plan disetujui via Plan Mode. `decisions.md` ditulis, mengunci 5 keputusan teknis (lokasi output, skema kolom, metode kerja, sumber kebenaran skema, penamaan mart_cleaned).
- Folder dibuat: `milestones/3.1-pemetaan-pola-akses-analyst/`, `docs/08-serving-data-analyst/`.
- Mulai Task 1 (Fase 0 — setup output doc + tabel referensi).

## 2026-08-09 — Checkpoint 1

- `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md` dibuat dengan skeleton skema kolom + tabel referensi domain → fact/dim table, diekstrak dari `DataSchema-mart-aggregated.md` (6 domain + lintas-domain + catatan `fact_ml_occupancy_forecast_property_room_type` provisional yang belum sync ke serving PostgreSQL).
- Verifikasi: jumlah fact table per domain di tabel referensi ditelusuri langsung per section `DataSchema-mart-aggregated.md` (Revenue 8+1 khusus, F&B 8, Facility 9, Spa&Event 6, HR 7+1 khusus, Corporate/Financial 9) — cocok dengan pengelompokan dokumen sumber.
- Commit: `9438509`.

## 2026-08-09 — Checkpoint 2

- Pemetaan Revenue Analyst (§1.3) dan F&B Analyst (§2.3) ditulis ke `pemetaan-pola-akses-analyst.md`.
- Temuan business rule kritis: (1) `fact_revenue_pace_booking_snapshot` append-only, status implementasi vs BigQuery Sandbox DML block belum final — ditandai perlu dicek ulang sebelum dipakai M3.2; (2) F&B basket analysis wajib row-level `mart_cleaned.fnb_transactions`, tidak bisa direkonstruksi dari fact table manapun (grain struk hilang total di agregat).
- Verifikasi: 11 metrik §1.3 (Revenue) dan seluruh metrik §2.3 (F&B) tertelusuri ke fact table yang sesuai; 2 gap data sumber per domain tercatat di kolom Catatan Gap.
