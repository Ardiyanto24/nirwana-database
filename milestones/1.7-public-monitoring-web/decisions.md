# Milestone 1.7: Website Monitoring Publik

**Source:** `docs/03-implementation-plans/01-monitoring-data-production-fase1.md` (section Milestone 1.7, ditambahkan 2026-08-07 bersamaan dengan Milestone 1.6 — lihat catatan penambahan di dokumen tsb).
**Status:** In Progress (Task 1-9 selesai & terverifikasi, Task 10 deploy publik menunggu user deploy manual lewat dashboard Vercel)
**Date started:** 2026-08-07

## Contract (from source doc)

- **Lingkup:** Website publik yang menampilkan status monitoring data production (volume/freshness, kualitas data, anomali nilai, schema drift, alert) dengan mengonsumsi API Milestone 1.6. Ditujukan untuk portofolio — bisa dibuka siapa pun tanpa login.
- **Output:** Website publik ter-deploy (di luar komputer lokal), menampilkan ringkasan status 23 tabel, hasil kualitas data, schema drift, dan alert terkini — versi publik dari dashboard Grafana Milestone 1.5. Deploy di repo terpisah dari `nirwana-database` dan dari `nirwana-monitoring-api`.
- **Kriteria keberhasilan:** Website dapat diakses publik tanpa login dan menampilkan data yang konsisten dengan API Milestone 1.6 (bukan data statis/basi). Tampilan mencakup keempat pilar monitoring (volume/freshness, kualitas data, anomali nilai, schema drift) plus alert aktif, setara cakupan dashboard Grafana Milestone 1.5.

## Task Breakdown

- [ ] Task 1: Setup Next.js project di `web/` (App Router, TypeScript, Tailwind default) — Acceptance: `next dev` jalan lokal, halaman default tampil — Verify: buka `localhost:3000` — XS
- [ ] Task 2: API client tipis (`lib/api.ts`) — fetch ke `NEXT_PUBLIC_API_BASE_URL` (env var, default `https://nirwana-monitoring-api.onrender.com`), `revalidate: 300` di tiap fetch — Acceptance: satu fungsi per endpoint API M1.6, typed response — Verify: import & panggil dari halaman percobaan, data API M1.6 tampil — S
- [ ] Task 3: Layout & navigasi (header, nav ke 6 halaman, footer dengan link ke repo GitHub) — Acceptance: nav berfungsi di semua halaman — Verify: klik tiap link — S
- [ ] Task 4: Halaman Overview (`/`) — ringkasan: jumlah alert aktif, jumlah schema drift pending, jumlah tabel dengan DQ failure, total 23 tabel — Acceptance: angka cocok dengan endpoint `/api/alerts`, `/api/schema-drift`, `/api/dq/summary` — Verify: bandingkan angka di halaman vs curl langsung ke API — M
- [ ] Task 5: Halaman Volume & Freshness (`/volume-freshness`) — tabel 23 baris dari `/api/status/tables` — Acceptance: semua kolom (baseline, pct_diff, freshness_lag) tampil — Verify: 23 baris cocok — S
- [ ] Task 6: Halaman Kualitas Data (`/kualitas-data`) — ringkasan per tabel (`/api/dq/summary`) + detail kegagalan (`/api/dq/failures`) — Acceptance: kedua data tampil dalam satu halaman, dikelompokkan jelas — Verify: cocok dengan API — S
- [ ] Task 7: Halaman Anomali Nilai (`/anomali`) — proporsi dirty data (`/api/dq/dirty-proportion`) + anomali IQR (`/api/dq/anomalies`) — Acceptance: kedua data tampil — Verify: cocok dengan API — S
- [ ] Task 8: Halaman Schema Drift (`/schema-drift`) — `/api/schema-drift` — Acceptance: tampil pending drift (kondisi normal: kosong, dengan pesan "tidak ada drift pending" bukan halaman kosong membingungkan) — Verify: cocok dengan API (0 baris saat ini) — XS
- [ ] Task 9: Halaman Sample Data Production (`/sample-data`) — 3 tabel whitelist (`/api/sample/properties`, `/fnb_outlets`, `/rooms`) — Acceptance: ketiganya tampil, dengan keterangan singkat kenapa hanya 3 tabel ini yang publik — Verify: cocok dengan API — S
- [ ] Task 10: Deploy ke Vercel dari repo terpisah `nirwana-monitoring-web` — Acceptance: website bisa diakses publik via URL Vercel — Verify: buka dari luar, cek tiap halaman — M
- [ ] Task 11: Verifikasi Kriteria Keberhasilan + `report.md`

**Checkpoint** setelah Task 2: kontrak data (bentuk response tiap endpoint) harus benar dipahami sebelum halaman apa pun dibangun di atasnya.

## Technical Decisions

### Decision: Styling — Tailwind CSS polos (tanpa component library)

- **Context:** Perlu styling untuk tampilan tabel/kartu statistik, tanpa menambah kompleksitas setup yang tidak perlu.
- **Decision:** Tailwind CSS default (bawaan `create-next-app`), tanpa component library tambahan (shadcn/ui, dll).
- **Alternatives considered:** shadcn/ui + Tailwind.
- **Rejected because:** kebutuhan tampilan (tabel, kartu angka, badge status) sederhana dan bisa dibuat langsung dengan utility class Tailwind — menambah shadcn/ui (Radix, CLI generator) adalah kompleksitas setup yang tidak sepadan untuk scope ini.

### Decision: Data fetching — server-side fetch + ISR revalidate 5 menit

- **Context:** API M1.6 di Render free tier bisa idle/cold-start, dan rate limit 60 request/menit dibagi ke seluruh pengunjung situs (bukan per-pengunjung) — perlu strategi yang tidak membombardir API tiap page view.
- **Decision:** Next.js Server Components fetch data di server dengan `fetch(url, { next: { revalidate: 300 } })` — data di-cache Next.js selama 5 menit, refresh otomatis setelahnya.
- **Alternatives considered:** Client-side fetch tanpa cache setiap page load.
- **Rejected because:** job GitHub Actions yang mengisi `monitoring.*` sendiri cuma jalan sekali sehari — revalidate 5 menit sudah jauh lebih sering dari kebutuhan riil, sekaligus melindungi API dari rate-limit saat trafik ramai dan menghindari cold-start Render terasa di tiap page view individual.

### Decision: Struktur halaman — multi-halaman (overview + 5 halaman detail per pilar/topik)

- **Context:** Perlu memutuskan apakah semua data ditampilkan dalam satu halaman atau dipisah.
- **Decision:** 6 halaman — Overview (`/`), Volume & Freshness, Kualitas Data, Anomali Nilai, Schema Drift, Sample Data Production — dengan navigasi antar halaman.
- **Alternatives considered:** Single-page dashboard (semua section dalam satu halaman, setara satu dashboard Grafana).
- **Rejected because:** User secara eksplisit memilih multi-halaman meski single-page direkomendasikan untuk kesederhanaan — pertimbangan user: terasa lebih seperti "aplikasi" utuh untuk portofolio, bukan cuma satu halaman panjang.

### Decision: Repo terpisah (`nirwana-monitoring-web`), publik, deploy ke Vercel

- **Context:** Konsisten dengan keputusan Milestone 1.6 — `web/` dikerjakan lokal di root `nirwana-database` (gitignored), lalu di-push ke repo GitHub baru.
- **Decision:** `git init` folder `web/` terpisah, repo GitHub baru `nirwana-monitoring-web` (publik, konsisten dengan `nirwana-database` dan `nirwana-monitoring-api`), deploy ke Vercel (sudah diputuskan user di awal diskusi M1.6/1.7).
- **Alternatives considered:** N/A — sudah diputuskan di sesi sebelumnya (lihat `milestones/1.6-public-monitoring-api/decisions.md`).

## Open Questions Resolved with User

- Q: Styling? → A: Tailwind CSS polos.
- Q: Strategi fetch data (mengingat Render free tier + rate limit)? → A: Server-side fetch + ISR revalidate 5 menit.
- Q: Struktur halaman? → A: Multi-halaman (overview + 5 halaman detail).
