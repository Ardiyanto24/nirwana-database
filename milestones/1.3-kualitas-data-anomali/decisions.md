# Milestone 1.3: Monitoring Kualitas Data dan Anomali Nilai

**Source:** docs/03-implementation-plans/01-monitoring-data-production-fase1.md (baris 77-96)
**Status:** Done
**Date started:** 2026-08-07

## Contract (from source doc)

- **Lingkup:** Membangun (1) validasi kualitas data (not_null, unique, relationships, accepted_values, business rule custom) untuk kolom kritis di tabel prioritas, dan (2) deteksi anomali nilai (outlier ekstrem, lonjakan proporsi NULL, nilai negatif tidak wajar) dengan baseline rolling. Tantangan utama: **tidak** mengalarm dirty data yang memang sengaja ada (lihat `docs/04-monitoring/baseline-inventaris-produksi.md`).
- **Output:** Rangkaian pengujian kualitas data; mekanisme deteksi anomali nilai; dokumentasi eksplisit pola dirty data yang dikecualikan.
- **Kriteria keberhasilan:** Pengujian terjadwal & hasil bisa ditelusuri; anomali buatan di luar pola dikenal berhasil terdeteksi; proporsi dirty data yang sudah diketahui TIDAK memicu false alert pada kondisi normal.
- **Bisa paralel dengan Milestone 1.2** — keduanya butuh hasil Milestone 1.1, tidak saling bergantung secara teknis.

## Task Breakdown

- [x] Task 1: Install & konfigurasi Great Expectations, verifikasi koneksi ke Supabase — Acceptance: `gx` bisa connect & baca 1 tabel uji — Verify: skrip test koneksi jalan tanpa error
- [x] Task 2: Perluas schema `monitoring` (tabel hasil DQ test, snapshot proporsi dirty, snapshot anomali nilai) — Acceptance: tabel baru terbentuk, `monitoring.alerts.alert_type` menerima 3 jenis baru — Verify: `information_schema` menunjukkan tabel ada
- [x] Task 3: Bangun expectation suite untuk 23 tabel dari katalog M1.1 (27 business rule) + not_null/unique/accepted_values dasar — Acceptance: tiap tabel prioritas Tinggi/Sedang/Rendah punya suite, kolom kritis tercakup — Verify: suite bisa di-load ulang tanpa error
- [ ] Task 4: Formalisasi baseline "proporsi kotor yang dikenal" per kolom (dari data M1.1) jadi rolling tolerance band — Acceptance: tiap kolom dirty-by-design punya baseline eksplisit — Verify: lihat "Technical Decisions" di bawah
- [x] Task 5: Bangun checkpoint runner GE — jalankan seluruh suite, tulis hasil ke `monitoring.dq_test_results` — Acceptance: hasil per test per tabel per waktu bisa di-query — Verify: 1 run penuh sukses, hasil match jumlah expectation (`build_and_run.py` menggabungkan Task 3+5: 173/174 expectation lolos di 23 tabel setelah 3 bug ditemukan & diperbaiki, lihat `logs.md`)
- [ ] Task 6: Bangun deteksi anomali nilai (IQR) untuk kolom numerik bisnis kritis — Acceptance: baseline rolling per kolom, deteksi outlier di luar `median ± k×IQR` — Verify: lihat "Technical Decisions"
- [x] Task 7: Perluas logic alert (`dq_test_failure`, `dirty_proportion_drift`, `value_anomaly` → `monitoring.alerts`) — Acceptance: 3 jenis alert baru terhubung ke sumber masing-masing — Verify: manual trace (1 alert real: `bookings.total_amount_matches_rate_x_nights`)
- [x] Task 8: Uji coba terkontrol — anomali buatan di luar pola dikenal (harus terdeteksi) + proporsi dirty normal disimulasikan (harus TIDAK memicu alert) — Acceptance: kedua jenis skenario sesuai ekspektasi (Kriteria Keberhasilan #2 & #3) — Verify: `_simulation` schema, terisolasi dari data production nyata (7/7 skenario PASS)
- [x] Task 9: Verifikasi Kriteria Keberhasilan #1 (hasil DQ test terjadwal & bisa ditelusuri) — Acceptance: query tunggal menunjukkan histori lolos/gagal per tabel per waktu — Verify: query dijalankan, 23/23 tabel muncul
- [x] Task 10: Tulis `logs.md` (progresif) & `report.md`

**Checkpoint** setelah Task 4: baseline dirty-data adalah fondasi seluruh milestone — dikonfirmasi lewat keputusan di bawah sebelum Task 5-8 dibangun di atasnya.

## Technical Decisions

### Decision: Great Expectations untuk pengujian kualitas data (bukan script custom, bukan dbt tests)

- **Context:** Dokumen sumber tidak menentukan tool. Repo ini belum punya project dbt maupun GE sama sekali.
- **Decision:** Great Expectations (`great_expectations[postgresql]`, versi 1.19.x — cocok dengan Python 3.13, terverifikasi via `pip install --dry-run`), dipasang langsung di atas koneksi Supabase yang sudah ada (Fluent Postgres Datasource, SQLAlchemy). Bukan project dbt penuh (yang butuh scaffolding `models/`/`sources.yml` untuk 23 tabel dulu sebelum satu test pun bisa ditulis — pekerjaan setup besar yang tidak dibutuhkan Fase 1 yang masih murni di sisi production Postgres).
- **Alternatives considered:** (a) Script Python+SQL custom (pola sama seperti Milestone 1.2); (b) dbt tests (dbt-core + dbt-postgres).
- **Rejected because:** User memilih GE secara eksplisit. (a) valid secara teknis tapi kalah dari GE dalam hal expectation types siap pakai (not_null/unique/accepted_values langsung tersedia sebagai built-in expectation, tidak perlu ditulis ulang) dan Data Docs (laporan hasil test otomatis). (b) setup dbt project penuh adalah pekerjaan besar yang lebih relevan saat Fase 2 (BigQuery, transformasi) daripada Fase 1 (validasi production Postgres).

### Decision: Pembagian scope GE vs script custom — GE untuk rule tetap, script custom untuk baseline rolling

- **Context:** GE dirancang untuk memvalidasi ekspektasi yang **relatif tetap** (nilai harus dalam rentang X, kolom harus unik, dst) — bukan untuk menghitung baseline statistik yang **berubah setiap hari** berdasarkan histori (rolling mean/stddev/IQR). Memaksakan baseline rolling ke dalam GE berarti menghitung ulang bound-nya di Python tiap hari lalu menyuntikkannya ke parameter expectation — lebih rumit daripada menyimpan & menghitungnya langsung di tabel `monitoring.*` (pola yang sudah terbukti bekerja di Milestone 1.2).
- **Decision:** Pembagian tanggung jawab eksplisit:
  - **Great Expectations** menjalankan Output #1 dokumen sumber — "rangkaian pengujian kualitas data" (not_null, unique, relationships, accepted_values, business rule dengan aturan tetap dari katalog M1.1). Ini murni soal **kebenaran struktural** nilai pada satu titik waktu.
  - **Script Python+SQL custom** (pola sama seperti `scripts/monitoring/` Milestone 1.2, tabel baru di schema `monitoring`) menjalankan Output #2 — "deteksi anomali nilai dengan baseline rolling" dan formalisasi "proporsi dirty data yang dikecualikan". Ini soal **penyimpangan dari histori**, yang butuh state yang terus di-update, bukan aturan tetap.
  - Kedua jalur menulis ke tabel monitoring yang sama (`monitoring.alerts`) sehingga tetap satu pintu keluar untuk Milestone 1.5 (dashboard).
- **Alternatives considered:** Memaksakan semuanya (termasuk baseline rolling) ke dalam GE expectation suite dengan parameter dihitung ulang tiap run.
- **Rejected because:** menambah kerumitan (harus menyuntikkan angka hasil hitungan Python ke dalam config GE tiap run) tanpa manfaat tambahan dibanding menyimpan baseline langsung di tabel Postgres yang sudah bisa di-query — dan pola ini sudah terbukti bekerja baik di Milestone 1.2.

### Decision: Strategi exclusion dirty data — tolerance band pada proporsi, bukan hard whitelist

- **Context:** Ini tantangan utama milestone (disebut eksplisit di dokumen sumber). `docs/04-monitoring/baseline-inventaris-produksi.md` sudah mendokumentasikan proporsi dirty yang diharapkan per kolom (mis. `guests.email` ~4% null, `fnb_transactions.guest_id` ~31% null "bermakna").
- **Decision:** Kolom dirty-by-design **tetap dipantau**, tapi ukurannya adalah **proporsi kotornya** (dihitung harian, snapshot ke `monitoring.dirty_proportion_snapshot`), bukan keberadaan kotornya. GE **tidak** menjalankan `expect_column_values_to_not_be_null` pada kolom-kolom ini (akan selalu gagal secara sah) — sebagai gantinya, not_null test GE hanya berlaku untuk kolom yang **benar-benar tidak boleh kosong** (lihat pemetaan di Task 3). Rolling baseline (mean ± k×stddev dari histori proporsi harian, pola sama seperti volume di M1.2) menentukan apakah proporsi hari ini masih dalam rentang wajar. Baseline awal (sebelum histori 3+ titik terkumpul) memakai angka yang sudah diverifikasi live di Milestone 1.1 sebagai titik referensi tunggal, ditandai `bootstrap` — bukan dianggap band penuh sampai histori riil terkumpul.
- **Alternatives considered:** Hard whitelist (skip total kolom dirty dari semua pengujian & pemantauan).
- **Rejected because:** buta terhadap regresi nyata (mis. null rate email tiba-tiba melonjak dari ~4% ke 40% karena form pendaftaran rusak) — persis skenario yang harus dibedakan dari dirty data yang sah, sesuai tantangan yang disebutkan dokumen sumber.

### Decision: Cakupan tabel — seluruh 23 tabel

- **Context:** Katalog business rule M1.1 paling lengkap untuk 19 tabel prioritas Tinggi/Sedang; 4 tabel prioritas Rendah (`fnb_outlets`, `fnb_inventory`, `venues`, `employee_performance`) minim/tanpa business rule spesifik di katalog.
- **Decision:** DQ test & anomaly detection diterapkan ke seluruh 23 tabel. Untuk 4 tabel prioritas Rendah yang katalog M1.1-nya minim, suite GE tetap dibangun dengan cakupan dasar (not_null kolom kritis + accepted_values enum, dari `Metadata.md`) — tidak menunggu katalog business rule custom yang lebih dalam.
- **Alternatives considered:** Hanya prioritas Tinggi (7 tabel); Prioritas Tinggi+Sedang (19 tabel).
- **Rejected because:** User memilih cakupan penuh. Dicatat sebagai konsekuensi: 4 tabel prioritas Rendah akan punya suite yang lebih tipis (basic checks) dibanding 19 tabel lain yang sudah punya katalog rule spesifik dari M1.1 — bukan kelalaian, tapi cerminan jujur dari kedalaman input yang tersedia.

### Decision: Deteksi anomali nilai — IQR (median ± k×IQR), bukan z-score

- **Context:** Kolom nilai bisnis (revenue, cost, salary) punya distribusi skewed secara wajar (mis. `room_rate` Villa vs Standard, `payroll.net_salary` staff vs manager) — berbeda dari volume harian (M1.2) yang lebih mendekati distribusi normal per hari-dalam-minggu.
- **Decision:** Baseline rolling untuk kolom nilai bisnis kritis dihitung sebagai `median ± k×IQR` (k default 1.5, standar Tukey's fence untuk outlier) dari histori nilai per kolom, bukan `mean ± k×stddev` seperti volume M1.2. Ini keputusan yang **sengaja berbeda metode** dari M1.2, bukan inkonsistensi — didokumentasikan eksplisit di sini supaya tidak disalahpahami sebagai bug saat dibandingkan dengan `detect_alerts.py` M1.2.
- **Alternatives considered:** Z-score (mean ± k×stddev), konsisten dengan M1.2.
- **Rejected because:** akan salah menandai nilai tinggi yang sah (Villa room_rate, gaji manager) sebagai anomali karena distribusi nilai transaksi individual tidak simetris seperti hitungan volume harian.

## Open Questions Resolved with User

- Q: Tool untuk DQ test & anomaly? → A: Great Expectations (bukan dbt tests, bukan script custom murni).
- Q: Strategi exclusion dirty data? → A: Tolerance band pada proporsi (rolling baseline), bukan hard whitelist.
- Q: Cakupan tabel? → A: Seluruh 23 tabel.
- Q: Metode deteksi outlier nilai? → A: IQR (median ± k×IQR), beda metode dari volume M1.2 secara sengaja.
