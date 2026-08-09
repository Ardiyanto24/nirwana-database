# Milestone 5.7: Menindaklanjuti Pengajuan Perubahan Cakupan `dim_employee.property_id` — Logs

## 2026-08-09 -- Checkpoint 1: decisions.md (Fase 0)

`decisions.md` ditulis. Temuan pengaju diverifikasi ulang langsung dari kode sebelum evaluasi dimulai (bukan diterima begitu saja): `property_id` memang ada di `mart_cleaned.employees` (passthrough utuh dari staging/produksi), memang hilang di `dim_employee.sql`, dan ketiga fact table yang disebut memang tidak punya jalur ke properti. Dikonfirmasi juga `milestones/5.2-.../decisions.md` KK#2 memang mewajibkan `property_id` sebagai kolom filter wajib -- `dim_employee` satu-satunya dimension yang terlewat. Evaluasi 3 kriteria M5.6 menghasilkan fast-track DISETUJUI (data tersedia + dampak rendah), tidak perlu `AskUserQuestion`.

## 2026-08-09 -- Checkpoint 2: implementasi + promote + sync + verifikasi (Fase 1)

`dim_employee.sql` diupdate (`e.property_id` ditambahkan ke select list). `_mart_aggregated_dimensions_tests.yml` diupdate (test `relationships` ke `dim_property`). `dbt run`+`test --select dim_employee` -- **7/7 PASS**, termasuk test relationships baru.

`promote.py --select dim_employee` -- sukses, 1 tabel dipromosikan ke `mart_aggregated` (BigQuery) sungguhan.

### Temuan signifikan: swap `sync.py` bentrok dengan `analyst_views` (M3.2)

`sync.py --table dim_employee` (percobaan pertama) **CRASH**: `psycopg2.errors.DependentObjectsStillExist` -- `DROP TABLE dim_employee__old` gagal karena 5 view `analyst_views` (`v_housekeeping_staff_daily`, `v_maintenance_technician_daily`, `v_hr_employee_monthly`, `v_hr_employee_performance_semester`, `v_hr_watchlist_monthly`) masih bergantung padanya.

**Diagnosis (dicek langsung ke Postgres, bukan ditebak):** swap RENAME-based M5.5 (`live -> __old`, `staging -> live`) bekerja benar untuk penamaan, tapi Postgres view mengikat ke tabel dasar lewat OID saat `CREATE VIEW`, bukan lewat nama. Begitu tabel lama di-rename ke `__old`, view-view yang sudah ada tetap mengikuti OID itu -- artinya begitu urutan rename selesai, view-view tersebut kini menunjuk ke tabel STALE (`__old`, tanpa `property_id`), bukan ke tabel live yang baru. `DROP TABLE __old` lalu gagal karena Postgres menolak menghapus tabel yang masih ada dependennya.

Dicek `pg_depend` langsung: dikonfirmasi 5 view di atas semuanya bergantung ke `dim_employee__old`, bukan ke `dim_employee` (live). Tabel live `dim_employee` sendiri sudah benar (755 baris, kolom `property_id` ada) -- yang salah murni referensi 5 view tersebut.

**Kenapa ini baru ketahuan sekarang, bukan di M5.5:** dicek `gh run list --workflow=reverse-etl-mart-aggregated.yml` -- run terjadwal terakhir yang sukses (`06:00:42Z` 2026-08-09) terjadi **sebelum** M3.2 checkpoint 1 (`analyst_views` schema, commit `2850308`, `19:06 WIB` / `12:06 UTC` hari yang sama) membuat view-view itu di Postgres serving. Jadi ini bukan insiden produksi yang sudah lama berjalan diam-diam -- ini collision pertama antara mekanisme swap M5.5 (dibangun sebelum ada view apa pun di atas `mart_aggregated`) dan `analyst_views` M3.2 (dibangun setelahnya, mengasumsikan tabel dasar stabil). Tapi ini akan terjadi lagi di **setiap** run terjadwal berikutnya untuk hampir semua dari 76 tabel (48 view M3.2 tersebar di 6 domain) kalau tidak diperbaiki -- berarti workflow `reverse-etl-mart-aggregated.yml` sudah pasti akan crash pada eksekusi terjadwal berikutnya kalau dibiarkan.

**Perbaikan (langsung, dalam scope M5.7 karena scriptnya `scripts/reverse_etl_mart_aggregated/` -- wilayah pemilik `mart_aggregated`, bukan M3.2):**
1. Pemulihan manual state saat ini: `scripts/data_analyst_views/apply_views.py --all` dijalankan (script M3.2, `CREATE OR REPLACE VIEW` idempotent, pakai kredensial admin serving terpisah dari writer `sync.py`) -- rebind ke-5 view ke tabel live yang benar. Dicek ulang `pg_depend`: 0 dependensi tersisa ke `__old`, 5 dependensi baru ke live `dim_employee`. `DROP TABLE dim_employee__old` lalu sukses manual.
2. `sync.py` diedit: langkah `DROP TABLE __old` di akhir `sync_table()` dibungkus try/except khusus `psycopg2.errors.DependentObjectsStillExist` -- kalau gagal karena dependency, di-downgrade jadi WARNING (bukan crash), tabel `__old` dibiarkan (orphan, tidak masalah untuk korektnes karena tabel live sudah benar), rollback transaksi yang gagal supaya koneksi tetap sehat untuk tabel berikutnya dalam batch `--all`. Field `old_table` baru ditambahkan ke return dict untuk observability.
3. **Dibuktikan lewat 2 siklus nyata (bukan cuma dibaca kodenya):**
   - Rerun `sync.py --table dim_employee` tanpa reapply view dulu -- **tidak crash**, tercetak WARNING yang jelas, sync tetap `synced` (BigQuery=755, Postgres=755).
   - Reapply view + drop orphan manual (persis siklus pemulihan di atas) -- 0 dependensi ke __old dikonfirmasi ulang.
   - Rerun `sync.py --table dim_employee` SEKALI LAGI -- persis reproduksi masalah yang sama (karena setiap sync selalu rename ulang live -> __old, dan view yang baru saja di-rebind otomatis mengikuti rename itu lagi) -- WARNING muncul lagi, sync tetap sukses tanpa crash. Ini membuktikan fix-nya genuinely robust terhadap kondisi berulang, bukan cuma menutupi 1 kejadian.
   - Cleanup akhir: `apply_views.py --all` + drop orphan manual sekali lagi -- state akhir bersih (tidak ada tabel `__old` tersisa, semua 5 view menunjuk ke tabel live).

**Keterbatasan yang didokumentasikan, bukan diperbaiki di M5.7:** fix ini membuat `sync.py` tidak crash lagi, tapi TIDAK mengotomasi reapply `analyst_views` -- itu tetap manual/terpisah (beda kredensial, beda skema, beda milestone owner). Setiap kali `reverse-etl-mart-aggregated.yml` jalan terjadwal ke depan, tabel `__old` akan menumpuk (orphan, aman tapi makan storage) sampai `apply_views.py --all` dijalankan manual atau diorkestrasi otomatis. Dicatat sebagai keputusan tertunda (lihat `docs/keputusan-tertunda.md`): apakah perlu step "reapply analyst views" otomatis dirantai setelah `reverse-etl-mart-aggregated.yml` di GitHub Actions -- di luar scope minimal M5.7 (menambah kolom), tapi ditemukan LEWAT verifikasi wajib M5.7 sehingga dicatat di sini, bukan disembunyikan.

### Verifikasi akhir langsung ke infrastruktur sungguhan

- **BigQuery**: `mart_aggregated.dim_employee` = 755 baris, 755 non-null `property_id` (100%). `mart_cleaned__employees` = 755 baris, 755 non-null `property_id`. **Cocok persis** -- passthrough tanpa kehilangan data.
- **Distribusi per properti** (BigQuery, sama persis di Postgres serving): P01=165, P02=270, P03=115, P04=100, P05=85, P06=20 (kantor pusat).
- **Postgres serving**: `mart_aggregated.dim_employee` live, 755 baris, kolom `property_id` ada, tidak ada tabel `__old` tersisa. 5 view `analyst_views` terverifikasi menunjuk ke tabel live lewat `pg_depend`.
- Tidak ada perubahan collateral ke fact table manapun -- tidak diedit, tidak perlu di-rebuild.
