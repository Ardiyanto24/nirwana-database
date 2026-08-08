# Milestone 5.4: Integrasi Feedback Loop ML (Join ke ml_output) — Report

**Status:** Completed
**Date completed:** 2026-08-08

## ⚠️ Status: Seluruhnya Provisional — Menunggu Tim ML Engineer

Sama seperti dicatat di header `decisions.md`: skema `ml_output.predictions`, use-case occupancy forecast, dan seluruh mekanisme mock scorer di milestone ini **bukan kontrak final**. Ini murni bukti-konsep mekanisme orkestrasi (trigger→sensor→join→test) — begitu tim ML Engineer mendefinisikan skema/use-case nyata, keputusan desain di sini kemungkinan besar berubah.

## Kriteria Keberhasilan — Hasil

- [x] **Simulasi siklus penuh (`mart_cleaned` refresh → trigger → sensor → join → `mart_aggregated` final) berhasil berjalan end-to-end tanpa intervensi manual.** — Terpenuhi. Dibuktikan terhadap GitHub Actions sungguhan (bukan simulasi lokal): 1 trigger manual `gh workflow run transform-mart-cleaned.yml` ([run 31259156230](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31259156230), mensimulasikan jadwal cron 05:00 UTC) menyebabkan **3 workflow downstream otomatis jalan lewat `workflow_run`** tanpa intervensi lanjutan: `reverse-etl-mart-cleaned.yml` (existing), `scoring-occupancy-forecast.yml`, dan `transform-mart-aggregated.yml` ([run 31259292176](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31259292176)) — seluruhnya `conclusion: success`. Sensor menemukan `ml_output` di attempt 1/30 (756 baris fresh), tabel ML ikut ter-promote di run yang sama. Detail lengkap di `logs.md` Checkpoint 6.
- [x] **Baris hasil prediksi yang muncul di `mart_aggregated` selalu punya `model_version` dan `feature_snapshot_at` terisi.** — Terpenuhi, dibuktikan 2 lapis: (1) 12 dbt test `not_null` pada kedua kolom, PASS (Checkpoint 3); (2) query langsung ke `mart_aggregated.fact_ml_occupancy_forecast_property_room_type` live setelah run CI sungguhan — `COUNTIF(model_version IS NULL)=0`, `COUNTIF(feature_snapshot_at IS NULL)=0` dari 756 baris. Terjamin **struktural**, bukan cuma diverifikasi test: model dbt mengambil `FROM ml_output.predictions` sebagai base query (bukan `LEFT JOIN` dari sisi `mart_aggregated`), jadi kedua kolom itu tidak pernah bisa NULL lewat mekanisme join manapun.
- [x] **Jika `ml_output` gagal/telat ditulis, `mart_aggregated` tidak ikut gagal total — bagian non-ML tetap bisa ter-refresh.** — Terpenuhi, dibuktikan lewat **uji coba terkontrol** (pola fault-injection sama seperti DQ gate M5.3): `gh workflow run transform-mart-aggregated.yml -f sensor_model_name=nonexistent_model_kk3_test -f sensor_max_attempts=2 -f sensor_interval_seconds=5` ([run 31259615980](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31259615980)) — sensor dipaksa mencari model yang tidak pernah ada, log membuktikan `Sensor TIMED OUT after 2 attempts (10s total)`, step promosi ML **SKIPPED** (kondisi `if` tidak terpenuhi), tapi log step wajib membuktikan `76 table(s) promoted to mart_aggregated (scope: 76 model(s) selected)` dan **job keseluruhan tetap `conclusion: success`**.

## Deliverables

- `scripts/ml_scoring/mock_score.py` — mock scoring pipeline (STAND-IN scoring eksternal), forecast naif occupancy per property×room_type, tulis `ml_output.predictions` via self-union CTAS.
- `scripts/ml_scoring/wait_for_ml_output.py` — sensor polling manual (GitHub Actions tidak punya sensor native).
- `scripts/mart_aggregated/promote.py` — diperluas dengan `--exclude` + promosi ter-scope (bukan lagi "copy semua tabel staging"), fix bug yang ditemukan saat verifikasi isolasi M5.4.
- `warehouse/models/mart_aggregated/ml_feedback/` — 1 model fact baru (`fact_ml_occupancy_forecast_property_room_type`, tag `ml_feedback_loop`) + source `ml_output` + 12 dbt test.
- `.github/workflows/scoring-occupancy-forecast.yml` — workflow baru, trigger off `transform-mart-cleaned.yml`.
- `.github/workflows/transform-mart-aggregated.yml` — **workflow terjadwal pertama untuk `mart_aggregated`** (M5.3 hanya manual), termasuk sensor + isolasi kegagalan + `workflow_dispatch` input untuk uji coba terkontrol KK3.
- Kredensial baru `ml-scoring-writer` (BigQuery, WRITER `ml_output` + READER `mart_aggregated`), GitHub Secret `GCP_ML_SCORING_WRITER_KEY_JSON` — didokumentasikan di `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`.
- Dataset BigQuery `ml_output` (baru) — live, 756 baris prediksi.
- `docs/07-mart-aggregated/DataSchema-mart-aggregated.md`, `Metadata-mart-aggregated.md` — masing-masing ditambah 1 addendum bertanda **PROVISIONAL** untuk tabel ML baru (46 fact + 27 dimension = 73 tabel total).
- `docs/keputusan-tertunda.md` — entri "Orchestrator sungguhan" diberi catatan bahwa prediksinya terbukti benar di M5.4 (workaround polling terpakai), status tetap **Open** (bukan di-resolve).
- `milestones/5.4-integrasi-feedback-loop-ml/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada deviasi pada 11 keputusan inti. **Beberapa koreksi teknis ditemukan & diperbaiki saat implementasi/verifikasi** (didokumentasikan eksplisit di `decisions.md`/`logs.md` per checkpoint, bukan diperbaiki diam-diam):
- **Sintaks selector dbt salah** (Keputusan #10a): draf `--select mart_aggregated,exclude:tag:ml_feedback_loop` bukan sintaks dbt valid — `--exclude` ternyata flag terpisah.
- **Bug laten `promote.py` (sejak M5.3)**: tahap promosi menyalin SEMUA tabel staging, tidak benar-benar di-scope `--select` — aman kebetulan waktu M5.3 (1 selector untuk semua), tapi akan salah kalau dipanggil 2x scope berbeda. Diperbaiki dengan `dbt --quiet ls --output name` untuk resolve scope sebenarnya.
- **Gap kredensial `ml-scoring-writer`**: draf awal cuma WRITER `ml_output`, ternyata `mock_score.py` juga perlu baca `mart_aggregated` (data fitur). Ditambah 1 ACL READER (user dikonfirmasi dulu, perubahan IAM).
- **`scripts/extract/bq.py` env var**: `scoring-occupancy-forecast.yml` lupa menulis `BIGQUERY_PROJECT_ID`/`BIGQUERY_DATASET` ke `.env` — ketahuan dari run CI sungguhan pertama (`renew_expiration.py` gagal `KeyError`), bukan dari review kode.
- **Asumsi salah soal least-privilege**: draf Keputusan #8 mengasumsikan `ml-scoring-writer` bisa `create_dataset(exists_ok=True)` — ternyata WRITER dataset ACL tidak termasuk hak buat dataset baru. Diperbaiki: script cuma verifikasi dataset ada, provisioning tetap tanggung jawab pemilik infrastruktur.

## Known Gaps / Follow-ups

- **Seluruh feedback loop ML di milestone ini PROVISIONAL** — lihat catatan status di atas dan header `decisions.md`. Jangan dibaca sebagai kontrak final `ml_output`.
- **Sensor tetap workaround polling, bukan sensor native** — `docs/keputusan-tertunda.md` "Orchestrator sungguhan" tetap Open, cuma dikonfirmasi prediksinya benar (lihat catatan yang ditambahkan di dokumen itu).
- **Tabel ML baru belum di-set partition/cluster key** — skala kecil (~750 baris) di scope simulasi ini, perlu direvisit kalau data bertambah signifikan atau setelah skema final dari tim ML Engineer.
- **ERD diagram (`ERD-mart-aggregated.md`/`.mmd`) TIDAK diupdate** — di luar scope Fase 6 yang disepakati di plan (cuma `DataSchema`/`Metadata`), jadi jumlah tabel di diagram (72) sudah tidak sinkron dengan realita (73). Perlu update terpisah kalau diagram dipakai lagi untuk referensi jumlah tabel.
- **Reverse ETL `mart_aggregated` (M5.5) belum dibangun** — tabel ML baru ini (dan 76 lainnya) masih cuma ada di BigQuery, belum tersedia di serving PostgreSQL.
- **Rotasi kredensial `ml-scoring-writer`** belum otomatis — gap yang sama seperti kredensial lain (lihat `kebijakan-akses-kredensial-scoped.md` "Rotasi dan Pencabutan").
- **Sensor timeout realistis (~60 menit) belum pernah benar-benar diuji habis** — uji coba terkontrol KK3 pakai timeout dipersingkat (`workflow_dispatch` input) untuk kepraktisan, bukan menunggu 60 menit penuh. Mekanisme timeout-nya sendiri (kode `wait_for_ml_output.py`) sudah diverifikasi benar secara logic, cuma durasi penuh belum pernah dijalani nyata.

## Handoff Notes

- **Milestone 5.5 (Reverse ETL Mart Aggregated)**: perlu memutuskan apakah tabel `fact_ml_occupancy_forecast_property_room_type` (provisional) ikut disinkronkan ke PostgreSQL bersama 76 tabel lain, atau ditunda sampai skema final dari tim ML Engineer — cek `docs/07-mart-aggregated/DataSchema-mart-aggregated.md` addendum M5.4 sebelum memutuskan.
- **Tim ML Engineer (kalau/ketika terlibat)**: `scripts/ml_scoring/mock_score.py` perlu diganti scoring pipeline sungguhan; skema `ml_output.predictions` (termasuk deviasi `target_date` dan format `entity_id`) perlu direview ulang terhadap kebutuhan model produksi sesungguhnya — jangan asumsikan skema di milestone ini final.
- **Milestone 5.6 (Mekanisme Pengajuan Perubahan Cakupan)**: kalau tim ML Engineer mengajukan skema `ml_output` yang berbeda, perubahan tabel `fact_ml_occupancy_forecast_property_room_type` sebaiknya lewat jalur pengajuan resmi M5.6 begitu milestone itu ada, bukan diedit ad-hoc.
- **`scripts/mart_aggregated/promote.py`** sekarang mendukung `--exclude` dan promosi ter-scope — pola ini bisa dipakai kalau ke depan ada kebutuhan isolasi kegagalan serupa untuk domain lain (mis. kalau salah satu dari 6 domain M5.3 butuh dipisah cadence refresh-nya).
