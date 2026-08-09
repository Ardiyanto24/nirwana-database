# Metadata & Data Dictionary — `mart_aggregated`

**Nirwana Hospitality Group — Data Platform ELT**

> **Tujuan dokumen ini**: sumber kebenaran tunggal tentang arti setiap kolom di `mart_aggregated` — cara hitung, unit, dan nuansa penting yang tidak terlihat dari nama kolom saja. Ditulis **setelah** implementasi Milestone 5.3 selesai dan teruji (Keputusan #8 `milestones/5.3-.../decisions.md`), mendeskripsikan skema yang sudah nyata berjalan — beda dari `DataSchema-mart-aggregated.md` (M5.2) yang mendokumentasikan struktur/keputusan desain sebelum diimplementasikan.
>
> Dokumen pendamping: `DataSchema-mart-aggregated.md` (struktur tabel, FK, partition/cluster), `ERD-mart-aggregated.md` (diagram relasi visual), `konsolidasi-agregasi-mart-aggregated.md` (M5.1, requirement asal tiap metrik).

---

## Konteks

`mart_aggregated` adalah lapisan BigQuery hasil agregasi dari `mart_cleaned`, dibangun via dbt (`warehouse/models/mart_aggregated/`), dipromosikan lewat `scripts/mart_aggregated/promote.py` (build → test → swap, gate DQ blocking — data yang gagal test tidak pernah terlihat di dataset final). Skema: **star schema** — 27 dimension table (conformed, dipakai lintas domain) + 49 fact table (dikelompokkan per domain bisnis dan grain).

**Grain waktu**: mayoritas fact table berkolom `period_date` (DATE), partition key BigQuery. Rollup ke mingguan/bulanan/kuartalan/tahunan dilakukan via `DATE_TRUNC`/`GROUP BY` di query konsumen, bukan tabel terpisah per granularitas — kecuali saat sumber data aslinya sudah non-harian (lihat catatan grain per tabel di bawah).

**Materialization**: `table` penuh (`CREATE OR REPLACE`), bukan `incremental` — BigQuery Sandbox mode (project `nirwana-database-elt` belum aktivasi billing) memblokir semua DML. Lihat `docs/keputusan-tertunda.md`.

---

## 1. Revenue

**Sumber:** `mart_cleaned__bookings`, `mart_cleaned__daily_occupancy`, `mart_cleaned__pricing_history`, `mart_cleaned__guests`.

### Dimension
| Tabel | Kolom kunci | Arti |
|---|---|---|
| `dim_room_type` | `room_type_name` | Tipe kamar (mis. Deluxe, Suite) dari `bookings.room_type`/`daily_occupancy.room_type` |
| `dim_room` | `room_id` | Kamar individual, FK ke `dim_property`+`dim_room_type` |
| `dim_channel` | `channel_name` | Saluran booking (mis. Direct, OTA) dari `bookings.booking_channel` |
| `dim_loyalty_tier` | `loyalty_tier_name` | Tier loyalty tamu (`guests.loyalty_tier`) |
| `dim_nationality_group` | `group_name` | Bucket **Domestik**/**Mancanegara** — aturan: `nationality='Indonesia'` → Domestik, selain itu → Mancanegara (tabel statis 2 baris, aturan diterapkan saat join di fact table) |
| `dim_pricing_reason` | `reason_name` | Alasan penyesuaian harga (manual/promo/dynamic-pricing-AI) dari `pricing_history.reason` |

### Fact
- **`fact_revenue_room_type_daily`** (property×room_type×hari): `occupancy_rate`/`adr`/`revpar` langsung dari `daily_occupancy`. `revenue` = SUM `total_amount` booking status `completed`/`confirmed`, grain `check_in_date`. `room_type_revenue_share_pct` = revenue tipe kamar itu ÷ total revenue properti hari itu.
- **`fact_revenue_channel_daily`** (property×channel×hari): `bookings_count` = seluruh booking (semua status). `cancellations_count`/`no_shows_count` = COUNTIF status terkait.
- **`fact_revenue_los_daily`** (property×room_type×channel×hari): `avg_los_nights`/`median_los_nights` dari `bookings.nights`, hanya status `completed`/`confirmed`.
- **`fact_revenue_property_daily`** (property×hari): `mom_*_growth`/`yoy_*_growth` = selisih nilai hari ini vs hari yang sama 1 bulan/1 tahun lalu (self-join tanggal persis, bukan `LAG` baris — tahan terhadap gap tanggal). `repeat_guest_rate` = % booking dari `guest_id` yang sudah pernah booking sebelumnya (`ROW_NUMBER() OVER (PARTITION BY guest_id ORDER BY booking_date) > 1`). `*_rank_group` = ranking antar 5 properti hari itu (`RANK() OVER (PARTITION BY period_date ORDER BY ... DESC)`).
- **`fact_revenue_gop_impact_monthly`** (property×bulan): `avg_pricing_deviation` = rata-rata `applied_rate−base_rate` bulan itu. `gop_margin` = `gop ÷ departmental_revenue` dari `financial_summary` baris `Overall`/`Corporate Overhead`. **Cross-domain** ke Corporate/Financial.
- **`fact_revenue_pricing_deviation`** (property×reason×hari): `day_share_pct` = proporsi hari dengan `reason` itu, dari total hari bulan tersebut.
- **`fact_revenue_loyalty_daily`** / **`fact_revenue_nationality_daily`** (property×tier/bucket×hari): booking count & revenue per segmen tamu.
- **`fact_revenue_pace_booking_snapshot`** — **Kasus Khusus**: grain property×room_type×`stay_date`(tanggal check-in masa depan)×`snapshot_date`(kapan snapshot diambil). Dibangun via self-union `CREATE OR REPLACE` (baca isi tabel lama + tambah baris hari ini), **full history tanpa retention**. Hanya mencakup booking `stay_date` dalam 14 hari ke depan dari `snapshot_date`. **Catatan penting**: dataset sintetis project ini statis (rentang tetap sampai 2026-07-01) — tabel ini akan **kosong** selama tanggal berjalan (`CURRENT_DATE()`) sudah lewat batas dataset, ini bukan bug (lihat `milestones/5.3-.../logs.md` Checkpoint 2).

---

## 2. F&B

**Sumber:** `mart_cleaned__fnb_transactions`, `fnb_outlets`, `recipe_bom`, `ingredient_price_history`, `fnb_inventory`, `fnb_waste_log`.

**Catatan penting**: `fnb_transactions.transaction_id` **bukan** row-level unik (~2,33 baris/transaksi, multi-item order) — setiap kolom yang menghitung transaksi (`transaction_count`, `walk_in_ratio`, dll) memakai `COUNT(DISTINCT transaction_id)`, bukan `COUNT(*)`.

### Dimension
`dim_outlet_type` (Restaurant/Bar/Room Service), `dim_outlet`, `dim_fnb_category` (Food/Beverage/Dessert), `dim_menu_item` (`item_name` teks sebagai natural key — tidak ada ID terstruktur di sumber), `dim_waste_reason` (overproduction/expired/spillage), `dim_ingredient` (`ingredient_id` STRING berperan ganda sebagai nama, mis. "Rice" — sumber tidak punya kolom nama terpisah).

### Fact
- **`fact_fnb_outlet_daily`**: `capture_rate` = jumlah transaksi `customer_type='inhouse'` (distinct) ÷ `rooms_sold` hari itu dari `daily_occupancy` — **cross-domain** ke Revenue, proksi populasi tamu menginap. `revenue_rank_vs_outlet_type_avg` = revenue outlet ÷ rata-rata revenue outlet dengan `outlet_type` sama hari itu.
- **`fact_fnb_menu_item_daily`**: `food_cost_ratio_actual` = (Σ `qty_per_portion×unit_cost` dari `recipe_bom`×`ingredient_price_history`) × `quantity_sold` ÷ `revenue`. `food_cost_ratio_target` **dihardcode** dari role-play Data Analyst §2.1: Food 34%, Beverage 24%, Dessert 28% — bukan turunan tabel manapun.
- **`fact_fnb_waste_daily`**: `waste_ratio` = `waste_quantity` ÷ total pemakaian bahan (dihitung dari `recipe_bom`×`fnb_transactions.quantity`).
- **`fact_fnb_inventory_status`**: **snapshot current-state** (`period_date=CURRENT_DATE()`) — `fnb_inventory` tidak punya kolom tanggal, cuma state terkini. `low_stock_item_count` = COUNTIF `stock_current < stock_min_threshold`.
- **`fact_fnb_ingredient_price_daily`**: `avg_unit_cost` per hari, langsung dari `ingredient_price_history` (grain sumber sudah harian per ingredient).

---

## 3. Facility/Ops

**Sumber:** `mart_cleaned__rooms`, `housekeeping_log`, `maintenance_tickets`.

### Dimension
`dim_facility_area`, `dim_issue_type`, `dim_priority` (maintenance ticket); `dim_room` (lintas-domain dengan Revenue).

### Fact
- **`fact_facility_room_status_daily`**: **snapshot current-state** (`rooms` tidak punya kolom tanggal) — `is_out_of_order` = `status='out-of-order'`. Kolom durasi (`out_of_order_hours`) di draf desain **dihapus** — tidak ada sumber histori durasi per kamar.
- **`fact_housekeeping_room_type_daily`** / **`_staff_daily`**: durasi pembersihan = `TIME_DIFF(cleaning_end_time, cleaning_start_time, MINUTE)`, hanya `status='completed'`. `baseline_duration_minutes`/`team_avg_duration_minutes` = rata-rata window (`AVG() OVER (PARTITION BY ...)`).
- **`fact_housekeeping_property_daily`**: `delayed_rate` = COUNTIF `status='delayed'` ÷ total. `occupancy_rate` — **cross-domain** dari `daily_occupancy`, kolom terpisah (bukan 1 kolom "vs" gabungan) supaya korelasinya bisa dihitung sendiri oleh konsumen lintas periode.
- **`fact_maintenance_ticket_daily`**: `avg_sla_duration_hours` = `TIMESTAMP_DIFF(resolved_date, reported_date, HOUR)`, **hanya nilai mentah, tanpa flag breach** — threshold SLA per `priority` belum ditentukan (Keputusan #7 M5.2). `pending_count` = tiket `open`/`in-progress`.
- **`fact_maintenance_cost_daily`**: grain `resolved_date` (cost dianggap final setelah tiket resolved). `cost_with_parts`/`cost_without_parts` = split berdasarkan `parts_replaced IS NOT NULL`.
- **`fact_maintenance_room_recurrence_yearly`** / **`_property_benchmark_yearly`**: grain tahunan. `vs_median_ratio` = ticket count kamar itu ÷ median ticket count seluruh kamar tahun itu. `building_age_years` dari `dim_property.opening_date`.

---

## 4. Spa & Event

**Sumber:** `mart_cleaned__spa_bookings`, `venues`, `event_bookings`.

### Dimension
`dim_spa_service`, `dim_venue_type`, `dim_venue`, `dim_event_type`; `dim_customer_type` (lintas-domain dengan F&B).

### Fact
- **`fact_spa_daily`**: `lead_time_days` = `service_date − booking_date`. `walk_in_ratio`/`cancellation_rate` = COUNTIF ÷ total booking hari itu.
- **`fact_spa_service_daily`**: `revenue_share_pct` = revenue layanan itu ÷ total revenue spa properti hari itu.
- **`fact_event_venue_daily`**: `utilization_rate` = Σ`capacity_booked` ÷ Σ`max_capacity` venue itu. `low_utilization_days_last_30` — **disederhanakan** dari "streak" (hari berturut-turut) jadi rolling count 30 hari terakhir dengan `utilization_rate < 30%` (threshold asumsi bisnis, tidak ada nilai baku dari dokumen manapun) — perhitungan *gaps-and-islands* streak murni di luar cakupan waktu M5.3.
- **`fact_event_type_daily`** / **`fact_event_property_daily`**: agregasi jumlah/revenue event dan cancellation rate.

---

## 5. HR

**Sumber:** `mart_cleaned__staff_shifts`, `employee_performance`, `employees`.

### Dimension
`dim_shift_type`, `dim_employee_status` (active/resigned/terminated); `dim_employee`, `dim_department` (lintas-domain). **`dim_employee.property_id`** (Milestone 5.7): properti tempat karyawan bertugas (`P06` = kantor pusat), langsung dari `mart_cleaned.employees.property_id` — sengaja terlewat di desain M5.2 semula, ditemukan oleh Data Analyst Serving (M3.2) dan ditutup lewat mekanisme pengajuan M5.6. Memungkinkan `fact_hr_employee_monthly`, `fact_hr_employee_performance_semester`, dan `fact_hr_watchlist_monthly` di-join ke properti lewat `dim_employee` untuk pertama kalinya.

### Fact
- **`fact_hr_attendance_daily`**: `overtime_hours_total` = Σ MAX(0, jam kerja − 8) per shift. Shift lintas tengah malam (`clock_out < clock_in`) ditangani `+24 jam` sebelum dikurangi 8.
- **`fact_hr_employee_monthly`**: `overtime_vs_dept_avg`/`late_vs_dept_avg` = nilai individu − rata-rata departemen bulan itu.
- **`fact_hr_employee_performance_semester`** / **`_department_semester`** / **`_by_status_semester`**: grain **semesteran** (`review_period` STRING `'YYYY-SN'`, mis. `'2025-S1'`) — **bukan bulanan**, mengikuti grain asli `employee_performance` (dikoreksi dari draf M5.2 yang keliru asumsi bulanan).
- **`fact_hr_turnover_snapshot`**: **snapshot current-state** — `employees` cuma punya `status` akhir, tidak ada tanggal resign/terminasi, sehingga turnover rate historis per bulan **tidak bisa dihitung** dari data yang tersedia. `turnover_rate` = COUNTIF `status != 'active'` ÷ total, per hari ini.
- **`fact_hr_headcount_status_daily`**: snapshot jumlah karyawan per status.
- **`fact_hr_watchlist_monthly`** — **Kasus Khusus**: `baseline_absence_rate`/`baseline_late_rate` = rata-rata SEMUA bulan **sebelum** bulan berjalan untuk karyawan yang sama (`AVG() OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)`, expanding window, bukan angka tetap). `*_deviation_ratio` = current ÷ baseline. **`in_watchlist`** (Milestone 5.6): `true` kalau `absence_deviation_ratio` ATAU `late_deviation_ratio` > 5x (`coalesce(..., false)` — bulan pertama karyawan, baseline belum ada, dianggap belum bisa dinilai, bukan otomatis ter-flag). Angka 5x dikalibrasi terhadap distribusi riil lewat `pengajuan-perubahan-cakupan.md` (draf awal 1.5x ternyata men-flag 47% baris, jauh terlalu sensitif — direvisi ke 5x, ~4.67% ter-flag).

---

## 6. Corporate/Financial

**Sumber:** `mart_cleaned__financial_summary`, `payroll`.

**Catatan penting #1**: kolom `department` di `payroll` merujuk **unit organisasi karyawan** (`dim_department`) — BUKAN `dim_business_line` (baris USALI `financial_summary`). Lihat disambiguasi `DataSchema-mart-aggregated.md`.

**Catatan penting #2**: baris P&L nyata `financial_summary` ada di `department='Overall'` (properti P01-P05) **dan** `department='Corporate Overhead'` (khusus P06, kantor pusat) — tabel `fact_financial_overall_monthly` filter `department IN ('Overall','Corporate Overhead')` untuk menangkap keduanya dengan benar (tiap `property_id` cuma punya salah satu).

**Catatan penting #3 (gap data)**: `undistributed_expense` di `financial_summary` cuma **1 kolom total** — **tidak ada breakdown per komponen** (Admin&General/Sales&Marketing/Utilities/Property Maintenance/IT) di skema sumber manapun. Asumsi breakdown 5-komponen di dokumen M5.1/M5.2 berasal dari narasi role-play "laporan USALI formal" (deskripsi umum industri), bukan skema data aktual — ditemukan saat implementasi M5.3 (lihat Known Gaps `report.md`).

### Dimension
`dim_business_line` (Room/F&B/Spa&Event/Overall/Corporate Overhead), `dim_access_level` (staff/manager).

### Fact
- **`fact_financial_business_line_monthly`**: **wajib filter** `business_line_id` ke Room/F&B/Spa&Event saat dipakai untuk "departmental margin" — jangan sertakan Overall/Corporate Overhead (risiko double counting, dibuktikan lewat `assert_gop_no_double_counting` test).
- **`fact_financial_overall_monthly`**: `gop_margin_pct` = `gop ÷ departmental_revenue` baris Overall/Corporate Overhead. `mom_gop_growth`/`yoy_gop_growth` via self-join bulan.
- **`fact_financial_revenue_runrate_daily`**: agregasi lintas **4 sumber revenue** (`bookings`+`fnb_transactions`+`spa_bookings`+`event_bookings`) per hari — pengganti GOP mingguan yang tidak bisa dihitung akurat (`financial_summary` grain bulanan).
- **`fact_payroll_department_monthly`**: total 6 komponen payroll (`base_salary`, `service_charge`, `overtime_pay`, `thr`, `deduction`, `net_salary`) per departemen per bulan.
- **`fact_financial_service_charge_monthly`**: grain **bulanan** (dikoreksi dari draf M5.2 yang keliru asumsi harian — `payroll.period` grain aslinya bulanan). `occupancy_rate` di-roll-up bulanan dari `daily_occupancy` supaya grain kedua sisi cocok.
- **`fact_financial_labor_cost_monthly`**: `labor_cost_pct_revenue` = (`base_salary+service_charge+overtime_pay`) ÷ `revenue_runrate` bulan itu (ref ke `fact_financial_revenue_runrate_daily`, di-roll-up bulanan).
- **`fact_payroll_access_level_monthly`**: `service_charge_to_base_ratio` = Σ`service_charge` ÷ Σ`base_salary`, per `access_level`.
- **`fact_financial_business_line_group_monthly`**: grain **grup, lintas 5 properti** (tanpa `property_id`) — `revenue_share_pct` = kontribusi lini bisnis itu terhadap total revenue grup bulan itu.
- **`fact_financial_property_benchmark_monthly`**: `gop_margin_rank` = `RANK() OVER (PARTITION BY period_date ORDER BY gop_margin_pct DESC)`.

---

## 7. Feedback Loop ML (Milestone 5.4, ⚠️ PROVISIONAL)

**Sumber:** `ml_output.predictions` (dataset BigQuery terpisah, ditulis `scripts/ml_scoring/mock_score.py` — STAND-IN untuk scoring pipeline eksternal yang tidak ada di repo ini) `LEFT JOIN` `fact_revenue_room_type_daily`.

**⚠️ Seluruh isi bagian ini PROVISIONAL** — skema `ml_output`, use-case occupancy forecast, dan format `entity_id` murni contoh/simulasi untuk membuktikan mekanisme trigger→sensor→join→test, bukan kontrak final dengan tim ML Engineer sungguhan. Lihat catatan status penuh di header `milestones/5.4-integrasi-feedback-loop-ml/decisions.md`.

### Fact
- **`fact_ml_occupancy_forecast_property_room_type`**: grain property×room_type×`target_date`×`scored_at`. `predicted_occupancy_rate` = moving average `occupancy_rate` 30 hari terakhir per property×room_type (forecast naif, bukan model ML sungguhan). `confidence_score` = `1 − (stddev÷avg)` occupancy 30 hari itu, dibatasi 0.05–0.99. `entity_id` sumber (`ml_output.predictions`) berformat composite `"property_id:room_type_id"`, di-split saat transformasi. `model_version`/`feature_snapshot_at` **selalu terisi** (`FROM ml_output.predictions` sebagai base query, bukan `LEFT JOIN` dari sisi `mart_aggregated` — jaminan struktural, bukan cuma test). `actual_occupancy_rate`/`forecast_error_abs` nullable, cuma terisi kalau `target_date` sudah lewat. **Isolasi kegagalan**: tabel ini di-tag `ml_feedback_loop`, dipromosikan terpisah dari 45 fact table lain (`scripts/mart_aggregated/promote.py --exclude tag:ml_feedback_loop` untuk yang lain) — kalau `ml_output` telat/gagal, cuma tabel ini yang stale, tidak memblokir refresh 45 tabel lain.

---

## Audit PII (re-verifikasi terhadap hasil akhir)

Ditelusuri langsung ke `INFORMATION_SCHEMA.COLUMNS` dataset `mart_aggregated` (bukan cuma desain di atas kertas — lihat `milestones/5.3-.../logs.md` Checkpoint 8): **satu-satunya** kolom personal di seluruh 76 tabel M5.3 adalah `dim_employee.full_name` (domain `employees_directory`, diteruskan apa adanya untuk name-resolution, akses diatur RBAC layer terpisah — Milestone 4.1-4.3, di luar scope repo ini). Tidak ada kolom `email`/`phone`/`guest_id` individual di mana pun — seluruh kebutuhan kontak tamu tetap dilayani row-level dari `mart_cleaned.guests`. Tabel ML baru M5.4 (`fact_ml_occupancy_forecast_property_room_type`) juga tidak menyentuh data tamu individual — grain-nya property×room_type, bukan per-guest.

## Validasi Silang (M5.3 Task 11)

6 metrik representatif (1 per domain) divalidasi manual terhadap `mart_cleaned` — seluruhnya cocok persis (lihat `milestones/5.3-.../logs.md` Checkpoint 8 untuk angka lengkap): occupancy_rate (Revenue), total revenue (F&B), total ticket count (Facility/Ops), total revenue (Spa & Event), total present_count (HR), total GOP (Corporate/Financial).
