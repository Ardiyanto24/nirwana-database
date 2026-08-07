# Milestone 1.5: Dashboard dan Alerting Terpadu (Fase 1)

**Source:** docs/03-implementation-plans/01-monitoring-data-production-fase1.md (baris 117-131)
**Status:** Done (implementasi selesai; lihat report.md untuk status Kriteria Keberhasilan — Partially Completed karena kanal notifikasi ditunda)
**Date started:** 2026-08-07

## Contract (from source doc)

- **Lingkup:** Menyatukan hasil Milestone 1.2, 1.3, 1.4 ke satu tampilan untuk memantau kesehatan data production, plus jalur alerting jelas (siapa menerima alert apa, lewat kanal apa).
- **Output:** Dashboard status volume/freshness/kualitas data/schema drift untuk tabel prioritas; konfigurasi alerting dengan tujuan/kanal jelas per jenis kejadian.
- **Kriteria keberhasilan:** Dashboard dapat diakses tim & mencerminkan kondisi terkini (bukan basi); setiap jenis alert M1.2-1.4 muncul di dashboard **dan** terkirim ke kanal yang benar saat diuji coba.
- **Murni konsolidasi & presentasi** — sengaja terakhir, baru bisa dikerjakan baik setelah M1.2-1.4 menghasilkan data.

## Routing via `using-agent-skills`

Berbeda dari M1.2-1.4 (yang didominasi `incremental-implementation`/`test-driven-development` karena menulis logic deteksi baru), Milestone 1.5 tidak menulis logic anomali baru — murni konsolidasi & deployment. Skill yang relevan untuk fase kerja: `ci-cd-and-automation` (GitHub Actions penjadwalan script M1.2-1.4), `observability-and-instrumentation` (dashboard & alerting adalah observability by definition), `shipping-and-launch` (deploy Grafana, verifikasi pra-serah-terima).

## Task Breakdown

- [x] Task 1: Deploy Grafana (Grafana Cloud free tier) — Acceptance: instance aktif, bisa diakses via URL — Verify: login berhasil
- [x] Task 2: Setup GitHub Actions — jadwalkan `scripts/monitoring`, `scripts/dq`, `scripts/schema_drift` — Acceptance: workflow run sukses minimal 1x, secrets aman — Verify: run history GitHub Actions (10m15s, semua step hijau)
- [x] Task 3: Konfigurasi datasource Grafana → Supabase Postgres — Acceptance: datasource test connection sukses — Verify: `GET /api/datasources/uid/.../health` → "Database Connection OK"
- [x] Task 4: Bangun dashboard 4 pilar untuk 23 tabel (dikelompokkan per prioritas) — Acceptance: setiap pilar (volume/freshness, DQ, schema drift) punya panel — Verify: 7/7 panel diuji langsung via `POST /api/ds/query`, 2 kebocoran data simulasi ditemukan & diperbaiki
- [x] Task 5: Konfigurasi alert rules baca dari `monitoring.alerts`/`schema_drift_events` — Acceptance: alert rule terpasang, tidak menduplikasi logic Python — Verify: 2 rule dibuat, evaluasi otomatis mencerminkan data real
- [x] Task 6: Uji coba terkontrol — trigger drift buatan, verifikasi muncul di dashboard — Acceptance: state alert bereaksi — Verify: siklus penuh inactive→firing→inactive terbukti
- [x] Task 7: Verifikasi Kriteria Keberhasilan — Acceptance: kedua kriteria dicek eksplisit, termasuk gap kanal notifikasi — Verify: KK#1 terpenuhi, KK#2 sebagian (lihat report.md)
- [x] Task 8: Tulis `logs.md`/`report.md`

**Checkpoint** setelah Task 1 & 2: kalau deployment/scheduling tidak jalan, pekerjaan dashboard di hilir tidak bisa diverifikasi betulan.

## Technical Decisions

### Decision: Platform Grafana — Grafana Cloud (free tier)

- **Context:** Perlu tempat Grafana benar-benar berjalan & bisa diakses tim, bukan cuma lokal.
- **Decision:** Grafana Cloud free tier — hosted oleh Grafana Labs, tanpa kelola server/Docker.
- **Alternatives considered:** Self-host Docker di Railway/Render/Fly.io.
- **Rejected because:** setup jauh lebih ringan tanpa Docker/config manual, dan free tier Grafana Cloud cukup untuk kebutuhan Fase 1 (tim kecil, 4 pilar monitoring). Self-host jadi opsi kalau nanti butuh kontrol lebih (mis. plugin custom) — bukan kebutuhan saat ini.

### Decision: Kanal notifikasi — ditunda, tanpa kanal eksternal untuk saat ini

- **Context:** Kriteria Keberhasilan eksplisit minta alert "terkirim ke kanal yang benar saat diuji coba" — butuh channel nyata (Discord/Slack/Email).
- **Decision:** **Tidak** mengkonfigurasi kanal eksternal di milestone ini. Alert tetap termanifestasi di dashboard Grafana (panel/state), tapi tidak ada push notification keluar. Dicatat sebagai keputusan tertunda di `docs/keputusan-tertunda.md`.
- **Konsekuensi eksplisit:** Kriteria Keberhasilan #2 **tidak terpenuhi penuh** — bagian "muncul di dashboard" tercapai, bagian "terkirim ke kanal yang benar" tidak. Status akhir milestone: **Partially Completed**, bukan dipaksakan Completed.
- **Alternatives considered:** Discord webhook (setup tercepat), Email/SMTP, Slack webhook.
- **Rejected because:** user memilih menunda dulu — kemungkinan pertimbangan waktu/prioritas di luar percakapan ini. Revisit kapan saja karena tidak butuh perubahan besar (tinggal tambah 1 contact point + notification policy di Grafana).

### Decision: Sumber alert Grafana — baca dari `monitoring.alerts`/`schema_drift_events`, bukan hitung ulang

- **Context:** Logic deteksi (rolling baseline M1.2, tolerance-band & IQR M1.3, baseline-tetap M1.4) sudah ditulis & teruji penuh di Python. Menulis ulang di Grafana alert query berisiko dua sumber kebenaran berbeda.
- **Decision:** Grafana alert rule = query sederhana "ada baris baru/pending di `monitoring.alerts` (M1.2 & M1.3) atau `monitoring.schema_drift_events` status='pending' (M1.4)?" — Grafana murni lapisan notifikasi di atas hasil yang sudah dihitung Python.
- **Alternatives considered:** Grafana hitung ulang logic anomali sendiri lewat SQL alert query.
- **Rejected because:** sebagian logic (mode bootstrap M1.3, model baseline-tetap-dengan-acknowledgment M1.4) sulit/tidak mungkin direplikasi murni sebagai satu query SQL — dan menduplikasinya menciptakan risiko drift antara "apa yang Python anggap anomali" vs "apa yang Grafana anggap anomali".

### Decision: Cakupan dashboard — 23 tabel, dikelompokkan per prioritas

- **Context:** M1.3 & M1.4 sudah menghitung penuh 23 tabel (bukan cuma 7 prioritas Tinggi seperti pola literal M1.2).
- **Decision:** Dashboard tampilkan seluruh 23 tabel, dikelompokkan/diurutkan Tinggi → Sedang → Rendah.
- **Alternatives considered:** Hanya 7 tabel prioritas Tinggi.
- **Rejected because:** data untuk 16 tabel Sedang/Rendah sudah ada dan lengkap (hasil kerja M1.3/M1.4) — tidak ada alasan menyembunyikannya, tinggal soal pengelompokan tampilan supaya tetap gampang dipindai.

### Decision: Jadwal GitHub Actions — satu workflow harian, sekuensial

- **Context:** Perlu memutuskan cadence & struktur workflow untuk menjalankan `scripts/monitoring`, `scripts/dq`, `scripts/schema_drift`.
- **Decision:** Satu workflow (`.github/workflows/monitoring.yml`), jadwal cron harian, menjalankan ketiga suite script secara berurutan (monitoring → dq → schema_drift) dalam satu job. Kredensial (`SUPABASE_DB_URL`) disimpan sebagai GitHub Secret, bukan hardcode.
- **Alternatives considered:** Workflow terpisah per milestone dengan jadwal berbeda-beda.
- **Rejected because:** kompleksitas tambahan (3 workflow, 3 jadwal) tidak sebanding manfaatnya untuk skala kerja saat ini — satu workflow harian sudah cukup dan lebih mudah dipantau. Bisa dipecah nanti kalau ada kebutuhan jadwal berbeda per komponen.

## Open Questions Resolved with User

- Q: Grafana di-deploy ke mana? → A: Grafana Cloud free tier.
- Q: Kanal notifikasi? → A: Ditunda, tanpa kanal eksternal untuk saat ini (KK#2 partially met).
- Q: Sumber alert Grafana? → A: Baca dari `monitoring.alerts`/`schema_drift_events`, bukan hitung ulang.
- Q: Cakupan dashboard? → A: 23 tabel, dikelompokkan per prioritas.
