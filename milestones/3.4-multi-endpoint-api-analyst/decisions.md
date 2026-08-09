# Milestone 3.4: Multi-Endpoint API untuk Data Analyst — Decisions

**Sumber:** `docs/03-implementation-plans/04-serving-data-analyst.md`, baris 104-119.
**Prasyarat:** Milestone 3.1 (pemetaan akses), 3.2 (48 view `analyst_views`), 3.3 (50 index, baseline performa) — semua Completed.
**Status:** In Progress
**Date started:** 2026-08-09

## Lingkup Sumber / Contract

- **Lingkup:** Membangun endpoint API terpisah sesuai pola domain (bukan satu endpoint generik) — jalur agregat (dashboard harian/mingguan/bulanan/kuartalan) per domain, dan jalur row-level/investigasi ad-hoc. Termasuk mekanisme filter/parameter yang mencerminkan dimensi yang sudah dipetakan (`property_id`, rentang waktu, dsb).
- **Output:**
  1. Endpoint API per domain (Revenue, F&B, Facility, Spa & Event, HR, Corporate/Financial), jalur agregat dan row-level.
  2. Dokumentasi API (parameter, format respons, contoh pemanggilan) untuk tim Data Analyst.
- **Kriteria Keberhasilan:**
  1. Setiap 6 pola peran (dan Property/GM Analyst sebagai union) bisa mendapatkan data yang relevan lewat endpoint yang sesuai, tanpa perlu mengakses endpoint domain lain di luar cakupannya.
  2. Endpoint row-level berhasil menjawab skenario investigasi ad-hoc representatif (mis. drill-down `bookings` granular untuk suatu periode/properti).

## Temuan Eksplorasi (sebelum breakdown)

- **API ini bukan portfolio-facing seperti `api/` (M1.6)** — `api/` gitignored dan dideploy dari repo terpisah (`nirwana-monitoring-api` di Render) khusus karena butuh URL publik untuk reviewer portofolio (`CLAUDE.md` menyebutnya eksplisit "portfolio-facing exception"). M3.4 adalah tool internal untuk 6 peran analyst Nirwana sendiri, bukan untuk publik.
- **Preseden lebih dekat: Milestone 2.5 menolak pola REST API M1.6** untuk konsumen internal (Data Scientist) — `decisions.md` M2.5: "Ditolak: REST API perantara (mirip pola M1.6 `api/`)... berlawanan dengan alasan arsitektur." Tapi M3.4 beda dari M2.5 karena dokumen sumbernya sendiri eksplisit minta "Multi-Endpoint API" sebagai Output — jadi kesimpulannya bukan "tolak API sama sekali", tapi "bangun API, dengan topologi internal (M2.5) bukan topologi publik (M1.6)".
- **Pola kode `api/` (M1.6) layak dipakai ulang**: FastAPI + `main.py`/`db.py`/`queries.py`, koneksi `psycopg2` `readonly=True` per-request (bukan pool), auto-docs Swagger/ReDoc bawaan FastAPI, whitelist dict untuk endpoint param-driven (`SAMPLE_TABLE_WHITELIST` + `GET /api/sample/{table}`, 404 kalau tidak ada di whitelist) — pola ini persis yang dibutuhkan M3.4 untuk endpoint aggregate/rowlevel per domain.
- **M3.4 tidak perlu auth/isolasi per-peran** — dikonfirmasi eksplisit garis batas M3.5 (KK M3.5: "kredensial terbukti TIDAK BISA mengakses..."), beda kata kerja dari KK M3.4 ("tanpa perlu mengakses" — soal ergonomi struktur, bukan keamanan credential-level).
- `scripts/data_analyst_views/` (M3.2) sudah membagi 6 domain jadi 6 file SQL terpisah — pola file-per-domain yang sama dipakai lagi untuk whitelist M3.4.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — mengikuti presenden project)

### 1. Topologi: in-repo, bukan gitignored/deploy terpisah

Folder `scripts/data_analyst_api/`, konsisten penamaan `scripts/data_analyst_views/`. Alasan: lihat Temuan Eksplorasi — API ini internal, bukan portfolio-facing, jadi tidak butuh alasan M1.6 (URL publik) untuk dipisah repo.

### 2. Pola kode: FastAPI, direplikasi dari `api/`

`main.py` (route registration), `connections.py` (copy pola `get_serving_connection`, bukan import — konvensi copy-lintas-`scripts/*` sejak M2.1). Auto-docs Swagger/ReDoc bawaan, tidak perlu dokumentasi OpenAPI manual. Tidak perlu `slowapi`/CORS — tidak diakses publik/browser lintas origin.

### 3. Desain route: domain sebagai path literal + whitelist parameter

`/api/{domain}/aggregate/{view_name}` dan `/api/{domain}/rowlevel/{table_name}`, domain didaftarkan eksplisit per domain (6×2 = 12 registrasi) — supaya "endpoint terpisah per domain" (KK1) tetap benar secara struktural dan gerbang isolasi M3.5 nanti bisa mengunci per-prefix URL. `view_name`/`table_name` di-whitelist per domain (pola `SAMPLE_TABLE_WHITELIST`), bukan 48 fungsi hardcoded terpisah maupun interpolasi nama tabel bebas dari user.

### 4. File whitelist: 1 file per domain

`whitelist_revenue.py`, dst — konsisten pola `views_<domain>.sql` M3.2, batas file bersih per checkpoint.

### 5. Keamanan query

Nama kolom filter per whitelist entry predefined (bukan bebas dari query string) — value selalu lewat parameter psycopg2 (`%s`), tidak pernah string-interpolated.

### 6. Paginasi row-level wajib

`limit` (default 100, maks 1000) + `offset` (default 0) — `mart_cleaned` punya tabel besar (`fnb_transactions` 902rb, `staff_shifts` 610rb baris).

### 7. Filter opsional, bukan wajib

`property_id`/rentang tanggal opsional (default: tanpa filter). Pembatasan wajib per-peran adalah tanggung jawab M3.5.

### 8. Property/GM Analyst: tidak ada endpoint baru

Union domain #1-5, `property_id` diisi eksplisit oleh pemanggil — konsisten pola M3.2/M3.3.

### 9. Dependency di `requirements.txt` root

`fastapi==0.115.6`, `uvicorn[standard]==0.34.0` — blok baru mengikuti pola `# Dependencies for scripts/<x>/ (Milestone <y>)`. `psycopg2-binary` sudah ada.

### 10. Verifikasi: server sungguhan + HTTP call nyata

`uvicorn` dijalankan lokal, `curl`/`requests` — bukan cuma baca kode.

## Task Breakdown

**Kenapa 8 task / 8 checkpoint:** 6 domain independen dan berukuran kecil (S — 1 file whitelist + 2 route registration + tes HTTP), tiap domain punya file whitelist sendiri sehingga checkpoint-per-domain cocok dengan batas file yang sudah alami terpisah (sama alasan M3.2 asli).

### Fase 0 — Fondasi
1. `scripts/data_analyst_api/{main.py,connections.py}` — app FastAPI, `/health`, helper generik `query_aggregate`/`query_rowlevel`. Update `requirements.txt`. Jalankan `uvicorn`, curl `/health` — Acceptance: server start, `/health` 200 — Verify: curl langsung — S

**✅ Checkpoint 1** — commit + log.

### Fase 1 — Revenue
2. `whitelist_revenue.py` (8 view + `bookings`/`pricing_history`), 2 route. Tes HTTP aggregate + row-level (cancellation P01 Maret) — M

**✅ Checkpoint 2** — commit + log.

### Fase 2 — F&B
3. `whitelist_fnb.py` (8 view + `fnb_transactions`). Tes HTTP — M

**✅ Checkpoint 3** — commit + log.

### Fase 3 — Facility/Ops
4. `whitelist_facility.py` (9 view + `maintenance_tickets`). Tes HTTP — M

**✅ Checkpoint 4** — commit + log.

### Fase 4 — Spa & Event
5. `whitelist_spa_event.py` (6 view + `event_bookings`). Tes HTTP — S

**✅ Checkpoint 5** — commit + log.

### Fase 5 — HR
6. `whitelist_hr.py` (8 view + `staff_shifts`/`employee_performance`, tanpa payroll). Tes HTTP — M

**✅ Checkpoint 6** — commit + log.

### Fase 6 — Corporate/Financial
7. `whitelist_corporate_financial.py` (9 view + `financial_summary`/`payroll`). Tes HTTP, konfirmasi business rule `Overall` exclusion end-to-end — M

**✅ Checkpoint 7** — commit + log.

### Fase 7 — Finalisasi
8. `docs/08-serving-data-analyst/api-analyst.md` + verifikasi KK1+KK2 lintas domain + `report.md` — M

**✅ Checkpoint 8 (final)** — commit; tanya user sebelum push.
