# Pemetaan Kebutuhan Data Scientist — Dasar Penentuan Skema `mart_cleaned`

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` |
| **Referensi silang** | Bagian 5.2 (definisi `mart_cleaned`) dan Bagian 10 No. 6 (area validasi) dokumen induk |
| **Tujuan dokumen** | Memetakan kebutuhan konkret Data Scientist sebagai dasar penentuan skema `mart_cleaned` |
| **Sumber data** | `Metadata.md` (data dictionary 6 database, 23 tabel) dan `DataSchema.md` (skema teknis) — Nirwana Hospitality Group |
| **Status** | Selesai dipetakan |

---

## Cara Membaca Dokumen Ini

Dokumen ini **tidak menggantikan** Bagian 5.2 dokumen arsitektur induk — dokumen ini adalah pekerjaan lanjutan yang secara eksplisit ditandai sebagai belum selesai di sana (lihat Bagian 10 No. 6). Hasil pemetaan ini dipakai untuk mengisi kembali detail skema `mart_cleaned` di dokumen induk.

Struktur dokumen:
1. **Prinsip desain** — batasan dan filosofi yang mengarahkan pemetaan (hasil klarifikasi dengan pemilik sistem)
2. **Kebutuhan konkret** — pemetaan tabel/kolom yang relevan
3. **Catatan implementasi** — hal yang perlu masuk ke dokumen arsitektur induk

---

## Pemetaan Kebutuhan: Data Scientist

### Prinsip Desain

| Prinsip | Penerapan |
|---|---|
| **Cleaning-only, tanpa feature engineering** | Data platform ini hanya bertanggung jawab membersihkan format data. Feature extraction/engineering sepenuhnya domain tim ML di sistem MLOps mereka sendiri, di luar data platform ini. |
| **1:1 dengan tabel sumber** | Setiap tabel production punya padanan `mart_cleaned.<nama_tabel>` — tidak digabung lintas domain, tidak dipecah ulang. Berlaku apapun granularitas aslinya di sumber (baik transaksi individual maupun tabel pre-aggregated seperti `daily_occupancy`). |
| **Missing value bermakna → dipertahankan** | Nilai kosong yang merepresentasikan kondisi bisnis nyata (mis. `guest_id` kosong untuk walk-in anonim) tidak diisi paksa dan tidak di-drop. |
| **Dirty data yang disengaja → dipertahankan** | Data quality issue yang sengaja disuntikkan sebagai simulasi kondisi nyata (duplicate rows, typo nama) dipertahankan apa adanya di `mart_cleaned`. Keputusan dedup/koreksi menjadi bagian dari eksperimen Data Scientist sendiri, bukan keputusan platform. |
| **Full history, tanpa windowing** | Konsisten dengan strategi reverse ETL full sync di Bagian 7.2 dokumen induk — tidak ada pembatasan rentang waktu. |

### Kebutuhan Konkret: 23 Tabel Sumber → 23 `mart_cleaned.<tabel>`

#### Database: `corporate_master`

| Tabel sumber | mart_cleaned | Cleaning spesifik |
|---|---|---|
| `properties` | `mart_cleaned.properties` | Tidak ada isu data kotor — disalin apa adanya |
| `employees` | `mart_cleaned.employees` | `full_name`: trim whitespace berlebih. `department`: normalisasi 19 variasi penulisan → 8 nilai baku (`.strip().lower()` lalu mapping ke Title Case standar). `hire_date`: standarkan semua ke ISO `YYYY-MM-DD` (dari campuran dengan `DD/MM/YYYY`). `role_title` kosong (~2%): **dipertahankan**, tidak diisi paksa |
| `guests` | `mart_cleaned.guests` | `phone`: normalisasi 4 variasi format → 1 format standar (khusus nomor domestik). `nationality`: normalisasi inkonsistensi kapitalisasi. `full_name`: typo (~2%) **tidak diperbaiki** — typo tidak bisa dinormalisasi via rule, didokumentasikan sebagai known-issue. `email`/`phone` kosong: dipertahankan. **367 baris duplicate (guest_id G24501+): dipertahankan apa adanya** |
| `role_permissions` | `mart_cleaned.role_permissions` | Tidak ada isu — disalin apa adanya. Disediakan sebagai tabel referensi bila DS butuh konteks role/akses dalam analisis |

#### Database: `reservation_revenue`

| Tabel sumber | mart_cleaned | Cleaning spesifik |
|---|---|---|
| `bookings` | `mart_cleaned.bookings` | Tidak ada isu data kotor terdaftar — disalin apa adanya |
| `daily_occupancy` | `mart_cleaned.daily_occupancy` | Disalin apa adanya. Pre-aggregated di sumber (hasil ETL dari `bookings`), namun tetap masuk `mart_cleaned` karena DS butuh granularitas harian ini utuh sebagai fitur time-series (mis. untuk model demand forecasting) |
| `pricing_history` | `mart_cleaned.pricing_history` | Tidak ada isu — disalin apa adanya |

#### Database: `fnb_operations`

| Tabel sumber | mart_cleaned | Cleaning spesifik |
|---|---|---|
| `fnb_outlets` | `mart_cleaned.fnb_outlets` | Disalin apa adanya |
| `fnb_transactions` | `mart_cleaned.fnb_transactions` | Tidak ada isu data kotor. `guest_id` kosong untuk walk-in (~31% baris): **dipertahankan** sebagai missing value bermakna, bukan data kotor |
| `recipe_bom` | `mart_cleaned.recipe_bom` | Disalin apa adanya |
| `ingredient_price_history` | `mart_cleaned.ingredient_price_history` | Disalin apa adanya |
| `fnb_inventory` | `mart_cleaned.fnb_inventory` | Disalin apa adanya (snapshot kondisi terkini, bukan time-series) |
| `fnb_waste_log` | `mart_cleaned.fnb_waste_log` | Disalin apa adanya |

#### Database: `facility_maintenance`

| Tabel sumber | mart_cleaned | Cleaning spesifik |
|---|---|---|
| `rooms` | `mart_cleaned.rooms` | Disalin apa adanya |
| `housekeeping_log` | `mart_cleaned.housekeeping_log` | Disalin apa adanya |
| `maintenance_tickets` | `mart_cleaned.maintenance_tickets` | Disalin apa adanya. `room_id` kosong (kerusakan area umum) dan `parts_replaced` kosong (~52%, tidak ganti part): dipertahankan sebagai missing value bermakna |

#### Database: `spa_event`

| Tabel sumber | mart_cleaned | Cleaning spesifik |
|---|---|---|
| `venues` | `mart_cleaned.venues` | Disalin apa adanya |
| `spa_bookings` | `mart_cleaned.spa_bookings` | Disalin apa adanya. `guest_id` kosong untuk walk-in (~21%): dipertahankan |
| `event_bookings` | `mart_cleaned.event_bookings` | Disalin apa adanya |

#### Database: `hr_finance`

| Tabel sumber | mart_cleaned | Cleaning spesifik |
|---|---|---|
| `staff_shifts` | `mart_cleaned.staff_shifts` | Disalin apa adanya. `clock_in`/`clock_out` kosong saat status `absent`/`leave`: dipertahankan sebagai missing value bermakna |
| `employee_performance` | `mart_cleaned.employee_performance` | Disalin apa adanya |
| `payroll` | `mart_cleaned.payroll` | Disalin apa adanya. Data sensitif, namun DS memerlukan akses penuh untuk fitur model turnover (M4) |
| `financial_summary` | `mart_cleaned.financial_summary` | Disalin apa adanya. Pre-aggregated (bulanan per departemen), tetap masuk `mart_cleaned` dengan alasan sama seperti `daily_occupancy` — dibutuhkan utuh sebagai fitur time-series |

### Catatan Implementasi untuk Dokumen Arsitektur Induk

- **Lokasi proses cleaning**: sesuai Bagian 5.1 dokumen induk, cleaning terjadi di **Layer Staging**, bukan di Layer Marts. `mart_cleaned` secara teknis hanya meneruskan hasil staging tanpa transformasi bisnis tambahan — konsisten dengan definisi `mart_cleaned` di Bagian 5.2 ("Cleaning saja: dedup, null handling, type cast").
- **Pengecualian sadar pada "dedup"**: definisi umum `mart_cleaned` di Bagian 5.2 dokumen induk mencantumkan "dedup" sebagai bagian dari cleaning. Untuk tabel `guests`, dedup **sengaja tidak diterapkan** terhadap 367 baris duplicate yang disuntikkan sebagai simulasi data quality issue. Ini adalah keputusan desain eksplisit (permintaan Data Scientist untuk melihat data mentah asli), bukan kelalaian, dan perlu dicatat sebagai pengecualian terhadap prinsip umum.
- **Tidak ada kolom turunan**: `mart_cleaned` tidak menambahkan kolom fitur hasil kalkulasi apa pun (mis. tidak menghitung "hari sejak transaksi terakhir"). Seluruh feature engineering adalah tanggung jawab sistem MLOps tim ML, di luar cakupan data platform ini.
- **Implikasi keamanan**: karena `mart_cleaned` menyertakan data sensitif secara penuh (PII di `guests`/`employees`, data payroll), ini menegaskan pentingnya isolasi service account `ds-write`/akses baca Data Scientist yang sudah disebutkan di Bagian 8.3 dokumen induk — akses granular penuh ke data sensitif menjadikan kontrol akses di titik ini kritis.

---

## Lampiran: Referensi Cepat 23 Tabel Sumber

| # | Database | Tabel | Granularitas | Volume (baris) |
|---|---|---|---|---|
| 1 | corporate_master | properties | 1 properti | 6 |
| 2 | corporate_master | employees | 1 karyawan | 755 |
| 3 | corporate_master | guests | 1 pelanggan | 24.867 |
| 4 | corporate_master | role_permissions | 1 (role × domain) | 42 |
| 5 | reservation_revenue | bookings | 1 reservasi | 217.155 |
| 6 | reservation_revenue | daily_occupancy | properti × tipe kamar × tanggal | 19.728 |
| 7 | reservation_revenue | pricing_history | properti × tipe kamar × tanggal | 19.728 |
| 8 | fnb_operations | fnb_outlets | 1 outlet | 17 |
| 9 | fnb_operations | fnb_transactions | 1 item dalam 1 struk | 901.360 |
| 10 | fnb_operations | recipe_bom | menu × bahan | 120 |
| 11 | fnb_operations | ingredient_price_history | bahan × tanggal | 32.880 |
| 12 | fnb_operations | fnb_inventory | outlet × bahan (snapshot) | 457 |
| 13 | fnb_operations | fnb_waste_log | outlet × tanggal × bahan | 108.630 |
| 14 | facility_maintenance | rooms | 1 kamar | 549 |
| 15 | facility_maintenance | housekeeping_log | 1 sesi pembersihan | 424.719 |
| 16 | facility_maintenance | maintenance_tickets | 1 tiket | 13.503 |
| 17 | spa_event | venues | 1 venue | 20 |
| 18 | spa_event | spa_bookings | 1 booking treatment | 127.762 |
| 19 | spa_event | event_bookings | 1 event | 1.331 |
| 20 | hr_finance | staff_shifts | karyawan × hari kerja | 609.364 |
| 21 | hr_finance | employee_performance | karyawan × periode review | 3.748 |
| 22 | hr_finance | payroll | karyawan × bulan | 23.383 |
| 23 | hr_finance | financial_summary | properti × bulan × departemen | 756 |

---

*Dokumen ini merupakan hasil pemetaan kebutuhan Data Scientist, sebagai masukan untuk penentuan skema `mart_cleaned` pada dokumen arsitektur induk.*
