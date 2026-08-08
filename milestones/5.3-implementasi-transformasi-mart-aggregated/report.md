# Milestone 5.3: Implementasi Transformasi Mart Aggregated — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Seluruh tabel `mart_aggregated` terisi dan dapat diquery di BigQuery, dengan hasil yang tervalidasi cocok terhadap perhitungan manual/sampel dari `mart_cleaned` untuk beberapa metrik kunci.** — Terpenuhi. Seluruh 76 tabel (27 dimension + 49 fact table) berhasil di-build via dbt dan dipromosikan lewat `scripts/mart_aggregated/promote.py` ke dataset `mart_aggregated` yang sebelumnya belum ada (dibuat sekali sebagai bagian Checkpoint 8). 6 metrik representatif (1 per domain) divalidasi manual terhadap `mart_cleaned` langsung via BigQuery client — **6/6 cocok persis**: occupancy_rate Revenue (0.4762=0.4762), total revenue F&B (Rp98.370.508.260=Rp98.370.508.260), total ticket count Facility/Ops (13.514=13.514), total revenue Spa & Event (Rp76.728.937.061=Rp76.728.937.061), total present_count HR (531.751=531.751), total GOP Corporate/Financial (Rp330.502.531.389=Rp330.502.531.389).
- [x] **Data quality gate berhasil menangkap pelanggaran business rule pada uji coba terkontrol.** — Terpenuhi. Singular test `warehouse/tests/assert_gop_no_double_counting.sql` ditulis mengecek `gop_margin_pct` (bukan `gop` mentah — `gop` ternyata sudah "terlindungi" struktural karena cuma non-zero di baris Overall/Corporate Overhead, dikonfirmasi via query agregat). Uji coba terkontrol: filter `WHERE department IN (...)` sengaja dihapus dari `fact_financial_overall_monthly` (simulasi bug double-counting), rebuild, test **FAIL 180 baris** — terbukti gate menangkap. Model direvert ke versi benar, rebuild, test **PASS** lagi. Total 176 dbt test (schema: unique/not_null/relationships/accepted_values) + 1 singular test lolos 100% sebelum promosi ke `mart_aggregated`.
- [x] **Kolom yang sudah diputuskan untuk di-mask/dianonimkan pada Milestone 5.2 terbukti benar-benar termask di hasil akhir — bukan diteruskan apa adanya karena terlewat saat implementasi.** — Terpenuhi. Keputusan M5.2: tidak ada kolom yang butuh masking (desain star schema teragregasi tidak pernah memuat guest PII mentah); satu-satunya data personal (`dim_employee.full_name`) diputuskan diteruskan apa adanya. Diverifikasi ulang terhadap hasil akhir via query `INFORMATION_SCHEMA.COLUMNS` pada dataset `mart_aggregated` yang sudah live — hasil cuma 1 baris (`dim_employee.full_name`), **tidak ada** kolom `email`/`phone`/`guest_id` yang tidak sengaja bocor di 76 tabel manapun. Keputusan M5.2 terbukti terimplementasi persis sesuai rencana.

## Deliverables

- 76 model dbt baru: 27 dimension table + 49 fact table di `warehouse/models/mart_aggregated/{corporate_master,reservation_revenue,fnb_operations,facility_maintenance,spa_event,hr_finance/{hr,corporate_financial}}/` (struktur folder hybrid, Keputusan #2).
- 244 dbt test (`_*_tests.yml` per folder) + 1 singular test (`warehouse/tests/assert_gop_no_double_counting.sql`).
- `scripts/mart_aggregated/promote.py` — DQ gate build→test→swap, pola sama `mart_cleaned`.
- Dataset BigQuery `mart_aggregated` (baru, disediakan sebagai bagian pekerjaan ini) — 76 tabel live, teruji.
- `docs/07-mart-aggregated/DataSchema-mart-aggregated.md` (rename dari M5.2, referensi diperbarui + 8 catatan koreksi grain), `Metadata-mart-aggregated.md` (baru — data dictionary penuh), `ERD-mart-aggregated.md` + `ERD-mart-aggregated.mmd` (baru — 1 diagram Mermaid, 76 entitas, disediakan 2 format: markdown untuk dibaca di GitHub/browser, `.mmd` murni untuk tool Mermaid).
- `docs/keputusan-tertunda.md` — entri "Data dictionary/metadata kolom mart_aggregated" ditutup Resolved.
- `milestones/5.3-implementasi-transformasi-mart-aggregated/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada deviasi pada 9 keputusan inti `decisions.md`. **Banyak koreksi teknis wajar muncul saat implementasi** (skema desain M5.2 ditulis di atas kertas sebelum ada akses langsung ke skema BigQuery aktual) — seluruhnya didokumentasikan eksplisit di `DataSchema-mart-aggregated.md` dan `logs.md` per checkpoint, bukan diperbaiki diam-diam:
- **Grain mismatch** (5 kasus): `fact_revenue_daily` dipecah jadi 4 tabel presisi-grain (`daily_occupancy` ternyata tidak punya kolom channel); `gop_pricing_impact` dipisah ke tabel bulanan (`financial_summary` grain bulanan, bukan harian); performa HR dipindah ke 3 tabel semester (`employee_performance.review_period` grain semesteran, bukan bulanan); `fact_financial_service_charge_daily` dikoreksi jadi bulanan (`payroll.period` grain bulanan).
- **Sumber tidak sesuai asumsi** (4 kasus): `dim_ingredient` tidak punya kolom nama terpisah; `rooms`/`fnb_inventory`/`employees` (untuk turnover) semuanya current-state tanpa kolom tanggal — 3 tabel jadi snapshot, bukan deret waktu; `undistributed_expense` cuma 1 kolom total, tidak ada breakdown 5-komponen sama sekali di skema sumber manapun (gap yang seharusnya tertangkap di M5.1, baru ketahuan sekarang).
- **Kolom "korelasi" 1-baris tidak bermakna** (3 kasus): `gop_pricing_impact`, `delayed_rate_vs_occupancy`, `deviation_from_correlation` — semuanya dipecah jadi 2 kolom nilai mentah terpisah, bukan 1 kolom "dampak/korelasi" yang tidak bisa dihitung benar dari 1 baris.
- **Simplifikasi terukur** (1 kasus): `low_utilization_streak_days` disederhanakan jadi rolling count 30 hari (bukan consecutive-day streak eksak) — gaps-and-islands di luar cakupan waktu M5.3.

## Known Gaps / Follow-ups

- **`undistributed_expense` breakdown per komponen tidak tersedia sama sekali** dari skema sumber (`financial_summary` cuma 1 kolom total) — bukan keterbatasan implementasi M5.3, murni gap data sumber yang seharusnya sudah ditandai di M5.1. Direkomendasikan ke pemilik sistem produksi untuk dipertimbangkan penambahan kolom breakdown jika metrik ini dianggap penting.
- **`fact_revenue_pace_booking_snapshot` kosong (0 baris) untuk saat ini** — dataset sintetis project ini statis (rentang tetap sampai 2026-07-01), sementara tanggal berjalan (`CURRENT_DATE()` BigQuery) sudah melewati itu. Bukan bug (konsisten karakteristik "freshness lag" yang sudah didokumentasikan project-wide di `CLAUDE.md`), tapi konsumen (M5.4/M04/M05) perlu tahu tabel ini akan tetap kosong sampai dataset sumber diperbarui atau workflow terjadwal menghasilkan data baru yang genuinely di masa depan relatif ke hari eksekusi.
- **Threshold SLA breach dan watchlist HR masih belum diputuskan** — kolom nilai mentah sudah tersedia (`avg_sla_duration_hours`, `absence_deviation_ratio`, dll), tapi klasifikasi breach/watchlist final butuh keputusan bisnis terpisah (diwariskan dari M5.1/M5.2). **Update Milestone 5.6 (2026-08-08): threshold watchlist HR diselesaikan** — kolom `in_watchlist` ditambahkan ke `fact_hr_watchlist_monthly` lewat siklus pengajuan-evaluasi-tindak lanjut, lihat `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md`. Threshold SLA breach Facility/Ops masih terbuka (belum diajukan).
- **`low_utilization_days_last_30`** adalah pendekatan rolling-count, bukan consecutive-streak eksak — cukup untuk kebutuhan "deteksi berulang" tapi tidak identik dengan makna literal "streak".
- **Aturan kategorisasi `nationality`** (Domestik/Mancanegara) sudah diimplementasi (`nationality='Indonesia'` → Domestik) tapi ini aturan sederhana yang diwariskan dari catatan M5.1 — belum diformalkan lewat proses keputusan bisnis terpisah.

## Handoff Notes

- **Milestone 5.4 (Feedback Loop ML)**: `fact_revenue_pace_booking_snapshot` yang kosong perlu diperhitungkan kalau ada model yang bergantung padanya — cek dulu apakah tabel ini punya data sebelum diasumsikan berguna untuk fitur ML apa pun.
- **Milestone 5.5 (Reverse ETL) dan Milestone 04/05 (serving)**: `docs/07-mart-aggregated/Metadata-mart-aggregated.md` adalah rujukan utama untuk memahami arti tiap kolom sebelum membangun view/API di atasnya — terutama 3 catatan penting Corporate/Financial (disambiguasi `dim_department` vs `dim_business_line`, aturan Overall/Corporate Overhead, gap `undistributed_expense`) yang berisiko disalahpahami tanpa membaca dokumen itu dulu.
- **PII sudah aman by design** — tidak ada `guests_pii` di `mart_aggregated` manapun, tapi `dim_employee.full_name` (`employees_directory`) tetap butuh RBAC layer (Milestone 4.1-4.3) untuk kontrol akses granular, belum diimplementasikan di sini.
- **Dataset `mart_aggregated`** perlu ikut proses `renew_expiration.py` di workflow terjadwal (Sandbox mode, 60 hari) — belum ditambahkan ke `.github/workflows/` karena scope M5.3 murni transformasi, bukan orchestration (kemungkinan scope Milestone 5.4/06 monitoring).
