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

---

### Orchestrator sungguhan (Airflow/Dagster/Prefect self-hosted) untuk Fase 2 (deferred dari Milestone 2.0)

- **Date:** 2026-08-08
- **What was deferred:** Menggunakan orchestrator sungguhan yang di-self-host (Airflow, Dagster, atau Prefect via Docker, dideploy ke platform seperti Railway/Render/Fly.io — pola sama seperti Grafana M1.5) untuk mengatur pipeline Fase 2 (ekstraksi → transform → reverse ETL → feedback loop scoring), lengkap dengan dependency graph, sensor, dan retry per-task native.
- **Why deferred:** Milestone 2.0 memilih **GitHub Actions extended** (workflow YAML + `workflow_run`/`needs` untuk dependency chaining, pola dilanjutkan dari Fase 1) sebagai gantinya, murni karena pertimbangan **biaya** — self-hosted orchestrator butuh service yang jalan 24/7 (beda dari GitHub Actions yang serverless) dan berisiko keluar dari free tier platform hosting begitu traffic/compute bertambah. Konsekuensi eksplisit: GitHub Actions tidak punya sensor native (dibutuhkan nanti untuk feedback loop scoring, Bagian 6.4 arsitektur — "tunggu hingga `ml_output` selesai ditulis") dan dependency graph-nya lebih terbatas dibanding orchestrator sungguhan. Untuk memitigasi, konvensi job & dependency di Milestone 2.0 sengaja didesain **sedekat mungkin dengan standar industri** (naming eksplisit, dependency terdokumentasi jelas) supaya migrasi nanti tidak perlu desain ulang total — lihat `milestones/2.0-fondasi-orchestrator-bersama/decisions.md`.
- **Alternatives considered:** Managed cloud orchestrator free tier (Prefect Cloud/Dagster Cloud) — tidak butuh kelola server 24/7, tapi terikat batasan free tier vendor pihak ketiga (jumlah run/bulan, retensi log) yang bisa berubah kapan saja; dipertimbangkan tapi tidak dipilih karena user lebih memilih opsi tanpa dependency ke uptime/kebijakan vendor eksternal sama sekali untuk fondasi ini.
- **Revisit when:** Ketika kebutuhan sensor/dependency graph sungguhan sudah tidak bisa lagi "dipaksakan" lewat GitHub Actions (kemungkinan besar saat masuk milestone feedback loop scoring, `03-mart-aggregated-owner.md`), atau ketika constraint biaya sudah tidak lagi jadi penghalang.
- **Status:** Open — **prediksi ini terbukti benar di Milestone 5.4** (`milestones/5.4-integrasi-feedback-loop-ml/`): sensor `ml_output` diimplementasikan lewat workaround "polling step manual" yang persis diantisipasi di atas (`scripts/ml_scoring/wait_for_ml_output.py`, query+`sleep` loop di dalam job), bukan sensor native. Workaround ini terbukti *cukup* untuk kebutuhan simulasi M5.4 (diverifikasi lewat uji coba terkontrol, sensor timeout & isolasi kegagalan bekerja) — tapi tetap bukan solusi permanen (tidak ada retry granular per-task, dependency graph masih terbatas ke `workflow_run`/polling manual). Keputusan ini **tetap Open**, belum di-resolve oleh M5.4.

---

### Aktivasi billing GCP untuk project `nirwana-database-elt` (deferred dari Milestone 2.1, meluas jadi project-wide di Milestone 2.3)

- **Date:** 2026-08-08
- **What was deferred:** Menghubungkan billing account (kartu kredit) ke project GCP `nirwana-database-elt`, yang saat ini berjalan di **BigQuery Sandbox mode**. Riset ke dokumentasi resmi GCP (dilakukan saat breakdown Milestone 2.3) mengonfirmasi Sandbox mode punya hard limit **60 hari expirasi untuk SEMUA tabel, view, dan partition** di seluruh project — tidak bisa dioverride per-tabel/per-dataset.
- **Why deferred:** Awalnya (Milestone 2.1) dipilih Sandbox mode karena provisioning "dari nol tanpa keluar biaya sebelum kebutuhan real dibuktikan" (lihat `milestones/2.1-extraction-production-raw-warehouse/decisions.md`). Saat Milestone 2.3 mengharuskan `mart_cleaned` sebagai tabel "full history" dengan refresh incremental, user diajak memutuskan ulang — jawaban: **belum bisa diaktifkan sekarang karena kendala kartu kredit**, bukan penolakan permanen; akan diaktifkan begitu kendala itu selesai.
- **Konsekuensi eksplisit (project-wide, bukan cuma Milestone 2.3):** Seluruh data Fase 2 (`raw_production` M2.1, `staging` M2.2, `mart_cleaned` M2.3) tunduk pada batas 60 hari ini. Mitigasi sementara: langkah `bq update --expiration` ditambahkan ke workflow terjadwal untuk memperpanjang `expirationTime` tiap kali job jalan (lihat `milestones/2.3-layer-intermediate-mart-cleaned/decisions.md`) — ini BUKAN solusi permanen. Kalau workflow terjadwal berhenti jalan lebih dari ~55 hari (mis. repo tidak aktif), seluruh Fase 2 akan hilang dan perlu di-rebuild dari Postgres dari nol. `mart_cleaned` juga terpaksa dibangun tanpa partitioning BigQuery (strategi `merge`, bukan `insert_overwrite` per-partition seperti diminta literal dokumen sumber M2.3) untuk menghindari kelas bug yang sama dengan insiden M2.1.
- **Alternatives considered:** Job drop+recreate berkala (lebih berat & berisiko daripada sekadar memperpanjang `expirationTime`); tetap Sandbox mode permanen tanpa mitigasi apa pun (ditolak — bertentangan langsung dengan syarat "full history" yang eksplisit diminta beberapa milestone).
- **Revisit when:** Begitu kendala kartu kredit user selesai. Setelah billing aktif: (1) hapus `defaultTableExpirationMs`/`defaultPartitionExpirationMs` di seluruh dataset (`raw_production`, `staging`, `mart_cleaned`), (2) reset `expirationTime` tabel-tabel existing yang masih membawa timestamp lama, (3) migrasi `mart_cleaned` ke partition-based incremental (`insert_overwrite`) sesuai desain asli dokumen sumber, (4) hapus langkah `bq update --expiration` dari workflow terjadwal (sudah tidak perlu).
- **Status:** Open

---

### Data dictionary/metadata kolom `mart_aggregated` (deferred dari Milestone 5.2 ke Milestone 5.3)

- **Date:** 2026-08-08
- **What was deferred:** Menulis data dictionary lengkap untuk `mart_aggregated` (cara hitung detail tiap kolom, unit, contoh nilai) — mirip `docs/01-architecture/Metadata.md` untuk tabel produksi. Milestone 5.2 hanya menulis skema **struktural** (nama tabel, nama/tipe kolom, FK dimension, partition/cluster key, keterangan singkat 1 baris per kolom) di `docs/07-mart-aggregated/DataSchema-mart-aggregated.md`.
- **Why deferred:** Dibahas eksplisit dengan user saat breakdown Milestone 5.2 (setelah membaca `04-serving-data-analyst.md` dan `05-serving-ai-chatbot.md` untuk memastikan kedua pekerjaan konsumen tidak diam-diam mengharapkan metadata dari sana). Keputusan: data dictionary penuh baru masuk akal ditulis **setelah** SQL transformasi (Milestone 5.3) selesai dan teruji — mendeskripsikan skema yang sudah nyata berjalan, bukan yang baru didesain di atas kertas, mengikuti pola `Metadata.md` vs `DataSchema.md` di produksi (`DataSchema.md` = histori/keputusan desain, peran itu yang diisi dokumen M5.2; `Metadata.md` = deskripsi skema aktual, peran itu untuk dokumen M5.3 nanti).
- **Revisit when:** Segera setelah Milestone 5.3 (implementasi transformasi `mart_aggregated`) selesai dan lolos data quality gate — data dictionary ditulis sebagai bagian output M5.3, bukan milestone terpisah.
- **Status:** Resolved (2026-08-08) — `docs/07-mart-aggregated/Metadata-mart-aggregated.md` ditulis di Milestone 5.3 Checkpoint 9, setelah seluruh 76 tabel (27 dimension + 49 fact) selesai diimplementasikan dan lolos DQ gate.

---

### Otomasi reapply `analyst_views` setelah swap reverse ETL `mart_aggregated` (ditemukan di Milestone 5.7)

- **Date:** 2026-08-09
- **What was deferred:** Merantai step "reapply `analyst_views`" (`scripts/data_analyst_views/apply_views.py --all`, kredensial admin serving) secara otomatis setelah `reverse-etl-mart-aggregated.yml` di GitHub Actions, plus pembersihan tabel `__old` orphan yang menumpuk di antara reapply.
- **Why deferred:** Ditemukan saat verifikasi Milestone 5.7 (`dim_employee.property_id`): swap RENAME-based `sync.py` (M5.5, dibangun sebelum `analyst_views` ada) meninggalkan view M3.2 menunjuk ke tabel `__old` yang stale, karena Postgres view mengikat ke tabel dasar lewat OID, bukan nama — `DROP TABLE __old` gagal (`DependentObjectsStillExist`) selama view belum di-reapply. `sync.py` sudah diperbaiki di M5.7 supaya kegagalan ini jadi WARNING (bukan crash), tapi itu cuma membuat sync tidak berhenti — reapply view + cleanup orphan tetap manual. Mengorkestrasi ini otomatis (menentukan urutan chaining, kredensial mana yang dipakai step itu, apakah reapply-semua-view tiap kali terlalu mahal vs cukup untuk tabel yang berubah) adalah keputusan orkestrasi lintas-milestone (M5.5 reverse ETL + M3.2 analyst views, beda owner) yang lebih tepat dibahas terpisah daripada diputuskan sepihak di tengah perbaikan 1 kolom.
- **Revisit when:** Sebelum `reverse-etl-mart-aggregated.yml` dijadwalkan jalan lagi dengan cakupan `--all` (setiap run berikutnya akan memicu WARNING ini untuk sebagian besar dari 76 tabel yang punya view M3.2 di atasnya, dan tabel `__old` akan terus menumpuk sampai reapply manual dijalankan) — atau kapan pun Milestone 3.x/mart_aggregated-owner berikutnya butuh jaminan `analyst_views` selalu segar tanpa intervensi manual.
- **Status:** Open
