# Milestone 1.6: API Publik Data Monitoring — Report

**Status:** Completed
**Date completed:** 2026-08-07

## Kriteria Keberhasilan — Hasil

- [x] **Endpoint API bisa diakses publik (tanpa login/API key) dan mengembalikan data yang konsisten dengan `monitoring.current_status` dan tabel `monitoring.*` lain.** — Terpenuhi. Deploy publik di Render: https://nirwana-monitoring-api.onrender.com. Seluruh 7 endpoint data diverifikasi dari luar (curl eksternal, bukan localhost) setelah deploy: `/api/status/tables` 23 baris, `/api/dq/summary` 23 baris, `/api/dq/failures` 3 baris, `/api/dq/dirty-proportion` 8 baris, `/api/dq/anomalies` 6 baris, `/api/schema-drift` 0 baris, `/api/alerts` 28 baris — semuanya konsisten dengan panel Grafana Milestone 1.5.
- [x] **Tidak ada endpoint yang mengekspos kredensial atau data production sensitif di luar whitelist yang disetujui.** — Terpenuhi, diverifikasi dua lapis: (1) teknis di level Postgres — role `monitoring_api_reader` ditolak SELECT ke tabel di luar whitelist dan ditolak INSERT sama sekali (`scripts/api_reader/setup_reader_role.py`); (2) level aplikasi — `/api/sample/{table}` mengembalikan 404 untuk tabel di luar whitelist, dikonfirmasi ulang dari deployment publik (`/api/sample/guests` → 404).
- [x] **Rate limiting per IP terbukti aktif saat diuji coba terkontrol.** — Terpenuhi, diuji lokal: `RATE_LIMIT=3/menit`, request ke-4 & ke-5 dalam window sama → HTTP 429. Konfigurasi yang sama (`slowapi`, default 60/menit) aktif di deployment publik.

## Deliverables

- Role Postgres read-only `monitoring_api_reader` (`scripts/api_reader/grants.sql`, `scripts/api_reader/setup_reader_role.py`) — scoped ke `monitoring.*` (seluruh tabel + otomatis untuk tabel baru via `ALTER DEFAULT PRIVILEGES`) plus 3 tabel whitelist non-sensitif.
- FastAPI app di `api/` — 9 endpoint (`/health`, `/api/status/tables`, `/api/dq/summary`, `/api/dq/failures`, `/api/dq/dirty-proportion`, `/api/dq/anomalies`, `/api/schema-drift`, `/api/alerts`, `/api/sample/{table}`), rate limiting per IP (`slowapi`), CORS terbuka.
- Repo GitHub publik: https://github.com/Ardiyanto24/nirwana-monitoring-api.
- Deploy publik live: **https://nirwana-monitoring-api.onrender.com** (Render free tier, Blueprint `render.yaml`).
- `milestones/1.6-public-monitoring-api/{decisions,logs,report}.md`.
- Penambahan section Milestone 1.6 & 1.7 di `docs/03-implementation-plans/01-monitoring-data-production-fase1.md`.

## Deviations from decisions.md

- Tidak ada deviasi teknis — seluruh keputusan (FastAPI, data scope, proteksi rate-limit-tanpa-auth, repo terpisah, Render sebagai platform final dipilih user saat konfirmasi Task 7) diimplementasikan sesuai rencana.

## Catatan Proses

Milestone ini sempat dieksekusi (Task 1-6) sebelum ditulis sebagai rancangan resmi di source doc — dikoreksi begitu ditegur user, lihat entri log 2026-08-07 "Koreksi proses" dan penambahan section di `docs/03-implementation-plans/01-monitoring-data-production-fase1.md`. Dicatat di sini secara permanen sebagai bagian riwayat milestone, bukan dihapus dari jejak.

Deploy publik (Task 7) mengalami 4 hambatan berurutan sebelum berhasil (repo tidak ter-authorize ke Render, Start Command salah, env var lupa diisi, env var korup whitespace) — seluruhnya diselesaikan lewat panduan langkah-demi-langkah karena aksinya harus dilakukan user sendiri (Render adalah akun pihak ketiga). Detail lengkap tiap hambatan & fix ada di `logs.md`.

## Known Gaps / Follow-ups

- Tidak ada gap terhadap Kriteria Keberhasilan milestone ini sendiri.
- Render free tier: service bisa "sleep" setelah idle (~15 menit) dan butuh beberapa detik cold-start di request pertama setelahnya — relevan untuk ekspektasi Milestone 1.7 (website publik akan terasa lambat di load pertama jika API sempat idle). Dicatat sebagai konteks, bukan bug.

## Handoff Notes

- **Base URL untuk Milestone 1.7**: `https://nirwana-monitoring-api.onrender.com`. 9 endpoint tersedia (lihat Deliverables), semua GET, JSON array of object, tanpa auth, rate limit 60/menit per IP default.
- **`/api/sample/{table}`**: `table` ∈ `properties`, `fnb_outlets`, `rooms` — tabel lain 404.
- **Rotasi kredensial**: `scripts/api_reader/setup_reader_role.py` aman dijalankan ulang (idempotent, generate password baru, update `api/.env` lokal otomatis) — tapi env var `API_DB_URL` di Render **harus di-update manual** setelahnya (pelajaran dari hambatan Task 7: pastikan tidak ada whitespace tersisa saat paste).
- **CORS**: saat ini `*` (semua origin). Setelah Milestone 1.7 punya domain final, pertimbangkan mempersempit `CORS_ALLOW_ORIGINS` di env var Render ke domain website itu saja.
