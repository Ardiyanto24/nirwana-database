# Index dan Baseline Performa — Data Analyst

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 3.3 (`milestones/3.3-index-optimasi-performa-analyst/`) |
| **Input utama** | `docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md` (M3.1, filter wajib) + `view-query-pattern-analyst.md` (M3.2, kolom join) |
| **Lokasi teknis** | `scripts/reverse_etl_mart_aggregated/mart_aggregated_indexes.py` (41 index) + `scripts/reverse_etl/mart_cleaned_indexes.py` (9 index), dijalankan lewat `reindex_analyze.py --all` di masing-masing folder, otomatis pasca-swap via `.github/workflows/reverse-etl-{mart-aggregated,mart-cleaned}.yml` |
| **Status** | Selesai — 50 index (41 `mart_aggregated` + 9 `mart_cleaned`), seluruhnya terverifikasi terpakai planner (`idx_scan≥1`) |

---

## Cara Membaca Dokumen Ini

Tiap baris di bawah adalah 1 index yang benar-benar dipasang dan diverifikasi terhadap serving PostgreSQL sungguhan — bukan desain di atas kertas. Kolom **Baseline** dan **Setelah Index** adalah `EXPLAIN ANALYZE` execution time nyata (bukan estimasi), diukur dengan query representatif per domain (filter properti/entitas + rentang waktu, meniru "laporan bulanan"/"investigasi ad-hoc" yang jadi pola akses nyata Data Analyst). Tabel yang **tidak** diindeks (karena terbukti tidak dipakai planner atau di bawah threshold empiris) dicatat eksplisit di bagian "Tabel yang Sengaja Tidak Diindeks" — bukan dihilangkan dari dokumen.

## Revenue (8 mart_aggregated + 2 mart_cleaned)

| Tabel | Schema | Kolom Index | Baseline | Setelah Index | Faktor Percepatan |
|---|---|---|---|---|---|
| `fact_revenue_room_type_daily` | mart_aggregated | `(property_id, period_date)` | 88.2ms | 2.2ms | ~40x |
| `fact_revenue_channel_daily` | mart_aggregated | `(property_id, period_date)` | 130.7ms | 1.8ms | ~72x |
| `fact_revenue_los_daily` | mart_aggregated | `(property_id, period_date)` | 276.6ms | 0.48ms | ~576x |
| `fact_revenue_property_daily` | mart_aggregated | `(property_id, period_date)` | — | 0.13ms | index terpakai (`idx_scan`≥1) |
| `fact_revenue_pricing_deviation` | mart_aggregated | `(property_id, period_date)` | — | 1.77ms | index terpakai |
| `fact_revenue_loyalty_daily` | mart_aggregated | `(property_id, period_date)` | — | 2.81ms | index terpakai |
| `fact_revenue_nationality_daily` | mart_aggregated | `(property_id, period_date)` | — | 2.78ms | index terpakai |
| `bookings` | mart_cleaned | `(property_id, check_in_date)` | 82.1ms | 3.3ms | ~25x |
| `pricing_history` | mart_cleaned | `(property_id, date)` | 2.7ms | 2.7ms | index terpakai, sudah cepat sebelumnya |

**Dikecualikan:** `fact_revenue_gop_impact_monthly` (180 baris) — di bawah threshold awal, lihat catatan Corporate/Financial untuk koreksi threshold ini (temuan Checkpoint 7).

## F&B (7 mart_aggregated + 1 mart_cleaned)

| Tabel | Schema | Kolom Index | Baseline | Setelah Index | Faktor Percepatan |
|---|---|---|---|---|---|
| `fact_fnb_outlet_daily` | mart_aggregated | `(outlet_id, period_date)` | 111.1ms | 3.0ms | ~37x |
| `fact_fnb_category_daily` | mart_aggregated | `(outlet_id, period_date)` | — | 8.1ms | index terpakai |
| `fact_fnb_hourly` | mart_aggregated | `(outlet_id, period_date)` | 299.7ms | 9.6ms | ~31x |
| `fact_fnb_customer_type_daily` | mart_aggregated | `(outlet_id, period_date)` | — | 2.4ms | index terpakai |
| `fact_fnb_menu_item_daily` | mart_aggregated | `(outlet_id, period_date)` | 793.2ms | 7.6ms | ~104x |
| `fact_fnb_waste_daily` | mart_aggregated | `(outlet_id, period_date)` | — | 1.7ms | index terpakai |
| `fact_fnb_ingredient_price_daily` | mart_aggregated | `(ingredient_id, period_date)` | — | 2.6ms | index terpakai |
| `fnb_transactions` | mart_cleaned | `(outlet_id, transaction_datetime)` | 1004.4ms | 4.9-5.6ms (stabil) | ~180-205x |

**Catatan operasional:** `fnb_transactions` (902.574 baris, tabel terbesar project) sempat terukur 1473.5ms pada run pertama tepat setelah `REINDEX` — anomali cache-dingin (buffer belum warm), bukan index gagal dipakai (plan tetap Bitmap Index Scan). 3 run berikutnya stabil 4.9-65ms. Relevan untuk operasional: baseline pertama pasca-swap/reindex terjadwal bisa terasa lebih lambat sampai cache warm — konsisten catatan ketergantungan dokumen sumber M3.3.

**Dikecualikan:** `fact_fnb_inventory_status` (17 baris — snapshot state terkini).

## Facility/Ops (7 mart_aggregated + 1 mart_cleaned)

| Tabel | Schema | Kolom Index | Baseline | Setelah Index | Faktor Percepatan |
|---|---|---|---|---|---|
| `fact_housekeeping_room_type_daily` | mart_aggregated | `(property_id, period_date)` | 74.5ms | 0.96ms | ~78x |
| `fact_housekeeping_property_daily` | mart_aggregated | `(property_id, period_date)` | 17.6ms | 2.5ms | ~7x |
| `fact_housekeeping_staff_daily` | mart_aggregated | `(staff_id, period_date)` | 348.7ms | 3.3ms | ~106x |
| `fact_maintenance_ticket_daily` | mart_aggregated | `(property_id, period_date)` | 50.3ms | 1.7ms | ~30x |
| `fact_maintenance_cost_daily` | mart_aggregated | `(property_id, period_date)` | 21.4ms | 1.4ms | ~15x |
| `fact_maintenance_technician_daily` | mart_aggregated | `(assigned_staff_id, period_date)` | 36.4ms | 2.7ms | ~13x |
| `fact_maintenance_room_recurrence_yearly` | mart_aggregated | `(room_id, year)` | 4.2ms | 2.6ms | ~1.6x (sudah cepat, tetap terbukti terpakai) |
| `maintenance_tickets` | mart_cleaned | `(property_id, reported_date)` | 84.8ms | 1.6ms | ~53x |

**Dikecualikan:** `fact_facility_room_status_daily` (549 baris, snapshot state terkini), `fact_maintenance_property_benchmark_yearly` (20 baris).

## Spa & Event (6 mart_aggregated + 1 mart_cleaned)

| Tabel | Schema | Kolom Index | Baseline | Setelah Index | Faktor Percepatan |
|---|---|---|---|---|---|
| `fact_spa_daily` | mart_aggregated | `(property_id, period_date)` | 17.5ms | 1.1ms | ~16x |
| `fact_spa_customer_type_daily` | mart_aggregated | `(property_id, period_date)` | 16.1ms | 1.0ms | ~16x |
| `fact_spa_service_daily` | mart_aggregated | `(property_id, period_date)` | 115.9ms | 1.2ms | ~97x |
| `fact_event_venue_daily` | mart_aggregated | `(venue_id, period_date)` | 8.1ms | 0.10ms | ~85x |
| `fact_event_property_daily` | mart_aggregated | `(property_id, period_date)` | 3.8ms | 1.6ms | ~2.4x |
| `fact_event_type_daily` | mart_aggregated | `(property_id, period_date)` | 1.5ms | 0.79ms | ~1.9x |
| `event_bookings` | mart_cleaned | `(property_id, event_date)` | 14.6ms | 0.13ms | ~112x |

**Catatan:** `fact_event_property_daily` (1.177 baris) dan `fact_event_type_daily` (1.300 baris) adalah tabel terkecil yang diuji sampai titik ini, dan keduanya tetap terbukti terpakai planner — bukti awal bahwa ukuran baris mentah bukan penentu tunggal (dikonfirmasi lebih jauh di Corporate/Financial).

## HR (5 mart_aggregated + 2 mart_cleaned)

| Tabel | Schema | Kolom Index | Baseline | Setelah Index | Faktor Percepatan |
|---|---|---|---|---|---|
| `fact_hr_attendance_daily` | mart_aggregated | `(property_id, department_id, period_date)` | 183.9ms | 7.4ms | ~25x |
| `fact_hr_employee_monthly` | mart_aggregated | `(employee_id, period_date)` | 102.8ms | 3.9ms | ~26x |
| `fact_hr_employee_performance_semester` | mart_aggregated | `(employee_id, review_period)` | 12.9ms | 4.6ms | ~2.8x |
| `fact_hr_watchlist_monthly` | mart_aggregated | `(employee_id, period_date)` | 66.8ms | 3.4ms | ~20x |
| `dim_employee` | mart_aggregated | `(property_id)` | 1.7ms | 1.5ms | index terpakai meski tabel kecil (755 baris) — join-side untuk 3 view besar |
| `staff_shifts` | mart_cleaned | `(employee_id, date)` | **1702.8ms** | 2.5ms | **~681x — perbaikan terbesar milestone ini** |
| `employee_performance` | mart_cleaned | `(employee_id, review_period)` | 16.6ms | 1.2ms | ~14x |

**Catatan:** `fact_hr_attendance_daily` adalah satu-satunya tabel dengan 2 filter wajib sekaligus (`property_id` DAN `department_id`, per M3.1) — composite index 3-kolom.

**Dikecualikan:** `fact_hr_turnover_snapshot` (43), `fact_hr_headcount_status_daily` (89), `fact_hr_performance_department_semester` (258), `fact_hr_performance_by_status_semester` (90) — seluruhnya di bawah threshold berbasis bukti (lihat catatan Corporate/Financial di bawah, ini adalah domain terakhir yang dikecualikan tanpa uji individual eksplisit sebelum koreksi threshold ditemukan).

## Corporate/Financial (9 mart_aggregated + 2 mart_cleaned)

| Tabel | Schema | Kolom Index | Baseline | Setelah Index | Catatan |
|---|---|---|---|---|---|
| `fact_financial_business_line_monthly` | mart_aggregated | `(property_id, period_date)` | 5.3ms | 2.0ms | juga basis `v_financial_departmental_margin` — business rule `Overall` exclusion diverifikasi tidak berubah |
| `fact_financial_overall_monthly` | mart_aggregated | `(property_id, period_date)` | 0.05ms | 1.3ms | index terpakai, tapi **tidak mempercepat** (tabel 216 baris, overhead B-tree > seq scan trivial) |
| `fact_financial_revenue_runrate_daily` | mart_aggregated | `(property_id, period_date)` | 0.44ms | 2.5ms | index terpakai, sama catatan di atas |
| `fact_payroll_department_monthly` | mart_aggregated | `(property_id, period_date)` | 0.17ms | 2.4ms | index terpakai, sama catatan |
| `fact_financial_service_charge_monthly` | mart_aggregated | `(property_id, period_date)` | 0.05ms | 2.0ms | index terpakai, sama catatan |
| `fact_financial_labor_cost_monthly` | mart_aggregated | `(property_id, period_date)` | 0.05ms | 1.2ms | index terpakai, sama catatan |
| `fact_payroll_access_level_monthly` | mart_aggregated | `(property_id, period_date)` | 0.11ms | 2.5ms | index terpakai, sama catatan |
| `fact_financial_business_line_group_monthly` | mart_aggregated | `(business_line_id, period_date)` | 0.05ms | 1.2ms | 180 baris — tabel yang memicu koreksi threshold (lihat di bawah) |
| `fact_financial_property_benchmark_monthly` | mart_aggregated | `(property_id, period_date)` | 0.06ms | 1.5ms | index terpakai, sama catatan |
| `financial_summary` | mart_cleaned | `(property_id, period)` | 6.9ms | 2.4ms | ~3x |
| `payroll` | mart_cleaned | `(employee_id, period)` | 145.2ms | 2.4ms | ~60x |

**Temuan penting — koreksi asumsi Keputusan #2 (`decisions.md`):** Rencana awal berasumsi tabel kecil (~ribuan baris atau kurang) hampir pasti tetap seq-scan meski diberi index. Spot-check di `fact_financial_business_line_group_monthly` (180 baris — seukuran `fact_revenue_gop_impact_monthly` yang sudah dikecualikan) membuktikan sebaliknya: dengan filter 2 kolom yang cukup selektif, Postgres **tetap memilih Index Scan** bahkan di tabel sekecil itu. Kesimpulan yang benar: **selektivitas filter, bukan jumlah baris mentah, yang menentukan pilihan planner** — koreksi ini diterapkan retroaktif di Corporate/Financial (seluruh 9 tabel diuji individual, tidak ada yang dikecualikan berdasar ukuran semata), tapi domain-domain sebelumnya (Revenue, F&B, Facility/Ops, Spa & Event, HR) yang sudah mengecualikan tabel <500 baris tanpa uji individual **tidak diuji ulang** — dicatat sebagai Known Gap di `report.md`, bukan didiamkan.

**Konsekuensi praktis ditemukan sekaligus:** untuk tabel yang sudah sub-milidetik sebelum index (`fact_financial_overall_monthly` dkk, 216 baris), index **terpakai planner** (memenuhi KK2 literal) tapi **tidak mempercepat** — bahkan sedikit menambah overhead (0.05ms→~1.3ms, traversal B-tree vs seq scan trivial). Ini bukan pelanggaran KK2 (index terbukti terpakai, bukan index yang tidak pernah dipakai) tapi perlu dipahami: manfaat index paling nyata di tabel besar (F&B/HR row-level `mart_cleaned`), bukan seragam di semua tabel.

---

## Ringkasan Verifikasi

- **50 index terpasang** (41 `mart_aggregated` + 9 `mart_cleaned`), seluruhnya dikonfirmasi `pg_stat_user_indexes.idx_scan ≥ 1` — tidak ada index yang terpasang tapi tidak pernah terpakai.
- **KK1 (waktu wajar untuk analisis interaktif):** seluruh query representatif domain turun ke rentang 0.1-10ms setelah index (kecuali beberapa tabel Corporate/Financial yang sudah sub-milidetik sejak awal). Perbaikan terbesar: `mart_cleaned.staff_shifts` 1702.8ms→2.5ms (~681x), `mart_cleaned.fnb_transactions` 1004.4ms→~5ms (~200x).
- **KK2 (index benar-benar terpakai):** dibuktikan 2 arah — `EXPLAIN ANALYZE` menunjukkan node Index/Bitmap Index Scan (bukan Seq Scan) untuk seluruh 50 index, dan `pg_stat_user_indexes.idx_scan` ≥1 setelah query verifikasi dijalankan.
- **Mekanisme pasca-swap** (business rule paling kritis dari catatan ketergantungan dokumen sumber): `reindex_analyze.py --all` sudah wired otomatis ke kedua workflow terjadwal (`reverse-etl-mart-aggregated.yml`, `reverse-etl-mart-cleaned.yml`) — index di dokumen ini akan otomatis dipasang ulang tiap kali `sync.py --all` melakukan swap, tidak bergantung eksekusi manual berikutnya.
