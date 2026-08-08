# Milestone 5.4: Integrasi Feedback Loop ML (Join ke ml_output) — Decisions

**Source:** `docs/03-implementation-plans/03-mart-aggregated-owner.md`, baris 103-119.
**Status:** Done
**Date started:** 2026-08-08

## ⚠️ Status: Seluruhnya Provisional — Menunggu Tim ML Engineer

**Skema `ml_output.predictions` (termasuk kolom tambahan `target_date`), use-case occupancy forecast, format `entity_id`, dan seluruh mekanisme mock scorer di milestone ini BUKAN kontrak final.** Ini murni **contoh/simulasi** untuk membuktikan mekanisme trigger→sensor→join→test bisa berjalan end-to-end (memenuhi 3 Kriteria Keberhasilan sumber) — **bukan** skema yang sudah disepakati dengan tim ML Engineer yang sesungguhnya akan membangun scoring pipeline eksternal. Begitu tim ML Engineer mendefinisikan skema/use-case nyata, seluruh keputusan desain di sini (terutama Keputusan #3, #5, #6, #9) **kemungkinan besar berubah**. Jangan baca milestone ini sebagai spesifikasi final `ml_output` — ini bukti-konsep mekanisme orkestrasi, bukan produk data ML sungguhan.

## Contract (from source doc)

- **Lingkup:** Mengimplementasikan join terkontrol dari `ml_output` ke `mart_aggregated` sesuai alur dokumen arsitektur (Bagian 6): `mart_cleaned` selesai refresh → trigger scoring eksternal → sensor menunggu `ml_output` selesai ditulis → transformasi `mart_aggregated` (LEFT JOIN ke `ml_output`) → pengujian data final. Termasuk validasi kolom wajib `model_version` dan `feature_snapshot_at`. Perluasan ke orchestrator bersama (Milestone 2.0), bukan instance terpisah.
- **Output:**
  1. Mekanisme trigger scoring job eksternal dan sensor yang menunggu `ml_output` selesai ditulis, terintegrasi dengan orkestrator pipeline utama.
  2. Transformasi LEFT JOIN `ml_output` ke `mart_aggregated` final, dengan validasi kelengkapan `model_version` dan `feature_snapshot_at`.
- **Kriteria Keberhasilan:**
  1. Simulasi siklus penuh (`mart_cleaned` refresh → trigger → sensor → join → `mart_aggregated` final) berhasil berjalan end-to-end tanpa intervensi manual.
  2. Baris hasil prediksi yang muncul di `mart_aggregated` selalu punya `model_version` dan `feature_snapshot_at` terisi.
  3. Jika `ml_output` gagal/telat ditulis, `mart_aggregated` tidak ikut gagal total — bagian non-ML tetap bisa ter-refresh.

## Temuan Eksplorasi

- `ml_output` **tidak ada sama sekali** sebagai infrastruktur nyata di repo ini — tidak ada dataset/tabel BigQuery, dbt model, script, atau `schema.sql` yang menyentuhnya. Scoring pipeline eksternal memang eksplisit di luar cakupan repo (`02-serving-data-scientist.md` baris 11: "platform belum ditentukan"), dimiliki tim Data Scientist/ML Engineer terpisah.
- Skema `ml_output.predictions` sudah didefinisikan di `docs/01-architecture/rancangan-arsitektur-data-platform-elt.md` Bagian 6.3: `prediction_id, entity_id (FK ke entity mart_cleaned), model_name, model_version (wajib), prediction_type, predicted_value, confidence_score, scored_at, feature_snapshot_at (wajib)`, partition `DATE(scored_at)`. Bagian 6.4 mendefinisikan 5 langkah orkestrasi: refresh → trigger → sensor → transform LEFT JOIN → test.
- `docs/05-orchestrator/konvensi-job-dependency.md`: GitHub Actions (satu-satunya "orchestrator" repo ini) **tidak punya sensor native** — hanya reaksi ke *completion* workflow lain (`workflow_run`), bukan ke state data eksternal. Dokumen ini sendiri menyarankan "polling step manual di dalam job (cek kondisi lewat query, retry dengan `sleep`)" sebagai workaround. Domain workflow `scoring` untuk feedback loop sudah diantisipasi di baris 14.
- `docs/keputusan-tertunda.md` entri "Orchestrator sungguhan untuk Fase 2" secara eksplisit menandai Milestone 5.4 sebagai titik paling mungkin gap sensor-native ini jadi nyata dan perlu diselesaikan.
- `scripts/mart_aggregated/promote.py` (M5.3) bersifat all-or-nothing per invocation — 1x panggilan `dbt run`/`test`/promote = 1 keputusan promosi untuk seluruh selector yang dicakup. Kalau selector mencakup model ML yang gagal, SELURUH tabel dalam selector itu (termasuk 76 tabel existing kalau tidak dipisah) ikut tidak ter-promote — bertentangan langsung dengan KK3. Script sudah mendukung `--select` sebagai argumen, jadi isolasi bisa dicapai lewat 2x pemanggilan terpisah tanpa mengubah script.
- Skema `mart_aggregated` (M5.2) sengaja full-aggregated (grain property/kategori x periode, tanpa data per-entity/guest, demi menghindari PII granular) — sementara `ml_output.predictions` di-grain per `entity_id` (per baris prediksi individual). Mismatch grain ini perlu jembatan desain eksplisit.
- `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`: pola kredensial scoped per-job sudah mapan (`extract-writer` = contoh paling dekat: dataset ACL WRITER scoped ke 1 dataset + `bigquery.jobUser`, dipakai proses yang menulis dari "luar" ke dalam warehouse). `dbt-transform` sudah project-level `bigquery.dataEditor` (pengecualian sadar M2.2) — sudah otomatis bisa baca `ml_output` tanpa kredensial baru untuk sisi dbt/sensor.
- `fact_revenue_pace_booking_snapshot` (M5.3) kosong 0 baris karena target tanggal dihitung dari `CURRENT_DATE()` sementara dataset sintetis statis berhenti ~2026-07-01 — pelajaran langsung yang harus dihindari di sini.

## Keputusan (via AskUserQuestion, 2 putaran — user diberi kebebasan tanya lebih dari 1 sesuai instruksi eksplisit)

### 1. Simulasi `ml_output`: mock scorer job terpisah, diperlakukan seolah eksternal

**Keputusan:** Script mock scoring Python biasa (**bukan** dbt — konsisten framing arsitektur "training & scoring pipeline di luar warehouse"), generate prediksi sintetis dari `mart_cleaned`, ditulis ke dataset `ml_output` BigQuery, dijalankan sebagai **job/workflow terpisah** dari `transform-mart-aggregated.yml`.

**Kenapa:** Supaya mekanisme trigger+sensor (bukan cuma join SQL) benar-benar teruji jalan. Kalau scoring digabung 1 workflow dengan mart_aggregated via `workflow_run` chaining biasa, sensor jadi tidak pernah benar-benar dibutuhkan (trivial — completion salah satu workflow lain di repo yang sama bukan situasi yang butuh sensor). Konsisten pola "proof mechanism" `orchestrator-demo-*.yml` M2.0.

**Ditolak:** Populate `ml_output` manual sekali + scope dipersempit ke SQL transformasi murni (opsi ini ditawarkan tapi tidak dipilih user).

### 2. Jembatan grain: tabel fact baru, teragregasi — bukan entity-level

**Keputusan:** 1 fact table baru khusus ML (`fact_ml_occupancy_forecast_property_room_type`), grain property x room_type x target_date x model_version.

**Kenapa:** Konsisten prinsip full-aggregated M5.2, tidak menyentuh 76 tabel existing, dan otomatis mengisolasi kegagalan (KK3) — cukup 1 tabel baru yang bergantung pada `ml_output`, 75 tabel lain independen sepenuhnya secara struktural (bukan cuma secara logic).

**Ditolak:** Tabel entity-level (per guest) — menyimpang dari prinsip full-aggregated M5.2.

### 3. Use-case ML: occupancy forecast per property x room type (bukan churn classifier)

**Keputusan:** Prediksi occupancy rate masa depan per property x jenis kamar — dipilih user, bukan contoh churn classifier di dokumen arsitektur.

**Kenapa:** Instruksi eksplisit user — lebih relevan/konkret untuk platform hospitality ini.

**Catatan provisional:** use-case ini murni untuk kebutuhan simulasi milestone ini, bukan keputusan bisnis final soal model ML apa yang akan dibangun tim ML Engineer.

### 4. Timeout sensor: realistis (bukan skala demo pendek)

**Keputusan:** Polling meniru skenario produksi sungguhan, bukan dioptimalkan untuk kecepatan testing developer. Angka konkret: 30 percobaan x jeda 120 detik (~60 menit total) — lihat Keputusan Teknis #7.

**Kenapa:** User memilih opsi realistis — scoring job eksternal sungguhan butuh waktu nyata untuk selesai (bisa training/inference batch besar), timeout harus mencerminkan itu.

### 5. Skema `ml_output.predictions`: tambah kolom `target_date DATE`

**Keputusan:** Extend skema Bagian 6.3 dengan 1 kolom baru `target_date` — deviasi eksplisit dari dokumen arsitektur.

**Kenapa:** Skema dokumen (`scored_at` = kapan model dijalankan, `feature_snapshot_at` = versi data sumber) tidak punya kolom untuk "tanggal yang diramal". Untuk use-case forecasting (occupancy MASA DEPAN), ini konsep yang sama sekali berbeda dari 2 kolom timestamp yang sudah ada — memaksakan salah satunya akan ambigu (mis. `scored_at` dipakai ganda untuk "kapan discore" DAN "untuk tanggal apa" akan membuat query LEFT JOIN salah/rancu).

**Catatan provisional:** ini deviasi skema yang sengaja dibuat untuk use-case simulasi occupancy forecast; tim ML Engineer nyata mungkin punya solusi berbeda (mis. encode di `predicted_value` sebagai JSON) tergantung use-case model produksi mereka.

### 6. Format `entity_id`: composite string `"property_id:room_type_id"`

**Keputusan:** Tetap 1 kolom `entity_id` sesuai skema dokumen (bukan pecah jadi 2 kolom terpisah), format didokumentasikan eksplisit dengan delimiter `:`, di-split (`SPLIT()`) saat transformasi ke `mart_aggregated`.

**Kenapa:** Occupancy forecast natural-nya 2 dimensi (property x room_type) sekaligus, tapi skema `ml_output.predictions` dirancang generik 1 kolom `entity_id` — composite string mempertahankan kontrak skema dokumen tanpa menambah kolom yang tidak perlu di luar `target_date` (Keputusan #5).

## Keputusan Teknis Lain (dikunci tanpa AskUserQuestion — mengikuti preseden project M5.3)

### 7. Angka konkret sensor: 30 percobaan x 120 detik (~60 menit); `target_date` window relatif ke `MAX(date)` sumber, bukan `CURRENT_DATE()`

Mengoperasionalkan Keputusan #4. Window tanggal target forecast (misal 14 hari ke depan) dihitung relatif terhadap `MAX(date)` yang ada di data occupancy sumber (`mart_cleaned`) — **bukan** `CURRENT_DATE()` BigQuery. Pelajaran langsung dari gap M5.3: `fact_revenue_pace_booking_snapshot` kosong 0 baris karena dataset sintetis statis (berhenti ~2026-07-01) sementara `CURRENT_DATE()` sudah lewat itu. Kalau mock scorer pakai `CURRENT_DATE()` mentah, tabel ML baru ini akan bernasib sama (kosong permanen, tidak bisa dipakai membuktikan KK1/KK2).

### 8. `scripts/ml_scoring/mock_score.py` — script Python baru, pola self-union CTAS (Sandbox mode)

Baca histori occupancy dari `mart_aggregated.fact_revenue_room_type_daily` (M5.3, grain sudah persis property x room_type x tanggal) via client, hitung forecast naif (moving average `occupancy_rate` 30 hari terakhir per property x room_type, `confidence_score` dari koefisien variasi), tulis ke `ml_output.predictions` lewat `CREATE OR REPLACE TABLE x AS SELECT <hasil scoring baru> UNION ALL SELECT * FROM x` (kalau tabel sudah ada) — DDL murni, kompatibel Sandbox mode (sama pola `fact_revenue_pace_booking_snapshot` M5.3). `model_name='occupancy_forecast'`, `model_version='occupancy_forecast_mock_v1'` (string statis, mock, tidak perlu versioning sungguhan).

**Koreksi saat implementasi:** dataset `ml_output` **tidak** dibuat idempotent oleh script (`create_dataset(exists_ok=True)`) seperti draf awal — kredensial `ml-scoring-writer` sengaja least-privilege (dataset ACL WRITER, bukan `bigquery.datasets.create` project-level), jadi secara desain TIDAK BISA membuat dataset baru. Script hanya verifikasi dataset sudah ada (`client.get_dataset`, gagal jelas kalau belum) — dataset provisioning tetap tanggung jawab pemilik infrastruktur data (sudah dibuat manual di Checkpoint 1), bukan job scoring itu sendiri. Ini konsisten dengan prinsip least-privilege di `kebijakan-akses-kredensial-scoped.md`, cuma draf Keputusan #8 awal keliru mengasumsikan write-access dataset = create-access dataset.

### 9. Model dbt baru di folder khusus `warehouse/models/mart_aggregated/ml_feedback/`, tag `ml_feedback_loop`

Folder ke-7 di luar 6 folder domain produksi existing — dijustifikasi karena "Feedback Loop ML" adalah Bagian 6 tersendiri di dokumen arsitektur, bukan bagian dari 6 domain bisnis produksi manapun. Tag `ml_feedback_loop` dipakai untuk `--select`/`--exclude` terpisah di `promote.py` (isolasi kegagalan Keputusan #2). Model: `FROM ml_output.predictions` (base — menjamin `model_version`/`feature_snapshot_at` selalu terisi by construction, bukan nullable lewat LEFT JOIN) `LEFT JOIN` data aktual dari `fact_revenue_room_type_daily` (M5.3) by `property_id, room_type_id, date=target_date` untuk kolom `actual_occupancy_rate`/`forecast_error_pct` (nullable — hanya terisi kalau `target_date` sudah lewat dan data aktual tersedia).

### 10. Dua workflow baru + `--select` ganda di `transform-mart-aggregated.yml` (workflow pertama yang pernah ada untuk `mart_aggregated`)

- `scoring-occupancy-forecast.yml` (`run-scoring-occupancy-forecast`) — trigger `workflow_run` off `"Transform Staging and Mart Cleaned"`, jalankan `mock_score.py`, `renew_expiration.py ml_output`.
- `transform-mart-aggregated.yml` (`run-transform-mart-aggregated`) — workflow terjadwal pertama untuk `mart_aggregated`, trigger `workflow_run` off `"Transform Staging and Mart Cleaned"` juga (**paralel** dengan scoring, BUKAN `workflow_run` off scoring — supaya sensor polling sungguhan dipakai, bukan sekadar chaining trivial, konsisten Keputusan #1):
  1. `dbt run`/`test`/`promote.py --select mart_aggregated,exclude:tag:ml_feedback_loop` — wajib sukses (76 tabel existing).
  2. Sensor: polling `ml_output.predictions` (30x/120 detik) menunggu baris baru muncul.
  3. Kalau sensor sukses: `dbt run`/`test`/`promote.py --select tag:ml_feedback_loop` — best-effort, `continue-on-error`, tidak menggagalkan job kalau gagal.
  4. Kalau sensor timeout: skip step ML, log jelas, job tetap sukses (KK3).
  5. `renew_expiration.py mart_aggregated mart_aggregated_staging`.

### 11. Kredensial: `ml-scoring-writer` baru (scoped write `ml_output`), tidak ada credential baru untuk sisi baca

**Keputusan:** Buat 1 kredensial baru `ml-scoring-writer` — BigQuery dataset ACL WRITER scoped ke `ml_output` + `bigquery.jobUser`, persis pola `extract-writer` (M2.1: dataset ACL WRITER scoped ke `raw_production` saja) karena perannya analog (proses yang menulis dari "luar" warehouse ke dalam 1 dataset spesifik). Dipakai eksklusif oleh `mock_score.py`/`scoring-occupancy-forecast.yml` via env var `ML_SCORING_WRITER_CREDENTIALS`. Verifikasi isolasi via `scripts/bigquery_common/verify_dataset_isolation.py --allow "ml_output.predictions" --deny "mart_cleaned.financial_summary"` — **PASS keduanya** (baca `ml_output` diizinkan, baca `mart_cleaned` ditolak).

**Koreksi saat implementasi (Checkpoint 2):** draf awal cuma scope WRITER `ml_output`, ternyata `mock_score.py` juga perlu BACA data fitur sumber (`mart_aggregated.fact_revenue_room_type_daily`) untuk menghitung forecast — gap yang baru ketahuan saat test-run pertama gagal `Access Denied`. **Ditambahkan 1 ACL READER `mart_aggregated`** ke service account yang sama (bukan bikin service account/key baru — user diminta konfirmasi eksplisit dulu karena ini perubahan IAM/security setting, disetujui). Konsisten peran "scoring pipeline eksternal" yang secara arsitektur (Bagian 6.1) memang butuh baca `mart_cleaned`/`mart_aggregated` sebagai sumber fitur DAN tulis hasil prediksi — 2 grant per-dataset terpisah (bukan role project-level), masih least-privilege.

Untuk sisi baca dbt LEFT JOIN + sensor polling di `transform-mart-aggregated.yml`: **tidak perlu kredensial baru** — `dbt-transform` (M2.2, project-level `bigquery.dataEditor`, pengecualian sadar) sudah otomatis bisa baca `ml_output` tanpa perubahan apa pun, dan workflow ini sudah memakai `dbt-transform` untuk seluruh step dbt-nya.

**Kenapa bukan reader terpisah untuk sensor:** Sensor berjalan di job yang sama dengan dbt run/test/promote (yang sudah pakai `dbt-transform`), menambah kredensial ketiga di 1 job yang sama menambah kompleksitas tanpa manfaat isolasi nyata (kedua step ada di boundary trust yang sama — proses transformasi warehouse, bukan proses eksternal).

Baris baru ditambahkan ke tabel inventaris `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`.

## Task Breakdown

7 fase, 7 checkpoint (commit tiap checkpoint, push di checkpoint final).

### Fase 0 — Setup: decisions.md + skema `ml_output` + kredensial
1. Tulis `decisions.md` (dokumen ini). Buat kredensial `ml-scoring-writer` (Keputusan #11), update `kebijakan-akses-kredensial-scoped.md`.

**Checkpoint 1**

### Fase 1 — Mock scorer
2. `scripts/ml_scoring/mock_score.py` (Keputusan #8) — buat dataset `ml_output` idempotent, hitung forecast naif per property x room_type, tulis ke `ml_output.predictions` (self-union CTAS, kolom termasuk `target_date`, `entity_id` composite). Jalankan manual sekali, verifikasi hasil.

**Checkpoint 2**

### Fase 2 — Model dbt + tes
3. Verifikasi skema riil `fact_revenue_room_type_daily`/`dim_room_type`/`dim_property`. Tulis `warehouse/models/mart_aggregated/ml_feedback/_ml_output_sources.yml` + `fact_ml_occupancy_forecast_property_room_type.sql` (tag `ml_feedback_loop`, Keputusan #9) + `_ml_feedback_tests.yml` (not_null `model_version`/`feature_snapshot_at` — KK2, relationships ke `dim_property`/`dim_room_type`, accepted_values `model_name`).

**Checkpoint 3**

### Fase 3 — Workflow scoring
4. `.github/workflows/scoring-occupancy-forecast.yml` (Keputusan #10) — trigger off mart_cleaned transform, jalankan mock scorer + renew expiration.

**Checkpoint 4**

### Fase 4 — Workflow mart_aggregated + sensor + isolasi kegagalan
5. `.github/workflows/transform-mart-aggregated.yml` (Keputusan #10) — dbt run/test/promote 76 tabel (wajib), sensor polling `ml_output`, dbt run/test/promote tabel ML (best-effort, non-blocking), renew expiration.

**Checkpoint 5**

### Fase 5 — Validasi end-to-end (3 KK)
6. Trigger manual (`gh workflow run`) siklus penuh, verifikasi KK1 (jalan tanpa intervensi manual). Verifikasi KK2 (`model_version`/`feature_snapshot_at` selalu terisi — cek langsung di BigQuery). Uji coba terkontrol untuk KK3: paksa sensor timeout, buktikan 76 tabel lain tetap ter-promote sukses.

**Checkpoint 6**

### Fase 6 — Dokumentasi + Finalisasi
7. Update `DataSchema-mart-aggregated.md`/`Metadata-mart-aggregated.md` (tambah 1 tabel fact ML baru, catatan deviasi skema `ml_output`, ditandai provisional/contoh). Verifikasi 3 KK sumber eksplisit, tulis `report.md` — wajib memuat catatan eksplisit status provisional (lihat header dokumen ini).

**Checkpoint 7 (final)** — commit + push.
