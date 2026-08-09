# Milestone 5.7: Menindaklanjuti Pengajuan Perubahan Cakupan `dim_employee.property_id` — Decisions

**Source:** Bukan dari `docs/03-implementation-plans/` — milestone ini menindaklanjuti 1 entri backlog nyata (bukan simulasi) di `docs/07-mart-aggregated/pengajuan-perubahan-cakupan.md` ("Kolom `property_id` hilang di `dim_employee`"), diajukan lewat mekanisme `docs/07-mart-aggregated/mekanisme-pengajuan-perubahan-cakupan.md` yang dibangun Milestone 5.6. "Kontrak" milestone ini adalah entri backlog tersebut plus dokumen mekanisme itu sendiri.
**Status:** Done
**Date started:** 2026-08-09

## Latar Belakang Pengajuan

Pengaju: Data Analyst Serving (Milestone 3.2), ditemukan nyata saat implementasi (verifikasi `information_schema.columns` terhadap `mart_aggregated` sungguhan di serving PostgreSQL) — bukan role-play, berbeda dari trial KK2 M5.6 yang disimulasikan. Dicatat sebagai entri backlog di commit `989a6dd` (2026-08-09), status awal "Diajukan".

Kebutuhan: `mart_aggregated.dim_employee` hanya berisi `employee_id`, `full_name`, `department_id`, `access_level_id` — tidak ada `property_id`, sehingga 3 fact table grain-karyawan (`fact_hr_employee_monthly`, `fact_hr_employee_performance_semester`, `fact_hr_watchlist_monthly`) tidak bisa difilter/di-join ke properti lewat `mart_aggregated`. Berpotensi memblokir Milestone 3.4 (API) kalau endpoint per-properti untuk HR dibangun sebelum gap ini ditutup.

## Verifikasi Independen Temuan (dilakukan sesi ini, sebelum keputusan apa pun)

Sebelum mengevaluasi, temuan pengaju diverifikasi ulang langsung dari kode — bukan diterima begitu saja:

1. **`property_id` memang ada di produksi**: `docs/01-architecture/Metadata.md` baris 134, kolom `employees.property_id` (FK), "`P06` = karyawan kantor pusat".
2. **Mengalir utuh ke staging**: `warehouse/models/staging/corporate_master/stg_corporate_master__employees.sql` baris 23 men-select `property_id` langsung dari `source` tanpa transformasi.
3. **Mengalir utuh ke `mart_cleaned`**: `warehouse/models/mart_cleaned/corporate_master/mart_cleaned__employees.sql` adalah passthrough murni (`select * from {{ ref('stg_corporate_master__employees') }}`) — dikonfirmasi live lewat test `relationships` di `warehouse/models/mart_cleaned/_mart_cleaned_tests.yml` baris 19-24 (FK `mart_cleaned__employees.property_id` → `mart_cleaned__properties.property_id`).
4. **Memang hilang di `dim_employee`**: `warehouse/models/mart_aggregated/corporate_master/dim_employee.sql` baris 4-8 hanya men-select `e.employee_id, trim(e.full_name), d.department_id, a.access_level_id` — `e.property_id` tidak disertakan padahal `e` (alias `mart_cleaned__employees`) sudah punya kolom itu.
5. **3 fact table yang disebut memang tidak punya jalur ke properti**: dibaca langsung `fact_hr_employee_monthly.sql` dan `fact_hr_employee_performance_semester.sql` — keduanya hanya join/select lewat `employee_id`, tidak ada `property_id` di manapun.
6. **Bukan celah kecil yang wajar terlewat**: `milestones/5.2-desain-struktur-tabel-mart-aggregated/decisions.md` Kriteria Keberhasilan #2 (baris 17) eksplisit mewajibkan `property_id` sebagai kolom filter/cluster wajib di seluruh desain skema `mart_aggregated`. Keputusan #5 milestone yang sama (baris 58) bahkan menetapkan `property_id` sebagai kolom clustering utama tiap fact table. `dim_employee` adalah satu-satunya dimension yang mewakili entitas dengan properti tapi terlewat menyertakan kolom ini saat desain M5.2.

**Kesimpulan verifikasi: temuan pengaju 100% akurat**, bukan kesalahpahaman atau informasi usang.

## Evaluasi (3 kriteria mekanisme M5.6)

Evaluasi ini sudah tercatat di entri backlog (`pengajuan-perubahan-cakupan.md`), dikonfirmasi ulang di sini:

| Kriteria | Nilai | Catatan |
|---|---|---|
| Ketersediaan data | Tersedia | `mart_cleaned.employees.property_id` sudah ada penuh sejak M2.1-2.3 (lihat Verifikasi #3 di atas) — tidak butuh data baru sama sekali, murni kolom yang terlewat di-select saat M5.2. |
| Dampak ke konsumen lain | Rendah | Menambah 1 kolom ke `dim_employee`, tidak mengubah kolom/grain yang sudah ada. Konsumen existing (Facility/Ops — `v_housekeeping_staff_daily`, `v_maintenance_technician_daily`) tidak terpengaruh, hanya dapat kolom opsional tambahan. |
| Prioritas relatif | Sedang-Tinggi | Tidak memblokir pekerjaan yang sudah selesai (M3.2 sudah ditutup dengan gap ini didokumentasikan), tapi berpotensi memblokir Milestone 3.4 (API) kalau endpoint HR per-properti dibangun duluan. |

**Keputusan: DISETUJUI, jalur cepat** — sesuai aturan keputusan mekanisme M5.6 sendiri: "kombinasi dampak rendah + data tersedia penuh → jalur cepat ke DISETUJUI." Tidak ada pertimbangan terbuka yang perlu didiskusikan lewat `AskUserQuestion` di titik ini — keputusan approve/reject sudah otomatis oleh aturan yang dikunci sebelumnya.

## Keputusan Proses: dibungkus sebagai Milestone 5.7, bukan hotfix

**Ini bukan pertanyaan baru** — dokumen mekanisme M5.6 sendiri (bagian "Alur Kerja" langkah 4 dan bagian "Peran") sudah mewajibkan: "Kalau disetujui: perubahan diimplementasikan ... via checkpoint milestone seperti biasa (bukan hotfix langsung ke production)" dan "Pemilik `mart_aggregated`: ... (kalau disetujui) mengimplementasikan perubahan lewat proses milestone/checkpoint yang sama seperti M5.1-5.6 — bukan hotfix ad-hoc." Keputusan disiplin proses ini sudah dikunci M5.6 untuk semua pengajuan mendatang, jadi diterapkan langsung di sini sebagai keputusan turunan, bukan ditanyakan ulang ke user.

## Keputusan Teknis (dikunci tanpa AskUserQuestion — turunan langsung dari pola existing)

### 1. Tambah `property_id` ke `dim_employee.sql`

`e.property_id` ditambahkan ke daftar select (alias `e` = `mart_cleaned__employees`, sudah di-join di model ini, tidak perlu join baru).

### 2. Tambah test `relationships` ke `dim_property`

`warehouse/models/mart_aggregated/_mart_aggregated_dimensions_tests.yml` — kolom `dim_employee.property_id` diberi test `relationships` ke `dim_property.property_id`, pola identik dengan `department_id`→`dim_department` dan `access_level_id`→`dim_access_level` yang sudah ada di entri `dim_employee` yang sama, dan konsisten test `property_id` di `mart_cleaned`.

### 3. Scope promote: `promote.py --select dim_employee`

Single table, DQ gate build→test→swap yang sama dipakai M5.1-5.6 — tidak perlu promote ulang 75 tabel lain yang tidak berubah.

### 4. Scope sync: `sync.py --table dim_employee`

`sync.py` (M5.5) sudah membaca skema BigQuery secara dinamis via `bq_client.get_table()` — tidak perlu perubahan kode, sama seperti preseden kolom `in_watchlist` di M5.6 Checkpoint 5.

### 5. Verifikasi: query langsung BigQuery + Postgres, bukan cuma log script

Konsisten disiplin "verifikasi terhadap infrastruktur sungguhan" yang dipakai sepanjang project — cek `mart_aggregated.dim_employee` (BigQuery) dan tabel serving (Postgres) langsung, bandingkan non-null count/row count terhadap `mart_cleaned.employees`.

## Task Breakdown

4 fase, 4 checkpoint.

### Fase 0 — Setup
1. Tulis `decisions.md` (dokumen ini).

**Checkpoint 1**

### Fase 1 — Implementasi + promote + sync
2. Edit `dim_employee.sql` + test dimension. `dbt run`/`test --select dim_employee`. `promote.py --select dim_employee`. `sync.py --table dim_employee`. Verifikasi langsung BigQuery + Postgres.

**Checkpoint 2**

### Fase 2 — Tutup siklus: dokumentasi + backlog + cross-reference
3. Update `DataSchema-mart-aggregated.md`, `Metadata-mart-aggregated.md`. Tutup entri backlog (Keputusan + Tindak Lanjut + status Selesai). Cross-reference Known Gaps `milestones/5.2-.../report.md` dan `milestones/3.2-.../report.md`.

**Checkpoint 3**

### Fase 3 — Finalisasi
4. Verifikasi hasil terhadap kebutuhan pengajuan, tulis `report.md`.

**Checkpoint 4 (final)** — commit setiap checkpoint terpisah.
