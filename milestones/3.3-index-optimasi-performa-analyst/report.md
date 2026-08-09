# Milestone 3.3: Index dan Optimasi Performa untuk Pola Akses Analyst — Report

**Status:** Completed
**Date completed:** 2026-08-09

## Kriteria Keberhasilan — Hasil

- [x] **KK1 — Query representatif tiap domain berjalan dalam waktu wajar untuk analisis interaktif, diverifikasi `EXPLAIN ANALYZE`.** Terpenuhi untuk seluruh 6 domain × 2 schema (`mart_aggregated`, `mart_cleaned`), diverifikasi langsung terhadap serving PostgreSQL sungguhan (bukan asumsi) — lihat `docs/08-serving-data-analyst/index-baseline-analyst.md` untuk baseline-vs-setelah lengkap per tabel. Perbaikan paling signifikan: `mart_cleaned.staff_shifts` 1702.8ms→2.5ms (~681x, penurunan terbesar milestone ini), `mart_cleaned.fnb_transactions` 1004.4ms→~5ms (~200x, tabel terbesar project di 902.574 baris), `fact_revenue_los_daily` 276.6ms→0.48ms (~576x).
- [x] **KK2 — Index yang dipasang benar-benar terpakai oleh query plan.** Terpenuhi, dibuktikan 2 arah untuk seluruh 50 index: (a) `EXPLAIN ANALYZE` menunjukkan node Index Scan/Bitmap Index Scan (bukan Seq Scan) pada query representatif setelah index dipasang; (b) `pg_stat_user_indexes.idx_scan ≥ 1` dikonfirmasi lewat query langsung ke `pg_stat_user_indexes` — tidak satu pun dari 50 index yang terpasang tapi tidak pernah terpakai (dicek eksplisit, list kosong).

## Deliverables

- `docs/08-serving-data-analyst/index-baseline-analyst.md` — baseline lengkap per tabel (sebelum/sesudah index), 50 entri.
- `scripts/reverse_etl_mart_aggregated/mart_aggregated_indexes.py` — 41 index, menggantikan `example_indexes.py` (M5.5 provisional).
- `scripts/reverse_etl/mart_cleaned_indexes.py` + `reindex_analyze.py` — mekanisme baru dari nol (sebelumnya tidak ada sama sekali untuk `mart_cleaned`).
- `.github/workflows/reverse-etl-mart-cleaned.yml` — step baru "REINDEX/ANALYZE pasca-swap".
- `milestones/3.3-index-optimasi-performa-analyst/{decisions,logs}.md`.

## Cakupan Final

50 index (41 `mart_aggregated` + 9 `mart_cleaned`) lintas 6 domain: Revenue (9), F&B (8), Facility/Ops (8), Spa & Event (7), HR (7), Corporate/Financial (11).

## Deviations from decisions.md

**1 koreksi signifikan ditemukan saat implementasi (Checkpoint 7), didokumentasikan eksplisit:** Keputusan #2 (`decisions.md`) berasumsi tabel kecil (ribuan baris atau kurang) hampir pasti tetap seq-scan meski diberi index. Spot-check di `fact_financial_business_line_group_monthly` (180 baris) membuktikan sebaliknya — dengan filter cukup selektif, Postgres tetap memilih Index Scan bahkan di tabel sekecil itu. **Kesimpulan yang benar: selektivitas filter, bukan jumlah baris mentah, yang menentukan pilihan planner.** Koreksi diterapkan retroaktif di Corporate/Financial (seluruh 9 tabel domain itu diuji individual tanpa pengecualian berdasar ukuran), tapi domain-domain sebelumnya (Revenue, F&B, Facility/Ops, Spa & Event, HR) yang sudah mengecualikan beberapa tabel <500 baris tanpa uji individual eksplisit **tidak diuji ulang** dalam milestone ini — dicatat sebagai Known Gap di bawah, bukan didiamkan. Tidak mengurangi bukti KK1/KK2 untuk index yang memang dipasang — cuma berarti beberapa tabel kecil di domain awal *mungkin* juga akan lolos uji index kalau dicoba, belum dibuktikan.

**Temuan sekunder (bukan deviasi, tapi nuansa penting):** untuk tabel yang sudah sub-milidetik sebelum index (Corporate/Financial, ~216 baris), index terpakai planner (KK2 terpenuhi) tapi **tidak mempercepat** — bahkan sedikit menambah overhead traversal B-tree dibanding seq scan trivial pada tabel sekecil itu. Bukan pelanggaran KK2 (index terbukti terpakai secara faktual), tapi menunjukkan manfaat nyata index terkonsentrasi di tabel besar, bukan seragam di semua tabel.

**Anomali operasional dicatat jujur:** `fnb_transactions` (902.574 baris) sempat terukur 1473.5ms pada run pertama tepat setelah `REINDEX` (cache-dingin, buffer belum warm) — 3 run berikutnya stabil 4.9-65ms. Bukan kegagalan index (plan tetap Bitmap Index Scan), tapi karakteristik operasional relevan: baseline pertama pasca-swap/reindex terjadwal bisa terasa lebih lambat sampai cache warm.

## Known Gaps / Follow-ups

- **Tabel kecil yang dikecualikan di Revenue/F&B/Facility/Spa&Event/HR tanpa uji individual** (mis. `fact_revenue_gop_impact_monthly` 180 baris, `fact_hr_turnover_snapshot` 43 baris, dkk) belum diuji ulang dengan pemahaman "selektivitas filter lebih penting dari ukuran tabel" yang baru ditemukan di Checkpoint 7. Kemungkinan sebagian akan lolos kalau diuji dengan filter yang cukup selektif — belum dibuktikan, follow-up untuk revisit milestone ini kalau performa tabel-tabel tersebut jadi masalah nyata di kemudian hari.
- **Baseline waktu eksekusi perlu diperiksa ulang berkala** (bukan sekali di awal) — sesuai catatan ketergantungan dokumen sumber M3.3 sendiri: tabel hasil swap tidak mewarisi statistik lama, dan meski `reindex_analyze.py` sudah wired otomatis pasca-swap, degradasi performa jangka panjang (mis. data bertambah signifikan, distribusi berubah) belum tentu tertangkap tanpa pengecekan ulang.
- **Composite index HR** (`fact_hr_attendance_daily`, 3 kolom) adalah satu-satunya index 3-kolom di seluruh milestone ini — domain lain yang berpotensi butuh composite serupa (mis. kombinasi filter tambahan di Facility/Ops untuk `priority_id`) belum dieksplorasi karena `EXPLAIN ANALYZE` domain itu sudah cukup cepat dengan index 2-kolom `(property_id, period_date)`.

## Handoff Notes

- **Operasional harian:** mekanisme `reindex_analyze.py --all` sudah otomatis jalan pasca-swap di kedua workflow terjadwal — tidak perlu intervensi manual untuk mempertahankan index yang sudah didesain di milestone ini.
- **Milestone 3.4 (API):** query representatif per domain di `index-baseline-analyst.md` adalah basis langsung untuk menentukan pola query endpoint (filter kolom mana yang harus jadi parameter wajib supaya index terpakai).
- **Pemilik `mart_aggregated`/`mart_cleaned` berikutnya:** kalau ada perubahan skema (kolom baru, tabel baru) lewat mekanisme M5.6, ingat index di 2 file `*_indexes.py` ini perlu direvisit — index tidak otomatis mengikuti perubahan skema.
- **Kalau Known Gap "tabel kecil belum diuji ulang" ingin diselesaikan:** pola yang sudah terbukti di Checkpoint 7 (buat index sementara dengan `CREATE INDEX IF NOT EXISTS` manual, uji `EXPLAIN ANALYZE`, baru putuskan pertahankan atau drop) bisa dipakai lagi langsung tanpa proses baru.
