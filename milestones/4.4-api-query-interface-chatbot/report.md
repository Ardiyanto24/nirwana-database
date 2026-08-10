# Milestone 4.4: API Query Interface untuk AI Chatbot — Report

**Status:** Completed
**Date completed:** 2026-08-10

## Kriteria Keberhasilan — Hasil

- [x] **Sampel persona dari masing-masing tingkat (Staff, Manager, Korporat) menghasilkan data sesuai cakupan akses role menurut `role_permissions`.** — Diuji HTTP nyata: Staff (Front Office Staff, F&B Staff, Housekeeping Staff, Spa & Event Staff, HR Staff), Manager (Finance Manager), Korporat (Corporate Revenue Director, CEO) — seluruhnya mengembalikan data sesuai domain yang diizinkan `role_permissions` masing-masing, diverifikasi lewat query production langsung sebagai ground truth sebelum tiap tes.
- [x] **Permintaan domain di luar cakupan role (uji terkontrol) ditolak API, tidak diteruskan ke database.** — `authorize()` (`authz.py`) selalu dipanggil sebelum whitelist lookup maupun koneksi ke kredensial domain manapun — dibuktikan lewat 403 untuk seluruh percobaan cross-domain (Front Office Staff→fnb, HR Staff→financial/guests_pii/guests_profial, Housekeeping Staff→spa_event, Spa & Event Staff→facility, role_title tak dikenal). Uji krusial pemisahan `guests_pii`/`guests_profile` tetap tertegakkan di layer API — dibuktikan dengan role tanpa akses keduanya, karena ditemukan tidak ada satu pun dari 20 persona nyata dengan `guests_profile` tanpa `guests_pii`.
- [x] **API terbukti tidak bisa menjangkau `role_permissions`, tabel `mart_cleaned` di luar peta M4.1, maupun raw data.** — `role_permissions` tidak pernah terdaftar sebagai `view_name` di whitelist manapun (404 struktural, bukan ditolak saat runtime). Setiap query data dieksekusi lewat kredensial domain M4.3 (bukan admin) yang sudah terbukti terisolasi penuh (M4.3 report.md). `chatbot_authz_reader` (kredensial baru M4.4) cuma bisa baca `role_permissions`, tidak ada jalur lain — hasilnya tidak pernah masuk response body.

## Deliverables

- `scripts/chatbot_api/{main.py,authz.py,connections.py,whitelist_<10 domain>.py}` — API FastAPI internal, 67 `view_name` terdaftar lintas 10 domain.
- Kredensial baru `chatbot_authz_reader` (`scripts/chatbot_credentials/role_config_authz.py`) — SELECT-only ke `mart_cleaned.role_permissions`.
- `docs/09-serving-ai-chatbot/api-chatbot.md` — dokumentasi endpoint, parameter, penanda stabil vs berpotensi berubah.
- Update `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` (+1 baris `chatbot_authz_reader` + catatan "Siapa Boleh Memegang").
- Koreksi `scripts/chatbot_views/views_facility.sql` (M4.2 artifact): `v_housekeeping_staff_daily`/`v_maintenance_technician_daily` ditambah `property_id`.

## Deviations from decisions.md

Tidak ada deviasi dari keputusan teknis — seluruh 10 keputusan (topologi, desain route, otorisasi wajib, eksekusi lewat kredensial domain, `own_property` resolve-jangan-percaya, kredensial baru, whitelist per domain, paginasi, dependency, verifikasi HTTP nyata) dieksekusi persis seperti direncanakan. Satu generalisasi teknis muncul di tengah implementasi (bukan deviasi dari keputusan, melainkan detail yang belum terlihat saat perencanaan): `own_property_column` dijadikan konfigurasi per-entry (bukan hardcode `"property_id"`) karena view `guests_pii`/`guests_profile` (M4.2) memakai nama kolom `last_active_property_id`.

## Known Gaps / Follow-ups

- **Gap keamanan M4.2 ditemukan & diperbaiki di sini** (bukan gap M4.4 sendiri): `v_housekeeping_staff_daily`/`v_maintenance_technician_daily` awalnya tidak mengekspos `property_id` sama sekali — tanpa perbaikan, filter `own_property` tidak bisa diterapkan ke kedua view performa individu staff itu (own_property role berpotensi melihat performa staff lintas properti). Ditambal di Fase 2, diverifikasi 0 baris `NULL`.
- **Belum ada konsumen chatbot sungguhan** — API ini siap dipanggil, tapi belum pernah dipanggil oleh sistem AI Chatbot nyata (karena sistem itu sendiri di luar cakupan repo ini). Seluruh verifikasi lewat `curl`/HTTP manual mensimulasikan bagaimana Lapis 1 akan memanggilnya.
- **Bentuk request/response ditandai eksplisit belum final** (lihat `api-chatbot.md` §Penanda Stabil vs Berpotensi Berubah) — sesuai catatan ketidakpastian dokumen sumber sendiri, bukan kelalaian.
- **Tidak ada mekanisme audit log** — setiap panggilan API belum tercatat di mana pun (mis. siapa akses domain apa, kapan, berhasil/ditolak). Ini eksplisit cakupan Milestone 4.5 berikutnya, bukan gap M4.4.
- **Tidak ada rate limiting/circuit breaker** untuk mencegah 1 persona membanjiri kredensial domain tertentu dengan request — konsisten klasifikasi "internal tool" (M3.4), dianggap di luar cakupan sampai ada kebutuhan nyata.

## Handoff Notes

- **Untuk Milestone 4.5 (Audit Log):** Titik integrasi paling wajar adalah di dalam `authorize()` (`authz.py`) — setiap panggilan (berhasil maupun ditolak) sudah otomatis melewati fungsi ini persis sekali per request, tempat paling representatif untuk mencatat `role_title`, `domain`, `view_name`, hasil (allow/deny), dan waktu.
- **Untuk Milestone 4.6 (Uji Ketahanan RBAC):** `scripts/chatbot_api/main.py` + `authz.py` sudah bisa langsung dipakai sebagai basis pengujian sistematis 20 persona — pola uji di `logs.md` milestone ini (role legitimate + cross-domain + own_property override) tinggal diperluas ke seluruh 20 role × domain yang relevan, bukan dirancang ulang dari nol.
- **Kalau bentuk request/response API berubah nanti** (sesuai catatan ketidakpastian dokumen sumber): `authz.py`/`connections.py` (logic akses) tidak perlu disentuh — cukup `main.py`/`whitelist_*.py` yang menyesuaikan, sesuai pemisahan yang sudah dijaga sejak awal (Keputusan #2-6 tidak bergantung bentuk URL/parameter).
