# Milestone 6.7: Dashboard dan Alerting Terpadu (Fase 2) — Report

**Status:** Completed (Bagian A — internal, Grafana) + Completed (Bagian B — `api/` publik) + **Kode selesai, deploy publik tertunda** (Bagian B — `web/` publik, aksi user)
**Date completed:** 2026-08-11 (Bagian A + B/`api`); Bagian B/`web` menunggu konfirmasi deploy user

Ini milestone **penutup keluarga 6.x** — tidak ada Milestone 6.8/fase 3 di `docs/03-implementation-plans/` saat ini.

## Kriteria Keberhasilan — Hasil

- [x] **KK1 — Dashboard mencerminkan kondisi terkini seluruh pipeline dan dapat diakses tim.** — Terpenuhi secara literal lewat Grafana: dashboard baru `"Nirwana - Warehouse & Serving Monitoring (Fase 2)"` (9 panel: status 10 titik, alert per akar masalah, DQ gate, volume anomaly warehouse, kesehatan `ml_output`, kesehatan swap reverse ETL, storage & vacuum serving, performa chatbot, tautan ke dashboard Fase 1), diverifikasi live lewat API Grafana Cloud dan query manual terhadap tiap panel. **Diperluas** (Keputusan G, atas permintaan user) ke dashboard publik: 8 endpoint `/api/warehouse/*` **live di Render** (diverifikasi HTTP nyata), 4 halaman baru di `web/` **kode selesai + terverifikasi via browser nyata** (lokal), **terpush ke GitHub**, tapi **belum live publik** — menunggu deploy manual Vercel oleh user (blocker independen sejak M1.7, di luar kendali milestone ini).
- [x] **KK2 — Simulasi kegagalan di satu titik akar (uji coba terkontrol) menghasilkan alert yang jelas menunjukkan titik akar tersebut, bukan alert terpisah dari setiap tahap downstream.** — Terpenuhi dan dibuktikan 2 kali: (1) uji coba terkontrol sintetis (`simulate_test.py` Skenario 7) — Titik 2 gagal + Titik 3/6/9 (1-hop) dan Titik 7 (2-hop lewat Titik 6) sebagai downstream, `monitoring.alerts_with_root_cause` mengelompokkan SEMUA ke `root_titik_id=2`; query bentuk rule Grafana atas data itu menghasilkan **tepat 1 baris** (bukan 5 terpisah); (2) **bukti tambahan dari data produksi ASLI** (bukan sintetis) — 2 temuan nyata M6.6 (`serving_swap_slow` di Titik 8, `serving_swap_orphan_table` di Titik 10) yang kebetulan aktif hari yang sama dan berbagi edge dependency, terkelompok otomatis oleh mekanisme yang sama, diverifikasi via browser nyata di halaman `/warehouse`.

## Deliverables

### Bagian A — Internal (Grafana)
- `monitoring.titik_dependency` (12 baris: 10 titik + edge dependency dari peta M6.1).
- View `monitoring.titik_event_today` + `monitoring.alerts_with_root_cause` (recursive CTE, real-time, root-cause grouping — tanpa job/tabel baru, tanpa dobel logic deteksi).
- `scripts/monitoring_warehouse/detect_pipeline_dependency_gap.py` (baru) — alert_type `pipeline_dependency_gap`, sinyal turunan gap Titik 1→2, dijadwalkan di `monitoring-warehouse-dq-anomaly.yml`.
- `scripts/grafana/build_dashboard_warehouse_serving.py`, `create_alerts_warehouse_serving.py` (baru) — dashboard 9 panel + 1 alert rule multi-dimensional + notification policy `group_by: [root_titik_id]`.
- `scripts/monitoring_warehouse/simulate_test.py` — Skenario 7 (root-cause grouping) ditambahkan, 8/8 skenario PASS.

### Bagian B — Publik (`api/`+`web/`, Keputusan G — perluasan atas permintaan user)
- `api/`: 8 endpoint `GET /api/warehouse/*` (pipeline-status, alerts, dq-gate, volume-anomaly, ml-output-health, reverse-etl-health, serving-storage, chatbot-perf) — semua agregat/read-only, **tidak ada kredensial baru** (`monitoring_api_reader` M1.6 sudah cakup semua tabel baru lewat `ALTER DEFAULT PRIVILEGES`, diverifikasi empiris). **Live di Render**, endpoint Fase 1 lama tetap utuh.
- `web/`: 4 halaman baru (`/warehouse`, `/warehouse/dq-volume-ml`, `/warehouse/reverse-etl-serving`, `/warehouse/chatbot-performance`), `Nav.tsx`+`src/lib/api.ts` extend. Performa chatbot **sengaja agregat-only** — tidak pernah expose baris mentah `chatbot_query_log` (ada `employee_id`). Terverifikasi via browser nyata (`next dev` lokal → `uvicorn` lokal). **Terpush ke GitHub, deploy Vercel tertunda** (lihat Known Gaps).

## Deviations from decisions.md

Tidak ada deviasi pada Keputusan A-J yang dikunci user — semua diimplementasikan sesuai rencana. **6 temuan ditemukan & diperbaiki saat implementasi** (dicatat lengkap di `logs.md`, ringkas di sini):

1. **Checkpoint 2**: 2 alert nyata M6.6 (tak terkait, kebetulan sama hari + berbagi edge) ikut terkorelasi — didokumentasikan sebagai limitation desain (korelasi berbasis hari-kalender), bukan bug, karena sesuai kebutuhan literal KK2.
2. **Checkpoint 3**: 3 panel baru ikut menampilkan data uji coba tersisa dari M6.4/M6.6 (termasuk 1 bug nyata `is_simulated` salah di script M6.6) — diperbaiki dengan filter defensif `schema_name != '_simulation'` di panel, sesuai instruksi eksplisit CLAUDE.md.
3. **Checkpoint 5**: `titik_event_today`/`alerts_with_root_cause` awalnya hardcode `is_simulated=false`, membuat mekanismenya sendiri mustahil diuji coba terkontrol — direfactor mengekspos `is_simulated` sebagai kolom, filter dipindah ke konsumen (Keputusan A tetap utuh, cuma cara filternya dipindah).
4. **Checkpoint 6**: ditemukan race condition NYATA di `detect_volume_anomaly.py` (M6.3) — workflow terjadwal bisa memindai data uji coba `simulate_test.py` sebagai data produksi kalau timing tumpang tindih, menghasilkan baris `is_simulated=FALSE` yang kebal cleanup manapun. Di luar scope diperbaiki (M6.3 closed) — diatasi defensif di query M6.7 sendiri, di-flag (`docs/keputusan-tertunda.md`, `task_7da36df0`).
5. **Checkpoint 7**: leftover 2 baris `dbt_test_result` dari pendekatan Checkpoint 5 yang ditinggalkan (sebelum refactor #3) — dibersihkan manual.
6. **Checkpoint 7**: `monitoring.pipeline_run_status` (M6.2) ternyata tidak simulation-aware sama sekali — panel/endpoint status titik bisa salah tampilkan run simulasi sebagai status terkini. Diperbaiki dengan query `pipeline_run_log` langsung + filter `trigger_event != 'simulated'`, tidak menyentuh view M6.2 itu sendiri.

Pola yang konsisten di semua 6 temuan: **tidak ada satu pun yang memperbaiki kode milestone lain yang sudah closed** — semua diatasi defensif di titik konsumsi M6.7 sendiri, dengan akar masalah didokumentasikan eksplisit untuk milestone asalnya.

## Known Gaps / Follow-ups

- **Deploy publik `web/` (Vercel) belum selesai** — kode sudah terpush ke `nirwana-monitoring-web`, user memilih deploy manual sendiri (bukan CLI, mengikuti pelajaran insiden M1.7). `milestones/1.7-public-monitoring-web/report.md` akan ditulis begitu URL live dikonfirmasi — ini juga secara efektif menutup blocker M1.7 yang sudah lama tertunda, sebagai side-effect M6.7.
- **Race condition `detect_volume_anomaly.py`** (M6.3, ditemukan Checkpoint 6) — `docs/keputusan-tertunda.md` entri baru, task `task_7da36df0` di-spawn, belum dikerjakan.
- **RENAME-step gap `sync.py`** (M6.6, `task_f2313778`) — masih belum dikerjakan, tidak tersentuh milestone ini.
- **Kanal notifikasi eksternal** — tetap Open, dikonfirmasi ulang eksplisit ke user, sekarang mencakup KEDUA folder Grafana (Fase 1 + Fase 2).
- **Otomasi reapply-view (M5.7/M6.6)** — tetap Open. Diamati LANGSUNG selama verifikasi Checkpoint 7: mayoritas tabel `mart_cleaned` sudah kembali berstatus "kept (orphan)" pasca 1 siklus reverse ETL terjadwal baru — persis diprediksi `report.md` M6.6, bukan temuan baru, tapi bukti nyata `detect_orphan_tables.py` (M6.6) akan segera memicu alert lagi tanpa intervensi manual.
- **Limitation desain (bukan bug)**: korelasi root-cause berbasis hari-kalender bisa salah atribusi kalau 2 kejadian nyata-tapi-tak-terkait kebetulan aktif hari yang sama dan berbagi edge dependency — ditemukan 2x selama implementasi (real M6.6 data, dan antar-skenario `simulate_test.py` sendiri), diterima sebagai proporsional untuk kebutuhan literal KK2, tidak diperbaiki lebih lanjut.

## Handoff Notes

- **Kalau `web/` sudah di-deploy**: konfirmasi URL live, lalu (1) tulis `milestones/1.7-public-monitoring-web/report.md`, (2) update `report.md` ini — ganti status Bagian B/`web` jadi "Completed", cek ulang KK1 (dashboard "dapat diakses" sekarang benar-benar mencakup publik, bukan cuma tim internal).
- **Pemilik infrastruktur monitoring berikutnya**: `monitoring.alerts` sekarang 14 `alert_type` (13 sebelumnya + `pipeline_dependency_gap`). `monitoring.titik_dependency`/`titik_event_today`/`alerts_with_root_cause` adalah sumber tunggal untuk pertanyaan "apa akar masalah hari ini" — jangan bangun mekanisme pengelompokan baru, extend CASE mapping di `titik_event_today` kalau ada `alert_type` baru di masa depan.
- **Kalau menambah `alert_type` baru ke `monitoring.alerts` di kemudian hari**: WAJIB tambah juga baris CASE di `monitoring.titik_event_today` (kalau relevan dengan salah satu 10 titik pipeline) — kalau tidak, alert baru itu otomatis tidak ikut serta di mekanisme root-cause grouping (titik_id NULL, tersaring diam-diam, bukan error).
- **`docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md`** — diupdate lengkap, closure KK2 M6.1 dicatat di bagian "Klasifikasi Prioritas".
