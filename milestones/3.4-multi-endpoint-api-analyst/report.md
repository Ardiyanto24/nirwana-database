# Milestone 3.4: Multi-Endpoint API untuk Data Analyst — Report

**Status:** Completed
**Date completed:** 2026-08-09

## Kriteria Keberhasilan — Hasil

- [x] **KK1 — Setiap 6 pola peran (dan Property/GM Analyst sebagai union) bisa mendapatkan data yang relevan dengan perannya lewat endpoint yang sesuai, tanpa perlu mengakses endpoint domain lain di luar cakupannya.** Terpenuhi. 12 route (6 domain × 2 jalur) diverifikasi via HTTP nyata terhadap server `uvicorn` sungguhan — bukan asumsi. Struktural: tiap domain punya prefix URL sendiri (`/api/revenue`, `/api/fnb`, dst) dengan whitelist view/tabel terpisah, tidak ada endpoint generik lintas domain. Property/GM Analyst diverifikasi eksplisit: 5 domain (bukan Corporate/Financial) dipanggil dengan `property_id=P02`, seluruhnya mengembalikan data yang benar-benar terbatas ke P02 tanpa endpoint baru.
- [x] **KK2 — Endpoint row-level berhasil menjawab skenario investigasi ad-hoc yang representatif.** Terpenuhi, diverifikasi dengan skenario **persis** yang dikutip dokumen sumber: `GET /api/revenue/rowlevel/bookings?property_id=P01&date_from=2024-03-01&date_to=2024-04-01&status=cancelled` ("kenapa cancellation Bali Maret 2024 tinggi") mengembalikan booking granular yang benar. Skenario row-level lain juga diverifikasi tiap domain: `fnb-transactions` (902rb baris), `maintenance-tickets`, `event-bookings`, `staff-shifts`, `financial-summary`/`payroll`.

## Deliverables

- `docs/08-serving-data-analyst/api-analyst.md` — dokumentasi lengkap 12 route, filter per view/tabel, contoh `curl`.
- `scripts/data_analyst_api/{main.py, connections.py, whitelist_revenue.py, whitelist_fnb.py, whitelist_facility.py, whitelist_spa_event.py, whitelist_hr.py, whitelist_corporate_financial.py}`.
- `requirements.txt` — blok `fastapi`/`uvicorn` baru.
- `milestones/3.4-multi-endpoint-api-analyst/{decisions,logs}.md`.

## Cakupan Final

12 route aktif: 6 domain × (1 aggregate whitelisted + 1 row-level whitelisted). Whitelist mencakup seluruh 48 view `analyst_views` (M3.2) dan 9 tabel row-level `mart_cleaned` yang dipetakan M3.1.

## Business Rule Kritis Diverifikasi End-to-End (DB → view → API)

1. **`Overall`/`Corporate Overhead` exclusion** (Corporate/Financial, paling berisiko sejak M3.1): `GET /api/corporate-financial/aggregate/departmental-margin?property_id=P01` tanpa filter `business_line_name` apa pun tetap hanya mengembalikan `F&B`/`Room`/`Spa&Event` — dikonfirmasi lewat panggilan HTTP nyata, bukan cuma di level SQL (M3.2/M3.3).
2. **Payroll eksklusif Corporate/Financial**: `GET /api/hr/rowlevel/payroll` → 404 nyata — endpoint itu memang tidak terdaftar di whitelist HR.
3. **SLA `pending_count` terpisah dari breach**: `v_maintenance_ticket_daily` lewat endpoint tetap mengembalikan `pending_count` dan `avg_exceeds_sla_threshold` sebagai kolom terpisah, tidak disederhanakan di layer API.
4. **Basket analysis dan repeat-client-event/cross-sell**: sengaja tidak ada endpoint — didokumentasikan eksplisit di `api-analyst.md`, bukan cuma "lupa dibuat".

## Deviations from decisions.md

**1 penyesuaian operasional, tidak mengubah keputusan inti:** `uvicorn --reload` (WatchFiles) terbukti tidak konsisten memuat ulang modul di lingkungan sesi ini — perubahan file terdeteksi tapi server lama kadang tetap melayani request (404 palsu untuk route yang baru saja ditambahkan). Solusi: tiap checkpoint domain, server di-kill dan direstart bersih (bukan mengandalkan `--reload`) sebelum verifikasi HTTP. Tidak memengaruhi keputusan desain apa pun — murni prosedur verifikasi.

## Known Gaps / Follow-ups

- **Tidak ada auth/isolasi per-peran** — sesuai desain (Milestone 3.5), API ini masih bisa diakses siapa pun yang punya akses ke server (belum dideploy ke mana pun, cuma jalan lokal `uvicorn`). Endpoint `corporate-financial` secara teknis masih bisa dipanggil oleh siapa saja termasuk role yang seharusnya tidak berwenang (HR Analyst, Property/GM) — larangan saat ini murni konvensi dokumentasi, bukan ditegakkan sistem.
- **Filter properti tidak wajib secara teknis** — Property/GM Analyst *seharusnya* selalu menyertakan `property_id`, tapi API tidak memaksanya (Keputusan #7). Kalau dipanggil tanpa `property_id`, endpoint tetap mengembalikan data lintas 5 properti — bukan bug, tapi risiko kalau dipakai keliru sebelum M3.5 menegakkan isolasi sungguhan.
- **`fact_revenue_pace_booking_snapshot`** tetap tidak punya endpoint — konsisten Known Gap M3.1/M3.2/M3.3 (status implementasi append-only belum final).
- **`dim_employee.property_id`-dependent endpoints** (`employee-monthly`, `employee-performance-semester`, `watchlist-monthly`) memakai kolom yang baru ada sejak M5.7 — bekerja benar, tapi belum ada uji beban khusus untuk kolom trailing (non-indexed) ini dibanding kolom yang memang diindeks M3.3.

## Handoff Notes

- **Milestone 3.5 (Isolasi Akses):** struktur URL per-domain (`/api/{domain}/...`) di dokumen ini dirancang eksplisit supaya gerbang akses (API key/middleware/reverse-proxy) bisa mengunci per-prefix — HR Analyst hanya boleh `/api/hr/*`, Property/GM Analyst boleh 5 domain tapi wajib `property_id` di-inject otomatis (bukan opsional dari sisi pemanggil), dst.
- **Kalau API ini nanti perlu benar-benar di-deploy** (bukan cuma jalan lokal): ikuti pola `api/` (M1.6) untuk konfigurasi deployment (`render.yaml`, dsb) TAPI evaluasi ulang apakah tetap perlu gitignored+repo terpisah — kemungkinan tidak, karena tetap internal-only meski di-deploy (beda alasan dari `api/` yang menyajikan monitoring publik).
- **Siapa pun yang menambah view/tabel baru** ke `analyst_views`/`mart_cleaned` untuk Data Analyst: tambahkan entri whitelist di file domain terkait (`scripts/data_analyst_api/whitelist_<domain>.py`), bukan endpoint baru — pola parametrized+whitelisted sudah menampung penambahan tanpa perlu route baru.
