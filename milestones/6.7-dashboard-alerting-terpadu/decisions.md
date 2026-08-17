# Milestone 6.7: Dashboard dan Alerting Terpadu (Fase 2)

**Source:** docs/03-implementation-plans/06-monitoring-warehouse-serving-fase2.md (baris 168-183)
**Status:** In Progress
**Date started:** 2026-08-11

## Contract (from source doc)

- **Lingkup**: Menyatukan hasil Milestone 6.2-6.6 ke satu tampilan yang mencerminkan kesehatan pipeline warehouse-hingga-serving secara keseluruhan, beserta jalur alerting yang jelas — mempertimbangkan dependency antar titik (Milestone 6.1) supaya satu akar masalah tidak muncul sebagai banjir alert terpisah.
- **Output 1**: Dashboard tunggal mencerminkan kesehatan pipeline dari `raw_production` hingga serving layer, termasuk performa query chatbot.
- **Output 2**: Konfigurasi alerting dengan tujuan/kanal yang jelas per jenis kejadian, mempertimbangkan dependency antar titik.
- **KK1**: Dashboard mencerminkan kondisi terkini seluruh pipeline dan dapat diakses tim.
- **KK2**: Simulasi kegagalan di satu titik akar (uji coba terkontrol) menghasilkan alert yang jelas menunjukkan titik akar tersebut, bukan alert terpisah dari setiap tahap downstream yang ikut terdampak.

**Milestone penutup** keluarga 6.x — tidak ada Milestone 6.8 atau dokumen fase 3 di `docs/03-implementation-plans/` saat ini.

## Perluasan Cakupan (di luar dokumen sumber, dikunci user sesi ini)

Project ini punya dua permukaan dashboard terpisah: Grafana (internal, M1.5, akses tim — memenuhi KK1 literal "dapat diakses tim") dan situs publik `api/`+`web/` (M1.6/1.7, tanpa autentikasi). Dikonfirmasi eksplisit ke user (`AskUserQuestion`, lihat Open Questions) bahwa M6.7 **diperluas mencakup keduanya** — bukan cuma Grafana — karena `api/` (live di Render) dan `web/` (belum full-deploy) sama sekali belum menyentuh data Fase 2 sejak dibangun (M1.6/1.7 hanya Fase 1).

## Temuan Riset

1. `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` (M6.1) sudah punya peta dependency + prioritas 10 titik, dan eksplisit mengundang M6.7 menyusun alerting berdasarkan peta itu. Titik 2 (transform staging→`mart_cleaned`) satu-satunya titik **Kritis** — akar fan-out ke 3 cabang paralel (Titik 3/9, Titik 4→5→6, Titik 6→7→8→10).
2. `scripts/monitoring_warehouse/titik_config.py` (M6.2) memetakan 9/10 titik ke sinyal GitHub Actions (workflow_name+step_name_substring+granularity) tapi **tidak** mengenkode dependency antar titik — cuma listener, bukan graph.
3. `monitoring.pipeline_run_log` (M6.2) sudah punya `titik_id` native (kolom langsung). `monitoring.alerts` (M1.2, diperluas tiap milestone, sekarang 13 `alert_type`) **tidak** punya `titik_id` — perlu mapping `alert_type`+`schema_name`(dataset) → titik_id saat dipakai untuk korelasi (mis. `warehouse_volume_anomaly` bisa Titik 1/2/6 tergantung dataset).
4. **Temuan**: `dbt_test_failure` ada di `CHECK` constraint `monitoring.alerts` sejak M6.3 (`scripts/monitoring_warehouse/schema.sql`) tapi **tidak pernah diinsert oleh skrip manapun** — dicek lewat grep `INSERT INTO monitoring.alerts` di seluruh `detect_*.py`/`check_*.py`, nol match untuk alert_type ini. M6.3 memilih membuat `monitoring.dbt_test_result` (tabel detail per-test) queryable tanpa alert di atasnya — KK M6.3 cuma minta "terlihat tanpa buka log mentah", bukan "alert". Alert_type ini reserved-tapi-mati. Di luar scope M6.7 untuk diperbaiki (tidak diminta KK manapun) — dicatat sebagai temuan; view root-cause M6.7 baca `monitoring.dbt_test_result` langsung untuk Titik 3/7, bukan lewat `monitoring.alerts`.
5. Grafana (M1.5, `scripts/grafana/`) sudah pakai 1 datasource Postgres ke `SUPABASE_DB_URL` (admin, production) — datasource ini **otomatis** sudah bisa baca seluruh tabel `monitoring.*` Fase 2 (schema `monitoring` sama, instance sama, desain "monitoring tetap terpusat" — lihat CLAUDE.md). Tidak perlu datasource/kredensial baru untuk sisi Grafana.
6. Dashboard Fase 1 (`nirwana-data-monitoring`, 7 panel) dan 2 alert rule Fase 1 (M1.2+M1.3 gabungan, M1.4 schema drift) hanya mencakup production — nol panel/rule Fase 2. Dokumen sumber eksplisit minta "dua tampilan terpisah... saling dirujuk", bukan menambah panel ke dashboard existing.
7. `api/app/queries.py`+`main.py` (M1.6, live) hanya punya 8 endpoint Fase 1 (`status/tables`, `dq/summary`, `dq/failures`, `dq/dirty-proportion`, `dq/anomalies`, `schema-drift`, `alerts`, `sample/{table}`). `scripts/api_reader/grants.sql` (M1.6) sudah `GRANT SELECT ON ALL TABLES IN SCHEMA monitoring` **+** `ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring GRANT SELECT ON TABLES TO monitoring_api_reader` — klausa DEFAULT PRIVILEGES ini otomatis mencakup tabel APA PUN yang dibuat sesudahnya lewat koneksi yang sama (`SUPABASE_DB_URL`, admin) yang menjalankan `ALTER DEFAULT PRIVILEGES` itu sendiri — pola yang konsisten dipakai tiap `apply_schema.py` milestone manapun (M6.2-6.6 semua connect via `SUPABASE_DB_URL`). **Kemungkinan besar `monitoring_api_reader` SUDAH bisa baca seluruh tabel/view Fase 2 tanpa grant tambahan** — akan diverifikasi empiris di Checkpoint 6, bukan diasumsikan.
8. `web/` (M1.7) — 6 halaman selesai+terverifikasi lokal (`decisions.md`+`logs.md` ada), **tidak ada `report.md`** → per konvensi project, milestone ini belum selesai. Log terakhir M1.7: percobaan deploy Vercel CLI dibatalkan (sesi tersimpan akun salah, `kertaslipatweb-1272` bukan akun user), user memilih deploy manual lewat dashboard Vercel sendiri, belum dikonfirmasi selesai. `web/` juga punya 1 perubahan belum dicommit: `.gitignore` (+`.vercel`, +`.env*`) — sisa cleanup insiden itu.
9. Kanal notifikasi eksternal alert (Discord/Slack/Email) tercatat Open sejak M1.5 di `docs/keputusan-tertunda.md`, dengan catatan "prioritaskan sebelum kanal alert dianggap lengkap secara operasional". Dikonfirmasi eksplisit ke user (M6.7 kemungkinan besar milestone alerting terakhir) — user memilih **tetap menunda**.

## Technical Decisions

### Keputusan A — Root-cause grouping: View SQL real-time + label Grafana
**Context:** KK2 minta kegagalan 1 titik akar menghasilkan SATU alert, bukan banjir alert terpisah dari tiap titik downstream. Butuh mekanisme mengelompokkan event lintas 13 `alert_type` + `pipeline_run_log` + `dbt_test_result` berdasarkan graph dependency titik.
**Decision:** Tabel baru `monitoring.titik_dependency` (10 titik + 11 edge dependency, statis, di-seed sekali) + 2 view baru: `monitoring.titik_event_today` (menyatukan 3 sumber sinyal ke bentuk seragam per titik) dan `monitoring.alerts_with_root_cause` (recursive CTE menaiki graph, hasilkan `root_titik_id`). Grafana query langsung ke view — real-time, tanpa job/tabel snapshot baru. Notification policy Grafana dikelompokkan lewat label `root_titik_id`.
**Alternatives considered:** Script Python terjadwal harian menulis hasil pengelompokan ke tabel baru `monitoring.alert_correlation`.
**Rejected because:** Menambah job terjadwal baru + hasil jadi snapshot beku per hari (bukan real-time); lebih penting, mendobelkan sebagian "logic keputusan" ke Python padahal seluruh precedent project ("Grafana tidak pernah menghitung ulang logic deteksi apa pun, cuma query tipis", lihat CLAUDE.md bagian `monitoring` schema) menjaga logic keputusan di SATU tempat. Pengelompokan bukan "deteksi anomali baru" (itu tetap di 8 `detect_*.py`/`check_*.py` existing) — murni penyusunan ulang hasil yang sudah ada, cocoknya di view, bukan job baru.
**User confirmed via AskUserQuestion**, opsi "View SQL + label Grafana (rekomendasi)".

### Keputusan B (derived) — Detektor baru: gap dependency Titik 1→2
**Context:** `docs/keputusan-tertunda.md` (entri "Dependency gate ekstraksi→transformasi belum ditegakkan", ditemukan M6.1) eksplisit mengundang M6.2/M6.7 membangun "sinyal turunan" untuk mendeteksi mismatch ini, tanpa menyentuh workflow YAML `extract-production.yml`/`transform-mart-cleaned.yml` (tetap di luar wewenang keluarga milestone monitoring).
**Decision:** `scripts/monitoring_warehouse/detect_pipeline_dependency_gap.py` (baru) — cek `pipeline_run_log`: kalau Titik 2 punya run hari ini tapi Titik 1 TIDAK punya run `status='success'` hari ini yang selesai sebelum Titik 2 mulai, push alert `pipeline_dependency_gap` (severity critical). Alert_type baru ditambah ke `CHECK` constraint. Dijalankan sebagai step baru di `monitoring-warehouse-dq-anomaly.yml` (workflow terjadwal existing M6.3) — bukan workflow baru.
**Why not asked to user:** Sudah "diundang" eksplisit oleh entri backlog sendiri sebagai hal yang M6.7 boleh kerjakan tanpa menyentuh infra pipeline — kapasitas baru murni observasional, konsisten wewenang keluarga milestone ini.

### Keputusan C (derived) — Dashboard Grafana baru terpisah, datasource existing
**Context:** Dokumen sumber closing note eksplisit minta "dua tampilan terpisah... saling dirujuk" untuk Fase 1 vs Fase 2.
**Decision:** `scripts/grafana/build_dashboard_warehouse_serving.py` (baru, pola persis `build_dashboard.py` M1.5) — dashboard `"Nirwana - Warehouse & Serving Monitoring (Fase 2)"`, datasource Postgres yang SAMA (tidak ada datasource/kredensial baru, lihat Temuan #5). ~9 panel: status 10 titik hari ini, alert dikelompokkan per akar masalah, DQ gate mart_cleaned/mart_aggregated, volume anomaly warehouse, kesehatan `ml_output` (freshness+staleness+completeness+drift canary), kesehatan swap reverse ETL (durasi+status+orphan), storage & vacuum serving layer, performa chatbot (latency percentile live+connection pool+tren denied), panel teks tautan ke dashboard Fase 1.

### Keputusan D (derived) — Alert rules baru, folder Grafana sama, rule group baru
**Decision:** `scripts/grafana/create_alerts_warehouse_serving.py` (baru) — 1-2 rule bersumber `alerts_with_root_cause`/`titik_event_today` (BUKAN 13 rule terpisah per alert_type — itu sendiri akan membanjiri, bertentangan langsung dengan KK2), `ruleGroup` baru (`warehouse-serving-monitoring`) di folder "Nirwana Monitoring" yang sudah ada. Notification policy baru dengan route `group_by: [root_titik_id]` khusus rule group ini — tidak mengubah 2 rule/policy Fase 1.

### Keputusan E (user-locked) — Kanal notifikasi eksternal: TETAP ditunda
**Context:** Lihat Temuan #9.
**Decision:** M6.7 memenuhi KK2 lewat visibility+grouping di Grafana (dashboard + alert state benar), TANPA pengiriman ke luar Grafana. `docs/keputusan-tertunda.md` entri existing diupdate (dicatat lagi, tetap Status: Open) — bukan entri baru.
**User confirmed via AskUserQuestion**, opsi "Tetap tunda".

### Keputusan F (derived) — Uji coba terkontrol KK2: injeksi sintetis multi-titik terkorelasi
**Context:** Membuktikan KK2 idealnya lewat kaskade kegagalan nyata dari Titik 2 ke seluruh downstream — tapi ini butuh pipeline live berjalan berhari-hari (jadwal cron nyata, `workflow_run` chain) dan berisiko mengganggu jadwal produksi tanpa manfaat sepadan untuk membuktikan fitur presentasi/grouping.
**Decision:** Insert baris `is_simulated=true`/tertanggal hari ini secara terkoordinasi di `pipeline_run_log` (Titik 2 `status='failure'`) + `monitoring.alerts`/`dbt_test_result` di beberapa titik downstream (Titik 3, 6, 8/9) — pola sama persis `simulate_test.py` yang sudah dipakai tiap milestone 6.x sebelumnya. Deteksi individual tiap alert_type SUDAH terbukti nyata di M6.3-6.6 masing-masing — yang baru dibuktikan di sini murni logic pengelompokannya.

### Keputusan G (user-locked) — Cakupan diperluas ke dashboard publik (`api/`+`web/`)
**Context:** Lihat "Perluasan Cakupan" di atas.
**Decision:** Endpoint/halaman baru murni agregat/read-only, mengikuti pola keamanan M1.6 (`SAMPLE_TABLE_WHITELIST`, tanpa data sensitif). **Batasan eksplisit**: performa chatbot publik HARUS agregat (percentile, count, tren) — TIDAK PERNAH expose baris mentah `chatbot_query_log` (ada `employee_id`/`resolved_property_id`, bukan untuk publik).
**Alternatives considered:** Grafana-saja (KK1 literal "tim" sudah terpenuhi); ringkasan publik minimal (1 endpoint agregat saja).
**Rejected because:** User memilih perluasan penuh secara eksplisit setelah diberi ketiga opsi dengan trade-off masing-masing (`AskUserQuestion`).

### Keputusan H (derived) — Tidak perlu kredensial/grant baru untuk `api/`
**Decision:** Lihat Temuan #7 — `ALTER DEFAULT PRIVILEGES` M1.6 kemungkinan besar sudah mencakup seluruh tabel `monitoring.*` Fase 2. Diverifikasi empiris di Checkpoint 6 sebelum diasumsikan bekerja; kalau ada tabel yang ternyata tidak tercakup, baru re-run `scripts/api_reader/grants.sql` (idempotent, aman re-run).

### Keputusan I (derived) — Root-cause grouping juga dipakai endpoint publik
**Decision:** `/api/warehouse/alerts` bersumber `monitoring.alerts_with_root_cause`, bukan `monitoring.alerts` mentah — prinsip "satu alert per akar masalah" konsisten di KEDUA permukaan (internal Grafana & publik), bukan cuma satu.

### Keputusan J (derived) — Push ke remote tetap butuh konfirmasi eksplisit terpisah
**Context:** Instruksi standing user sejak awal sesi ini: selalu minta konfirmasi eksplisit via `AskUserQuestion` sebelum `git push` apa pun.
**Decision:** Berlaku untuk SEMUA remote yang disentuh milestone ini: `nirwana-database` (utama), `nirwana-monitoring-api`, `nirwana-monitoring-web` (2 repo nested terpisah, git history sendiri-sendiri) — 3 titik konfirmasi berbeda, bukan diasumsikan dari 1 persetujuan. Status deploy Vercel `web/` dikonfirmasi ulang ke user di Checkpoint 8 (Temuan #8 sudah agak lama, bisa sudah berubah). TIDAK mencoba Vercel CLI lagi kecuali user re-otorisasi eksplisit (pelajaran insiden akun salah, `milestones/1.7-public-monitoring-web/logs.md`).

## Task Breakdown

Lihat plan file sesi ini (`C:\Users\LENOVO\.claude\plans\cek-progress-pengerjaan-project-snug-floyd.md`) untuk 38 atomic task di bawah 8 checkpoint — direplikasi ringkas di `logs.md` saat tiap checkpoint dikerjakan.

- **Checkpoint 1** — Fondasi: `titik_dependency` + seed + alert_type baru.
- **Checkpoint 2** — Root-cause correlation core: `titik_event_today`, `alerts_with_root_cause`, `detect_pipeline_dependency_gap.py`.
- **Checkpoint 3** — Dashboard Grafana Fase 2 (KK1 internal).
- **Checkpoint 4** — Alert rules + grouping Grafana (KK2 penyampaian internal).
- **Checkpoint 5** — Uji coba terkontrol root-cause (pembuktian KK2) + docs internal.
- **Checkpoint 6** — Perluasan `api/` (Keputusan G-I).
- **Checkpoint 7** — Perluasan `web/`.
- **Checkpoint 8 (final)** — Deploy publik + `docs/keputusan-tertunda.md` + `logs.md`/`report.md`.

## Open Questions Resolved with User

- Q: Mekanisme pengelompokan akar-masalah KK2 — view SQL real-time+label Grafana, atau script+tabel baru? → A: View SQL + label Grafana (rekomendasi).
- Q: Kanal notifikasi eksternal (Open sejak M1.5) — diselesaikan sekarang atau tetap ditunda? → A: Tetap tunda.
- Q: Cakupan dashboard publik (`api/`+`web/`) — Grafana saja, perluas penuh, atau ringkasan minimal? → A: Perluas penuh ke publik juga.
