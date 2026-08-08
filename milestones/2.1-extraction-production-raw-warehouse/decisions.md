# Milestone 2.1: Extraction Production ke Raw Warehouse (Fase 2)

**Source:** `docs/03-implementation-plans/02-serving-data-scientist.md` (baris 64-81, "Milestone 2.1 — Extraction Production ke Raw Warehouse")
**Status:** Done (lihat `report.md` untuk verifikasi Kriteria Keberhasilan — Partially Completed, 3 gap eksplisit)
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
- [x] Task 3: `scripts/extract/` — koneksi psycopg2 ke primary via user replikasi Task 2, skrip ekstraksi generik yang push ke BigQuery — Acceptance: 1 tabel percobaan berhasil sinkron end-to-end — Verify: `corporate_master.properties`, 6/6 baris cocok sumber (dicek nilai, bukan cuma count)
- [x] Task 4: Tabel state cursor (`monitoring.extract_cursor`) + logic `WHERE pk > last_cursor` — Acceptance: cursor tersimpan & terbaca ulang antar-run — Verify: `fnb_outlets` run 1 = 17 baris (WRITE_TRUNCATE), run 2 = 0 baris (WRITE_APPEND, tidak mengambil ulang)
- [x] Task 5: Skema raw 1:1 untuk 23 tabel + kolom metadata (`_synced_at`) di BigQuery — Acceptance: 23 tabel raw ada, kolom identik + metadata — Verify: seluruh 23 tabel dibuat via autodetect load job, ditemukan & diperbaiki bug tipe `TIME` (`housekeeping_log.cleaning_start_time`/`cleaning_end_time`) yang tidak ter-handle `_json_safe` awal
- [~] Task 6: Partitioning per tabel raw sesuai kolom tanggal relevan — **Blocked oleh batasan BigQuery Sandbox mode, dicoba lalu di-revert** — lihat Technical Decision "Partitioning per kolom tanggal bisnis tidak bisa dilakukan tanpa billing" untuk insiden lengkap & keputusan akhir
- [x] Task 7: Sync awal (full load) 23 tabel + validasi row count vs sumber — Acceptance: row count cocok persis pada snapshot sama — Verify: script pembanding `COUNT(*)` Postgres vs BigQuery per tabel — **23/23 OK, seluruh baris cocok persis** (total ~2.529.584 baris, sesuai `CLAUDE.md` "~2.53M rows")
- [x] Task 8: Uji coba terkontrol cursor tracking — insert baris uji coba langsung ke `fnb_outlets` (bukan schema `_simulation` terpisah -- tabel sudah cukup kecil/aman untuk insert+cleanup terkontrol via admin connection) — Acceptance: delta count cocok jumlah baris uji coba — Verify: insert `OUT018` -> sync mendeteksi tepat 1 baris baru (18 total), cleanup (delete Postgres + reset cursor + full re-sync) -> BigQuery kembali 17 baris bersih. **Temuan penting:** BigQuery Sandbox mode (tanpa billing) tidak mengizinkan DML (`UPDATE`/`DELETE`) langsung — cleanup harus lewat reset cursor + `WRITE_TRUNCATE` full reload, bukan `DELETE` biasa
- [x] Task 9: Uji privilese user replikasi — akses ke tabel di luar whitelist harus ditolak — Acceptance: percobaan akses gagal — Verify: sudah terverifikasi di Task 2 (`setup_extract_role.py` — SELECT `monitoring.alerts` & INSERT keduanya ditolak), tidak diulang
- [x] Task 10: Jadwalkan job ekstraksi lewat GitHub Actions (`.github/workflows/extract-production.yml`, cron harian 03:00 UTC + `workflow_dispatch`) — Acceptance: job jalan terjadwal — Verify: trigger manual, run [`31232217473`](https://github.com/Ardiyanto24/nirwana-database/actions/runs/31232217473) sukses — cursor tracking terbukti benar di CI (0 baris baru untuk tabel `pk`/`date`, full_refresh table re-sync seperti seharusnya)
- [x] Task 11: Dokumentasi + verifikasi Kriteria Keberhasilan (termasuk gap read replica, CDC, & partitioning) + `logs.md`/`report.md` — Acceptance: semua KK sumber dicek eksplisit, gap dicatat jelas — Verify: `report.md`

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

### Decision: BigQuery Sandbox mode — load jobs (WRITE_TRUNCATE/WRITE_APPEND) saja, tidak ada DML

- **Context:** Ditemukan saat cleanup uji coba terkontrol Task 8 — BigQuery Sandbox mode (tanpa billing) menolak query DML (`UPDATE`/`DELETE`) dengan pesan eksplisit "DML queries are not allowed in the free tier". Ini tambahan atas batasan yang sudah diketahui sebelumnya (60 hari retensi tabel/partition).
- **Decision:** Seluruh mekanisme sync di `scripts/extract/extract.py` sengaja hanya memakai **load job** (`client.load_table_from_file` dengan `WRITE_TRUNCATE`/`WRITE_APPEND`), tidak pernah DML — jadi batasan ini secara kebetulan tidak menghalangi jalur produksi normal, hanya menghalangi cleanup manual ad-hoc (diselesaikan lewat reset cursor + full reload, bukan `DELETE`).
- **Konsekuensi eksplisit:** kalau nanti butuh operasi row-level yang benar-benar butuh DML (mis. hapus baris tertentu tanpa reload seluruh tabel), itu tidak bisa dilakukan tanpa mengaktifkan billing. Dicatat sebagai batasan Sandbox mode, bukan bug.
- **Alternatives considered:** N/A — temuan, bukan pilihan desain.

### Decision: Partitioning per kolom tanggal bisnis tidak bisa dilakukan tanpa billing — Task 6 dihentikan, gap didokumentasikan

- **Context:** Percobaan pertama mem-partisi 11 tabel (yang punya kolom DATE/TIMESTAMP asli — lihat `scripts/extract/partition_tables.py`) via `CREATE TABLE ... PARTITION BY <kolom tanggal bisnis>` **menyebabkan kehilangan data masif** di seluruh 11 tabel (mis. `bookings` dari 217.654 jadi 1.958 baris, `staff_shifts` dari 610.019 jadi 12.968). Root cause: dataset `raw_production` (BigQuery Sandbox mode, tanpa billing) punya `defaultPartitionExpirationMs` = 60 hari yang **wajib** ada di Sandbox mode (`bq update --default_partition_expiration=0` ditolak eksplisit: "The default table expiration time must be less than 60 days"). Untuk tabel partisi berbasis **kolom tanggal bisnis** (bukan waktu ingest), BigQuery menghitung expirasi tiap partisi relatif ke **nilai tanggal partisi itu sendiri** — karena data production di sini historis (`CLAUDE.md`: static synthetic snapshot, banyak baris bertanggal jauh lebih dari 60 hari sebelum hari ini secara real-world), hampir seluruh partisi langsung dianggap kedaluwarsa begitu tabel dibuat.
- **Recovery:** 11 tabel partisi yang rusak di-drop, cursor state di-reset (`DELETE FROM monitoring.extract_cursor`), re-sync penuh dari Postgres via `extract.py` (tanpa partitioning). Row count parity 23/23 diverifikasi ulang — **semua kembali cocok 100%**, tidak ada data yang benar-benar hilang secara permanen (sumber Postgres tidak tersentuh sama sekali).
- **Decision:** Task 6 **tidak dilanjutkan** dengan partitioning kolom tanggal bisnis di milestone ini. Seluruh 23 tabel `raw_production` tetap **tanpa partitioning** (unpartitioned) untuk saat ini.
- **Konsekuensi eksplisit:** Kriteria "tabel ter-partition" (Output milestone sumber) **tidak terpenuhi** — dicatat sebagai gap eksplisit di `report.md`, seperti gap read replica & CDC.
- **Alternatives considered:** (1) Ingestion-time partitioning (partisi berdasar `_PARTITIONTIME`/waktu load, bukan kolom tanggal bisnis) — secara teknis menghindari masalah expirasi (karena expirasi dihitung dari waktu load = hari ini, bukan tanggal bisnis lama), tapi tidak memenuhi maksud asli dokumen sumber ("partitioning **sesuai kolom tanggal yang relevan**" — yang dimaksud adalah tanggal bisnis untuk query pruning yang berguna, bukan waktu sync). (2) Set `partition_expiration_days` eksplisit lebih besar per tabel — tidak mungkin, Sandbox mode membatasi keras di 60 hari untuk **seluruh** bentuk expirasi, tidak ada override per-tabel yang melampaui batas dataset.
- **Rejected because:** Ingestion-time partitioning akan memberi kesan "sudah dipartisi dengan benar" padahal tidak memenuhi tujuan query pruning berbasis tanggal bisnis yang sebenarnya diminta — lebih jujur mendokumentasikan gap ini apa adanya daripada memasang solusi yang secara teknis "partisi" tapi tidak berguna. **Revisit when:** billing GCP diaktifkan (lihat Decision "GCP project baru... BigQuery Sandbox mode" di atas) — begitu itu terjadi, `scripts/extract/partition_tables.py` (sudah ditulis & terbukti bekerja secara mekanis, hanya gagal karena expirasi) tinggal dijalankan ulang tanpa modifikasi.

## Open Questions Resolved with User

- Q: Sumber ekstraksi (read replica vs alternatif)? → A: Koneksi langsung primary + cursor tracking, bukan replica/REST API.
- Q: Strategi incremental (CDC vs alternatif)? → A: Cursor tracking custom berbasis primary key, bukan CDC (meski CDC dikonfirmasi gratis).
- Q: Tool ekstraksi? → A: Custom Python.
- Q: GCP project apa yang dipakai? → A: Project baru `nirwana-database-elt` (bukan `nirwana-data-platform` lama).
- Q: Billing GCP? → A: BigQuery Sandbox mode dulu (tanpa billing), dengan catatan batas retensi 60 hari.
- Q: Siapa yang generate key file service account? → A: User sendiri, manual.
