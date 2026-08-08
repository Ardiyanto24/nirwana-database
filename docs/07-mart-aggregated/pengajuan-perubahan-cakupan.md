# Pengajuan Perubahan Cakupan `mart_aggregated` (Backlog)

> Dokumen ini mencatat **setiap pengajuan** perubahan/penambahan agregasi ke `mart_aggregated` dari tim konsumen (Data Analyst, AI Chatbot), mengikuti alur di `mekanisme-pengajuan-perubahan-cakupan.md`. Setiap pengajuan tetap dicatat permanen di sini apa pun hasilnya (disetujui/ditolak/ditunda) — bukan dihapus begitu selesai diproses. Pola sama `docs/keputusan-tertunda.md`.

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
- **Tindak lanjut:** `warehouse/models/mart_aggregated/hr_finance/hr/fact_hr_watchlist_monthly.sql` + `_hr_facts_tests.yml` diupdate (kolom `in_watchlist` + test `not_null`), dipromosikan ke `mart_aggregated` (BigQuery) dan disinkronkan ke serving PostgreSQL — diverifikasi lewat GitHub Actions sungguhan (`transform-mart-aggregated.yml` + `reverse-etl-mart-aggregated.yml`). Detail lengkap di `milestones/5.6-.../logs.md` Checkpoint 5.
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
