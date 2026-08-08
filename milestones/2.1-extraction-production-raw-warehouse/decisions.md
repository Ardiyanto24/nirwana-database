# Milestone 2.1: Extraction Production ke Raw Warehouse (Fase 2)

**Source:** `docs/03-implementation-plans/02-serving-data-scientist.md` (baris 64-81, "Milestone 2.1 — Extraction Production ke Raw Warehouse")
**Status:** In Progress
**Date started:** 2026-08-08

## Contract (from source doc)

- **Lingkup:** Ekstraksi dari 6 schema Postgres (1 instance Supabase) ke `raw_production` di BigQuery untuk 23 tabel, strategi incremental sync dari read replica, skema raw identik 1:1 tanpa transformasi bisnis. Termasuk aktivasi CDC/incremental di sisi production dan user replikasi privilese terbatas + whitelist tabel eksplisit.
- **Output:** Jalur ekstraksi berjalan untuk 23 tabel; skema raw 1:1 + metadata kolom (waktu sinkronisasi); partitioning pada tabel raw; user replikasi terkonfigurasi & terdokumentasi.
- **Kriteria keberhasilan:**
  1. Seluruh 23 tabel tersinkronisasi ke `raw_production` dengan row count cocok sumber pada snapshot sama.
  2. Sinkronisasi berjalan terjadwal secara incremental tanpa membebani primary (tervalidasi lewat read replica).
  3. User replikasi terbukti **tidak bisa** akses tabel di luar whitelist saat diuji coba.

## Konteks: Temuan yang Mengubah Bentuk Keputusan

Breakdown (`planning-and-task-breakdown`) menemukan 3 fakta yang tidak sesuai asumsi literal dokumen sumber:

1. **Tidak ada kolom `updated_at`/audit-timestamp** di 23 tabel production (dicek `docs/01-architecture/Metadata.md`) — hanya kolom tanggal bisnis (`check_in_date`, `hire_date`, dst).
2. **Data production adalah static synthetic snapshot** (`CLAUDE.md`), bukan live stream.
3. **Read Replica Supabase adalah fitur berbayar** (plan Pro+), beda dari CDC/logical replication slot yang gratis (fitur inti Postgres).

## Task Breakdown

- [x] Task 1: Provisioning GCP project + dataset `raw_production` di BigQuery — Acceptance: project & dataset ada — Verify: `bq ls --project_id=nirwana-database-elt` menampilkan `raw_production`
- [x] Task 2: Buat user replikasi privilese terbatas (read-only) + whitelist 23 tabel eksplisit di Postgres — Acceptance: user ada, hanya bisa akses 23 tabel whitelist — Verify: `scripts/extract/setup_extract_role.py` — 4 check OK (2 whitelisted SELECT sukses, akses non-whitelist & INSERT ditolak), 23/23 grant count cocok
- [ ] Task 3: `scripts/extract/` — koneksi psycopg2 ke primary via user replikasi Task 2, skrip ekstraksi generik yang push ke BigQuery — Acceptance: 1 tabel percobaan berhasil sinkron end-to-end — Verify: row count BigQuery cocok sumber — M
- [ ] Task 4: Tabel state cursor (`monitoring.extract_cursor`) + logic `WHERE pk > last_cursor` — Acceptance: cursor tersimpan & terbaca ulang antar-run — Verify: 2x run berturutan, run kedua hanya proses baris baru — S
- [ ] Task 5: Skema raw 1:1 untuk 23 tabel + kolom metadata (`_synced_at`) di BigQuery — Acceptance: 23 tabel raw ada, kolom identik + metadata — Verify: `bq show` tiap tabel vs skema sumber — L → pecah per 6 schema production
- [ ] Task 6: Partitioning per tabel raw sesuai kolom tanggal relevan — Acceptance: tabel ter-partition — Verify: `bq query --dry_run` menunjukkan partition pruning — M
- [ ] Task 7: Sync awal (full load) 23 tabel + validasi row count vs sumber — Acceptance: row count cocok persis pada snapshot sama — Verify: query count kedua sisi — M
- [ ] Task 8: Uji coba terkontrol cursor tracking — insert baris uji coba ke schema `_simulation`, jalankan sync kedua, buktikan hanya baris baru yang masuk — Acceptance: delta count cocok jumlah baris uji coba — Verify: log sync + query BigQuery — S
- [ ] Task 9: Uji privilese user replikasi — akses ke tabel di luar whitelist harus ditolak — Acceptance: percobaan akses gagal — Verify: uji coba langsung — S
- [ ] Task 10: Jadwalkan job ekstraksi lewat GitHub Actions (`extract-*.yml`, mengikuti `docs/05-orchestrator/konvensi-job-dependency.md`) — Acceptance: job jalan terjadwal — Verify: run history — S
- [ ] Task 11: Dokumentasi + verifikasi Kriteria Keberhasilan (termasuk gap read replica & sandbox BigQuery) + `logs.md`/`report.md` — Acceptance: semua KK sumber dicek eksplisit, gap dicatat jelas — Verify: `report.md` — S

**Checkpoint** setelah Task 4: kalau cursor tracking tidak terbukti benar untuk 1 tabel percobaan, Task 5-8 (skema penuh 23 tabel) belum ada gunanya dikerjakan.

## Technical Decisions

### Decision: Sumber ekstraksi — koneksi langsung primary (psycopg2), bukan Read Replica

- **Context:** Kriteria Keberhasilan sumber eksplisit minta ekstraksi dari read replica. Supabase Read Replica adalah fitur berbayar (plan Pro+), sementara CDC/logical replication slot gratis (fitur inti Postgres, beda infrastruktur).
- **Decision:** Koneksi langsung ke primary lewat `psycopg2`, pola sama seperti `SUPABASE_DB_URL` yang sudah dipakai `scripts/monitoring`/`scripts/dq`. Bukan Supabase REST/PostgREST API (dipertimbangkan, ditolak karena jauh lebih lambat untuk 2.53M baris dibanding SQL langsung).
- **Konsekuensi eksplisit:** Kriteria Keberhasilan #2 ("tervalidasi lewat read replica") **tidak terpenuhi literal** — dicatat sebagai gap di `report.md`, mirip pola M1.5 (kanal notifikasi ditunda, dilaporkan Partially Completed untuk poin itu, bukan disembunyikan).
- **Alternatives considered:** Upgrade Supabase ke plan Pro+ untuk replica sungguhan; Supabase REST/PostgREST API.
- **Rejected because:** replica sungguhan menambah biaya bulanan yang tidak sepadan untuk portofolio; REST API terlalu lambat untuk volume data ini.

### Decision: Strategi incremental — cursor tracking custom, bukan CDC

- **Context:** Tidak ada kolom `updated_at` di 23 tabel, dan data production statis (bukan live stream). CDC (`wal_level=logical`) dikonfirmasi gratis tapi effort implementasi manual jauh lebih besar (parsing `pgoutput`/`wal2json`).
- **Decision:** Cursor tracking custom — tiap tabel dilacak lewat kolom primary key di tabel state `monitoring.extract_cursor`, tiap sync query `WHERE <pk> > last_cursor ORDER BY <pk>`.
- **Konsekuensi eksplisit:** Hanya menangkap baris **baru** (INSERT) — tidak menangkap UPDATE ke baris lama, beda dari CDC yang menangkap keduanya. Diterima sebagai batasan sadar karena data production di sini memang statis (tidak ada UPDATE nyata untuk ditangkap sampai batas manapun juga).
- **Alternatives considered:** CDC via `wal_level=logical` + Airbyte/Debezium; CDC manual via `psycopg2.extras.LogicalReplicationConnection`.
- **Rejected because:** kompleksitas implementasi tidak sepadan dengan manfaatnya untuk dataset yang secara faktual statis — cursor tracking sudah cukup membuktikan mekanisme "incremental" tanpa over-engineering.

### Decision: Tool ekstraksi — Custom Python

- **Context:** Tiga opsi dipertimbangkan (Airbyte OSS self-host, Airbyte Cloud, custom Python), konsisten dengan pertanyaan yang sama di M2.0 (orchestrator) soal biaya/dependency vendor.
- **Decision:** Custom Python di `scripts/extract/`, konsisten pola `scripts/monitoring`/`scripts/dq`. Sudah tidak butuh CDC connector (Airbyte) karena keputusan strategi incremental di atas.
- **Alternatives considered:** Airbyte OSS (perlu hosting sendiri, overkill untuk cursor tracking sederhana); Airbyte Cloud (terikat free/trial tier vendor pihak ketiga, pola sama seperti opsi orchestrator managed yang ditolak di M2.0).
- **Rejected because:** custom Python cukup untuk cursor tracking + push ke BigQuery, tanpa menambah dependency infra/vendor baru.

### Decision: GCP project baru `nirwana-database-elt`, BigQuery Sandbox mode (tanpa billing)

- **Context:** Project GCP lama (`nirwana-data-platform`) ternyata project latihan lama milik user, tidak dipakai. Perlu project baru. Billing account belum dihubungkan.
- **Decision:** Project baru `nirwana-database-elt`, dataset `raw_production` (region US), berjalan di **BigQuery Sandbox mode** (tanpa billing account) untuk saat ini.
- **Konsekuensi eksplisit (ditemukan otomatis oleh GCP, bukan dikonfigurasi manual):** dataset punya `defaultTableExpirationMs`/`defaultPartitionExpirationMs` = 60 hari — ini batasan bawaan Sandbox mode, tabel/partition akan otomatis expire kalau tidak ada billing dihubungkan. Perlu direvisit sebelum Milestone 2.1 dianggap "selesai penuh untuk jangka panjang" — cukup untuk uji coba & pembuktian mekanisme, tidak untuk retensi permanen.
- **Alternatives considered:** Pakai `nirwana-data-platform` yang sudah ada; hubungkan billing dari awal.
- **Rejected because:** project lama bukan milik pekerjaan ini (project latihan terpisah); billing ditunda dulu sampai jelas kebutuhan skala sungguhan (konsisten prinsip "jangan keluar biaya sebelum kebutuhan real dibuktikan" yang juga dipakai di keputusan orchestrator M2.0).

### Decision: Service account `extract-writer` — least privilege di level dataset, key file dibuat manual oleh user

- **Context:** Service account untuk `scripts/extract/` butuh akses tulis ke BigQuery. Percobaan awal memberi role `bigquery.dataEditor` di level **project** (akses ke seluruh dataset, termasuk yang akan ada nanti seperti `staging`/`mart_cleaned` di milestone selanjutnya) — dikoreksi ke scope **dataset** (`raw_production` saja) via dataset ACL (`bq update` dengan access list, karena `bq add-iam-policy-binding` level-dataset butuh allowlisting yang tidak tersedia). Percobaan membuat *key file* JSON untuk service account ini **diblokir otomatis** oleh classifier keamanan sesi (kredensial jangka panjang, sensitif).
- **Decision:** Service account `extract-writer@nirwana-database-elt.iam.gserviceaccount.com` — `WRITER` di dataset ACL `raw_production` saja + `roles/bigquery.jobUser` di level project (wajib untuk menjalankan job, tidak memberi akses data). Key file JSON dibuat **manual oleh user** lewat `gcloud iam service-accounts keys create` di terminal mereka sendiri, bukan oleh assistant — konsisten prinsip project ini yang menghindari penanganan kredensial mentah oleh pihak ketiga/otomatis.
- **Alternatives considered:** `bigquery.dataEditor` di level project (lebih sederhana, ditolak karena scope kelebihan); Application Default Credentials (ADC) interaktif untuk lokal + key file terpisah nanti untuk GitHub Actions saja.
- **Rejected because:** project-level role melanggar least-privilege yang sudah jadi pola konsisten di project ini (whitelist tabel M2.1, read-only role M1.6). Key file dibuat user sendiri karena pembuatan kredensial oleh assistant dianggap aksi sensitif yang lebih aman diserahkan ke user secara eksplisit.

## Open Questions Resolved with User

- Q: Sumber ekstraksi (read replica vs alternatif)? → A: Koneksi langsung primary + cursor tracking, bukan replica/REST API.
- Q: Strategi incremental (CDC vs alternatif)? → A: Cursor tracking custom berbasis primary key, bukan CDC (meski CDC dikonfirmasi gratis).
- Q: Tool ekstraksi? → A: Custom Python.
- Q: GCP project apa yang dipakai? → A: Project baru `nirwana-database-elt` (bukan `nirwana-data-platform` lama).
- Q: Billing GCP? → A: BigQuery Sandbox mode dulu (tanpa billing), dengan catatan batas retensi 60 hari.
- Q: Siapa yang generate key file service account? → A: User sendiri, manual.
