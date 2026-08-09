# Milestone 3.3: Index dan Optimasi Performa untuk Pola Akses Analyst — Decisions

**Sumber:** `docs/03-implementation-plans/04-serving-data-analyst.md`, baris 84-101.
**Prasyarat:** Milestone 3.1 (`pemetaan-pola-akses-analyst.md`, filter wajib per peran) dan Milestone 3.2 (48 view `analyst_views`, kolom join per view) — keduanya Completed, jadi acuan langsung kolom kandidat index.
**Status:** In Progress
**Date started:** 2026-08-09

## Lingkup Sumber / Contract

- **Lingkup:** Merancang dan memasang index (termasuk composite index) di PostgreSQL sesuai pola akses nyata Data Analyst — query jarang tapi berat (agregasi rentang waktu panjang, join lintas tabel), beda dari AI Chatbot.
- **Output:** Index/composite index terpasang pada kolom filter/join utama; baseline waktu eksekusi query representatif tiap domain.
- **Kriteria Keberhasilan:**
  1. Query representatif tiap domain berjalan dalam waktu wajar untuk analisis interaktif, diverifikasi `EXPLAIN ANALYZE`.
  2. Index yang dipasang benar-benar terpakai oleh query plan (bukan index yang tidak pernah dipakai).
- **Catatan ketergantungan (dari dokumen sumber):** tabel hasil swap `full refresh + swap table` (M5.5) tidak mewarisi statistik index dari tabel lama — REINDEX/ANALYZE pasca-swap harus konsisten, baseline perlu diperiksa ulang berkala.

## Temuan Eksplorasi (sebelum breakdown)

- **Mekanisme post-swap index sudah ada sebagian.** `scripts/reverse_etl_mart_aggregated/reindex_analyze.py` (M5.5) sudah wired otomatis sebagai step 2 di `.github/workflows/reverse-etl-mart-aggregated.yml`, setelah `sync.py --all` — karena staging table hasil swap RENAME-based tidak mewarisi index sama sekali (bukan cuma statistik basi, index-nya betul-betul tidak ada di tabel baru). `example_indexes.py` isinya 1 entri PROVISIONAL dengan docstring eksplisit "Jangan dianggap sebagai desain index M3.3" — menunggu milestone ini mengisi desain sungguhan.
- **`mart_cleaned` (M2.4) tidak punya mekanisme setara sama sekali** — `reverse-etl-mart-cleaned.yml` cuma `sync.py --all`, tanpa reindex/ANALYZE apa pun.
- **Row count live (dicek langsung serving PostgreSQL) mengonfirmasi `mart_cleaned` justru tabel row-level terbesar**: `fnb_transactions` 902.574, `staff_shifts` 610.019, `bookings` 217.654 — jauh lebih besar dari fact table `mart_aggregated` terbesar (`fact_fnb_menu_item_daily` 289.938). Sample fact table lain: `fact_revenue_room_type_daily` 19.746, `fact_revenue_los_daily` 68.011, `fact_fnb_hourly` 149.346, `fact_housekeeping_staff_daily` 164.707, `fact_maintenance_ticket_daily` 12.840, `fact_maintenance_technician_daily` 12.789, `fact_spa_service_daily` 41.718, `fact_event_venue_daily` 1.333, `fact_hr_attendance_daily` 46.376, `fact_hr_employee_monthly`/`fact_hr_watchlist_monthly` 24.036, `fact_hr_employee_performance_semester` 3.748, `fact_financial_business_line_monthly` 756, `dim_employee` 755.
- Precedent `CREATE INDEX`: selalu `IF NOT EXISTS`, penamaan `idx_<table>_<purpose>`, didorong list Python (bukan file `.sql` mentah) dikonsumsi `reindex_analyze.py`.
- `docs/keputusan-tertunda.md` entri "Otomasi reapply `analyst_views`..." (M5.7) cuma bahas view, tidak menyinggung index — bukan tumpang tindih dengan pekerjaan M3.3.

## Keputusan (via AskUserQuestion, dikonfirmasi user)

### 1. Cakupan: `mart_aggregated` DAN `mart_cleaned`

**Keputusan:** Index dipasang di kedua schema, bukan cuma `mart_aggregated`.

**Kenapa:** Data row count live membuktikan `mart_cleaned` adalah tabel row-level terbesar yang dipakai Data Analyst (902rb/610rb/217rb baris) — jauh lebih besar dari fact table `mart_aggregated` manapun. Query row-level ad-hoc (drill-down, basket analysis) adalah pola akses nyata Data Analyst yang eksplisit dipetakan M3.1 ("dua karakter kebutuhan": agregat via `mart_aggregated`, ad-hoc via `mart_cleaned`), bukan pola sekunder.

**Ditolak:** Hanya `mart_aggregated` (ikut teks literal Output M3.2 "kolom filter/join di view Milestone 3.2", yang cuma dibangun di atas `mart_aggregated`) — lebih cepat selesai tapi meninggalkan tabel terbesar yang dipakai analyst tanpa index/REINDEX pasca-swap sama sekali.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 2. Threshold "layak diindex": data-driven, bukan blanket semua tabel

Tabel kecil (`fact_financial_business_line_monthly` 756 baris, `dim_employee` 755 baris) kemungkinan besar tetap di-seq-scan Postgres meski ada index — memasang index buta di situ berisiko melanggar KK2. Keputusan per tabel dibuat empiris lewat `EXPLAIN ANALYZE` saat eksekusi, didokumentasikan jujur kalau ternyata tidak terpakai — pola disiplin sama dipakai M5.6 (kalibrasi threshold watchlist HR berdasar distribusi riil, bukan angka di atas kertas).

### 3. Kolom kandidat index

"Filter Wajib" per domain dari `pemetaan-pola-akses-analyst.md` (M3.1) + kolom join utama tiap view (M3.2) — bukan menerka ulang pola akses. Composite index: kolom filter entitas (properti/entity) dulu, baru rentang waktu — konsisten contoh Bagian 9.3.2 dokumen arsitektur.

### 4. `mart_aggregated`: isi ulang mekanisme existing

`example_indexes.py` → rename `mart_aggregated_indexes.py` (konsisten `mart_aggregated_tables.py` di folder sama), isi diganti desain sungguhan, docstring PROVISIONAL dihapus. `reindex_analyze.py` cukup update 1 baris import — mekanismenya sudah benar dan sudah wired ke workflow terjadwal.

### 5. `mart_cleaned`: bangun mekanisme kembar dari nol

`scripts/reverse_etl/mart_cleaned_indexes.py` + `scripts/reverse_etl/reindex_analyze.py`, struktur identik `reverse_etl_mart_aggregated` (pola copy-bukan-import lintas `scripts/*` subfolder, konvensi sejak M2.1). Step baru ditambahkan ke `reverse-etl-mart-cleaned.yml` setelah `sync.py --all`.

### 6. Index diterapkan langsung sekarang

Lewat `reindex_analyze.py --all` di kedua schema, bukan menunggu run terjadwal berikutnya — pola sama `apply_views.py` M3.2, diverifikasi terhadap database sungguhan di sesi ini.

### 7. Baseline "sebelum" wajib direkam sebelum index dipasang

`EXPLAIN ANALYZE` tanpa index dicatat lebih dulu di dokumen output — klaim "index mempercepat query" perlu bukti pembanding, bukan cuma "index ada".

### 8. Verifikasi KK2 pakai 2 bukti

(a) `EXPLAIN ANALYZE` menunjukkan node `Index Scan`/`Bitmap Index Scan` (bukan `Seq Scan`); (b) `pg_stat_user_indexes.idx_scan > 0` setelah query representatif dijalankan.

## Task Breakdown

**Kenapa 8 task / 8 checkpoint, bukan pola 9/5 M3.1-M3.2:** Di M3.2, tiap domain punya file SQL terpisah sehingga pairing 2 domain per checkpoint murni pacing di atas unit kerja yang sudah alami terpisah. Di M3.3, desain index 6 domain sama-sama menulis ke 2 file bersama (`mart_aggregated_indexes.py`, `mart_cleaned_indexes.py`) — tidak ada alasan file-level maupun business-coupling untuk memaksa 2 domain jadi 1 checkpoint. Tiap domain independen dan kecil (S), jadi checkpoint per domain memberi granularitas rollback lebih baik. 6 domain adalah fakta struktural project sejak M3.1, bukan angka yang dipilih.

### Fase 0 — Fondasi
1. Bangun `scripts/reverse_etl/{mart_cleaned_indexes.py,reindex_analyze.py}` (clone pola `reverse_etl_mart_aggregated`), tambah step ke `reverse-etl-mart-cleaned.yml`. Rename `example_indexes.py`→`mart_aggregated_indexes.py`, update import — Acceptance: kedua `reindex_analyze.py --all` jalan tanpa error — Verify: `ANALYZE` sukses di kedua schema — S

**✅ Checkpoint 1** — commit + log.

### Fase 1 — Revenue
2. Index `fact_revenue_*` (mart_aggregated) + `bookings`/`pricing_history` (mart_cleaned). Baseline EXPLAIN ANALYZE → pasang → verifikasi — M

**✅ Checkpoint 2** — commit + log.

### Fase 2 — F&B
3. Index `fact_fnb_*` + `fnb_transactions` (902rb baris, tabel terbesar project) — M

**✅ Checkpoint 3** — commit + log.

### Fase 3 — Facility/Ops
4. Index `fact_maintenance_*`/`fact_housekeeping_*` + `maintenance_tickets` — M

**✅ Checkpoint 4** — commit + log.

### Fase 4 — Spa & Event
5. Index `fact_spa_*`/`fact_event_*` + `event_bookings` — S

**✅ Checkpoint 5** — commit + log.

### Fase 5 — HR
6. Index `fact_hr_*` + `dim_employee.property_id`/`department_id` + `staff_shifts`/`employee_performance` — M

**✅ Checkpoint 6** — commit + log.

### Fase 6 — Corporate/Financial
7. Index `fact_financial_business_line_monthly` (uji empiris, 756 baris) + `financial_summary`/`payroll`. Validasi business rule filter `Overall` exclusion tidak berubah perilaku — M

**✅ Checkpoint 7** — commit + log.

### Fase 7 — Finalisasi
8. Tulis `docs/08-serving-data-analyst/index-baseline-analyst.md` + `report.md`, verifikasi KK1+KK2 lintas domain — M

**✅ Checkpoint 8 (final)** — commit; tanya user sebelum push.
