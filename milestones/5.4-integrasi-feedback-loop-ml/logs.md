# Milestone 5.4: Integrasi Feedback Loop ML — Logs

## 2026-08-08 -- Checkpoint 1: decisions.md + kredensial ml-scoring-writer (Fase 0)

`decisions.md` ditulis (11 keputusan: 6 via AskUserQuestion 2 putaran, 5 teknis dikunci mengikuti preseden M5.3). Termasuk catatan status provisional di header dokumen (permintaan eksplisit user setelah plan pertama sempat ditolak untuk direvisi) -- seluruh desain `ml_output`/use-case occupancy forecast di milestone ini murni contoh/simulasi, menunggu definisi nyata dari tim ML Engineer.

Kredensial `ml-scoring-writer` dibuat mengikuti pola `extract-writer` (M2.1) persis -- service account + dataset ACL WRITER scoped, key file dibuat manual oleh user (bukan assistant), konsisten prinsip project ini soal penanganan kredensial mentah:

- `gcloud iam service-accounts create ml-scoring-writer --project=nirwana-database-elt` -- sukses, `ml-scoring-writer@nirwana-database-elt.iam.gserviceaccount.com`.
- `bq mk --dataset --location=US --default_table_expiration=5184000 --default_partition_expiration=5184000 nirwana-database-elt:ml_output` -- dataset baru dibuat, default expiration 60 hari (5184000000 ms) konsisten Sandbox mode, sama seperti dataset lain (`mart_cleaned` dicek sebagai referensi).
- `gcloud projects add-iam-policy-binding nirwana-database-elt --member=serviceAccount:ml-scoring-writer@... --role=roles/bigquery.jobUser` -- sukses.
- Dataset ACL `ml_output`: `bq show --format=prettyjson` -> tambah entry `{"role": "WRITER", "userByEmail": "ml-scoring-writer@..."}` via Python (round-trip JSON, path Windows-native dipakai karena `python.exe` di git-bash tidak resolve path style `/c/...`) -> `bq update --source=<file> nirwana-database-elt:ml_output` -- sukses, diverifikasi ulang lewat `bq show` (WRITER entry ada).

`docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`: baris baru ditambahkan ke tabel inventaris + daftar "Kredensial per-job". `.env.example`: `ML_SCORING_WRITER_CREDENTIALS=scripts/extract/gcp-ml-scoring-writer-key.json` ditambahkan (path sama seperti kredensial lain -- semua key file BigQuery memang disimpan di folder `scripts/extract/` walau beda milestone asal, sudah tercakup pattern `.gitignore` `scripts/extract/*.json` yang ada, tidak perlu entry baru).

**Belum selesai (butuh aksi user):** key file JSON untuk `ml-scoring-writer` belum dibuat -- assistant tidak membuat key file kredensial (prinsip project + batasan keamanan). User perlu jalankan sendiri sebelum Checkpoint 2 (`mock_score.py`) bisa benar-benar dites end-to-end terhadap BigQuery:

```bash
gcloud iam service-accounts keys create scripts/extract/gcp-ml-scoring-writer-key.json \
  --iam-account=ml-scoring-writer@nirwana-database-elt.iam.gserviceaccount.com
```

Setelah key file ada, isi `ML_SCORING_WRITER_CREDENTIALS` di `.env` (bukan `.env.example`) dengan path yang sama, lalu verifikasi isolasi:

```bash
python scripts/bigquery_common/verify_dataset_isolation.py \
  --keyfile scripts/extract/gcp-ml-scoring-writer-key.json \
  --project nirwana-database-elt \
  --allow "ml_output.predictions" \
  --deny "mart_cleaned.financial_summary"
```

## 2026-08-08 -- Checkpoint 2: mock_score.py ditulis, ditest, koreksi kredensial (Fase 1)

User membuat key file (`scripts/extract/gcp-ml-scoring-writer-key.json`) dan mengisi `.env` sendiri, sesuai prinsip project. `scripts/ml_scoring/mock_score.py` ditulis (Keputusan #8) -- baca histori occupancy dari `mart_aggregated.fact_revenue_room_type_daily` (bukan `mart_cleaned` mentah -- grain sudah pas), hitung moving average 30 hari + confidence dari koefisien variasi, tulis ke `ml_output.predictions` via self-union CTAS.

**Run pertama gagal:** `Access Denied` baca `mart_aggregated.fact_revenue_room_type_daily` -- `ml-scoring-writer` cuma di-scope WRITER `ml_output`, lupa scoring pipeline juga butuh baca data fitur sumber (gap di Keputusan #11 draf awal). **Diperbaiki:** minta konfirmasi user dulu (perubahan IAM/security setting), lalu tambah 1 ACL READER `mart_aggregated` ke service account yang sama (`bq show`/`bq update` round-trip, pola sama Checkpoint 1). `kebijakan-akses-kredensial-scoped.md` dan `decisions.md` Keputusan #11 diperbarui mencatat koreksi ini.

**Run kedua (setelah fix) -- sukses:**
- First run: `ml_output.predictions` dibuat baru, 252 baris. `target_date` range `2026-07-02..2026-07-15` (relatif ke `MAX(period_date)`=2026-07-01 di sumber, BUKAN `CURRENT_DATE()` -- pelajaran M5.3 pace booking berhasil dihindari). 18 entity (property x room_type) distinct.
- Sample row dicek manual: `entity_id='P01:1'`, `model_version='occupancy_forecast_mock_v1'`, `predicted_value='0.8272'`, `confidence_score=0.918`. `COUNTIF(model_version IS NULL)=0`, `COUNTIF(feature_snapshot_at IS NULL)=0` -- KK2 (kolom wajib selalu terisi) terbukti sejak level mock scorer, bukan cuma di dbt layer nanti.
- Run kedua (test self-union append): 252 -> 504 baris, `scored_at` baru muncul di samping yang lama -- pola self-union/full-history (Keputusan #7 turunan M5.3 pace booking) terbukti bekerja, bukan cuma diasumsikan.
- Isolasi kredensial (`verify_dataset_isolation.py`, setelah fix): `ml_output.predictions` (allow) PASS, `mart_cleaned.financial_summary` (deny) PASS.

## 2026-08-08 -- Checkpoint 3: model dbt + tes ML feedback loop (Fase 2)

Skema riil diverifikasi dulu (bukan asumsi): `fact_revenue_room_type_daily` (property_id STRING, room_type_id INTEGER, period_date DATE, occupancy_rate FLOAT, dst -- persis grain yang dibutuhkan), `dim_room_type`/`dim_property` (PK sesuai ekspektasi). `entity_id` yang ditulis `mock_score.py` sudah pakai `room_type_id` asli dari `fact_revenue_room_type_daily` (bukan dihitung ulang), jadi tidak ada risiko mismatch surrogate key dengan `dim_room_type` (yang di-generate `row_number() over (order by room_type)`).

Dibuat: `_ml_output_sources.yml` (source `ml_output.predictions`, catatan provisional diulang di description), `fact_ml_occupancy_forecast_property_room_type.sql` (`FROM ml_output.predictions` sebagai base -- KK2 by construction -- `LEFT JOIN` `fact_revenue_room_type_daily` by `target_date` untuk `actual_occupancy_rate`/`forecast_error_abs`), `_ml_feedback_tests.yml` (12 test: not_null x7 termasuk `model_version`/`feature_snapshot_at`, unique `prediction_id`, relationships x2, accepted_values `model_name`). `dbt_project.yml` ditambah blok `ml_feedback: +tags: ['ml_feedback_loop']`.

`dbt run --select tag:ml_feedback_loop` -- sukses, 504 baris (cocok `ml_output.predictions` saat ini). `dbt test --select tag:ml_feedback_loop` -- **12/12 PASS**, termasuk `not_null_..._model_version` dan `not_null_..._feature_snapshot_at` (bukti otomatis KK2, bukan cuma manual).

**Ditemukan & diperbaiki 2 bug saat verifikasi `promote.py` dengan scope terpisah** (dicatat detail di `decisions.md` Keputusan #10a):
1. Sintaks selector draf awal (`--select mart_aggregated,exclude:tag:ml_feedback_loop`) bukan sintaks dbt valid -- `dbt` cuma punya `--exclude` sebagai flag terpisah. Diverifikasi ulang: `dbt ls --select mart_aggregated --exclude tag:ml_feedback_loop --resource-type model` -> tepat 76 model.
2. `promote.py` (M5.3) ternyata mempromosikan SEMUA tabel di dataset staging, tidak benar-benar di-scope oleh `--select` -- cuma kebetulan aman waktu M5.3 karena selalu 1 selector untuk semuanya. Ditambah `--exclude` + tahap promosi sekarang resolve scope lewat `dbt --quiet ls ... --output name` dulu (butuh `--quiet` supaya banner log dbt tidak ikut ke-parse jadi "nama model").

Verifikasi akhir terhadap BigQuery sungguhan: `promote.py --select tag:ml_feedback_loop` -> "1 model(s) selected", 1 tabel dipromosikan. `mart_aggregated` (dataset asli, bukan staging) diquery langsung: **77 tabel total** (76 M5.3 + 1 baru), `fact_ml_occupancy_forecast_property_room_type` berisi 504 baris -- isolasi promosi terbukti bekerja (bukan cuma diklaim), tanpa perlu rebuild 76 tabel lain untuk membuktikannya.

## 2026-08-08 -- Checkpoint 4: sensor + workflow scoring (Fase 3)

`scripts/ml_scoring/wait_for_ml_output.py` ditulis (sensor polling manual, workaround yang direkomendasikan `konvensi-job-dependency.md` sendiri) -- pakai kredensial `dbt-transform` yang sudah ada (bukan kredensial baru, lihat decisions.md Keputusan #11), query `COUNT(*) WHERE model_name=... AND scored_at >= now - lookback_minutes`, bukan "since" timestamp literal (toleran skew waktu mulai antara 2 workflow paralel). Ditest langsung terhadap BigQuery sungguhan (bukan disimulasikan): `--max-attempts 1` dengan data asli -> exit 0 ("Sensor: ml_output is ready", 504 baris ketemu); `--model-name nonexistent_model --max-attempts 1` -> exit 1 ("Sensor TIMED OUT") -- kedua jalur (found/timeout) terbukti bekerja sebelum dipasang ke workflow.

`.github/workflows/scoring-occupancy-forecast.yml` ditulis -- trigger `workflow_run` off "Transform Staging and Mart Cleaned" (nama persis harus cocok `name:` di `transform-mart-cleaned.yml`), jalankan `mock_score.py` + `renew_expiration.py ml_output`. Pola step identik `reverse-etl-mart-cleaned.yml` (key dari secret via `env:`+`printf '%s'`, bukan `echo` -- aman untuk JSON multi-baris).

`.github/workflows/transform-mart-aggregated.yml` ditulis sekaligus (Fase 4) -- workflow terjadwal pertama untuk `mart_aggregated`, trigger paralel dari sumber yang sama (BUKAN off scoring workflow, Keputusan #1), 76 tabel wajib -> sensor (`continue-on-error: true`) -> ML best-effort (`if: steps.sensor.outcome == 'success'`) -> renew expiration.

**Validasi sintaks sebelum commit (bukan cuma ditulis dan diasumsikan benar):** `python -c "import yaml; yaml.safe_load(...)"` terhadap kedua file -- ketemu 1 bug nyata: `name:` step "... (KK3: mart_aggregated tetap sukses tanpa ML)" gagal parse (`mapping values are not allowed here`) karena colon-spasi di dalam scalar YAML unquoted. Diperbaiki (colon dihapus dari kalimat). Setelah fix, kedua file `yaml.safe_load` bersih.

Butuh 1 GitHub Secret baru: `GCP_ML_SCORING_WRITER_KEY_JSON` (isi `scripts/extract/gcp-ml-scoring-writer-key.json`). Minta izin user dulu (preseden M2.1/M2.4: memindahkan kredensial yang SUDAH ada ke secret storage, bukan membuat baru, jadi tidak diblokir classifier tapi tetap perlu izin eksplisit karena mengubah config shared repo) -- disetujui, `gh secret set GCP_ML_SCORING_WRITER_KEY_JSON < scripts/extract/gcp-ml-scoring-writer-key.json` sukses, diverifikasi via `gh secret list`.
