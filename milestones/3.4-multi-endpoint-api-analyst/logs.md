# Milestone 3.4: Multi-Endpoint API untuk Data Analyst — Logs

## 2026-08-09 — Mulai kerja

- Plan disetujui via Plan Mode. `decisions.md` ditulis, mengunci 10 keputusan teknis (topologi in-repo untuk tool internal, pola kode FastAPI dari `api/`, desain route domain+whitelist, keamanan query, paginasi, dst).
- Folder dibuat: `milestones/3.4-multi-endpoint-api-analyst/`, `scripts/data_analyst_api/`.
- Mulai Task 1 (Fase 0 — FastAPI app skeleton).

## 2026-08-09 — Checkpoint 1

- `scripts/data_analyst_api/{connections.py,main.py}` dibuat. `connections.py` copy pola `get_serving_connection` dari `scripts/data_analyst_views/connections.py`, ditambah `query()` helper `RealDictCursor` persis pola `api/app/db.py` (M1.6). `main.py` berisi app FastAPI, `/health`, helper generik `_run_whitelisted_query` (filter kolom/operator dari whitelist entry, value selalu psycopg2 parameter) dan `register_domain_routes(domain, aggregate_whitelist, rowlevel_whitelist)` untuk dipanggil tiap checkpoint domain berikutnya.
- `requirements.txt` root ditambah blok baru `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`.
- Verifikasi: `python -m uvicorn main:app --reload` dijalankan sungguhan di `127.0.0.1:8101`, `curl`/HTTP call langsung ke `/health` → `{"status":"ok"}` (200), `/docs` (Swagger auto-docs) → 200.
- **Catatan operasional**: `--reload` (WatchFiles) tidak konsisten memuat ulang modul baru di lingkungan ini (perubahan terdeteksi tapi server lama tetap melayani request, 404 palsu) — checkpoint berikutnya pakai kill+restart server biasa (tanpa `--reload`) tiap kali `main.py`/whitelist berubah, bukan mengandalkan auto-reload.

## 2026-08-09 — Checkpoint 2: Revenue API

- `whitelist_revenue.py` (8 view aggregate `_PROPERTY_PERIOD_FILTERS` seragam `property_id`+`date_from`/`date_to`→`period_date`; 2 tabel row-level `bookings` — `property_id`/`date_from`/`date_to`→`check_in_date`/`status`, `pricing_history` — `property_id`/`date_from`/`date_to`→`date`). 2 route didaftarkan di `main.py` via `register_domain_routes("revenue", ...)`.
- Server dijalankan ulang (bukan `--reload`, lihat catatan di atas), port 8102.
- **Verifikasi KK1**: `GET /api/revenue/aggregate/room-type-daily?property_id=P01&date_from=2024-07-01&date_to=2024-08-01` → 100 baris (limit default), data cocok pola yang sudah diverifikasi M3.2/M3.3.
- **Verifikasi KK2** (skenario persis dokumen sumber): `GET /api/revenue/rowlevel/bookings?property_id=P01&date_from=2024-03-01&date_to=2024-04-01&status=cancelled` → mengembalikan booking granular P01, `status=cancelled`, `check_in_date` dalam rentang Maret 2024 — persis skenario "kenapa cancellation Bali Maret 2024 tinggi" dari `04-serving-data-analyst.md`.
- Verifikasi tambahan: nama view di luar whitelist → 404 dengan pesan jelas; `limit=5` mengembalikan tepat 5 baris (paginasi berfungsi).

## 2026-08-09 — Checkpoint 3: F&B API

- `whitelist_fnb.py` (8 view aggregate — filter `outlet_id`/`property_id`/`date_from`/`date_to`, `hourly` tambah `hour_of_day`, `ingredient-price-daily` pakai `ingredient_id` karena tidak terikat outlet; 1 tabel row-level `fnb_transactions`, tabel terbesar project 902rb baris — filter `outlet_id`/tanggal/`customer_type`/`item_name`).
- Server direstart (bukan `--reload`), port 8103.
- Verifikasi HTTP: `v_fnb_outlet_daily` filter `outlet_id=OUT001` bulan Juli → 31 baris (cocok jumlah hari); `fnb_transactions` row-level dengan paginasi `limit=5` → tepat 5 baris transaksi granular.

## 2026-08-09 — Checkpoint 4: Facility/Ops API

- `whitelist_facility.py` (9 view aggregate; 1 tabel row-level `maintenance_tickets` — filter `property_id`/`room_id`/tanggal/`status`/`priority`).
- Server direstart, port 8104.
- Verifikasi HTTP: `v_maintenance_ticket_daily` lewat endpoint tetap mengembalikan `pending_count` dan `avg_exceeds_sla_threshold` sebagai kolom terpisah apa adanya (business rule M3.1/M3.2 tidak disederhanakan di layer API); `maintenance_tickets` row-level mengembalikan tiket granular sesuai filter.

## 2026-08-09 — Checkpoint 5: Spa & Event API

- `whitelist_spa_event.py` (6 view aggregate; 1 tabel row-level `event_bookings` — filter `property_id`/`venue_id`/tanggal/`event_type`/`status`; sengaja tidak ada endpoint repeat-client/cross-sell, konsisten larangan M3.1/M3.2).
- Server direstart, port 8105.
- Verifikasi HTTP: `v_event_venue_daily` filter `venue_id` mengembalikan data venue yang benar; `event_bookings` row-level mengembalikan event granular termasuk `client_name` untuk investigasi ad-hoc.

## 2026-08-09 — Checkpoint 6: HR API

- `whitelist_hr.py` (8 view aggregate — `attendance-daily`/`turnover-snapshot`/`headcount-status-daily` pakai `property_id`+`department_name` sekaligus, 2 filter wajib per M3.1; `employee-monthly`/`watchlist-monthly` pakai `employee_id`+`property_id` (kolom trailing hasil follow-up M5.7); 2 tabel row-level `staff_shifts`/`employee_performance` — **tanpa payroll**, business rule M3.1).
- Server direstart, port 8106.
- **Verifikasi eksplisit business rule kritis**: `GET /api/hr/rowlevel/payroll` → 404 (bukan sekadar tidak dibuat — dikonfirmasi lewat panggilan HTTP nyata bahwa endpoint itu memang tidak ada di whitelist HR). `v_hr_watchlist_monthly` mengembalikan `property_id`/`property_name` (hasil follow-up M5.7/M3.2) dengan benar.

## 2026-08-09 — Checkpoint 7: Corporate/Financial API

- `whitelist_corporate_financial.py` (9 view aggregate; 2 tabel row-level `financial_summary`/`payroll` — eksklusif domain ini, tidak muncul di whitelist domain manapun lain).
- Server direstart, port 8107.
- **Verifikasi business rule kritis end-to-end (DB → view → API)**: `GET /api/corporate-financial/aggregate/departmental-margin?property_id=P01&limit=500` TANPA filter `business_line_name` apa pun tetap hanya mengembalikan `['F&B','Room','Spa&Event']` — `Overall`/`Corporate Overhead` terbukti tidak pernah muncul lewat panggilan HTTP nyata, konsisten hasil verifikasi M3.2/M3.3 di level database.
- `v_financial_gop_overhead` dan `mart_cleaned.payroll` row-level (lewat endpoint `corporate-financial`, bukan `hr`) berfungsi benar.

## 2026-08-09 — Checkpoint 8 (final) — Tutup milestone

- **Validasi Property/GM Analyst**: 5 domain (Revenue, F&B, Facility, Spa&Event, HR — bukan Corporate/Financial) dipanggil via HTTP dengan `property_id=P02`, seluruhnya mengembalikan data yang benar-benar terbatas ke P02. Tidak ada endpoint baru dibuat untuk peran ini, konsisten pola M3.2/M3.3.
- `docs/08-serving-data-analyst/api-analyst.md` ditulis — dokumentasi 12 route lengkap dengan filter, contoh `curl`, dan catatan business rule per domain.
- KK1 dan KK2 diverifikasi ulang lintas 6 domain, `report.md` ditulis.
- Milestone ditutup. Handoff eksplisit ke M3.5: struktur URL per-domain dirancang supaya gerbang akses nanti bisa mengunci per-prefix.
