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

## 2026-08-09 — Checkpoint 3

- Pemetaan Facility/Ops Analyst (§3.3) dan Spa & Event Analyst (§4.3) ditulis.
- Business rule kritis baru: (1) `pending_count` SLA Facility wajib terpisah dari breach rate; (2) performa individu staff Facility ditandai sensitif meski label RBAC domain "Rendah" — filtering akses granular didelegasikan ke M3.4/3.5; (3) repeat client event dan cross-sell spa×event **dilarang** dibangun sebagai metrik otomatis (bukan cuma "gap data" tapi larangan eksplisit karena datanya tidak andal untuk deteksi otomatis).
- Verifikasi: seluruh metrik §3.3 dan §4.3.1/§4.3.2 tertelusuri ke fact table yang sesuai.

## 2026-08-09 — Checkpoint 4

- Pemetaan HR Analyst (§5.3) dan Corporate/Financial Analyst (§6.3) ditulis.
- Business rule kritis terpenting di seluruh dokumen dicatat di sini: filter `business_line_id IN ('Room','F&B','Spa&Event')` untuk departmental margin (exclude `Overall`), `fact_financial_overall_monthly` khusus GOP/overhead, payroll exclusive Corporate/Financial (HR dilarang akses), koherensi check adalah kebutuhan DQ bukan metrik analitik biasa, dan `undistributed_expense_total` cuma 1 kolom (tidak ada breakdown komponen).
- Verifikasi: seluruh metrik §5.3 dan §6.3 tertelusuri ke fact table yang sesuai.

## 2026-08-09 — Checkpoint 5 (final) — Tutup milestone

- Pemetaan Property/GM Analyst (union peran #1-5, tanpa Corporate/Financial, filter `property_id` wajib tanpa pengecualian) ditulis.
- Daftar 12 business rule kritis dikonsolidasikan dari seluruh 7 baris pemetaan ke satu section akhir dokumen.
- Kriteria Keberhasilan tunggal Milestone 3.1 diverifikasi terpenuhi — lihat `report.md`.
- Milestone ditutup. Handoff eksplisit ke M3.2 (pakai dokumen ini langsung sebagai acuan view), M3.3 (kolom filter wajib = kandidat index), M3.5 (business rule payroll/financial_summary grup = kandidat desain kredensial).
