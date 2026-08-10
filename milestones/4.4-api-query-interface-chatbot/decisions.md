# Milestone 4.4: API Query Interface untuk AI Chatbot — Decisions

**Sumber:** `docs/03-implementation-plans/05-serving-ai-chatbot.md`, Milestone 4.4 (baris 106-124).
**Prasyarat:** Milestone 4.1 (pemetaan RBAC, Completed), 4.2 (67 view `chatbot_views`, Completed), 4.3 (10 kredensial domain read-only, Completed).
**Status:** In Progress
**Date started:** 2026-08-10

## Lingkup Sumber / Contract

- **Lingkup:** Membangun API yang menjadi jalur query dari sistem AI Chatbot ke `mart_aggregated` — menerima permintaan yang sudah lolos validasi intent di Lapis 1, lalu mengeksekusi ke view yang sesuai dengan role dan domain yang diminta. Skema API ditandai eksplisit masih bisa berubah — desain harus memisahkan "logic akses" (stabil) dari "bentuk request/response" (bisa berubah).
- **Output:**
  1. Endpoint API yang menerima permintaan (role/persona, domain, parameter filter) dan mengembalikan hasil dari view yang sesuai.
  2. Mekanisme penolakan eksplisit untuk permintaan di luar cakupan role (lapisan tambahan, bukan pengganti Lapis 1).
  3. Dokumentasi API dengan penanda jelas bagian stabil vs berpotensi berubah.
- **Kriteria Keberhasilan:**
  1. Sampel persona dari masing-masing tingkat (Staff, Manager, Korporat) menghasilkan data sesuai cakupan akses role menurut `role_permissions`.
  2. Permintaan domain di luar cakupan role (uji terkontrol) ditolak API, tidak diteruskan ke database.
  3. API terbukti tidak bisa menjangkau `role_permissions`, tabel `mart_cleaned` di luar peta M4.1, maupun raw data.

## Temuan Eksplorasi (sebelum breakdown)

- Preseden terdekat: `milestones/3.4-multi-endpoint-api-analyst/` (`scripts/data_analyst_api/`) — FastAPI internal (bukan portfolio-facing), route whitelist per domain, filter parametrized (psycopg2 `%s`, tidak pernah interpolasi bebas), paginasi wajib row-level (`limit`/`offset`).
- **Beda struktural krusial dari M3.4**: M3.4 memakai 1 koneksi admin untuk semua query — isolasi sesungguhnya diserahkan ke M3.5 yang dipakai manusia analyst **langsung**, di luar API. API M3.4 bukan trust boundary sesungguhnya. **API M4.4 justru harus jadi trust boundary itu** — dokumen sumber eksplisit "tidak boleh mengasumsikan Lapis 1 selalu benar". Chatbot tidak punya "manusia pemegang kredensial M4.3 langsung" seperti analyst — API adalah satu-satunya perantara ke seluruh 10 kredensial domain.
- **Gap ditemukan**: tidak ada satu pun dari 10 kredensial M4.3 yang bisa baca `role_permissions` (memang sengaja, diverifikasi M4.3) — tapi API M4.4 butuh cara membaca tabel itu untuk memutuskan otorisasi per request. Dibutuhkan kredensial ke-11, scoped SELECT-only ke `mart_cleaned.role_permissions` saja, murni untuk keputusan internal API — bukan untuk dijawabkan ke pengguna chatbot manapun.
- `mart_cleaned.employees` (kolom: `employee_id`, `property_id`, `full_name`, `role_title`, `department`, `access_level`, `hire_date`, `status`) dan `chatbot_views.v_employees_directory` (M4.2, kolom: `employee_id`, `full_name`, `property_id`, `property_name`, `department_name`, `access_level_name`) sudah cukup untuk resolve `employee_id` → `property_id` sebenarnya, dipakai kredensial `employees_directory_chatbot_reader` (M4.3) yang sudah ada.
- `corporate_master.role_permissions` (production, disinkronkan M4.1): kolom `role_title`, `data_domain`, `access_scope`, `permission_type` — 77 baris, cocok persis di serving `mart_cleaned.role_permissions` (disinkronkan reverse ETL M2.4).

## Keputusan Teknis (dikunci tanpa AskUserQuestion — turunan langsung M3.4/M4.1-4.3)

### 1. Topologi: in-repo, tidak dideploy

`scripts/chatbot_api/`, FastAPI, tidak ada auth/CORS/rate-limit — klasifikasi sama M3.4 (internal, bukan portfolio-facing).

### 2. Desain route: 1 pola per domain, whitelist gabungan

`GET /chatbot/{domain}/{view_name}` — beda dari M3.4 (`aggregate`/`rowlevel` terpisah): di `chatbot_views` seluruh view (agregat maupun lookup) sudah seragam satu schema, tidak perlu 2 namespace URL. `view_name` di-whitelist per domain.

### 3. Otorisasi wajib per request — sumber kebenaran `role_permissions`

Parameter `role_title` wajib di setiap request (klaim identitas dari Lapis 1, **tidak dipercaya buta**). API lookup `mart_cleaned.role_permissions` lewat kredensial baru (#6) sebelum query data apa pun: `role_title` tidak dikenal → 403; domain diminta tidak ada di cakupan role itu → 403.

### 4. Eksekusi query lewat kredensial domain M4.3, bukan admin

Setelah lolos otorisasi #3, API connect pakai kredensial domain yang sesuai (`RESERVATION_CHATBOT_READER_DB_URL`, dst) untuk mengeksekusi query sesungguhnya — kalau logic #3 pernah punya bug, kredensial itu (sudah terverifikasi M4.3, 10/10 isolated) tetap jadi pengaman independen. Ini defense-in-depth sesungguhnya, beda dari M3.4 yang eksplisit menyebut isolasinya "cheap, bukan mekanisme isolasi nyata".

### 5. Penerapan `own_property`: resolve, jangan percaya klaim

`access_scope == 'own_property'` → `employee_id` wajib di request; API resolve `property_id` sebenarnya lewat `chatbot_views.v_employees_directory` (kredensial `employees_directory_chatbot_reader`), **override** filter `property_id` ke hasil resolve itu — mengabaikan `property_id` apa pun yang diklaim caller. `access_scope == 'all_properties'` → `property_id` jadi filter opsional biasa (boleh dipakai untuk mempersempit, mis. CEO membandingkan 1 properti).

### 6. Kredensial baru: `chatbot_authz_reader`

`SELECT`-only ke `mart_cleaned.role_permissions` saja. Dibuat dengan pola identik `setup_chatbot_roles.py` (M4.3) — ditambahkan sebagai `role_config_authz.py` baru di `scripts/chatbot_credentials/`, didaftarkan ke `ROLE_CONFIGS`. Hasil query tabel ini **tidak pernah** diteruskan sebagai response endpoint manapun — cuma dipakai internal untuk keputusan allow/deny (diuji eksplisit di Fase 6).

### 7. Whitelist: 1 file per domain

`whitelist_<domain>.py` di `scripts/chatbot_api/`, format `{"source": "chatbot_views.<view>", "filters": [...]}` — pola persis M3.4.

### 8. Paginasi row-level wajib

`limit` (default 100, maks 1000) + `offset` (default 0) — reuse konstanta M3.4.

### 9. Dependency

`fastapi`/`uvicorn` sudah ada di `requirements.txt` sejak M3.4 — tidak ada tambahan.

### 10. Verifikasi: server sungguhan + HTTP call nyata

`uvicorn` lokal, `requests`/`curl` — bukan baca kode saja, sama pola M3.4.

## Task Breakdown

12 task, 7 fase, 7 checkpoint (commit tiap checkpoint; checkpoint final commit + tanya user dulu sebelum push).

### Fase 0 — Fondasi
1. Kredensial `chatbot_authz_reader` (`role_config_authz.py`, ditambahkan ke `ROLE_CONFIGS` `setup_chatbot_roles.py`). `scripts/chatbot_api/{main.py,connections.py}` — koneksi per-domain (10 kredensial M4.3, dari `.env`) + koneksi authz + helper `resolve_property_id(employee_id)` (query `v_employees_directory` via `employees_directory_chatbot_reader`) + helper otorisasi (query `role_permissions` via `chatbot_authz_reader`). `/health`. Test server start. — M — **Selesai**

**✅ Checkpoint 0** — commit + log.

### Fase 1 — Reservation + F&B
2. `whitelist_reservation.py` (10 entry) + register route. Tes HTTP: persona legitimate + percobaan domain lain ditolak. — M — **Selesai**
3. `whitelist_fnb.py` (11 entry) + register route + tes. — M — **Selesai**

**✅ Checkpoint 1** — commit + log.

### Fase 2 — Facility + Spa & Event
4. `whitelist_facility.py` (12 entry) + tes. — M — **Selesai**. Gap ditemukan & diperbaiki: `v_housekeeping_staff_daily`/`v_maintenance_technician_daily` (M4.2) tidak punya `property_id` sama sekali, ditambal via `views_facility.sql` (join `dim_employee` sudah ada, tinggal `SELECT`).
5. `whitelist_spa_event.py` (9 entry) + tes. — M — **Selesai**

**✅ Checkpoint 2** — commit + log.

### Fase 3 — HR + Financial
6. `whitelist_hr.py` (10 entry, tanpa payroll) + tes: role HR mencoba domain `financial` → 403. — M
7. `whitelist_financial.py` (11 entry) + tes. — M

**✅ Checkpoint 3** — commit + log.

### Fase 4 — 4 Domain Granular
8. `whitelist_properties_ref.py`/`whitelist_employees_directory.py` (1 entry masing-masing) + tes. — S
9. `whitelist_guests_pii.py`/`whitelist_guests_profile.py` (1 entry masing-masing) + **uji krusial**: role permitted `guests_pii` memanggil `/chatbot/guests_profile/...` → 403 di layer API (lapisan independen dari deny DB M4.3). — M

**✅ Checkpoint 4** — commit + log.

### Fase 5 — `own_property` end-to-end
10. Tes eksplisit: role `own_property` (Front Office Staff) dengan `employee_id` sungguhan → hasil difilter ke `property_id` karyawan itu; percobaan menyisipkan `property_id` lain di request diabaikan/di-override. Role `all_properties` (Corporate Revenue Director) → bebas filter properti apa pun. — M

**✅ Checkpoint 5** — commit + log.

### Fase 6 — Finalisasi
11. Sampel lintas 3 tingkat (minimal 1 Staff/Manager/Korporat) verifikasi KK1.
12. Tulis `docs/09-serving-ai-chatbot/api-chatbot.md` (endpoint, parameter, penanda stabil vs berpotensi berubah). Update `kebijakan-akses-kredensial-scoped.md` (+1 baris `chatbot_authz_reader`). Verifikasi ulang KK1-KK3, tulis `report.md`. — M

**✅ Checkpoint 6 (final)** — commit; tanya user sebelum push.
