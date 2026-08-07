# Keputusan Tertunda (Project-Wide Backlog)

> Dokumen ini mencatat keputusan yang **sengaja ditunda** (bukan diputuskan) di milestone manapun — biasanya karena mengeksekusinya sekarang berarti mengubah infrastruktur/konfigurasi bersama yang layak dapat persetujuan eksplisit tersendiri. Dicek di awal tiap milestone baru untuk melihat apakah ada yang sudah waktunya diambil lagi. Lihat `milestone-execution` (skills) untuk konvensi penggunaan.

---

### Aktivasi `pg_cron` untuk penjadwalan otomatis monitoring (deferred dari Milestone 1.2)

- **Date:** 2026-08-07
- **What was deferred:** Mengaktifkan ekstensi `pg_cron` di Supabase project (tersedia, versi 1.6.4, belum di-`CREATE EXTENSION`) dan menjadwalkan job harian untuk snapshot volume/freshness Milestone 1.2 agar berjalan otomatis tanpa trigger manual. **Update Milestone 1.3 (2026-08-07):** cakupan bertambah — DQ test runner (`scripts/dq/build_and_run.py`), snapshot proporsi dirty (`snapshot_dirty_proportion.py`), snapshot anomali nilai (`snapshot_value_anomaly.py`), dan alert gabungan (`dq_alerts.py`) sama-sama masih dijalankan on-demand/manual, bukan terjadwal — keputusan penundaan yang sama berlaku, tidak perlu entri terpisah.
**Update Milestone 1.4 (2026-08-07):** cakupan bertambah lagi — `scripts/schema_drift/snapshot_and_diff.py` juga dijalankan on-demand/manual. Catatan tambahan: untuk Milestone 1.4 secara spesifik, keputusan metode deteksi (`decisions.md` milestone ini) juga sudah menetapkan snapshot-diff (bukan Postgres Event Trigger) sebagai pilihan permanen — jadi bagian yang benar-benar tertunda di sini murni soal *penjadwalan* eksekusinya, bukan soal metode deteksi itu sendiri.
- **Why deferred:** Mengaktifkan ekstensi & menjadwalkan job adalah perubahan konfigurasi project Supabase (bukan sekadar tulis-baca data biasa) — user memilih agar Milestone 1.2 fokus dulu membangun & membuktikan mekanismenya (schema + script + uji coba terkontrol) sebelum mengambil keputusan terpisah soal cara kerjanya berjalan otomatis tiap hari.
- **Revisit when:** Setelah mekanisme Milestone 1.2 terbukti benar lewat uji coba terkontrol (Kriteria Keberhasilan #2), saat project siap membahas strategi otomasi/orkestrasi secara keseluruhan (kemungkinan relevan juga untuk Fase 2 — lihat "Catatan Serah Terima" di `01-monitoring-data-production-fase1.md`).
- **Status:** Resolved (2026-08-07, diskusi sebelum Milestone 1.5) — lihat entri baru "Platform penjadwalan & deployment mekanisme monitoring" di bawah. `pg_cron` sendiri **ditolak permanen** sebagai solusi tunggal (bukan cuma ditunda lagi): `pg_cron` hanya bisa menjalankan SQL/PL-pgSQL di dalam Postgres, sementara Milestone 1.3 bergantung ke Great Expectations (library Python di luar database) — jadi `pg_cron` tidak bisa mencakup seluruh pipeline yang sudah dibangun (M1.2, M1.3, M1.4 sama-sama script Python).

---

### Platform penjadwalan & deployment mekanisme monitoring (M1.2-1.4) + dashboard (M1.5)

- **Date:** 2026-08-07
- **What was deferred:** Dulu dianggap bagian dari keputusan `pg_cron` di atas — sekarang dipisah jadi keputusan sendiri karena cakupannya lebih luas dari sekadar "jadwalkan job Postgres": seluruh mekanisme monitoring (`scripts/monitoring/`, `scripts/dq/`, `scripts/schema_drift/`) saat ini hanya bisa dijalankan manual di komputer lokal, belum bisa dijalankan otomatis di tempat lain. Dashboard Milestone 1.5 juga perlu di-deploy ke suatu tempat yang bisa diakses, bukan cuma jalan lokal.
- **Decision:** **GitHub Actions** (scheduled workflow, `cron` trigger) untuk menjalankan seluruh script Python (`scripts/monitoring/`, `scripts/dq/`, `scripts/schema_drift/`) secara terjadwal. **Grafana** (self-hosted via Docker, di-deploy ke platform seperti Railway/Render/Fly.io atau Grafana Cloud free tier) untuk dashboard & alerting Milestone 1.5, dengan datasource Postgres (Supabase, Fase 1) dan BigQuery (Fase 2, saat relevan).
- **Why chosen:** GitHub Actions gratis, tidak perlu infra/server terpisah untuk dikelola, secrets management bawaan (`SUPABASE_DB_URL` aman sebagai GitHub Secret, bukan hardcode — prinsip sama seperti `.env`/`config_variables.yml` di M1.3), cron scheduling bawaan, dan history run terlihat langsung di repo sebagai bukti berjalan. Grafana dipilih karena satu-satunya dari opsi yang dibandingkan (vs Metabase, Superset) yang punya alerting engine native selain visualisasi — pas dengan output Milestone 1.5 ("dashboard **dan** alerting terpadu"), dan datasource BigQuery native untuk Fase 2 nanti.
- **Alternatives considered:** `pg_cron` (ditolak, lihat entri di atas); orchestrator penuh (Airflow/Dagster/Prefect) — dinilai overkill untuk kebutuhan Fase 1 (4 script Python dijadwalkan harian), lebih masuk akal dibahas ulang saat Fase 2; scheduled job di platform cloud (Cloud Run Jobs/Railway/Render cron) — lebih "production-grade" tapi menambah kerumitan setup yang belum perlu sekarang; Metabase/Superset untuk dashboard — dibahas di diskusi sebelum Milestone 1.5, ditolak karena tidak punya alerting native (Metabase) atau overkill untuk kebutuhan saat ini (Superset).
- **Status:** Resolved (keputusan diambil) — **implementasi belum dikerjakan**, direncanakan sebagai bagian kerja Milestone 1.5 (workflow YAML GitHub Actions untuk M1.2-1.4 + deploy Grafana untuk dashboard/alerting M1.5).

---

### Kanal notifikasi eksternal untuk alert (deferred dari Milestone 1.5)

- **Date:** 2026-08-07
- **What was deferred:** Menghubungkan alert Grafana ke kanal notifikasi eksternal nyata (Discord webhook, Email/SMTP, atau Slack webhook) supaya alert benar-benar "terkirim", bukan cuma terlihat di panel/state dashboard Grafana.
- **Why deferred:** User memilih menunda dulu, tanpa alasan spesifik dicatat dalam diskusi — kemungkinan prioritas waktu. Konsekuensi eksplisit: Kriteria Keberhasilan #2 Milestone 1.5 ("...dan terkirim ke kanal yang benar saat diuji coba") **tidak terpenuhi penuh** — hanya bagian "muncul di dashboard" yang tercapai. Milestone 1.5 dilaporkan **Partially Completed**, bukan Completed, karena gap ini.
- **Revisit when:** Kapan saja — perubahan yang dibutuhkan kecil (tambah 1 contact point + notification policy di Grafana, tidak menyentuh logic deteksi apa pun di Python). Prioritaskan sebelum project ini dianggap "selesai" untuk portofolio, karena ini gap yang eksplisit disebut di Kriteria Keberhasilan sumber.
- **Status:** Open
