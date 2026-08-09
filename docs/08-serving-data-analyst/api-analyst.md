# API Multi-Endpoint — Data Analyst

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 3.4 (`milestones/3.4-multi-endpoint-api-analyst/`) |
| **Kode** | `scripts/data_analyst_api/` (FastAPI, internal-only — bukan `api/` M1.6 yang portfolio-facing) |
| **Input utama** | `docs/08-serving-data-analyst/view-query-pattern-analyst.md` (M3.2, 48 view) + `index-baseline-analyst.md` (M3.3, 50 index) |
| **Status** | Selesai — 12 route (6 domain × 2), seluruhnya diverifikasi via HTTP nyata |

---

## Cara Menjalankan

```bash
pip install -r requirements.txt
cd scripts/data_analyst_api
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Swagger UI otomatis di `http://127.0.0.1:8000/docs`, ReDoc di `/redoc`. Health check: `GET /health`.

**Catatan:** internal tool untuk 6 peran analyst Nirwana sendiri — **tidak ada auth/CORS/rate-limit** (beda dari `api/` M1.6 yang publik). Isolasi akses per peran adalah cakupan Milestone 3.5, belum diimplementasikan di sini. Koneksi database memakai kredensial admin (`SERVING_DB_URL`) dengan `readonly=True` di level session sebagai defense-in-depth murah, bukan mekanisme isolasi sungguhan.

## Pola URL

```
GET /api/{domain}/aggregate/{view_name}?<filter params>&limit=<int>&offset=<int>
GET /api/{domain}/rowlevel/{table_name}?<filter params>&limit=<int>&offset=<int>
```

- `{domain}`: salah satu dari `revenue`, `fnb`, `facility`, `spa-event`, `hr`, `corporate-financial` — path literal tetap, bukan parameter bebas.
- `{view_name}`/`{table_name}`: harus ada di whitelist domain tersebut (lihat tabel di bawah), kalau tidak → `404`.
- Filter params: hanya nama yang dideklarasikan whitelist per view/tabel yang berpengaruh ke query — nama lain diabaikan (bukan error), aman dari SQL injection karena kolom/operator predefined, value selalu lewat parameter `%s`.
- `limit` (default 100, maks 1000), `offset` (default 0) — wajib untuk tabel row-level besar (`fnb_transactions` 902rb, `staff_shifts` 610rb baris).
- Response: array JSON, tiap elemen 1 baris (`RealDictCursor`), diurutkan `ORDER BY` kolom pertama untuk paginasi konsisten.

## Revenue (`/api/revenue`)

| Path | Sumber | Filter |
|---|---|---|
| `aggregate/room-type-daily` | `v_revenue_room_type_daily` | `property_id`, `date_from`, `date_to` |
| `aggregate/channel-daily` | `v_revenue_channel_daily` | sama |
| `aggregate/los-daily` | `v_revenue_los_daily` | sama |
| `aggregate/property-daily` | `v_revenue_property_daily` | sama |
| `aggregate/gop-impact-monthly` | `v_revenue_gop_impact_monthly` | sama |
| `aggregate/pricing-deviation` | `v_revenue_pricing_deviation` | sama |
| `aggregate/loyalty-daily` | `v_revenue_loyalty_daily` | sama |
| `aggregate/nationality-daily` | `v_revenue_nationality_daily` | sama |
| `rowlevel/bookings` | `mart_cleaned.bookings` | `property_id`, `date_from`/`date_to`→`check_in_date`, `status` |
| `rowlevel/pricing-history` | `mart_cleaned.pricing_history` | `property_id`, `date_from`/`date_to`→`date` |

**Contoh — laporan bulanan Revenue Analyst:**
```bash
curl "http://127.0.0.1:8000/api/revenue/aggregate/room-type-daily?property_id=P01&date_from=2024-07-01&date_to=2024-08-01"
```

**Contoh — investigasi ad-hoc (skenario KK2 dokumen sumber, "kenapa cancellation Bali Maret 2024 tinggi"):**
```bash
curl "http://127.0.0.1:8000/api/revenue/rowlevel/bookings?property_id=P01&date_from=2024-03-01&date_to=2024-04-01&status=cancelled"
```

## F&B (`/api/fnb`)

| Path | Sumber | Filter |
|---|---|---|
| `aggregate/outlet-daily` | `v_fnb_outlet_daily` | `outlet_id`, `property_id`, `date_from`, `date_to` |
| `aggregate/category-daily` | `v_fnb_category_daily` | sama |
| `aggregate/hourly` | `v_fnb_hourly` | sama + `hour_of_day` |
| `aggregate/customer-type-daily` | `v_fnb_customer_type_daily` | sama pola outlet |
| `aggregate/menu-item-daily` | `v_fnb_menu_item_daily` | sama pola outlet |
| `aggregate/waste-daily` | `v_fnb_waste_daily` | sama pola outlet |
| `aggregate/inventory-status` | `v_fnb_inventory_status` | sama pola outlet |
| `aggregate/ingredient-price-daily` | `v_fnb_ingredient_price_daily` | `ingredient_id`, `date_from`, `date_to` (tidak terikat outlet) |
| `rowlevel/fnb-transactions` | `mart_cleaned.fnb_transactions` (902rb baris, terbesar project) | `outlet_id`, `date_from`/`date_to`→`transaction_datetime`, `customer_type`, `item_name` |

**Catatan:** basket analysis (kombinasi item per struk) sengaja tidak punya endpoint tersendiri — business rule M3.1/M3.2: harus row-level manual dari `fnb-transactions` per `transaction_id`, tidak bisa direkonstruksi dari agregat manapun.

## Facility/Ops (`/api/facility`)

| Path | Sumber | Filter |
|---|---|---|
| `aggregate/room-status-daily` | `v_facility_room_status_daily` | `property_id`, `room_id`, `date_from`, `date_to` |
| `aggregate/housekeeping-room-type-daily` | `v_housekeeping_room_type_daily` | `property_id`, `date_from`, `date_to` |
| `aggregate/housekeeping-property-daily` | `v_housekeeping_property_daily` | sama |
| `aggregate/housekeeping-staff-daily` | `v_housekeeping_staff_daily` | `staff_id`, `date_from`, `date_to` |
| `aggregate/maintenance-ticket-daily` | `v_maintenance_ticket_daily` | `property_id`, `date_from`, `date_to` — respons termasuk `pending_count` dan `avg_exceeds_sla_threshold` terpisah (business rule M3.1/M3.2, tidak disederhanakan) |
| `aggregate/maintenance-cost-daily` | `v_maintenance_cost_daily` | `property_id`, `date_from`, `date_to` |
| `aggregate/maintenance-room-recurrence-yearly` | `v_maintenance_room_recurrence_yearly` | `room_id`, `year` |
| `aggregate/maintenance-property-benchmark-yearly` | `v_maintenance_property_benchmark_yearly` | `property_id`, `year` |
| `aggregate/maintenance-technician-daily` | `v_maintenance_technician_daily` | `assigned_staff_id`, `date_from`, `date_to` |
| `rowlevel/maintenance-tickets` | `mart_cleaned.maintenance_tickets` | `property_id`, `room_id`, `date_from`/`date_to`→`reported_date`, `status`, `priority` |

## Spa & Event (`/api/spa-event`)

| Path | Sumber | Filter |
|---|---|---|
| `aggregate/spa-daily` | `v_spa_daily` | `property_id`, `date_from`, `date_to` |
| `aggregate/spa-customer-type-daily` | `v_spa_customer_type_daily` | sama |
| `aggregate/spa-service-daily` | `v_spa_service_daily` | sama |
| `aggregate/event-venue-daily` | `v_event_venue_daily` | `venue_id`, `property_id`, `date_from`, `date_to` |
| `aggregate/event-property-daily` | `v_event_property_daily` | `property_id`, `date_from`, `date_to` |
| `aggregate/event-type-daily` | `v_event_type_daily` | sama |
| `rowlevel/event-bookings` | `mart_cleaned.event_bookings` | `property_id`, `venue_id`, `date_from`/`date_to`→`event_date`, `event_type`, `status` |

**Catatan:** repeat-client-event dan cross-sell spa×event sengaja tidak punya endpoint — business rule M3.1/M3.2: `client_name` teks bebas tanpa ID terstruktur, tidak andal untuk deteksi otomatis.

## HR (`/api/hr`)

| Path | Sumber | Filter |
|---|---|---|
| `aggregate/attendance-daily` | `v_hr_attendance_daily` | `property_id` **dan** `department_name` (2 filter wajib sekaligus, satu-satunya domain begitu), `date_from`, `date_to` |
| `aggregate/employee-monthly` | `v_hr_employee_monthly` | `employee_id`, `property_id`, `date_from`, `date_to` |
| `aggregate/employee-performance-semester` | `v_hr_employee_performance_semester` | `employee_id`, `property_id`, `review_period` |
| `aggregate/turnover-snapshot` | `v_hr_turnover_snapshot` | `property_id`, `department_name`, `date_from`, `date_to` |
| `aggregate/headcount-status-daily` | `v_hr_headcount_status_daily` | sama + `status_name` |
| `aggregate/performance-department-semester` | `v_hr_performance_department_semester` | `property_id`, `department_name`, `review_period` |
| `aggregate/performance-by-status-semester` | `v_hr_performance_by_status_semester` | `property_id`, `status_name`, `review_period` |
| `aggregate/watchlist-monthly` | `v_hr_watchlist_monthly` | `employee_id`, `property_id`, `date_from`, `date_to` |
| `rowlevel/staff-shifts` | `mart_cleaned.staff_shifts` | `employee_id`, `date_from`, `date_to`, `status` |
| `rowlevel/employee-performance` | `mart_cleaned.employee_performance` | `employee_id`, `review_period` |

**Business rule kritis: tidak ada endpoint payroll di domain ini** — `GET /api/hr/rowlevel/payroll` sengaja 404 (dikonfirmasi lewat panggilan HTTP nyata). Payroll eksklusif `corporate-financial`.

## Corporate/Financial (`/api/corporate-financial`)

| Path | Sumber | Filter |
|---|---|---|
| `aggregate/departmental-margin` | `v_financial_departmental_margin` | `property_id`, `business_line_name`, `date_from`, `date_to` — **`Overall`/`Corporate Overhead` tidak akan pernah muncul**, filter itu sudah tertanam di view (M3.2), bukan di API |
| `aggregate/gop-overhead` | `v_financial_gop_overhead` | `property_id`, `date_from`, `date_to` — sumber GOP/overhead yang benar |
| `aggregate/revenue-runrate-daily` | `v_financial_revenue_runrate_daily` | `property_id`, `date_from`, `date_to` |
| `aggregate/payroll-department-monthly` | `v_payroll_department_monthly` | `property_id`, `department_name`, `date_from`, `date_to` |
| `aggregate/service-charge-monthly` | `v_financial_service_charge_monthly` | `property_id`, `date_from`, `date_to` |
| `aggregate/labor-cost-monthly` | `v_financial_labor_cost_monthly` | sama |
| `aggregate/payroll-access-level-monthly` | `v_payroll_access_level_monthly` | sama + `access_level_name` |
| `aggregate/business-line-group-monthly` | `v_financial_business_line_group_monthly` | `business_line_name`, `date_from`, `date_to` — **grain grup, tanpa `property_id`** (larangan akses Property/GM Analyst, lihat di bawah) |
| `aggregate/property-benchmark-monthly` | `v_financial_property_benchmark_monthly` | `property_id`, `date_from`, `date_to` |
| `rowlevel/financial-summary` | `mart_cleaned.financial_summary` | `property_id`, `period_from`/`period_to`, `department` |
| `rowlevel/payroll` | `mart_cleaned.payroll` | `employee_id`, `period_from`, `period_to` |

**Contoh — konfirmasi business rule end-to-end:**
```bash
curl "http://127.0.0.1:8000/api/corporate-financial/aggregate/departmental-margin?property_id=P01"
# business_line_name hasil selalu hanya {"Room","F&B","Spa&Event"} — tidak pernah "Overall"/"Corporate Overhead"
```

## Property/GM Analyst

**Tidak ada endpoint baru** — union domain #1-5 di atas (Revenue, F&B, Facility, Spa & Event, HR — **bukan** Corporate/Financial), dipakai dengan `property_id` diisi eksplisit ke properti yang jadi tanggung jawab GM tersebut. Diverifikasi lewat HTTP nyata: kelima domain, difilter `property_id=P02`, seluruhnya mengembalikan data yang benar-benar terbatas ke P02.

**Konvensi (belum ditegakkan teknis — itu cakupan Milestone 3.5):**
- WAJIB selalu sertakan `property_id` di tiap panggilan (endpoint tidak memaksa ini di M3.4).
- DILARANG akses domain `corporate-financial` sama sekali, termasuk `business-line-group-monthly` yang levelnya grup lintas-properti.

## Verifikasi

12 route (6 domain × 2) diuji via `uvicorn` sungguhan + panggilan HTTP nyata (bukan baca kode) — hasil lengkap ada di `milestones/3.4-multi-endpoint-api-analyst/{logs.md,report.md}`.
