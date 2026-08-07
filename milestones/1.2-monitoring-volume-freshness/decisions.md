# Milestone 1.2: Monitoring Volume dan Freshness Data Masuk

**Source:** docs/03-implementation-plans/01-monitoring-data-production-fase1.md (baris 58-73)
**Status:** Done
**Date started:** 2026-08-07

## Contract (from source doc)

- **Lingkup:** Membangun kemampuan menjawab "data apa yang masuk, berapa banyak, apakah tepat waktu" untuk seluruh tabel production sesuai prioritas Milestone 1.1. Termasuk baseline historis rolling (bukan angka statis) agar volume "wajar" mengikuti pola bisnis riil (musiman, weekday/weekend).
- **Output:** (1) Mekanisme pemantauan volume harian per tabel vs baseline rolling. (2) Mekanisme pemantauan freshness (kapan data terakhir masuk/berubah). (3) Alert untuk penyimpangan volume signifikan atau keterlambatan data.
- **Kriteria keberhasilan:** Untuk tabel prioritas tinggi, tim bisa jawab "berapa baris masuk hari ini vs biasanya" & "kapan data terakhir update" tanpa query manual; simulasi penurunan/lonjakan volume buatan berhasil memicu alert sesuai ekspektasi.
- **Independen** dari Milestone 1.3 & 1.4 — bisa berjalan lebih dulu.

## Task Breakdown

- [x] Task 1: Desain schema `monitoring` (snapshot volume, snapshot freshness, alert) — Acceptance: 3 tabel terbentuk dengan kolom yang cukup untuk rolling baseline per-weekday — Verify: `information_schema` menunjukkan schema & tabel ada
- [x] Task 2: Petakan kolom sinyal freshness per 23 tabel — Acceptance: setiap tabel punya keputusan eksplisit (kolom mana / tidak dimonitor freshness & kenapa) — Verify: tabel di bawah ("Pemetaan Kolom Freshness")
- [x] Task 3: Formalisasi metode baseline rolling per-hari-dalam-minggu — Acceptance: algoritma terdefinisi (window, band, cara tangani data historis <8 minggu) — Verify: bagian "Technical Decisions" di bawah
- [x] Task 4: Bangun script snapshot volume harian (`COUNT(*)` per tabel → insert `monitoring.volume_daily_snapshot`, hitung band baseline dari histori) — Acceptance: berjalan untuk 23 tabel tanpa error — Verify: baris baru muncul di tabel snapshot, band dihitung benar untuk kasus histori kosong
- [x] Task 5: Bangun script freshness check (`MAX(kolom sinyal)` per tabel yang punya sinyal → insert `monitoring.freshness_snapshot`) — Acceptance: berjalan untuk semua tabel yang punya kolom sinyal (bukan 23, lihat Task 2) — Verify: lag vs `now()` terhitung benar
- [x] Task 6: Bangun logic alert (deteksi penyimpangan volume di luar band, atau freshness lag melewati threshold → insert `monitoring.alerts`) — Acceptance: alert tercatat dengan `severity`, `metric`, `detail` — Verify: manual trace satu kasus true-positive & satu kasus true-negative
- [x] Task 7: Uji coba terkontrol — simulasi penurunan/lonjakan volume buatan & keterlambatan buatan — Acceptance: kedua skenario memicu alert sesuai ekspektasi (Kriteria Keberhasilan #2) — Verify: query `monitoring.alerts` menunjukkan hasil yang benar, dan skenario normal (tanpa anomali) TIDAK memicu alert palsu
- [x] Task 8: Verifikasi Kriteria Keberhasilan #1 — Acceptance: satu query tunggal (bukan analisis manual) menjawab "volume hari ini vs biasa" & "kapan data terakhir update" untuk 7 tabel prioritas Tinggi — Verify: query dijalankan & hasilnya masuk akal
- [x] Task 9: Tulis `logs.md` (progresif) & `report.md`

**Checkpoint** setelah Task 3: rubrik/metode sudah dikonfirmasi user sebelum breakdown ini ditulis (lihat "Open Questions Resolved with User") — checkpoint terpenuhi di muka, bukan jeda terpisah.

## Technical Decisions

### Decision: Lokasi penyimpanan monitoring — schema baru `monitoring` di Supabase

- **Context:** Snapshot volume/freshness harian dan catatan alert butuh tempat penyimpanan persisten yang bisa di-query lintas waktu.
- **Decision:** Schema baru `monitoring` di Supabase project yang sama, berisi 3 tabel:
  - `monitoring.volume_daily_snapshot(id, schema_name, table_name, snapshot_date, row_count, day_of_week, created_at)`
  - `monitoring.freshness_snapshot(id, schema_name, table_name, snapshot_date, freshness_column, latest_value, lag_hours, created_at)`
  - `monitoring.alerts(id, schema_name, table_name, alert_type, severity, detail, triggered_at, snapshot_date)`
- **Alternatives considered:** (a) Store terpisah (SQLite/JSON di repo).
- **Rejected because:** (a) tidak bisa di-`JOIN` langsung dengan tabel production untuk validasi silang, butuh mekanisme sync sendiri, dan menyimpang dari scope repo ini ("database engineering") ke arah aplikasi terpisah yang tidak perlu.

### Decision: Definisi freshness — kolom event bisnis terdekat, bukan kolom audit baru

- **Context:** 23 tabel production tidak punya kolom `created_at`/`loaded_at`. Menambah kolom audit ke production mengubah kontrak data yang sudah didokumentasikan di `Metadata.md`/`DataSchema.md` dan berisiko ke sistem lain yang bergantung pada schema tersebut.
- **Decision:** Freshness = `MAX(kolom datetime/date bisnis paling relevan)` per tabel, **hanya untuk tabel yang punya kolom seperti itu**. Tabel master/referensi statis tanpa kolom datetime (`properties`, `role_permissions`, `fnb_outlets`, `recipe_bom`, `rooms`, `venues`) **tidak** punya sinyal freshness yang valid — dipantau lewat volume saja (perubahan row count pada tabel kecil-stabil itu sendiri adalah sinyal yang berarti). Caveat didokumentasikan eksplisit: metrik ini mengukur "seberapa baru event bisnisnya", bukan "kapan baris itu masuk ke database" — tidak bisa mendeteksi batch load yang telat tapi event-nya sendiri lama.
- **Alternatives considered:** Tambah kolom audit (`_loaded_at`) ke semua tabel production.
- **Rejected because:** mengubah schema production yang dipakai sistem lain adalah perubahan berisiko tinggi untuk milestone monitoring yang seharusnya hanya *mengamati*, bukan mengubah apa yang diamati.

**Pemetaan Kolom Freshness (Task 2)**:

| Schema.Tabel | Kolom sinyal freshness | Catatan |
|---|---|---|
| `corporate_master.properties` | — | Master statis, tanpa kolom datetime → volume-only |
| `corporate_master.employees` | `hire_date` | Proxy tidak sempurna (tidak reflect update `status`/`access_level`), tapi satu-satunya kolom datetime tersedia. **Catatan implementasi**: kolom ini bertipe `text` (bukan `date`) karena ~2% baris sengaja berformat `DD/MM/YYYY` (dirty data, sesuai `Metadata.md`) — parsing dua format dilakukan di aplikasi (Python), bukan `MAX()` SQL langsung, supaya baris kotor tidak salah diurutkan atau bikin query gagal |
| `corporate_master.guests` | `registered_date` | MAX = kapan pelanggan baru terakhir terdaftar |
| `corporate_master.role_permissions` | — | Tanpa kolom datetime sama sekali → volume-only (77 baris harus sangat stabil, perubahan row count = sinyal kuat) |
| `reservation_revenue.bookings` | `booking_date` | |
| `reservation_revenue.daily_occupancy` | `date` | |
| `reservation_revenue.pricing_history` | `date` | |
| `fnb_operations.fnb_outlets` | — | Master statis → volume-only |
| `fnb_operations.recipe_bom` | — | Master statis → volume-only |
| `fnb_operations.ingredient_price_history` | `date` | |
| `fnb_operations.fnb_transactions` | `transaction_datetime` | Resolusi jam — sinyal freshness terbaik di seluruh database |
| `fnb_operations.fnb_waste_log` | `date` | |
| `fnb_operations.fnb_inventory` | — | Snapshot "kondisi saat ini" by design, tanpa kolom datetime → volume-only (row count harus tetap ~457, perubahan berarti perlu dicek) |
| `facility_maintenance.rooms` | — | Master statis (status berubah tapi tanpa timestamp) → volume-only |
| `facility_maintenance.housekeeping_log` | `date` | **Dikoreksi saat implementasi**: `cleaning_start_time` ternyata bertipe `time without time zone` (bukan `timestamp` seperti tersirat di `Metadata.md`) — tidak punya komponen tanggal, tidak bisa dipakai untuk freshness. Pakai kolom `date` (tipe `date`, terverifikasi) sebagai gantinya. Lihat `logs.md`. |
| `facility_maintenance.maintenance_tickets` | `reported_date` | |
| `spa_event.venues` | — | Master statis → volume-only |
| `spa_event.spa_bookings` | `booking_date` | |
| `spa_event.event_bookings` | — | **Gap diketahui**: hanya ada `event_date` (tanggal acara, bisa jauh di masa depan — booking event lazim dibuat berbulan-bulan sebelumnya), bukan tanggal booking dibuat. Memakai `event_date` sebagai sinyal freshness akan salah (tanggal masa depan akan selalu terlihat "paling baru"). Tidak ada kolom pengganti yang valid → volume-only, dicatat sebagai keterbatasan nyata (lihat Known Gaps di `report.md`) |
| `hr_finance.staff_shifts` | `date` | |
| `hr_finance.employee_performance` | `review_period` | Resolusi rendah (semesteran, format `YYYY-S1`/`YYYY-S2`, bukan tipe date) — cukup untuk tabel prioritas Rendah |
| `hr_finance.payroll` | `period` | Resolusi bulanan (`YYYY-MM`) — sesuai kadence payroll |
| `hr_finance.financial_summary` | `period` | Resolusi bulanan |

### Decision: Metode baseline rolling — per-hari-dalam-minggu, mean ± stddev

- **Context:** `DataSchema.md` mendokumentasikan pola musiman (Desember 82,7% vs Februari 59,1% okupansi) dan weekend-effect (Jumat-Sabtu +18% di Bali). Baseline flat N-hari akan salah alarm di minggu low-season atau di hari-hari weekend yang secara wajar lebih ramai/sepi.
- **Decision:** Untuk tiap tabel, baseline "wajar" hari ini = rata-rata ± standar deviasi dari row count di **hari-yang-sama-dalam-minggu** pada N minggu (default N=8) sebelumnya, diambil dari `monitoring.volume_daily_snapshot`. Band normal = `mean ± 2×stddev`. Di luar band → kandidat alert. Untuk tabel yang histori snapshot-nya belum cukup (<3 titik data historis pada hari-yang-sama), tidak menghasilkan alert (butuh histori minimum agar band bermakna secara statistik) — dicatat eksplisit di log, bukan silently pass.
- **Alternatives considered:** Rolling N-hari flat (tanpa membedakan hari-dalam-minggu).
- **Rejected because:** akan salah membaca weekend-effect & musiman yang sudah terbukti ada di data sebagai "anomali", padahal itu pola normal yang berulang.

### Decision: Cakupan Milestone 1.2 — mekanisme teruji, penjadwalan otomatis ditunda

- **Context:** `pg_cron` tersedia di Supabase project ini (v1.6.4) tapi belum diaktifkan. Mengaktifkannya = mengubah konfigurasi project, bukan sekadar tulis-baca data.
- **Decision:** Milestone 1.2 membangun mekanisme (schema + script Task 4-6) dan membuktikannya lewat uji coba terkontrol (Task 7) — bisa dijalankan on-demand. Menjadwalkannya berjalan otomatis harian (via `pg_cron` atau orkestrator lain) **ditunda**, dicatat di `docs/keputusan-tertunda.md`.
- **Alternatives considered:** Sekalian aktifkan `pg_cron` & jadwalkan job harian di milestone ini.
- **Rejected because:** mengaktifkan ekstensi & menjadwalkan job Supabase adalah perubahan konfigurasi project yang punya dampak di luar scope Milestone 1.2 — layak jadi keputusan terpisah setelah mekanismenya terbukti benar dulu.

### Decision: Threshold freshness per kelas kadensi, dan uji coba terkontrol pakai data snapshot buatan (bukan live production)

- **Context:** Data production di Supabase adalah dataset sintetis dengan rentang waktu tetap (berhenti di 2026-07-01), bukan aliran live — lihat `logs.md`. Terhadap `now()` server, SEMUA tabel berkolom tanggal akan selalu terlihat "telat" (~37 hari dan terus bertambah), karena dataset memang tidak diperbarui. Jika threshold freshness dikalibrasi ke `now()` wall-clock secara naif, seluruh tabel akan selalu alert — bukan sinyal yang berguna, dan uji coba terkontrol (Task 7) tidak bisa membedakan skenario normal vs anomali kalau semuanya sama-sama "telat".
- **Decision:** Dua bagian:
  1. **Threshold produksi** (untuk dipakai kalau/ketika data benar-benar live): threshold lag disesuaikan kadensi alami tiap tabel, bukan angka tunggal — kelas harian (`fnb_transactions`, `bookings`, `staff_shifts`, dst) pakai ambang jam (mis. warning >48 jam, critical >96 jam); kelas bulanan (`payroll`, `financial_summary`) pakai ambang hari (mis. warning >45 hari); kelas semesteran (`employee_performance`) pakai ambang lebih longgar lagi. Ini yang diimplementasikan di logic alert Task 6.
  2. **Uji coba terkontrol (Task 7)** dijalankan terhadap **snapshot buatan** yang disisipkan ke `monitoring.volume_daily_snapshot`/`monitoring.freshness_snapshot` (merepresentasikan histori rolling hipotetis: baseline normal 8 minggu + satu hari anomali), bukan terhadap query live ke tabel production. Ini memisahkan "apakah logic alert bekerja benar" (yang diminta Kriteria Keberhasilan #2) dari "apakah data production saat ini fresh" (temuan terpisah, jujur dilaporkan sebagai delay nyata karena sifat dataset, bukan bug mekanisme).
- **Alternatives considered:** Kalibrasi threshold ke `now()` wall-clock apa adanya tanpa penyesuaian kadensi, dan uji coba langsung ke data production live.
- **Rejected because:** akan menghasilkan alert palsu terus-menerus di semua tabel (tidak actionable), dan uji coba tidak bisa membuktikan mekanisme bekerja kalau kondisi "normal" pun sudah selalu terlihat sebagai "anomali".

## Open Questions Resolved with User

- Q: Simpan snapshot/alert di mana? → A: Schema baru `monitoring` di Supabase.
- Q: Freshness didefinisikan bagaimana tanpa kolom audit? → A: Kolom event bisnis terdekat per tabel, dengan caveat didokumentasikan.
- Q: Metode baseline volume wajar? → A: Rolling per-hari-dalam-minggu, mean ± stddev.
- Q: Sampai level apa Milestone 1.2 dibangun? → A: Mekanisme + skrip teruji; penjadwalan otomatis (`pg_cron`) ditunda ke `docs/keputusan-tertunda.md`.
