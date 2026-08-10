# Milestone 6.1: Inventarisasi Titik Pengamatan dan Baseline Pipeline — Report

**Status:** Completed
**Date completed:** 2026-08-10

## Kriteria Keberhasilan — Hasil

- [x] **Setiap 10 titik pengamatan punya sumber sinyal yang jelas dan bisa dirujuk langsung oleh milestone berikutnya (6.2) tanpa perlu analisis ulang dari nol.** — Terpenuhi. `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` memetakan 10/10 titik §9.1 dengan sumber sinyal konkret (nama tabel `monitoring.*`, nama file workflow, evidence dari `report.md` historis) untuk 8 titik (1,2,4,6,8,9,10, dan 5 dengan catatan fokus M6.3), dan gap eksplisit untuk 2 titik (3,7) yang langsung merujuk prasyarat Milestone 6.3 di `docs/keputusan-tertunda.md` — bukan sekadar "belum ada", tapi jelas siapa yang perlu menutupnya, kenapa, dan apa konsekuensinya kalau tidak ditutup.
- [x] **Dependency antar titik terdokumentasi sehingga saat menyusun alerting nanti, satu kegagalan akar tidak memicu banjir alert yang membingungkan dari titik-titik downstream-nya.** — Terpenuhi. Kolom Dependency tiap titik merujuk mekanisme YAML nyata (`workflow_run` vs buffer waktu cron, dibedakan eksplisit — bukan diasumsikan seragam), fan-out 3-cabang-paralel dari titik 2 (ke titik 3/9, titik 4, titik 6) didokumentasikan sebagai akar blast-radius tertinggi, dan klasifikasi prioritas 3 level (Kritis/Tinggi/Sedang, bukan generik 2 level) memberi Milestone 6.7 dasar konkret untuk desain dedup alert.

## Deliverables

- `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` — deliverable utama: peta 10 titik + klasifikasi prioritas + catatan titik 11 out-of-scope.
- `docs/keputusan-tertunda.md` — 2 entri baru: dependency gate titik 1→2 tidak ditegakkan; hasil DQ gate `promote.py` (titik 3/7) tidak queryable (prasyarat Milestone 6.3, ditandai wajib direvisit di awal breakdown-nya).
- `milestones/6.1-inventarisasi-titik-pengamatan/decisions.md` — kontrak, metode eksplorasi 7 layer, 7 keputusan teknis dengan alasan & alternatif ditolak.
- `milestones/6.1-inventarisasi-titik-pengamatan/logs.md` — jurnal 7 sesi eksplorasi layer + 4 checkpoint penulisan.

## Deviations from decisions.md

Tidak ada. `decisions.md` ditulis setelah seluruh eksplorasi dan diskusi keputusan dengan user selesai (bukan sebelum, seperti pola default milestone lain) — jadi isinya sudah mencerminkan persis apa yang dieksekusi, termasuk 1 penyimpangan dari permintaan literal user yang sudah dicatat eksplisit sebagai Keputusan #5 (lokasi dokumen jadi folder `docs/10-monitoring-warehouse-serving/`, bukan file tunggal `docs/10-monitoring-warehouse-serving.md` seperti awalnya diketik user) — dikomunikasikan ke user, bukan diselipkan diam-diam.

## Known Gaps / Follow-ups

- **2 temuan risiko lintas-titik tetap Open di `docs/keputusan-tertunda.md`** — tidak diperbaiki di M6.1 (di luar wewenang milestone observasional ini). Temuan #2 (DQ gate tidak queryable) **wajib direvisit di awal breakdown Milestone 6.3**, bukan diasumsikan "sudah tersedia" dari bunyi literal dokumen sumber M6.3.
- **Titik 11 (konsumsi Data Analyst/AI Chatbot) out-of-scope** punya gap sendiri yang dicatat tapi tidak ditindaklanjuti di M6.1: `chatbot_query_log` tidak punya kolom latency (perlu join `pg_stat_statements`, catatan untuk M6.5), dan Data Analyst API (M3.4) tidak punya audit log sama sekali (asimetri dengan AI Chatbot).
- **Metode verifikasi milestone ini murni berbasis dokumen-review + 1 kali `grep` live** (konfirmasi `renew_expiration.py` terjadwal untuk `mart_aggregated`), bukan query langsung ke `monitoring.*`/trigger workflow live seperti pola verifikasi milestone lain di project ini. Ini sesuai kontrak M6.1 sendiri (memetakan infrastruktur yang **sudah ada dan sudah diverifikasi** oleh 32 milestone sebelumnya, bukan membangun/menguji ulang) — tapi berarti sebagian klaim "sinyal tersedia" di peta ini mewarisi kepercayaan pada evidence historis (mis. "70+ baris log 0 mismatch" dari M2.4/M5.5), bukan hasil pengecekan independen ulang di sesi ini. Kalau Milestone 6.2 dst menemukan drift dari klaim ini, itu bukan berarti M6.1 salah — kemungkinan besar kondisi berubah sejak laporan asal ditulis.
- **`fact_revenue_pace_booking_snapshot`** (tension append-only vs Sandbox mode, carry-over M5.2-5.3) tidak masuk peta 10 titik karena bukan bagian §9.1 — tetap relevan sebagai konteks kalau M6.3/6.4 menyentuh freshness `mart_aggregated` secara menyeluruh.

## Handoff Notes

- **Milestone 6.2 (Log Proses Pipeline):** pakai peta ini langsung, tidak perlu re-eksplorasi. Kandidat kuat pertama: bangun kemampuan menyilangkan status titik 1 (hasil `extract-production.yml`) dengan waktu mulai titik 2 (`transform-mart-cleaned.yml`) — mendeteksi (bukan memperbaiki) gap dependency-tidak-digate dari `docs/keputusan-tertunda.md`.
- **Milestone 6.3 (Kesalahan dan Anomali):** **wajib baca `docs/keputusan-tertunda.md` entri DQ gate sebelum breakdown dimulai** — Output #1-nya ("konsolidasi hasil DQ gate") butuh dibangun dari nol dulu (instrumentasi `promote.py` menulis ke `monitoring.*`), bukan cuma dikonsolidasi dari yang sudah ada. Freshness `ml_output` (titik 5) juga eksplisit jadi fokus milestone ini per dokumen sumber.
- **Milestone 6.4 (Drift ML):** titik 5 (sensor `ml_output`) punya catatan penting — timeout realistis (~60 menit) belum pernah diuji habis, cuma versi dipersingkat di CI. Skema `ml_output`/`fact_ml_occupancy_forecast_property_room_type` sendiri masih PROVISIONAL (M5.4), belum kontrak final dari tim ML Engineer.
- **Milestone 6.5 (Performa Query Chatbot):** `docs/09-serving-ai-chatbot/audit-log-chatbot.md` bagian "Cara Query untuk M6.5" sudah punya 2 query contoh siap pakai. Ingat `chatbot_query_log` **tidak punya kolom latency** — wajib join `pg_stat_statements` terpisah. Kemungkinan perlu kredensial baca baru (`chatbot_audit_reader` atau setara), karena `chatbot_audit_writer` sengaja INSERT-only.
- **Milestone 6.6 (Reverse ETL dan Serving Layer):** titik 8/9/10 sinyalnya sama (`reverse_etl_sync_log` + `reindex_analyze.py`). Dua pola operasional penting dari Layer 6 (M3.3) perlu diantisipasi supaya tidak disalahartikan sebagai regresi: query pertama pasca-swap/reindex bisa lambat karena cache dingin (bukan kegagalan), dan WARNING "expected" M5.7 (`analyst_views` terikat OID) akan muncul di hampir tiap run terjadwal — perlu dibedakan dari alert kegagalan sungguhan.
- **Milestone 6.7 (Dashboard Terpadu):** pakai klasifikasi prioritas 3 level di peta ini langsung sebagai dasar desain dedup alert — titik 2 adalah satu-satunya titik Kritis (blast-radius tertinggi + tidak digate dari titik 1), titik 4/5 terbukti isolated-by-design (fault-injection nyata M5.4) sehingga kegagalannya tidak seharusnya memicu alert seberat titik lain.
