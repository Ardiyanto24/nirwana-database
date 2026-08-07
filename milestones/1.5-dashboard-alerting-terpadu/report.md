# Milestone 1.5: Dashboard dan Alerting Terpadu (Fase 1) — Report

**Status:** Partially Completed
**Date completed:** 2026-08-07

## Kriteria Keberhasilan — Hasil

- [x] **Dashboard dapat diakses tim dan mencerminkan kondisi terkini (bukan data basi).** — Terpenuhi. Dashboard "Nirwana - Data Production Monitoring" aktif di Grafana Cloud (URL instance milik user), 7 panel query langsung ke Supabase Postgres tiap kali dibuka (live query, bukan data ter-cache/ingest) sehingga selalu mencerminkan kondisi terkini. Kesegaran data yang mendasarinya dijamin `GitHub Actions` (jadwal harian, terverifikasi jalan 10m15s tanpa error) yang menjalankan seluruh mekanisme M1.2-1.4.
- [~] **Setiap jenis alert dari Milestone 1.2–1.4 muncul di dashboard dan terkirim ke kanal yang benar saat diuji coba.** — **Terpenuhi sebagian.** Bagian "muncul di dashboard": terpenuhi dan terbukti — 2 Grafana alert rule (baca dari `monitoring.alerts` untuk M1.2+M1.3, `monitoring.schema_drift_events` untuk M1.4) bereaksi benar terhadap data real (rule M1.2+M1.3 `firing` karena temuan nyata `bookings.total_amount`, rule M1.4 `inactive` karena 0 drift pending) dan terhadap uji coba terkontrol (siklus penuh `inactive → firing → inactive` dibuktikan langsung). Bagian "terkirim ke kanal yang benar": **tidak terpenuhi** — kanal notifikasi eksternal (Discord/Slack/Email) sengaja ditunda atas pilihan user, dicatat di `docs/keputusan-tertunda.md`.

## Deliverables

- Repo GitHub publik: https://github.com/Ardiyanto24/nirwana-database (baru dibuat di milestone ini — repo sebelumnya belum pernah dihubungkan ke remote).
- `.github/workflows/monitoring.yml` — jadwal harian (+ `workflow_dispatch` manual) menjalankan 8 script M1.2-1.4 berurutan, kredensial via GitHub Secret.
- Grafana Cloud instance (free tier, permanen setelah trial 14 hari berakhir — diverifikasi via WebFetch ke grafana.com/pricing, bukan diasumsikan).
- `scripts/grafana/` — `grafana_client.py`, `create_datasource.py`, `priority_case_sql.py`, `build_dashboard.py` (7 panel), `create_alerts.py` (2 alert rule), semua idempotent (bisa dijalankan ulang, upsert bukan duplicate).
- Dashboard "Nirwana - Data Production Monitoring" (`uid: nirwana-data-monitoring`) — 7 panel: Alert Aktif, Schema Drift Pending, Volume & Freshness (23 tabel), Ringkasan DQ per tabel, Detail Kegagalan DQ, Proporsi Dirty Data, Anomali Nilai IQR.
- 2 Grafana alert rule (folder "Nirwana Monitoring", rule group `data-production-monitoring`).
- `.env.example` diperbarui (2 key baru: `GRAFANA_URL`, `GRAFANA_SERVICE_ACCOUNT_TOKEN`).
- **Fix pada `scripts/monitoring/views.sql`** — `monitoring.current_status` sekarang mengecualikan `schema_name != '_simulation'` (bug lama dari M1.2, baru ketahuan saat validasi dashboard).
- `milestones/1.5-dashboard-alerting-terpadu/{decisions,logs}.md`.
- `docs/keputusan-tertunda.md` — entri baru "Kanal notifikasi eksternal" (Open).

## Deviations from decisions.md

- **Perbaikan `monitoring.current_status` (M1.2) tidak direncanakan di `decisions.md`** — ditemukan saat validasi panel dashboard (Task 4), bukan bagian breakdown awal. Ditangani segera karena langsung berdampak ke kebenaran data yang ditampilkan dashboard (data simulasi tercampur data production nyata) — konsisten dengan prinsip "temuan saat implementasi dicatat & diperbaiki, bukan disembunyikan" yang sudah jadi pola sejak M1.2/M1.3.
- Query panel "Schema Drift - Menunggu Review" juga diberi filter tambahan `schema_name != '_simulation'` yang tidak eksplisit direncanakan di `decisions.md` — perluasan wajar dari temuan yang sama.
- Tidak ada deviasi lain.

## Known Gaps / Follow-ups

- **Kanal notifikasi eksternal belum ada** — gap paling penting, sudah dicatat eksplisit di `docs/keputusan-tertunda.md`. Sampai ini diselesaikan, Milestone 1.5 tidak bisa dianggap "selesai penuh" terhadap Kriteria Keberhasilan sumbernya sendiri.
- **Repo baru dipublikasikan di milestone ini** — histori commit sebelum ini (Milestone 1.1-1.4) baru pertama kali muncul di GitHub sekarang, bukan berarti dikerjakan hari ini (lihat timestamp commit asli).
- **Dashboard belum diverifikasi visual oleh manusia** — seluruh verifikasi dilakukan lewat API (`POST /api/ds/query`, `GET .../rules`), bukan screenshot/tinjauan visual langsung di browser oleh user. Disarankan user membuka dashboard-nya sendiri untuk konfirmasi tampilan sudah sesuai harapan.
- **Grafana Free tier**: 3 active users/bulan — cukup untuk kebutuhan saat ini, tapi perlu diperhatikan kalau tim bertambah.

## Handoff Notes

- **Untuk siapa pun yang melanjutkan**: begitu kanal notifikasi diputuskan (lihat `docs/keputusan-tertunda.md`), tinggal tambah 1 contact point + notification policy di Grafana (Alerting > Contact points) — tidak perlu mengubah `create_alerts.py` sama sekali, alert rule yang sudah ada otomatis mulai mengirim begitu policy-nya terpasang.
- **URL dashboard**: `<GRAFANA_URL>/d/nirwana-data-monitoring/nirwana-data-production-monitoring` (nilai `GRAFANA_URL` ada di `.env` user).
- **Rerun manual GitHub Actions**: `gh workflow run monitoring.yml --repo Ardiyanto24/nirwana-database` atau lewat tab Actions di GitHub.
- **Peringatan**: jangan hapus schema `monitoring` atau ubah nama tabel di dalamnya tanpa memperbarui `scripts/grafana/build_dashboard.py` dan `create_alerts.py` — keduanya query langsung ke nama tabel/kolom yang sudah tetap.
- Dengan selesainya Milestone 1.5 (dengan catatan gap kanal notifikasi), **seluruh Fase 1** (`docs/03-implementation-plans/01-monitoring-data-production-fase1.md`) sudah tercakup. Fase 2 (warehouse/ELT ke BigQuery) adalah lanjutan berikutnya sesuai "Catatan Serah Terima ke Fase 2" di dokumen sumber.
