# Data Profiling Findings — 23 Tabel Production (Pra-Milestone 2.2)

**Dikerjakan:** 2026-08-08, sebelum `decisions.md` Milestone 2.2 ditulis.
**Sumber data:** `raw_production` (via koneksi langsung Postgres, role `extract_reader`) — hasil sinkron Milestone 2.1, terverifikasi 1:1 dengan production.
**Metodologi:** `scripts/profiling/profile_tables.py` (per kolom: null count/pct, distinct count, whitespace/case-variant detection untuk teks, min/max/negative count untuk angka, deteksi duplikat full-row) dijalankan ke seluruh 23 tabel, hasil mentah di `scripts/profiling/output/profile_20260808T013253Z.json`. Diikuti beberapa query manual bertarget untuk kasus yang tidak bisa ditangkap pemeriksaan generik (dijelaskan di bagian Metodologi & Keterbatasan).

**Kenapa dokumen ini ada:** `docs/01-architecture/Metadata.md` sudah mendokumentasikan pola dirty-data yang disengaja. Dokumen ini adalah verifikasi independen terhadap data sungguhan — tujuannya membuktikan (bukan mengasumsikan) bahwa dokumentasi itu akurat, dan menangkap apa pun yang mungkin terlewat. Dipakai sebagai input `decisions.md` Milestone 2.2, bukan pengganti `Metadata.md`.

---

## 1. Konfirmasi — Sesuai Dokumentasi

Temuan berikut cocok persis atau mendekati `Metadata.md`:

| Tabel.Kolom | Dokumentasi | Hasil Profiling | Status |
|---|---|---|---|
| `employees.role_title` | ~2% kosong | 15/755 = 1.99% null | ✅ Cocok persis |
| `employees.department` | 19 variasi tulisan untuk 8 departemen | 19 distinct, 7 case-variant group, 11 baris whitespace issue | ✅ Cocok, lihat catatan §3 |
| `employees.full_name` | ~2% whitespace berlebih | 11/755 = 1.46% | ✅ Mendekati (dokumentasi approximate) |
| `employees.hire_date` | ~2% format `DD/MM/YYYY` | Kolom tersimpan sebagai `text` (bukan `date`) — konsisten dengan format campuran | ✅ Konsisten |
| `guests.email` | ~4% kosong | 989/24893 = 3.97% null | ✅ Cocok persis |
| `guests.phone` | ~3% kosong | 750/24893 = 3.01% null | ✅ Cocok persis |
| `guests` 367 baris duplikat (guest_id G24501+) | 367 baris | 393 baris dengan `guest_id >= G24501`, **368 di antaranya** punya `full_name` (case/trim-insensitive) yang cocok dengan guest lain ber-ID lebih awal | ✅ Cocok (selisih 1 diabaikan, kemungkinan boundary counting) — **kunci pencocokan adalah `full_name` saja**, bukan kombinasi dengan email/phone (yang sengaja dibuat beda untuk simulasi re-entry) |
| `properties.star_rating` | Kosong untuk P06 (kantor pusat) | 1/6 = 16.67% null | ✅ Cocok |
| `fnb_transactions.guest_id` | ~31% kosong (walk-in) | 280.359/902.574 = 31.06% null | ✅ Cocok persis |
| `spa_bookings.guest_id` | ~21% kosong (walk-in) | 27.057/127.890 = 21.16% null | ✅ Cocok persis |
| `maintenance_tickets.room_id` | 27,54% kosong (bermakna) | 3.722/13.514 = **27.54%** | ✅ Cocok persis (2 desimal) |
| `maintenance_tickets.parts_replaced` | 52,21% kosong | 7.055/13.514 = **52.21%** | ✅ Cocok persis (2 desimal) |
| `staff_shifts.clock_in`/`clock_out` | 100% kosong utk absent/leave | Keduanya persis 42.418/610.019 = 6.95% null (angka identik utk kedua kolom) | ✅ Konsisten internal |

Tidak ditemukan duplikat full-row (semua kolom identik) di 23 tabel manapun — diharapkan karena setiap tabel punya PK/near-PK unik (lihat keterbatasan metodologi §4 soal kenapa ini tidak otomatis membuktikan tidak ada duplikat *bermakna*, seperti kasus `guests` di atas).

---

## 2. Temuan Baru / Koreksi Terhadap Dokumentasi

Ini bagian paling penting dari observability pass ini — hal yang **tidak eksplisit** atau **kurang tepat** di `Metadata.md`, ditemukan lewat verifikasi langsung ke data:

### 2.1 `payroll.thr` dan `financial_summary.gop`/`undistributed_expense` — "kosong" ternyata **nol, bukan NULL**

`Metadata.md` menyiratkan kolom ini kosong/tidak terisi di luar kondisi tertentu (`thr` "hanya terisi 1x/tahun di Maret"; `gop`/`undistributed_expense` "hanya terisi di baris `department='Overall'`"). Profiling menunjukkan **null_count = 0** untuk ketiganya di seluruh baris — bukan NULL sama sekali. Verifikasi lanjutan (`GROUP BY` bulan/departemen):

- `payroll.thr`: bulan 01–12 kecuali Maret ('03') → **100% baris bernilai tepat 0**. Maret → 1925/1954 baris (98.5%) bernilai bukan-nol.
- `financial_summary.gop`/`undistributed_expense`: departemen `F&B`, `Room`, `Spa&Event` → **100% baris bernilai tepat 0**. Departemen `Overall` dan `Corporate Overhead` → 100% baris bernilai bukan-nol (termasuk negatif, wajar untuk P&L).

**Dampak untuk Milestone 2.2:** Logic apa pun di staging/downstream yang berasumsi "kolom ini NULL kalau tidak berlaku" (mis. `WHERE gop IS NOT NULL`) akan salah — harus filter eksplisit by `department IN ('Overall', 'Corporate Overhead')` atau bulan Maret, bukan null-check. Bukan kesalahan data (nilai 0 valid sebagai representasi "tidak berlaku" versi sistem sumber), tapi kesalahan asumsi kalau staging ditulis berdasar bacaan literal `Metadata.md` tanpa verifikasi ini.

### 2.2 `financial_summary` — bukan cuma `department='Overall'` yang punya angka P&L nyata

`Metadata.md` hanya menyebut `department='Overall'`. Profiling menemukan **`department='Corporate Overhead'` juga punya nilai `gop`/`undistributed_expense` nyata** (36 baris, seluruhnya non-zero, rentang -1,37M hingga -405jt — masuk akal sebagai biaya overhead, selalu negatif). Ditelusuri lebih lanjut: `Corporate Overhead` **hanya muncul untuk `property_id='P06'`** (kantor pusat), sementara `Overall` hanya muncul untuk 5 properti hotel (P01–P05). Artinya P06 memakai nama departemen berbeda ("Corporate Overhead") sebagai padanan "Overall"-nya sendiri, konsisten dengan P06 yang memang tidak punya F&B/Room/Spa&Event (sudah didokumentasikan di tabel `properties`, tapi keterkaitannya ke `financial_summary` belum eksplisit ditulis di `Metadata.md`).

**Dampak untuk Milestone 2.2:** Aturan filter "ambil baris `Overall` untuk baca P&L hotel" harus diperluas jadi "`Overall` ATAU `Corporate Overhead`, tergantung `property_id`" — kalau tidak, P&L kantor pusat (P06) akan selalu hilang dari hasil manapun yang mengikuti definisi literal dokumen.

### 2.3 `guests.nationality` — jauh lebih kotor dari perkiraan dokumen

`Metadata.md` hanya menyebut "~3% kapitalisasi tidak konsisten". Profiling menemukan:
- **466 nilai distinct** untuk kolom yang secara bisnis seharusnya ≤ ~195 (jumlah negara di dunia).
- **362 baris** (bukan kolom, tapi baris) dengan whitespace issue (leading/trailing space).
- **156 case-variant group** — 156 nilai "dasar" (setelah lower+trim) yang masing-masing punya ≥2 variasi penulisan berbeda.

Ini jauh lebih besar dari kesan "~3%" di dokumen — 156 group varian dari total 466 nilai distinct berarti **lebih dari sepertiga nilai distinct** terlibat masalah normalisasi, bukan minoritas kecil.

**Dampak untuk Milestone 2.2:** Kalau `nationality` termasuk kolom yang perlu dinormalisasi di staging (perlu keputusan eksplisit di `decisions.md`), normalisasi sederhana (`LOWER(TRIM())`) kemungkinan **tidak cukup** — 466 distinct vs 156 case-variant-group berarti ada variasi lain di luar case/whitespace (kemungkinan typo, singkatan berbeda, atau penulisan bahasa campuran) yang butuh mapping manual/fuzzy-matching, bukan cuma normalisasi mekanis.

### 2.4 `fnb_transactions.transaction_id` bukan pengenal baris unik

Sudah diketahui dari M2.1 bahwa tabel ini **tidak punya primary key sama sekali**. Profiling menambah detail: `transaction_id` sendiri **tidak unik** — 387.972 nilai distinct dari 902.574 baris (rata-rata ~2,33 baris per `transaction_id`). Pola ini konsisten dengan satu transaksi F&B berisi beberapa item (satu baris per item, `transaction_id` sama). Tidak eksplisit disebutkan di `Metadata.md`.

**Dampak untuk Milestone 2.2/2.3:** Kalau `mart_cleaned.fnb_transactions` atau layer berikutnya butuh row-level unique key, `transaction_id` sendirian tidak cukup — perlu kombinasi (`transaction_id`, `item_name`) atau surrogate key baru. Perlu keputusan eksplisit, bukan asumsi implisit.

---

## 3. Catatan Tambahan (Bukan Masalah, Tapi Perlu Diketahui)

- `employees.department`: 19 nilai distinct tapi cuma 7 case-variant group — artinya **sisa variasi bukan cuma beda kapitalisasi**, ada kemungkinan singkatan/ejaan berbeda juga (mis. "F&B" vs "FnB" vs "F & B"). Normalisasi department butuh mapping tabel eksplisit (8 nilai kanonik → 19 variasi), bukan cuma `LOWER(TRIM())`.
- `staff_shifts.clock_in`/`clock_out`: null count identik persis (42.418) untuk kedua kolom — bagus, konsisten secara internal dengan penjelasan "kosong bersamaan untuk status absent/leave".
- `financial_summary.departmental_profit`: 76/756 baris bernilai negatif — wajar (departemen rugi di periode tertentu), bukan anomali.
- `maintenance_tickets.resolved_date`: hanya 17/13.514 (0.13%) NULL — sangat sedikit tiket yang masih `open`/`in-progress` di snapshot ini, sesuai ekspektasi data historis yang hampir seluruhnya sudah selesai.

---

## 4. Metodologi & Keterbatasan

- **Deteksi duplikat full-row otomatis (`GROUP BY` seluruh kolom) tidak bisa menangkap kasus `guests`** karena PK (`guest_id`) selalu ikut serta dalam pembandingan — dua baris "duplikat" secara bisnis (orang sama, ID beda) tidak akan pernah dianggap identik oleh pemeriksaan generik ini. Butuh query bertarget per tabel (dilakukan manual untuk `guests` di sesi ini) — kalau tabel lain punya pola serupa (entitas sama, ID beda), ini **tidak akan otomatis ketahuan** dari `profile_tables.py` saja.
- **Deteksi format teks** (mis. 4 variasi format telepon `guests.phone`) belum diimplementasikan sebagai regex classifier di `profile_tables.py` — hanya null-check yang dijalankan untuk kolom ini. Kesesuaian dengan "4 variasi format" di `Metadata.md` **belum diverifikasi independen**, hanya diterima dari dokumentasi. Kalau Milestone 2.2 perlu menormalisasi `phone`, sebaiknya jalankan sampling manual dulu untuk memastikan pola formatnya.
- **Deteksi typo nama** (`guests.full_name` ~2%, `employees.full_name`) tidak bisa diverifikasi otomatis — tidak ada cara generik membedakan nama valid vs typo tanpa kamus rujukan. Diterima dari dokumentasi apa adanya.
- Profiling dijalankan terhadap `raw_production` (BigQuery) secara tidak langsung — query sebenarnya jalan ke Postgres (`EXTRACT_DB_URL`), bukan BigQuery, karena hasilnya seharusnya identik (M2.1 sudah membuktikan row-count parity 23/23) dan query analitik jauh lebih murah/cepat di Postgres untuk kebutuhan eksploratif seperti ini.

---

## 5. Item yang Perlu Keputusan Eksplisit di `decisions.md` Milestone 2.2

1. `financial_summary`: aturan filter P&L per properti harus menyertakan `Corporate Overhead` untuk P06, tidak cukup `Overall` saja.
2. `payroll.thr`, `financial_summary.gop`/`undistributed_expense`: dokumentasikan eksplisit di staging bahwa "tidak berlaku" = 0, bukan NULL — supaya tidak ada test/business-rule yang salah asumsi NULL.
3. `nationality`: putuskan apakah normalisasi case/whitespace saja (cakupan sebagian, 156 dari 466 distinct) atau perlu mapping lebih menyeluruh (cakupan lebih besar, effort lebih tinggi).
4. `department`: pastikan mapping normalisasi berbasis tabel referensi 19→8, bukan fungsi mekanis `LOWER(TRIM())` semata.
5. `fnb_transactions`: putuskan definisi row-level key untuk layer berikutnya (`transaction_id`+`item_name` composite, atau surrogate key baru).
