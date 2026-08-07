# Keputusan Tertunda (Project-Wide Backlog)

> Dokumen ini mencatat keputusan yang **sengaja ditunda** (bukan diputuskan) di milestone manapun — biasanya karena mengeksekusinya sekarang berarti mengubah infrastruktur/konfigurasi bersama yang layak dapat persetujuan eksplisit tersendiri. Dicek di awal tiap milestone baru untuk melihat apakah ada yang sudah waktunya diambil lagi. Lihat `milestone-execution` (skills) untuk konvensi penggunaan.

---

### Aktivasi `pg_cron` untuk penjadwalan otomatis monitoring (deferred dari Milestone 1.2)

- **Date:** 2026-08-07
- **What was deferred:** Mengaktifkan ekstensi `pg_cron` di Supabase project (tersedia, versi 1.6.4, belum di-`CREATE EXTENSION`) dan menjadwalkan job harian untuk snapshot volume/freshness Milestone 1.2 agar berjalan otomatis tanpa trigger manual. **Update Milestone 1.3 (2026-08-07):** cakupan bertambah — DQ test runner (`scripts/dq/build_and_run.py`), snapshot proporsi dirty (`snapshot_dirty_proportion.py`), snapshot anomali nilai (`snapshot_value_anomaly.py`), dan alert gabungan (`dq_alerts.py`) sama-sama masih dijalankan on-demand/manual, bukan terjadwal — keputusan penundaan yang sama berlaku, tidak perlu entri terpisah.
**Update Milestone 1.4 (2026-08-07):** cakupan bertambah lagi — `scripts/schema_drift/snapshot_and_diff.py` juga dijalankan on-demand/manual. Catatan tambahan: untuk Milestone 1.4 secara spesifik, keputusan metode deteksi (`decisions.md` milestone ini) juga sudah menetapkan snapshot-diff (bukan Postgres Event Trigger) sebagai pilihan permanen — jadi bagian yang benar-benar tertunda di sini murni soal *penjadwalan* eksekusinya, bukan soal metode deteksi itu sendiri.
- **Why deferred:** Mengaktifkan ekstensi & menjadwalkan job adalah perubahan konfigurasi project Supabase (bukan sekadar tulis-baca data biasa) — user memilih agar Milestone 1.2 fokus dulu membangun & membuktikan mekanismenya (schema + script + uji coba terkontrol) sebelum mengambil keputusan terpisah soal cara kerjanya berjalan otomatis tiap hari.
- **Revisit when:** Setelah mekanisme Milestone 1.2 terbukti benar lewat uji coba terkontrol (Kriteria Keberhasilan #2), saat project siap membahas strategi otomasi/orkestrasi secara keseluruhan (kemungkinan relevan juga untuk Fase 2 — lihat "Catatan Serah Terima" di `01-monitoring-data-production-fase1.md`).
- **Status:** Open
