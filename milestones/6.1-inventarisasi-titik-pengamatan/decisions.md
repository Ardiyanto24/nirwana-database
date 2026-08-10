# Milestone 6.1: Inventarisasi Titik Pengamatan dan Baseline Pipeline — Decisions

**Source:** `docs/03-implementation-plans/06-monitoring-warehouse-serving-fase2.md`, baris 50-64.
**Status:** In Progress
**Date started:** 2026-08-10

## Contract (from source doc)

- **Lingkup:** Memetakan seluruh titik dalam alur end-to-end (§9.1 arsitektur, 10 langkah: extract→transform mart_cleaned→DQ test→trigger scoring→sensor `ml_output`→transform mart_aggregated→DQ test→reverse ETL mart_aggregated→reverse ETL mart_cleaned→post-sync validation) yang perlu diamati, beserta bentuk sinyal yang tersedia di tiap titik. Termasuk memahami dependency antar langkah sebagai dasar menentukan bagaimana kegagalan di satu titik seharusnya terlihat kaitannya dengan titik lain.
- **Output:** (1) Peta 10 titik pengamatan dengan sinyal yang tersedia di masing-masing, dan dependency-nya satu sama lain. (2) Klasifikasi prioritas per titik.
- **Kriteria Keberhasilan:**
  1. Setiap 10 titik pengamatan punya sumber sinyal yang jelas dan bisa dirujuk langsung oleh milestone berikutnya (6.2) tanpa perlu analisis ulang dari nol.
  2. Dependency antar titik terdokumentasi sehingga saat menyusun alerting nanti (6.7), satu kegagalan akar tidak memicu banjir alert yang membingungkan dari titik-titik downstream-nya.

Milestone ini murni **observasional/dokumentasi** — sama sifatnya dengan Milestone 3.1 (`milestones/3.1-pemetaan-pola-akses-analyst/`). Tidak ada kode, schema, atau kredensial yang disentuh. Belum ada satu pun folder `milestones/6.x-*` sebelum ini — titik mulai keluarga monitoring Fase 2 (6.1-6.7) dari nol.

## Metode Eksplorasi

Atas instruksi eksplisit user, eksplorasi dilakukan dengan membaca langsung (bukan delegasi Explore agent seperti pola default milestone lain), bertahap per **7 layer pengerjaan warehouse**, dengan konfirmasi lanjut/berhenti dari user di tiap layer:

1. **Fondasi Monitoring Production (Fase 1)** — `report.md` Milestone 1.1-1.7 + `docs/04-monitoring/baseline-inventaris-produksi.md`.
2. **Orchestrator + Extraction** — `report.md` Milestone 2.0-2.1 + `docs/05-orchestrator/konvensi-job-dependency.md`.
3. **Staging + Mart Cleaned + Reverse ETL** — `report.md` Milestone 2.2-2.4.
4. **Akses Data Scientist + Kredensial** — `report.md` Milestone 2.5-2.6 + `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`.
5. **Mart Aggregated + Feedback Loop ML + Reverse ETL** — `report.md` Milestone 5.1-5.7 + `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md`.
6. **Serving Data Analyst** — `report.md` Milestone 3.1-3.6.
7. **Serving AI Chatbot** — `report.md` Milestone 4.1-4.6 + `docs/09-serving-ai-chatbot/audit-log-chatbot.md` (bagian "Cara Query untuk M6.5").

Total: 32 `report.md` milestone (1.1-5.7) + 9 dokumen substantif `docs/04` s.d. `docs/09`. Hasil peta disilang-cek ke `.github/workflows/*.yml` (dibaca langsung, termasuk 1× `grep` live untuk verifikasi `renew_expiration.py` terjadwal untuk `mart_aggregated`/`mart_aggregated_staging`) dan skema `monitoring.*` (`scripts/*/schema.sql`) — bukan cuma dari narasi dokumen arsitektur.

## Temuan Risiko Lintas-Titik

Dua temuan muncul dari sintesis 7 layer, didiskusikan penuh dengan user sebelum diputuskan cara penanganannya:

1. **Titik 1→2 tidak digate** — `extract-production.yml`→`transform-mart-cleaned.yml` cuma buffer waktu (cron 03:00→05:00 UTC), bukan `workflow_run` seperti semua dependency lain di pipeline ini (konvensi `docs/05-orchestrator/konvensi-job-dependency.md`). Kalau ekstraksi gagal, transform tetap jalan tanpa gate apa pun. Risiko rendah saat ini (dataset production statis, lihat `CLAUDE.md`), tapi gap struktural nyata — tidak ditemukan tercatat sebagai keputusan sadar di `decisions.md` manapun.
2. **Titik 3 & 7 (DQ gate `promote.py`) tidak punya sinyal queryable** — gate-nya terbukti benar (2× fault-injection nyata: M2.3 `bookings.total_amount` negatif, M5.3 GOP double-counting, keduanya tertangkap sebelum swap), tapi hasilnya cuma exit code + `dbt run_results.json` efemeral di dalam run CI. `monitoring.dq_test_results` yang sudah ada adalah untuk pengujian data production Fase 1 (`scripts/dq/build_and_run.py`), bukan untuk gate ini. **Prasyarat langsung KK #1 Milestone 6.3** — kalau tidak ditutup penuh, menjalar jadi titik buta di dashboard final M6.7.

## Task Breakdown

- [x] Eksplorasi 7 layer (di atas) — Acceptance: seluruh `report.md` 1.1-5.7 + 9 dokumen substantif dibaca — Verify: ringkasan tiap layer dikonfirmasi user di chat sebelum lanjut — M
- [x] Sintesis peta 10 titik + 2 temuan risiko, didiskusikan dampaknya terhadap M6.2-6.7 dengan user — Verify: user mengonfirmasi klasifikasi dampak (temuan 1 = risiko berdiri sendiri, temuan 2 = prasyarat M6.3) — S
- [ ] Tulis `decisions.md` (dokumen ini) — Acceptance: kontrak + 7 keputusan + 2 temuan tercatat sebelum file lain ditulis — S
- [ ] Tulis 2 entri baru `docs/keputusan-tertunda.md` — Acceptance: format konsisten entri existing — S
- [ ] Tulis `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` — Acceptance: 10/10 titik terisi Sumber Sinyal atau Gap eksplisit, dependency merujuk file YAML nyata — M
- [ ] Tulis `logs.md` + verifikasi akhir + commit — M

## Technical Decisions

### 1. Segmentasi eksplorasi: 7 layer bertahap dengan checkpoint konfirmasi

**Context:** User eksplisit meminta pembacaan "per layer pengerjaan data warehousing", berhenti tiap layer menunggu instruksi lanjut.
**Decision:** 7 layer sesuai urutan konstruksi pipeline sungguhan (bukan urutan nomor milestone), dengan konfirmasi user di tiap batas layer.
**Alternatives considered:** Delegasi Explore agent (pola default milestone lain) — ditolak karena user menekankan M6.1 "butuh pengamatan yang jeli dan mendetail" dan deviasi/insiden nyata (bagian Deviations/Known Gaps tiap `report.md`) berisiko hilang dalam ringkasan agent.

### 2. Resolusi diskrepansi "10 vs 11 titik": ikuti §9.1, titik 11 dicatat terpisah out-of-scope

**Context:** `rancangan-arsitektur-data-platform-elt.md` §9.1 (sumber kanonis) mendefinisikan persis 10 langkah, berakhir di post-sync validation. `06-monitoring-warehouse-serving-fase2.md` (baris 35-46) menambahkan butir ke-11 ("Konsumsi Data Analyst/AI Chatbot") tanpa mengubah Kriteria Keberhasilan yang tetap menyebut literal "10 titik".
**Decision:** Peta inti mengikuti persis 10 langkah §9.1. Titik ke-11 dicatat sebagai baris terpisah bertanda out-of-scope di dokumen peta, dengan alasan eksplisit.
**Alternatives considered:** Memaksa 11 titik masuk peta inti (ditolak — menyimpang dari KK literal sumber, dan konsumsi Data Analyst/AI Chatbot punya sifat berbeda dari 10 langkah pipeline internal); mendiamkan diskrepansi tanpa catatan (ditolak — menyembunyikan inkonsistensi dokumen sumber, bukan pola project ini).

### 3. 2 temuan risiko → `docs/keputusan-tertunda.md`, bukan diperbaiki di M6.1

**Context:** Temuan 1 dan 2 (lihat "Temuan Risiko Lintas-Titik" di atas) ditemukan saat eksplorasi, di luar Lingkup M6.1 yang murni observasional.
**Decision:** Dicatat sebagai 2 entri baru mengikuti format standar `docs/keputusan-tertunda.md` (What was deferred/Why deferred/Revisit when/Status), bukan ditambal langsung.
**Alternatives considered:** Memperbaiki langsung di M6.1 (ditolak — mengubah `.github/workflows/*.yml`/`promote.py` adalah perubahan infrastruktur pipeline milik lineage Milestone 2.x/5.x, bukan wewenang milestone observasional; CLAUDE.md eksplisit "mengamati, bukan membangun"); tidak mencatat sama sekali (ditolak — pola berulang project ini: M2.1 partitioning, M2.3 DML block, M5.2 `property_id` semuanya gap yang baru ketahuan lebih dalam dari asumsi dokumen sumber — mencatat eksplisit mencegah M6.3 under-scope breakdown-nya sendiri, persis pelajaran dari preseden itu).

### 4. `report.md` ditunda, tidak ditulis di batch penulisan ini

**Context:** 4 file (`decisions.md`, `docs/keputusan-tertunda.md`, dokumen peta, `logs.md`) ditulis dalam satu batch kerja.
**Decision:** `report.md` menunggu user membaca dan mengonfirmasi `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md` akurat, baru ditulis dan milestone ditutup Completed.
**Alternatives considered:** Langsung menulis `report.md` di batch yang sama (ditolak — disiplin "jangan klaim sukses tanpa verifikasi" konsisten dipakai 32 milestone sebelumnya; isi peta baru pertama kali ada dalam bentuk file sungguhan di batch ini, belum direview user di luar bentuk tabel chat).

### 5. Lokasi dokumen: folder `docs/10-monitoring-warehouse-serving/`, bukan file tunggal

**Context:** User meminta `docs/10-monitoring-warehouse-serving.md` (file tunggal).
**Decision:** Folder baru bernomor urut lanjutan (`07-mart-aggregated`, `08-serving-data-analyst`, `09-serving-ai-chatbot` sudah ada), isi file `pemetaan-titik-pengamatan-pipeline.md`.
**Alternatives considered:** File tunggal persis seperti diketik user (ditolak — menyimpang dari preseden identik 3× berturut-turut; folder bernomor menampung dokumen dari seluruh rangkaian milestone terkait, dan M6.1 cuma milestone pertama dari 7 — folder ini kemungkinan besar menampung dokumen output M6.2-6.7 berikutnya, sama pola 08/09 yang masing-masing menampung 6 dokumen). Mudah dikoreksi kalau asumsi ini salah.

### 6. Skema kolom tabel peta

**Decision:** `Titik | Tahap | Sumber Sinyal Tersedia | Sinyal Belum Ada (Gap) | Dependency (menunggu titik apa) | Klasifikasi Prioritas`.
**Alternatives considered:** Menggabung kolom Sinyal dan Gap jadi 1 sel (ditolak — mengikuti rigor M3.1 yang memisahkan kolom Gap secara eksplisit, supaya M6.2/6.3 bisa filter langsung baris mana yang masih perlu dibangun).

### 7. Klasifikasi prioritas: Kritis (titik 2) / Tinggi (titik 1,3,6,7,8,9,10) / Sedang (titik 4,5)

**Context:** KK #2 M6.1 minta dependency terdokumentasi supaya 1 akar masalah tidak memicu banjir alert.
**Decision:** Titik 2 diberi level terpisah "Kritis" (bukan cuma "Tinggi" tertinggi) karena satu-satunya akar fan-out ke 3 cabang paralel (titik 3/9, titik 4, titik 6) dan tidak digate dari titik 1. Titik 4/5 "Sedang" karena terbukti isolated-by-design lewat fault-injection nyata M5.4 (kegagalan sensor tidak menjatuhkan 76 tabel `mart_aggregated` lain).
**Alternatives considered:** Klasifikasi 2 level (Tinggi/Rendah) generik (ditolak — tidak cukup granular untuk memberi M6.7 dasar konkret desain dedup alert; 3 level dengan justifikasi blast-radius/isolasi-desain lebih actionable).

## Open Questions Resolved with User

- Q: Segmentasi eksplorasi per layer atau langsung baca semua? → A: Per layer, 7 layer, konfirmasi tiap batas.
- Q: Apakah 2 temuan risiko adalah masalah yang mengganggu kesuksesan M6.x? → A: Tidak mengancam kesuksesan keseluruhan, tapi temuan 2 adalah prasyarat langsung M6.3 dan berisiko menjalar ke M6.7 kalau under-scoped — perlu dicatat eksplisit dengan penekanan khusus.
- Q: Siapa yang bertanggung jawab menyelesaikan 2 temuan itu di antara M6.2-6.7? → A: Tidak satu pun milestone monitoring "memiliki" perbaikan temuan 1 (di luar wewenang, perlu keputusan terpisah); M6.3 memiliki penuh temuan 2 (Output #1-nya secara literal).
- Q: Lanjutkan langsung tulis file (bukan cuma diskusi)? → A: Ya — tulis 2 entri `keputusan-tertunda.md` (temuan 1 dan 2, penekanan khusus temuan 2) + buat `docs/10-monitoring-warehouse-serving/pemetaan-titik-pengamatan-pipeline.md`.
