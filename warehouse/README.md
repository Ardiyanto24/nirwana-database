# `warehouse/` — dbt project (Milestone 2.2, Layer Staging)

Transformasi `raw_production` (BigQuery, hasil Milestone 2.1) → `staging` (view, cleaning per tabel). Lihat `milestones/2.2-layer-staging-cleaning-per-tabel/decisions.md` untuk keputusan lengkap.

## Setup

```bash
pip install dbt-core dbt-bigquery
cp warehouse/profiles.yml.example warehouse/profiles.yml   # isi path keyfile sesuai lokal Anda
cd warehouse
dbt debug --profiles-dir .
dbt run --profiles-dir .
```

Kredensial: `scripts/extract/gcp-dbt-transform-key.json` (service account `dbt-transform`, `bigquery.dataEditor` + `bigquery.jobUser` di level project — beda dari `extract-writer` M2.1 yang scoped ke satu dataset, karena dbt perlu mengelola beberapa dataset ke depannya).

## Daftar Kolom/Baris yang Sengaja TIDAK Dibersihkan

Output wajib sumber Milestone 2.2 ("daftar kolom/tabel yang sengaja tidak dibersihkan agar tidak 'diperbaiki' secara tidak sengaja di iterasi berikutnya"). Identik dengan raw pada kolom/baris ini — **jangan** normalisasi lebih lanjut tanpa keputusan eksplisit baru:

| Tabel | Kolom/Baris | Kenapa Dipertahankan |
|---|---|---|
| `stg_corporate_master__properties` | `star_rating` null (1 baris, P06) | Missing value bermakna — P06 kantor pusat, bukan properti tamu |
| `stg_corporate_master__employees` | `role_title` null (~2%) | Missing value — belum diisi HR admin, tidak bisa diisi paksa |
| `stg_corporate_master__guests` | `full_name` typo (~2%) | Dirty data disengaja — typo tidak bisa dinormalisasi via rule |
| `stg_corporate_master__guests` | `email`/`phone` null | Missing value bermakna — walk-in tidak isi form lengkap |
| `stg_corporate_master__guests` | 367 baris duplikat (`guest_id` ≥ G24501, kunci `full_name`) | Dirty data disengaja — dedup diserahkan ke eksperimen Data Scientist |
| `stg_fnb_operations__fnb_transactions` | `guest_id` null (~31%) | Missing value bermakna — walk-in anonim |
| `stg_facility_maintenance__maintenance_tickets` | `room_id` null (~27,5%) | Missing value bermakna — kerusakan area umum, bukan kamar |
| `stg_facility_maintenance__maintenance_tickets` | `parts_replaced` null (~52%) | Missing value bermakna — tidak ada penggantian part |
| `stg_facility_maintenance__maintenance_tickets` | `resolved_date` null | Missing value bermakna — tiket masih `open`/`in-progress` |
| `stg_spa_event__spa_bookings` | `guest_id` null (~21%) | Missing value bermakna — walk-in anonim |
| `stg_hr_finance__staff_shifts` | `clock_in`/`clock_out` null | Missing value bermakna — status `absent`/`leave` |

## Catatan Kategori C (Bukan Dirty Data, Tapi Perlu Diketahui)

Ditemukan lewat profiling (`milestones/2.2-.../data-profiling-findings.md`), bukan bug atau data kotor — nilai valid dari sumber, tapi perilakunya tidak intuitif kalau cuma baca `Metadata.md`:

- **`stg_hr_finance__payroll.thr`** dan **`stg_hr_finance__financial_summary.gop`/`undistributed_expense`**: "tidak berlaku" = **0**, bukan NULL. Jangan filter pakai `IS NOT NULL`.
- **`stg_hr_finance__financial_summary`**: P&L nyata ada di `department='Overall'` (P01-P05) **dan** `department='Corporate Overhead'` (khusus P06) — bukan cuma `'Overall'`.
- **`stg_fnb_operations__fnb_transactions.transaction_id`**: bukan row-level unique key (~2,33 baris/transaksi, multi-item order).

Detail lengkap tiap temuan ada di komentar SQL model terkait dan `milestones/2.2-layer-staging-cleaning-per-tabel/data-profiling-findings.md`.
