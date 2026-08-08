# Milestone 5.6: Mekanisme Pengajuan Perubahan Cakupan — Report

**Status:** Completed
**Date completed:** 2026-08-08

## Kriteria Keberhasilan — Hasil

- [x] **Ada jalur yang disepakati bersama (didokumentasikan) yang bisa dipakai tim Data Analyst dan AI Chatbot saat mengajukan kebutuhan agregasi baru.** — Terpenuhi. `docs/07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md`: alur kerja 5 langkah (submit → evaluasi → keputusan → tindak lanjut → tutup), template pengajuan (5 field wajib), 3 kriteria evaluasi persis contoh dokumen sumber (ketersediaan data, dampak ke konsumen lain, prioritas relatif), 1 aturan keputusan sederhana, peran pengaju vs pemilik dipisah eksplisit. Backlog terpusat `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` (pola sama `docs/keputusan-tertunda.md`, terbukti dipakai konsisten sepanjang project) menyediakan tempat mencatat pengajuan dari waktu ke waktu, bukan cuma dokumen proses statis.
- [x] **Sekurangnya satu siklus pengajuan-evaluasi-tindak lanjut berhasil dilakukan sebagai uji coba jalur ini.** — Terpenuhi, dengan bukti tindak lanjut nyata (bukan cuma diajukan lalu didiamkan). Siklus threshold watchlist HR: **diajukan** (persona HR Manager, disimulasikan eksplisit — lihat catatan di bawah) → **dievaluasi** (3 kriteria: data tersedia, dampak rendah, prioritas sedang) → **diputuskan** (disetujui, threshold dikalibrasi terhadap distribusi riil, bukan angka sembarang) → **ditindaklanjuti** (kolom `in_watchlist` ditambahkan ke `fact_hr_watchlist_monthly`, dipromosikan ke `mart_aggregated` BigQuery, disinkronkan ke serving PostgreSQL) → **ditutup** (backlog diupdate status Selesai, Known Gaps M5.1/M5.2/M5.3 di-cross-reference). Diverifikasi langsung terhadap infrastruktur sungguhan: BigQuery `mart_aggregated_staging`/`mart_aggregated` dan Postgres serving project keduanya menunjukkan 1122/24036 baris (4.67%) `in_watchlist=true`, angka identik di kedua sisi.

## Deliverables

- `docs/07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md` — dokumen proses.
- `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` — backlog, 2 entri (1 selesai, 1 ditunda).
- Kolom baru `fact_hr_watchlist_monthly.in_watchlist` (BOOLEAN) — live di BigQuery `mart_aggregated` dan Postgres serving project, `threshold = 5x` baseline individu, dikalibrasi terhadap distribusi riil.
- `docs/07-mart-aggregated/DataSchema-mart-aggregated.md`, `Metadata-mart-aggregated.md` — didokumentasikan.
- Cross-reference "Update Milestone 5.6" di 3 report.md (`5.1`, `5.2`, `5.3`) — jejak keputusan tidak terputus.
- `milestones/5.6-mekanisme-pengajuan-perubahan-cakupan/{decisions,logs}.md`.

## Deviations from decisions.md

Tidak ada deviasi pada 7 keputusan inti. **1 koreksi teknis signifikan ditemukan & diperbaiki saat implementasi** (didokumentasikan eksplisit): threshold draf awal 1.5x (Keputusan #5) ternyata men-flag 47% seluruh baris begitu dicek terhadap data riil — jauh terlalu sensitif untuk sebuah "early warning". Direvisi ke 5x setelah dicek `APPROX_QUANTILES` (mendekati P95), menghasilkan proporsi ter-flag 4.67% yang jauh lebih masuk akal. Ini justru **bukti nyata kenapa kriteria evaluasi M5.6 penting** — kalau langsung dipromosikan tanpa dicek dulu, `mart_aggregated` akan memuat kolom "early warning" yang secara statistik tidak berguna (nyaris setengah karyawan ter-flag setiap bulan).

**1 penyesuaian scope disengaja, dikonfirmasi user:** verifikasi tambahan lewat GitHub Actions terjadwal (trigger `transform-mart-aggregated.yml` → `reverse-etl-mart-aggregated.yml`) dibatalkan di tengah jalan — run jadi lambat karena sensor `ml_output` (mock, M5.4) tidak menemukan data fresh dalam lookback window (trigger manual langsung ke `transform-mart-aggregated.yml`, tidak lewat `transform-mart-cleaned.yml` yang biasanya juga memicu ulang scoring). User meminta dihentikan karena lapisan ML memang masih simulasi, bukan bagian inti yang perlu dibuktikan ulang untuk M5.6. **Tidak mengurangi bukti KK2** — perubahan sudah diverifikasi langsung terhadap BigQuery dan Postgres sungguhan lewat jalur manual (`promote.py`/`sync.py`), cuma lapisan "otomatis penuh via CI" yang dilewati.

## Known Gaps / Follow-ups

- **Threshold SLA breach Facility/Ops masih terbuka** — gap serupa (tercatat M5.1→M5.3), tidak dipilih sebagai trial KK2 (Keputusan #1) supaya scope tetap fokus 1 contoh. Kandidat pengajuan berikutnya yang jelas kalau ada yang mau memakai jalur M5.6 lagi.
- **Breakdown `undistributed_expense` masih tidak tersedia** — gap data sumber murni, tidak bisa diselesaikan lewat jalur M5.6 (butuh perubahan skema produksi). Tetap tercatat sebagai referensi di `konsolidasi-agregasi-mart-aggregated.md`, belum diajukan formal lewat backlog baru — bisa ditambahkan kapan saja kalau relevan.
- **Perubahan skema tabel ML masih ditunda** — dicatat di backlog (entri ke-2), menunggu proposal konkret dari tim ML Engineer sungguhan. Tidak ada tindakan lanjutan yang bisa diambil sekarang.
- **Verifikasi CI penuh untuk perubahan `in_watchlist` tidak selesai dijalankan** (lihat Deviations) — kalau suatu saat perlu dibuktikan ulang jalur otomatis penuhnya, trigger dari `transform-mart-cleaned.yml` (bukan langsung `transform-mart-aggregated.yml`) supaya `scoring-occupancy-forecast.yml` ikut refresh dan sensor `ml_output` tidak menunggu lama.
- **Jalur M5.6 belum pernah diuji oleh pengaju sungguhan** — seluruh siklus trial disimulasikan (Keputusan #2, project solo). Validitas jalur untuk kolaborasi tim sungguhan baru bisa dibuktikan penuh begitu Milestone 3.x/4.x (Data Analyst/AI Chatbot) benar-benar berjalan dan mengajukan sesuatu.

## Handoff Notes

- **Milestone 3.x (Data Analyst)/4.x (AI Chatbot), kapan pun mulai:** kalau menemukan kebutuhan agregasi yang belum tercakup di `mart_aggregated`, jalurnya adalah `docs/07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md` — isi template, tambahkan sebagai entri baru di `pengajuan-perubahan-cakupan.md`. Jangan edit model dbt `mart_aggregated` langsung.
- **Pemilik `mart_aggregated` (siapa pun berikutnya):** pola implementasi tindak lanjut M5.6 (edit model → dbt test → `promote.py` scoped → `sync.py` scoped → verifikasi query langsung) bisa dipakai lagi untuk pengajuan berikutnya — tidak perlu proses baru, infrastrukturnya (M5.3 promote, M5.5 reverse ETL) sudah reusable persis seperti dibuktikan di sini.
- **Kalibrasi threshold berbasis data, bukan angka di atas kertas** — pelajaran eksplisit dari koreksi 1.5x→5x: setiap kali M5.6 memproses pengajuan yang melibatkan angka ambang batas, cek dulu distribusi riil (`APPROX_QUANTILES` atau setara) sebelum keputusan dianggap final, jangan langsung dipromosikan dari angka yang "terdengar masuk akal" di atas kertas.
