# Milestone 1.6: API Publik Data Monitoring

**Source:** `docs/03-implementation-plans/01-monitoring-data-production-fase1.md` (baris ditambahkan 2026-08-07, lihat catatan penambahan sebelum Milestone 1.6 di dokumen tsb) — milestone baru di luar rancangan Fase 1 semula: Grafana Cloud free tier tidak mendukung publicly shared dashboard (diverifikasi via dokumentasi Grafana), sehingga diputuskan membangun API + website sendiri agar hasil monitoring bisa diakses publik tanpa expose instance Grafana/kredensial Supabase.

> **Catatan proses:** Implementasi Task 1–6 milestone ini sempat berjalan sebelum baris di atas ditambahkan ke source doc — `decisions.md` ini sendiri sudah ditulis lebih dulu (sesuai urutan yang benar), tapi penambahan ke `docs/03-implementation-plans/01-monitoring-data-production-fase1.md` baru menyusul setelah ditegur user. Dicatat di sini sebagai penyimpangan proses yang jujur, bukan disembunyikan — lihat `report.md` untuk detail.

**Status:** Done — lihat `report.md` (Completed, seluruh Kriteria Keberhasilan terpenuhi)
**Date started:** 2026-08-07

## Contract (ditentukan bersama user, bukan dari source doc)

- **Lingkup:** API read-only yang menarik data dari `monitoring.*` (hasil M1.2-1.4: volume/freshness, DQ, dirty proportion, value anomaly, schema drift, alerts) plus sample data non-sensitif dari tabel production, untuk dikonsumsi website publik Milestone 1.7.
- **Output:** Service FastAPI ter-deploy publik (Railway/Render free tier), endpoint-endpoint read-only di atas `monitoring.*` + whitelist sample data production, rate limiting per IP, tanpa autentikasi.
- **Kriteria keberhasilan:** Endpoint API bisa diakses publik (tanpa login/API key) dan mengembalikan data monitoring terkini yang konsisten dengan `monitoring.current_status`/tabel lain; tidak ada endpoint yang mengekspos kredensial atau data production sensitif (PII, finansial, HR) di luar whitelist yang disetujui; rate limiting terbukti aktif saat diuji.

## Task Breakdown

- [ ] Task 1: Setup folder `api/` (FastAPI project skeleton, `requirements.txt`, `.env.example`) — Acceptance: `uvicorn` jalan lokal, endpoint `/health` merespons 200 — Verify: curl lokal — XS
- [ ] Task 2: Role Postgres read-only baru khusus API (`monitoring_api_reader`), scoped SELECT-only ke schema `monitoring` + tabel whitelist production — Acceptance: role tidak bisa INSERT/UPDATE/DELETE, tidak bisa SELECT tabel di luar whitelist — Verify: uji query manual dengan role tsb ditolak untuk tabel di luar whitelist — S
- [ ] Task 3: Whitelist sample data production — pilih tabel/kolom non-sensitif (mis. `corporate_master.properties`, `corporate_master.property_types` — bukan `hr_finance.*`, bukan kolom guest/finance) — Acceptance: daftar tertulis + alasan tiap tabel dipilih aman — Verify: cross-check `docs/01-architecture/Metadata.md` tiap tabel yang dipilih — S
- [ ] Task 4: Endpoint `monitoring.current_status` (volume+freshness 23 tabel) — Acceptance: `GET /api/status/tables` mengembalikan 23 baris sesuai view — Verify: bandingkan hasil endpoint vs query langsung — S
- [ ] Task 5: Endpoint DQ (`dq_test_results` ringkasan + detail kegagalan) — Acceptance: `GET /api/dq/summary`, `GET /api/dq/failures` — Verify: hasil cocok dengan panel Grafana yang sudah ada — S
- [ ] Task 6: Endpoint dirty proportion + value anomaly (M1.3) — Acceptance: `GET /api/dq/dirty-proportion`, `GET /api/dq/anomalies` — Verify: cocok dengan `dirty_proportion_snapshot`/`value_anomaly_snapshot` terbaru — S
- [ ] Task 7: Endpoint schema drift (M1.4) — Acceptance: `GET /api/schema-drift` (exclude `_simulation`, sama seperti fix panel Grafana) — Verify: 0 baris untuk kondisi production saat ini — S
- [ ] Task 8: Endpoint alert aktif (M1.2+M1.3 gabungan) — Acceptance: `GET /api/alerts` (exclude `is_simulated=true`) — Verify: cocok dengan panel "Alert Aktif" Grafana — S
- [ ] Task 9: Endpoint sample data production whitelist (Task 3) — Acceptance: `GET /api/sample/{table}` hanya untuk tabel whitelist, 404 untuk tabel lain — Verify: uji tabel whitelist vs non-whitelist — S
- [ ] Task 10: Rate limiting per IP (`slowapi` atau setara) — Acceptance: request ke-N dalam window waktu tertentu mengembalikan 429 — Verify: uji coba terkontrol (burst request lokal) — S
- [ ] Task 11: CORS — izinkan origin domain website Milestone 1.7 (dan `*` sementara sebelum domain final ada) — Acceptance: response header `Access-Control-Allow-Origin` sesuai — Verify: request dari browser origin berbeda — XS
- [ ] Task 12: Deploy ke Railway/Render dari repo terpisah `nirwana-monitoring-api` — Acceptance: endpoint publik bisa diakses via URL — Verify: curl dari luar (bukan localhost) — M
- [ ] Task 13: Verifikasi Kriteria Keberhasilan + `report.md`

**Checkpoint** setelah Task 2 & 3: kredensial/scope akses harus benar dulu sebelum endpoint apa pun dibangun di atasnya — API publik yang salah scope role adalah risiko keamanan langsung, bukan bug biasa.

## Technical Decisions

### Decision: Framework & hosting — FastAPI (Python) di Railway/Render free tier

- **Context:** Perlu backend API publik yang membaca `monitoring.*` dan sebagian data production, di-deploy ke luar komputer lokal.
- **Decision:** FastAPI, deploy ke Railway atau Render (free tier).
- **Alternatives considered:** Cloudflare Worker (TypeScript) + Hyperdrive; Supabase auto-REST (PostgREST) langsung.
- **Rejected because:** Cloudflare Worker berarti bahasa baru (TS) di luar stack Python yang sudah konsisten dipakai seluruh `scripts/`; PostgREST langsung tidak memberi kontrol response shape/agregasi/rate-limiting custom yang dibutuhkan (mis. gabungan alert M1.2+M1.3, filter `_simulation`). FastAPI memakai pola koneksi Postgres yang sudah familiar dari `scripts/monitoring/db.py`.

### Decision: Repo terpisah (`nirwana-monitoring-api`), bukan satu repo dengan `nirwana-database`

- **Context:** `nirwana-database` didefinisikan eksplisit di `CLAUDE.md`-nya sendiri sebagai "hanya sisi database engineering" — API publik adalah consumer/serving-layer concern yang terpisah.
- **Decision:** Folder `api/` dikembangkan di root `nirwana-database` untuk kemudahan development (akses mudah ke dokumentasi schema, `Metadata.md`, dll), tapi **di-gitignore** dari repo ini. Setelah siap, `git init` folder tsb terpisah dan push ke repo GitHub baru `nirwana-monitoring-api`, yang jadi sumber deploy Railway/Render.
- **Alternatives considered:** Tetap satu repo, Railway/Render deploy dari subfolder (root directory config).
- **Rejected because:** Menjaga scope repo `nirwana-database` tetap murni DB engineering (konsisten dengan `CLAUDE.md`), memisahkan kredensial publik (API) dari kredensial internal (monitoring scripts), dan versioning/CI API independen dari perubahan schema database. Simetris dengan keputusan yang sama untuk folder `web/` (Milestone 1.7).

### Decision: Data scope — `monitoring.*` plus sample data non-sensitif dari production

- **Context:** User memilih opsi ini secara eksplisit, bukan opsi "hanya monitoring.*".
- **Decision:** Selain seluruh `monitoring.*`, expose sample data dari whitelist tabel production yang **tidak** memuat PII/data finansial/HR. Whitelist final (Task 3, cross-check `docs/01-architecture/Metadata.md`):
  - `corporate_master.properties` (6 baris) — master 6 properti (nama, kota, region, jumlah kamar, star rating). Data statis, publik by design (setara info di situs hotel).
  - `fnb_operations.fnb_outlets` (17 baris) — master outlet F&B (nama, tipe, properti). Tidak ada transaksi/harga.
  - `facility_maintenance.rooms` (549 baris) — master kamar fisik (nomor, tipe, lantai, status operasional). Tidak terhubung ke identitas tamu.
  Tabel yang eksplisit **tidak** masuk whitelist: seluruh `hr_finance.*` (payroll, staff_shifts, employee_performance, financial_summary), `corporate_master.guests`/`employees`/`role_permissions`, dan semua tabel transaksi (`bookings`, `fnb_transactions`, `spa_bookings`, `event_bookings`) — semuanya memuat PII, data finansial, atau bisa dipakai menyimpulkan pola tamu individual.
- **Alternatives considered:** Hanya `monitoring.*` (lebih aman, lebih cepat, tetapi sample data production non-sensitif diperlukan untuk memberi konteks pada dashboard).
- **Rejected because:** N/A — ini pilihan eksplisit user, bukan hasil eliminasi. Mitigasi risiko: role Postgres terpisah (Task 2) yang secara teknis (bukan cuma di level query API) tidak bisa SELECT tabel di luar whitelist, sehingga bug di kode API tidak bisa membocorkan data di luar whitelist.

### Decision: Tanpa autentikasi, rate limiting per IP

- **Context:** API ini menyajikan monitoring publik — pengguna harus dapat mengaksesnya tanpa daftar/API key, tetapi tetap perlu proteksi dari abuse.
- **Decision:** Semua endpoint read-only tanpa auth; rate limiting per IP (mis. 60 request/menit) via `slowapi`.
- **Alternatives considered:** Wajib API key.
- **Rejected because:** API key menambah friksi bagi pengguna dashboard dan membutuhkan proses distribusi key yang tidak sepadan untuk API read-only tanpa data sensitif.

## Open Questions Resolved with User

- Q: Framework & hosting API? → A: FastAPI di Railway/Render free tier.
- Q: Data scope? → A: `monitoring.*` + sample data non-sensitif production.
- Q: Proteksi API publik? → A: Read-only + rate limiting per IP, tanpa API key.
- Q: Repo API terpisah atau satu repo dengan `nirwana-database`? → A: Repo terpisah (`nirwana-monitoring-api`), folder `api/` di root dikerjakan lokal dulu lalu di-gitignore.
