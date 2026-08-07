# Milestone 1.4: Monitoring Perubahan Struktur (Schema Drift)

**Source:** docs/03-implementation-plans/01-monitoring-data-production-fase1.md (baris 99-114)
**Status:** Done
**Date started:** 2026-08-07

## Contract (from source doc)

- **Lingkup:** Deteksi perubahan struktur tabel production tanpa pemberitahuan — kolom baru, kolom dihapus, tipe data berubah. Termasuk alur notifikasi (bukan auto-diteruskan tanpa review), khususnya untuk kolom baru yang berpotensi memuat data sensitif.
- **Output:** Mekanisme deteksi perubahan skema; alur notifikasi ke tim yang tepat.
- **Kriteria keberhasilan:** Perubahan skema buatan (uji coba terkontrol) berhasil terdeteksi & memicu notifikasi; tidak ada perubahan skema yang otomatis diteruskan tanpa jejak/notifikasi.
- **Independen penuh** dari Milestone 1.2 & 1.3 — soal bentuk data, bukan isi.

## Task Breakdown

- [x] Task 1: Baseline awal — snapshot `information_schema.columns` 23 tabel ke `monitoring.schema_column_baseline`, status `approved` — Acceptance: 23/23 tabel & seluruh kolomnya terekam — Verify: `COUNT(DISTINCT schema_name, table_name)` = 23 (165 kolom)
- [x] Task 2: Schema penyimpanan drift event (`monitoring.schema_drift_events`) — Acceptance: tabel terbentuk dengan kolom drift_type/severity/status — Verify: `information_schema` menunjukkan tabel ada
- [x] Task 3: Keyword heuristik sensitif — Acceptance: fungsi `classify_severity` bisa dites langsung — Verify: manual test beberapa nama kolom, sesuai ekspektasi
- [x] Task 4: Snapshot + diff engine — bandingkan snapshot terkini vs baseline `approved` — Acceptance: 3 jenis drift (kolom baru/hilang/tipe berubah) terdeteksi — Verify: uji coba terkontrol Task 6 (4/4 jenis terdeteksi benar)
- [x] Task 5: Alur acknowledgment — Acceptance: acknowledge satu event memperbarui baseline; yang belum di-acknowledge tetap pending — Verify: 2 run berturutan, event yang belum direview tidak hilang
- [x] Task 6: Uji coba terkontrol — ALTER TABLE di tabel staging terpisah (schema `_simulation`) — Acceptance: semua skenario (tambah kolom biasa, tambah kolom sensitif, hapus kolom, ubah tipe) terdeteksi + severity benar — Verify: query `schema_drift_events` (5/5 skenario PASS)
- [x] Task 7: Verifikasi Kriteria Keberhasilan — Acceptance: kedua kriteria dicek eksplisit — Verify: query antrian review menunjukkan 3 drift simulasi masih pending
- [x] Task 8: Tulis `logs.md`/`report.md`

**Checkpoint** setelah Task 1: baseline yang diambil sekarang jadi acuan "disetujui" untuk seluruh milestone.

## Technical Decisions

### Decision: Metode deteksi — snapshot + diff, dipicu waktu nyata (bukan event trigger, bukan terikat generator)

- **Context:** Dua sumbu keputusan bercampur di sini: (a) mekanisme deteksi (snapshot-diff vs Postgres native event trigger), (b) kapan mekanisme itu dijalankan (waktu nyata vs terikat siklus generator data sintetis proyek ini, yang bisa memasukkan banyak "hari" bisnis dalam hitungan detik waktu nyata).
- **Decision:**
  1. **Mekanisme**: snapshot `information_schema.columns` + diff terhadap baseline tersimpan — pola sama seperti `monitoring.volume_daily_snapshot` (M1.2) dan `monitoring.dq_test_results` (M1.3).
  2. **Waktu pemicu**: real-world time, terpisah dari generator. ALTER TABLE adalah aksi manual/deliberate yang jarang terjadi — tidak ada alasan mengaitkannya dengan kecepatan generator mengisi data bisnis (yang mengisi banyak "hari" sintetis dalam hitungan detik waktu nyata, tapi itu soal volume baris, bukan struktur tabel).
- **Alternatives considered:** Postgres `CREATE EVENT TRIGGER` (deteksi seketika saat DDL dieksekusi).
- **Rejected because:** diverifikasi read-only bahwa role koneksi kita (`postgres` via Supabase pooler) **bukan superuser** (`rolsuper=False`). `CREATE EVENT TRIGGER` di Postgres standar butuh superuser, dan Supabase managed Postgres lazim membatasi ini untuk role standar demi isolasi multi-tenant — kemungkinan besar tidak bisa dipakai tanpa akses yang tidak kita miliki. Snapshot-diff tidak butuh privilege khusus (sudah terbukti jalan di M1.2/M1.3) dan cukup memadai karena perubahan skema jarang terjadi & deliberate — deteksi "saat snapshot berikutnya jalan" (bukan seketika) adalah trade-off yang wajar.

### Decision: Cakupan — kolom di 23 tabel yang sudah dikenal

- **Context:** Dokumen sumber literal menyebut "kolom baru ditambahkan, kolom dihapus, tipe data berubah" — tidak menyebut tabel baru/hilang di level schema.
- **Decision:** Deteksi dibatasi ke kolom dalam 23 tabel yang sudah terdaftar (dari `docs/04-monitoring/baseline-inventaris-produksi.md`). Tabel baru/hilang di 6 schema production **tidak** dicakup.
- **Alternatives considered:** Perluas ke deteksi tabel baru/hilang juga (query `information_schema.tables` selain `.columns`).
- **Rejected because:** user memilih tetap fokus ke lingkup literal dokumen, konsisten dengan cara M1.1-1.3 membatasi scope ke yang eksplisit diminta — bisa diperluas nanti tanpa mengubah desain inti kalau dibutuhkan.

### Decision: Model baseline — baseline tetap + acknowledgment eksplisit

- **Context:** Kriteria Keberhasilan eksplisit: "tidak ada perubahan skema yang otomatis diteruskan tanpa jejak/notifikasi". Day-over-day diff (bandingkan snapshot kemarin vs hari ini, pola M1.2 untuk volume) berisiko "melupakan" drift yang sudah terjadi begitu snapshot pembanding berpindah ke hari berikutnya, walau belum ada manusia yang me-review-nya.
- **Decision:** Baseline diambil sekali di awal (`monitoring.schema_column_baseline`, status `approved`). Setiap snapshot berikutnya dibandingkan ke baseline **approved** ini (bukan ke snapshot hari sebelumnya). Drift baru masuk `monitoring.schema_drift_events` berstatus `pending`. Status `pending` **tidak hilang** sampai ada aksi eksplisit `acknowledge` (yang lalu memperbarui baseline dengan kolom yang di-acknowledge itu).
- **Alternatives considered:** Day-over-day diff sederhana.
- **Rejected because:** day-over-day tidak menjamin "jejak" bertahan — kalau drift terjadi lalu tidak direview, run berikutnya akan membandingkan ke snapshot yang *sudah* memuat drift itu, sehingga drift dianggap "normal" dan hilang dari radar. Baseline tetap + acknowledgment memaksa setiap drift punya jejak eksplisit sampai ada manusia yang menyatakan "sudah saya lihat, ini bukan masalah" — cocok dengan tuntutan "bukan otomatis diteruskan tanpa review" di lingkup dokumen.

### Decision: Heuristik sensitif — keyword matching pada nama kolom

- **Context:** Dokumen sumber eksplisit minta perhatian lebih untuk "kolom baru yang berpotensi memuat data sensitif", tapi tidak menentukan caranya.
- **Decision:** Daftar keyword (password, nik, ktp, salary/gaji, email, phone/telepon, token, secret, ssn, credit_card, rekening, no_hp, dst) dicocokkan (case-insensitive, substring) ke nama kolom baru. Kolom yang cocok mendapat `severity=high` di `schema_drift_events`; yang tidak cocok `severity=normal`. Ini **hanya memprioritaskan urutan review**, bukan keputusan otomatis approve/reject.
- **Alternatives considered:** Tanpa klasifikasi otomatis — semua kolom baru severity sama.
- **Rejected because:** tidak memenuhi penekanan eksplisit dokumen soal kolom sensitif butuh perhatian lebih. Keyword list terinspirasi dari domain sensitif yang sudah ada di `role_permissions` (`guests_pii`, `financial`, `hr` — sensitivitas "Tinggi" di `Metadata.md`).

## Open Questions Resolved with User

- Q: Snapshot dipicu berdasar waktu nyata atau siklus generator? → A: Waktu nyata, terpisah dari generator (ALTER TABLE tidak terkait kecepatan data masuk).
- Q: Metode deteksi? → A: Snapshot + diff (event trigger tidak feasible — role bukan superuser).
- Q: Cakupan tabel baru/hilang ikut dicakup? → A: Tidak, hanya kolom di 23 tabel yang sudah dikenal.
- Q: Model baseline day-over-day atau tetap? → A: Baseline tetap + acknowledgment eksplisit.
- Q: Cara tandai kolom sensitif? → A: Keyword matching pada nama kolom.
