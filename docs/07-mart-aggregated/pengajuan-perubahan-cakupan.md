# Pengajuan Perubahan Cakupan `mart_aggregated` (Backlog)

> Dokumen ini mencatat **setiap pengajuan** perubahan/penambahan agregasi ke `mart_aggregated` dari tim konsumen (Data Analyst, AI Chatbot), mengikuti alur di `mekanisme-pengajuan-perubahan-cakupan.md`. Setiap pengajuan tetap dicatat permanen di sini apa pun hasilnya (disetujui/ditolak/ditunda) — bukan dihapus begitu selesai diproses. Pola sama `docs/keputusan-tertunda.md`.

---

### Kolom `property_id` hilang di `dim_employee`

- **Tanggal:** 2026-08-09
- **Pengaju:** Data Analyst Serving (Milestone 3.2, `04-serving-data-analyst.md`) — *bukan simulasi*: ditemukan langsung saat implementasi nyata (verifikasi `information_schema.columns` terhadap `mart_aggregated` sungguhan di serving PostgreSQL), berbeda dari pengajuan watchlist HR di atas yang disimulasikan ala persona.
- **Kebutuhan:** `mart_aggregated.dim_employee` saat ini hanya berisi `employee_id`, `full_name`, `department_id`, `access_level_id` — **tidak ada `property_id`**, meski `employees.property_id` sudah ada di produksi (`docs/01-architecture/Metadata.md` baris 134; `P06` = kantor pusat). Akibatnya 3 fact table grain-karyawan (`fact_hr_employee_monthly`, `fact_hr_employee_performance_semester`, `fact_hr_watchlist_monthly`) tidak bisa difilter/di-join ke properti lewat `mart_aggregated` sama sekali — Milestone 3.1 (pemetaan akses) mensyaratkan filter `property_id` untuk peran HR Analyst dan Property/GM Analyst, dan Milestone 3.4 (API) kemungkinan besar butuh filter ini untuk 3 view terkait (`v_hr_employee_monthly`, `v_hr_employee_performance_semester`, `v_hr_watchlist_monthly` di `analyst_views`) begitu endpoint per-properti dibangun.
- **Domain terdampak:** HR.
- **Referensi:** `milestones/3.2-view-dan-query-pattern-per-domain/report.md` Known Gaps; `docs/08-serving-data-analyst/view-query-pattern-analyst.md` §HR (catatan "Known Gap ditemukan di M3.2"); `milestones/5.2-desain-struktur-tabel-mart-aggregated/decisions.md` (desain awal `dim_employee` yang tidak menyertakan `property_id`).
- **Evaluasi:**
  | Kriteria | Nilai | Catatan |
  |---|---|---|
  | Ketersediaan data | Tersedia | `employees.property_id` sudah ada penuh di produksi, tinggal dialirkan lewat `mart_cleaned.employees.property_id` (sudah tersedia di `mart_cleaned` sejak M2.1-2.3) ke `dim_employee` — tidak butuh data baru, murni kolom yang terlewat saat desain M5.2. |
  | Dampak ke konsumen lain | Dampak rendah | Menambah 1 kolom (`property_id`) ke `dim_employee`, tidak mengubah kolom/grain yang sudah ada. Konsumen yang sudah pakai `dim_employee` (Facility/Ops — `v_housekeeping_staff_daily`, `v_maintenance_technician_daily`) tidak terpengaruh, hanya mendapat kolom tambahan opsional. |
  | Prioritas relatif | Sedang | Tidak memblokir M3.2 (sudah diselesaikan dengan gap ini didokumentasikan), tapi berpotensi memblokir Milestone 3.4 (API) kalau endpoint per-properti untuk HR dibangun sebelum gap ini ditutup. |
- **Keputusan:** *(menunggu evaluasi pemilik `mart_aggregated`)*
- **Tindak lanjut:** *(menunggu keputusan)*
- **Status:** Diajukan.

---

### Threshold watchlist HR untuk early warning pra-resign

- **Tanggal:** 2026-08-08
- **Pengaju:** HR Manager, tim Data Analyst *(⚠️ SIMULASI — project ini solo, tidak ada tim Data Analyst sungguhan; pengajuan ditulis ala persona berdasarkan gap yang sudah tercatat berulang di M5.1→M5.3, lihat Referensi. Lihat `milestones/5.6-.../decisions.md` Keputusan #2.)*
- **Kebutuhan:** `fact_hr_watchlist_monthly` sudah punya rasio deviasi mentah (`absence_deviation_ratio`, `late_deviation_ratio`) sejak M5.3, tapi tidak ada kolom yang langsung menjawab "karyawan mana yang perlu diperhatikan bulan ini?" — setiap laporan bulanan harus menghitung ulang threshold sendiri secara manual. Butuh 1 kolom flag baku (`in_watchlist`) supaya dashboard/laporan bisa langsung filter tanpa logic tambahan di setiap konsumen.
- **Domain terdampak:** HR.
- **Referensi:** `docs/07-mart-aggregated/konsolidasi-agregasi-mart-aggregated.md` §Kebutuhan Khusus Kategori C; `milestones/5.2-desain-struktur-tabel-mart-aggregated/report.md` Known Gaps; `milestones/5.3-implementasi-transformasi-mart-aggregated/report.md` Known Gaps — ketiganya menandai threshold ini belum diputuskan.
- **Evaluasi:**
  | Kriteria | Nilai | Catatan |
  |---|---|---|
  | Ketersediaan data | Tersedia | `absence_deviation_ratio`/`late_deviation_ratio` sudah ada di `fact_hr_watchlist_monthly` sejak M5.3 — tidak butuh data baru, murni kalkulasi tambahan dari kolom yang sudah ada. |
  | Dampak ke konsumen lain | Dampak rendah | Kolom baru ditambahkan (`in_watchlist`), tidak mengubah kolom/grain yang sudah ada. Konsumen yang sudah pakai `absence_deviation_ratio`/`late_deviation_ratio` mentah tidak terpengaruh. |
  | Prioritas relatif | Sedang | Tidak mendesak (tidak ada laporan tertunda karena ini), tapi sudah 3 milestone berturut-turut (M5.1, M5.2, M5.3) menandai gap yang sama — layak diselesaikan sebelum ada milestone konsumen (M3.x/M4.x) yang butuh kolom ini dan terpaksa menunda lagi.
- **Keputusan:** **DISETUJUI**. Threshold: `in_watchlist = coalesce(absence_deviation_ratio > 5, false) OR coalesce(late_deviation_ratio > 5, false)` — rasio deviasi lebih dari 5x baseline individu (absence ATAU late), konsisten filosofi "within-entity-over-time" yang sudah dikunci sejak M5.1/M5.2 (deviasi dari baseline individu sendiri, bukan rate absolut lintas-karyawan). `coalesce(..., false)`: bulan pertama karyawan (baseline belum ada, ratio `NULL`) dianggap belum bisa dinilai, bukan otomatis ter-flag.
  **Catatan kalibrasi:** angka awal yang diputuskan (1.5x) ternyata men-flag 47% seluruh baris begitu diimplementasikan dan dicek terhadap data riil — jauh terlalu sensitif untuk sebuah "early warning". Direvisi ke 5x (mendekati P95 distribusi rasio riil) setelah dicek `APPROX_QUANTILES` — proporsi ter-flag turun ke 4.67%, jauh lebih masuk akal sebagai watchlist minoritas kecil. Detail di `milestones/5.6-.../decisions.md` Keputusan #5.
- **Tindak lanjut:** `warehouse/models/mart_aggregated/hr_finance/hr/fact_hr_watchlist_monthly.sql` + `_hr_facts_tests.yml` diupdate (kolom `in_watchlist` + test `not_null`), dipromosikan ke `mart_aggregated` (BigQuery, via `scripts/mart_aggregated/promote.py`) dan disinkronkan ke serving PostgreSQL (via `scripts/reverse_etl_mart_aggregated/sync.py`) — keduanya dijalankan manual dan diverifikasi langsung terhadap BigQuery/Postgres sungguhan (kolom ada, 1122/24036 baris `true` = 4.67% cocok persis kedua sisi). Verifikasi tambahan lewat GitHub Actions terjadwal dibatalkan (lihat `milestones/5.6-.../logs.md` Checkpoint 5 untuk alasan) — tidak mengurangi bukti KK2, cuma lapisan "otomatis penuh via CI" yang dilewati.
- **Status:** Selesai (2026-08-08) — lihat `milestones/5.6-mekanisme-pengajuan-perubahan-cakupan/report.md` untuk bukti KK2.

---

### Perubahan skema `fact_ml_occupancy_forecast_property_room_type` begitu tim ML Engineer punya skema final

- **Tanggal:** 2026-08-08
- **Pengaju:** *(dicatat proaktif oleh pemilik `mart_aggregated`, bukan pengajuan masuk — lihat Referensi)*
- **Kebutuhan:** Skema `ml_output.predictions`/`fact_ml_occupancy_forecast_property_room_type` yang dibangun M5.4 eksplisit PROVISIONAL (mock scorer, bukan scoring pipeline sungguhan). Begitu tim ML Engineer sungguhan terlibat dan mendefinisikan skema/use-case final, kemungkinan besar akan berbeda dari yang ada sekarang (target_date, format entity_id, use-case occupancy forecast semuanya cuma contoh).
- **Domain terdampak:** Lintas-domain (Feedback Loop ML) + Revenue (use-case saat ini).
- **Referensi:** `milestones/5.4-integrasi-feedback-loop-ml/report.md` Handoff Notes ("Milestone 5.6 ... perubahan tabel `fact_ml_occupancy_forecast_property_room_type` sebaiknya lewat jalur pengajuan resmi M5.6"); `milestones/5.5-reverse-etl-mart-aggregated/report.md` Handoff Notes (pernyataan yang sama, ditulis ulang independen).
- **Evaluasi:** Belum bisa dievaluasi tuntas — kriteria "ketersediaan data" tidak relevan sampai ada skema konkret yang diajukan (tabelnya SUDAH ada di BigQuery, cuma isinya provisional). Ini contoh nyata pengajuan yang **tidak bisa langsung diproses lewat 3 kriteria standar** karena belum ada proposal konkret untuk dievaluasi, bukan karena datanya tidak tersedia.
- **Keputusan:** **DITUNDA** — menunggu skema/use-case final dari tim ML Engineer. Bukan penolakan, murni belum ada yang bisa dievaluasi.
- **Tindak lanjut:** Tidak ada saat ini. Entri ini sengaja dibiarkan terbuka di backlog sebagai penanda — dicek ulang begitu tim ML Engineer (kalau/ketika terlibat) mengajukan proposal konkret.
- **Status:** Ditunda.
