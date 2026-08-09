# Milestone 3.1: Pemetaan Pola Akses per Peran Analyst — Report

**Status:** Completed
**Date completed:** 2026-08-09

## Kriteria Keberhasilan — Hasil

- [x] **Setiap 6 pola peran (plus Property/GM Analyst sebagai union) punya pemetaan akses yang jelas dan bisa langsung dipakai sebagai acuan Milestone 3.2 tanpa perlu membuka ulang dokumen kebutuhan dari nol.** — Terpenuhi. `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md` berisi 7 baris pemetaan (Revenue, F&B, Facility/Ops, Spa & Event, HR, Corporate/Financial, Property/GM Analyst sebagai union #1-5), masing-masing dengan skema kolom lengkap: cakupan properti, tabel `mart_aggregated` (fact+dim aktual, bukan naratif), tabel `mart_cleaned` row-level, filter wajib, business rule kritis terkait, dan catatan gap data sumber. Seluruh referensi nama tabel diverifikasi langsung terhadap `DataSchema-mart-aggregated.md` (skema pasca-koreksi M5.3), bukan draft M5.1 yang sudah diketahui punya beberapa grain salah — sehingga pemetaan ini akurat terhadap skema yang benar-benar diimplementasikan dan bisa langsung dipakai Milestone 3.2 tanpa verifikasi ulang ke dokumen kebutuhan asli.

## Deliverables

- `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md` — dokumen pemetaan utama: tabel referensi domain→fact/dim table, 7 baris pemetaan peran, dan daftar 12 business rule kritis terkonsolidasi.
- `milestones/3.1-pemetaan-pola-akses-analyst/{decisions,logs}.md`.

## Business Rule Kritis Terkonsolidasi (ringkasan)

12 rule dicatat eksplisit (daftar lengkap di dokumen utama), 3 yang paling berisiko tinggi bila terlewat di Milestone 3.2:
1. Filter `business_line_id IN ('Room','F&B','Spa&Event')` untuk departmental margin — exclude `Overall`/`Corporate Overhead` (risiko double counting, ditandai sejak M5.1).
2. Payroll eksklusif Corporate/Financial Analyst — HR Analyst dan Property/GM Analyst dilarang akses (segregation of duties).
3. `property_id` wajib tanpa pengecualian untuk Property/GM Analyst, plus larangan akses tabel level-grup (`fact_financial_business_line_group_monthly`) dan seluruh Corporate/Financial.

Selain itu, 2 pasang metrik ditandai **dilarang** dibangun sebagai metrik otomatis di layer manapun (bukan sekadar gap data yang bisa ditambal nanti): basket analysis F&B (harus row-level `mart_cleaned`), dan repeat-client-event/cross-sell spa×event (data sumber tidak andal untuk deteksi otomatis — `client_name` teks bebas, tidak ada `guest_id` penghubung).

## Deviations from decisions.md

Tidak ada deviasi. Seluruh 5 keputusan teknis di `decisions.md` diikuti persis: lokasi output (`docs/08-serving-data-analyst/`), skema kolom pemetaan, metode pembacaan langsung tanpa sub-agent, `DataSchema-mart-aggregated.md` sebagai sumber kebenaran, dan penamaan tabel `mart_cleaned` dengan nama produksi asli.

## Known Gaps / Follow-ups

- **Status implementasi `fact_revenue_pace_booking_snapshot` belum dikonfirmasi ulang** — tabel ini terdaftar di skema `DataSchema-mart-aggregated.md` dengan catatan append-only vs constraint BigQuery Sandbox (DML diblokir) yang belum final per dokumen itu sendiri. Milestone 3.2 (view/query pattern) perlu mengecek status aktualnya di BigQuery/serving PostgreSQL sebelum membangun view di atasnya — di luar cakupan M3.1 untuk memverifikasi status implementasi tabel lain.
- **Threshold early-warning HR (selain `in_watchlist`)** masih terbuka per arsitektur §10 No. 3 — M3.1 hanya mencatat bahwa metrik dasarnya tersedia, kalibrasi threshold lain (jika ada yang dibutuhkan Milestone 3.4) tetap perlu jalur pengajuan terpisah, bukan diasumsikan siap pakai.
- **Filtering akses granular performa individu staff Facility** (housekeeping/maintenance) didelegasikan eksplisit ke Milestone 3.4 (API)/3.5 (kredensial) — M3.1 hanya menandai sensitivitasnya, belum mendesain mekanisme kontrolnya.
- **`fact_ml_occupancy_forecast_property_room_type`** dikonfirmasi tidak tersedia di serving PostgreSQL (belum di-sync M5.5) — dicatat sebagai flag agar Milestone 3.2-3.4 tidak keliru mengasumsikan tabel ini bisa diakses lewat jalur PostgreSQL manapun.

## Handoff Notes

- **Milestone 3.2 (View dan Query Pattern per Domain):** pakai `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md` sebagai acuan langsung — 1 kelompok view per baris pemetaan (6 domain + union Property/GM), dengan seluruh 12 business rule kritis di bagian akhir dokumen wajib tertanam di view (bukan diserahkan ke pemakai), sesuai Kriteria Keberhasilan M3.2 sendiri ("percobaan query tanpa filter eksplisit tetap menghasilkan output yang benar").
- **Milestone 3.3 (Index):** kolom filter wajib per peran (`property_id`, `department_id`, `business_line_id`, dst) di dokumen ini adalah kandidat utama index/composite index — sudah tersedia tanpa perlu re-analisis pola akses dari nol.
- **Milestone 3.5 (Isolasi Akses):** business rule #2 dan #3 (payroll exclusive, financial_summary grup di luar Property/GM) adalah kandidat langsung untuk desain role/kredensial read-only per kelompok peran — memetakan 1:1 ke kebutuhan isolasi yang diminta Kriteria Keberhasilan M3.5 ("HR Analyst tidak bisa mengakses payroll").
- **Jika ditemukan kebutuhan agregasi yang belum tercakup** saat mengerjakan M3.2 (mis. metrik yang ternyata butuh fact table baru), jalurnya adalah mekanisme pengajuan Milestone 5.6 (`docs/07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md`), bukan membangun agregasi versi sendiri di layer ini — ditegaskan ulang di `04-serving-data-analyst.md` Catatan Serah Terima.
