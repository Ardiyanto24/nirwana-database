# Milestone 2.0: Fondasi Orchestrator Bersama (Fase 2)

**Source:** `docs/03-implementation-plans/02-serving-data-scientist.md` (baris 45-61, "Milestone 2.0 — Fondasi Orchestrator Bersama")
**Status:** In Progress
**Date started:** 2026-08-08

## Contract (from source doc)

- **Lingkup:** Men-setup platform orchestrator yang akan dipakai bersama sepanjang pipeline Fase 2 — instalasi/provisioning tool, konvensi penamaan job dan dependency, mekanisme dasar penjadwalan, serta akses yang diperlukan pemilik pekerjaan lain (Orang 5 pemilik `mart_aggregated`, dan pekerjaan monitoring Fase 2) untuk menambahkan job mereka sendiri ke instance yang sama di kemudian hari.
- **Tidak termasuk:** Mendefinisikan seluruh 10 langkah dependency dari dokumen arsitektur (Bagian 9.1) — hanya langkah yang relevan dengan Milestone 2.1-2.5 (ekstraksi, transformasi s/d `mart_cleaned`, reverse ETL `mart_cleaned`). Langkah scoring/join `ml_output`/`mart_aggregated` ditambahkan pemilik pekerjaan tersebut sebagai perluasan nanti.
- **Output:** Platform orchestrator terpasang & bisa menjalankan job terjadwal; konvensi penamaan job/dependency terdokumentasi; mekanisme akses bagi pemilik pekerjaan lain.
- **Kriteria keberhasilan:**
  1. Job percobaan sederhana berhasil dijadwalkan dan dijalankan melalui platform ini.
  2. Pemilik pekerjaan lain (diverifikasi lewat uji coba akses) bisa menambahkan job baru ke instance yang sama tanpa perlu membangun instance terpisah.

## Konteks Tambahan (di luar dokumen sumber, disepakati di sesi ini)

Sebelum breakdown ini, ditemukan bahwa Milestone 2.0/Fase 2 sebelumnya ditandai eksplisit "out of scope" untuk repo `nirwana-database` di `CLAUDE.md` (warisan dari saat repo ini murni fokus Fase 1). Empat keputusan scope/pendekatan perlu diambil dulu sebelum breakdown task bisa jalan — dikonfirmasi user lewat `AskUserQuestion`, dicatat di bawah sebagai bagian dari Technical Decisions.

## Task Breakdown

Catatan lingkup: sesuai source doc, M2.0 murni fondasi platform orchestrator — **tidak termasuk** provisioning GCP/BigQuery (itu output Milestone 2.1). Job percobaan di sini sengaja dibuat self-contained (tidak bergantung ke infra eksternal apa pun) supaya mekanisme scheduling & dependency bisa dibuktikan tuntas tanpa terikat kesiapan GCP.

- [x] Task 1: Update `CLAUDE.md` — cerminkan bahwa Fase 2 kini dikerjakan di repo ini mulai M2.0 — Acceptance: bagian Project Scope & status Fase konsisten dengan kenyataan — Verify: baca ulang `CLAUDE.md` — XS
- [ ] Task 2: Desain & dokumentasikan konvensi penamaan job + dependency (naming pattern, cara mendeklarasikan `needs`/`workflow_run`, lokasi workflow file, cara pemilik pekerjaan lain menambah job) — Acceptance: konvensi tertulis di `docs/`, dipakai konsisten di Task 3 & 4 — Verify: review manual — S
- [ ] Task 3: Workflow GitHub Actions job percobaan sederhana (`.github/workflows/orchestrator-demo-extract.yml`) — job A (scheduled) → trigger job B (`.github/workflows/orchestrator-demo-transform.yml`) via `workflow_run`, dependency eksplisit — Acceptance: job B hanya jalan setelah job A sukses — Verify: run history GitHub Actions, urutan run kedua job — S
- [ ] Task 4: Simulasi "pemilik pekerjaan lain" — tambah job ketiga (`.github/workflows/orchestrator-demo-monitoring.yml`, berperan sebagai pekerjaan monitoring Fase 2) mengikuti konvensi Task 2, ditambahkan sebagai perluasan tanpa mengubah job A/B — Acceptance: job ketiga jalan di instance/repo yang sama tanpa setup terpisah — Verify: run history, konfirmasi tidak ada instance/repo baru dibuat — S
- [x] Task 5: Tambah entri baru di `docs/keputusan-tertunda.md` untuk keputusan self-hosted-nanti — Acceptance: entri lengkap dengan Why/Revisit — Verify: baca ulang dokumen
- [ ] Task 6: Verifikasi Kriteria Keberhasilan + tulis `logs.md`/`report.md` — Acceptance: kedua KK dicek eksplisit — Verify: `report.md` mengacu ke run history sungguhan sebagai bukti — S

**Catatan serah terima ke Milestone 2.1:** provisioning GCP project + dataset `raw_production` + service account, yang sempat dibahas di sesi perencanaan ini, adalah pekerjaan Milestone 2.1 — dicatat di sini supaya tidak hilang, bukan dikerjakan di M2.0.

**Checkpoint** setelah Task 3: kalau job percobaan pertama tidak berhasil dijadwalkan otomatis, Task 4 (simulasi pemilik lain) tidak ada gunanya diverifikasi.

## Technical Decisions

### Decision: Scope repo — Fase 2 dikerjakan di `nirwana-database` (bukan repo baru)

- **Context:** `CLAUDE.md` sebelumnya eksplisit menyatakan Fase 2 "out of this repo's scope, reference only". Perlu diputuskan apakah Milestone 2.0 dst dikerjakan di sini atau repo terpisah (pola M1.6/1.7).
- **Decision:** Dikerjakan di repo `nirwana-database` ini. `CLAUDE.md` diupdate untuk mencerminkan scope baru.
- **Alternatives considered:** Repo baru terpisah (mis. `nirwana-warehouse-elt`), konsisten dengan pola `api/`/`web/` yang gitignored & deploy dari repo sendiri.
- **Rejected because:** user memilih tetap di repo ini — beda karakter dari M1.6/1.7 (yang portfolio-facing, deployed services terpisah dari environment Python repo ini); Fase 2 secara teknis adalah kelanjutan langsung pipeline data yang sama, bukan aplikasi terpisah yang butuh runtime/deploy target berbeda.

### Decision: Tool orchestrator — GitHub Actions extended (bukan orchestrator sungguhan)

- **Context:** Dokumen arsitektur (Bagian 12) menyebut Airflow/Dagster/Prefect sebagai contoh ilustratif kategori tool orchestrator. Tiga opsi dipertimbangkan: (A) GitHub Actions extended — lanjutan pola Fase 1, dependency via `workflow_run`/`needs`; (B) self-hosted penuh (Airflow/Dagster/Prefect via Docker di Railway/Render/Fly.io); (C) managed cloud free tier (Prefect Cloud/Dagster Cloud).
- **Decision:** Opsi A — GitHub Actions extended. Desain job & konvensi dibuat **sedekat mungkin dengan standar industri** (naming eksplisit, dependency terdokumentasi jelas di Task 3, retry per-step dimanfaatkan semaksimal fitur native GitHub Actions) supaya migrasi ke orchestrator sungguhan di masa depan tidak butuh desain ulang total.
- **Konsekuensi eksplisit:** GitHub Actions tidak punya sensor native (dibutuhkan nanti untuk feedback loop scoring — Bagian 6.4 arsitektur, "tunggu hingga `ml_output` selesai ditulis") dan dependency graph-nya lebih terbatas (`workflow_run` cuma bisa reaksi ke completion, bukan kondisi arbitrer) dibanding Airflow/Dagster/Prefect. Ini diterima sebagai batasan sadar untuk Milestone 2.0-2.5 (extraction → mart_cleaned → reverse ETL), bukan untuk seluruh Fase 2 selamanya.
- **Alternatives considered:** Opsi B (self-hosted) — fitur paling lengkap (dependency graph, sensor, retry per-task, UI), tapi butuh service jalan 24/7 dan risiko biaya hosting begitu keluar free tier platform. Opsi C (managed cloud) — tidak perlu kelola server 24/7, tapi terikat batasan free tier vendor pihak ketiga yang bisa berubah kapan saja.
- **Rejected because:** user memilih Opsi A murni karena **pertimbangan biaya** — baik Opsi B maupun C membawa risiko biaya/ketergantungan infra tambahan yang belum sepadan untuk fondasi awal Fase 2 ini. Dicatat sebagai keputusan tertunda (bukan final permanen) di `docs/keputusan-tertunda.md` — kemungkinan besar pindah ke **self-hosted** (Opsi B) di masa mendatang begitu constraint biaya berubah atau kebutuhan sensor/dependency graph tidak bisa lagi dipaksakan lewat GitHub Actions.

### Decision: Provisioning BigQuery/GCP — di luar lingkup M2.0, dari nol di Milestone 2.1

- **Context:** Belum ada GCP project atau BigQuery dataset apa pun di project ini sebelumnya (dikonfirmasi: tidak ada jejak `bigquery`/`gcp` di `requirements.txt`, `.env.example`, atau kode repo — hanya di dokumen rancangan). Sempat dipertimbangkan sebagai task M2.0, tapi source doc eksplisit menyatakan M2.0 "tidak mencakup mendefinisikan seluruh 10 langkah dependency" — provisioning `raw_production` adalah **output eksplisit Milestone 2.1**, bukan M2.0.
- **Decision:** Job percobaan M2.0 dibuat self-contained (tanpa koneksi ke GCP/BigQuery apa pun) untuk membuktikan mekanisme orchestrator murni. Provisioning GCP project + dataset `raw_production` dari nol menjadi task pembuka Milestone 2.1, dicatat sebagai catatan serah terima di Task Breakdown di atas.
- **Alternatives considered:** Menggabungkan provisioning GCP ke M2.0 supaya job percobaan langsung "nyata" (menyentuh BigQuery).
- **Rejected because:** mencampur keputusan platform (M2.0) dengan keputusan konten pipeline (M2.1) — persis hal yang menurut source doc sengaja ingin dihindari dengan memisah M2.0 sebagai milestone tersendiri ("Kenapa Ini Jadi Milestone Terpisah").

### Decision: Verifikasi Kriteria Keberhasilan #2 — simulasi job kedua sebagai "pemilik lain"

- **Context:** Kriteria Keberhasilan #2 sumber minta pembuktian "pemilik pekerjaan lain bisa menambahkan job baru ke instance yang sama tanpa instance terpisah" — tapi project ini dikerjakan solo, tidak ada pemilik `mart_aggregated`/monitoring Fase 2 sungguhan yang bisa diajak uji coba.
- **Decision:** Divalidasi lewat **simulasi** — Task 5 menambahkan job ketiga (berperan sebagai "pemilik lain", mis. mewakili pekerjaan monitoring Fase 2) mengikuti konvensi Task 3, tanpa mengubah job A/B yang sudah ada, di repo/instance yang sama.
- **Alternatives considered:** Cukup dokumentasi konvensi + akses tanpa uji coba job kedua sungguhan.
- **Rejected because:** user memilih simulasi aktif — pembuktian lewat job kedua yang sungguhan berjalan lebih kuat daripada klaim dokumentasi semata, konsisten dengan pola project ini yang selalu memverifikasi lewat uji coba terkontrol (mis. M1.4/M1.5 uji drift buatan) ketimbang asumsi.

## Open Questions Resolved with User

- Q: Fase 2 dikerjakan di repo ini atau repo baru? → A: Repo ini (`nirwana-database`), `CLAUDE.md` diupdate.
- Q: Tool orchestrator? → A: GitHub Actions extended (Opsi A), karena biaya — didesain dekat standar industri, dengan catatan revisit ke self-hosted di `keputusan-tertunda.md`.
- Q: GCP/BigQuery sudah ada? → A: Belum, provisioning dari nol jadi bagian kerja milestone ini.
- Q: Bagaimana validasi kriteria "pemilik lain bisa menambahkan job"? → A: Simulasi — job ketiga ditambahkan sebagai "pemilik lain" di instance yang sama.
