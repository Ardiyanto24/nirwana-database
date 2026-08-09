# Kebijakan Akses dan Kredensial — Data Analyst

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 3.5 (`milestones/3.5-isolasi-akses-kredensial-analyst/`) |
| **Kode** | `scripts/data_analyst_credentials/` |
| **Input utama** | `docs/08-serving-data-analyst/{pemetaan-pola-akses-analyst.md,view-query-pattern-analyst.md,api-analyst.md}` (M3.1/3.2/3.4) |
| **Status** | Selesai — 7 role read-only, seluruhnya terverifikasi terisolasi |

---

## Cara Membaca Dokumen Ini

Dokumen ini adalah Output resmi kedua Milestone 3.5 ("Dokumentasi kebijakan akses per peran"). Tiap peran punya 1 kredensial Postgres read-only di serving project, dicatat juga di inventaris project-wide `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`. Semua isolasi bersifat **table/schema-level** (GRANT/REVOKE) — bukan Row-Level Security, lihat `decisions.md` untuk alasan (RLS tidak pernah dipakai di project ini; isolasi per-properti untuk Property/GM Analyst tetap tanggung jawab API/query-layer M3.4).

## Prinsip Desain

- **Sumber kebenaran GRANT = whitelist M3.4** (`scripts/data_analyst_api/whitelist_<domain>.py`) — role Postgres dan endpoint API selalu punya cakupan yang identik, diturunkan dari file yang sama.
- **Tidak ada grant ke `mart_aggregated` sama sekali** — seluruh akses agregat lewat `analyst_views` (view berjalan dengan privilege pemilik), row-level lewat `mart_cleaned` langsung. Ini membuat bypass business rule (mis. filter `Overall` exclusion) mustahil tanpa mengubah desain schema.
- **Read-only murni**: `NOSUPERUSER NOCREATEDB NOCREATEROLE`, cuma `SELECT`, tidak ada `INSERT`/`UPDATE`/`DELETE` — diverifikasi eksplisit tiap role.

## 7 Role

| Role | Env Var | Cakupan Aggregate (`analyst_views`) | Cakupan Row-Level (`mart_cleaned`) |
|---|---|---|---|
| `revenue_analyst_reader` | `REVENUE_ANALYST_READER_DB_URL` | 8 view Revenue | `bookings`, `pricing_history` |
| `fnb_analyst_reader` | `FNB_ANALYST_READER_DB_URL` | 8 view F&B | `fnb_transactions` |
| `facility_analyst_reader` | `FACILITY_ANALYST_READER_DB_URL` | 9 view Facility/Ops | `maintenance_tickets` |
| `spa_event_analyst_reader` | `SPA_EVENT_ANALYST_READER_DB_URL` | 6 view Spa & Event | `event_bookings` |
| `hr_analyst_reader` | `HR_ANALYST_READER_DB_URL` | 8 view HR (**tanpa payroll**) | `staff_shifts`, `employee_performance` |
| `corporate_financial_analyst_reader` | `CORPORATE_FINANCIAL_ANALYST_READER_DB_URL` | 9 view Corporate/Financial | `financial_summary`, `payroll` |
| `property_gm_analyst_reader` | `PROPERTY_GM_ANALYST_READER_DB_URL` | **Warisan** dari 5 role di atas (bukan Corporate/Financial) via `GRANT <role> TO` | Warisan sama |

## Bukti Isolasi per Role

Seluruh bukti di bawah diverifikasi lewat `scripts/data_analyst_credentials/verify_role_isolation.py` (connect-as-role sungguhan, bukan asumsi) — detail lengkap di `milestones/3.5-isolasi-akses-kredensial-analyst/logs.md`.

### Revenue, F&B, Facility/Ops, Spa & Event (4 role — pola seragam)

- **Allow:** SELECT ke 1 view + 1 tabel row-level milik domain sendiri — sukses.
- **Deny:** SELECT langsung ke tabel dasar `mart_aggregated.fact_<domain>_*` (bypass) — `InsufficientPrivilege`. SELECT ke `payroll`, ke tabel/view domain lain — `InsufficientPrivilege`.
- **Write:** `INSERT` ke tabel row-level sendiri — `InsufficientPrivilege`.

### HR — business rule kritis KK1 M3.5 (contoh literal dokumen sumber)

- **Deny diperkuat**: 5 target payroll-adjacent sekaligus diuji — `mart_cleaned.payroll` langsung, `v_payroll_department_monthly`, `v_payroll_access_level_monthly`, `v_financial_service_charge_monthly`, `v_financial_labor_cost_monthly`. **Semua gagal** — HR Analyst benar-benar tidak bisa mengakses payroll dalam bentuk apa pun.

### Corporate/Financial — pengujian paling kritis di seluruh milestone

- **Allow**: `v_financial_departmental_margin`, `payroll`, `financial_summary` — sukses (satu-satunya role dengan akses payroll).
- **Deny paling krusial**: SELECT langsung ke `mart_aggregated.fact_financial_business_line_monthly` (tabel dasar di balik `v_financial_departmental_margin`) — **gagal**. Ini membuktikan filter `WHERE line_name NOT IN ('Overall','Corporate Overhead')` yang ditanam di view (M3.2) tidak bisa dilewati dengan query langsung ke tabel di baliknya — kredensial tidak bisa dipakai untuk melihat baris yang sengaja disembunyikan.

### Property/GM — role inheritance, bukan grant terpisah

- **Allow**: 1 view/tabel representatif dari **masing-masing** 5 domain (Revenue, F&B, Facility, Spa&Event, HR) — sukses lewat privilege warisan (`INHERIT` default Postgres, tanpa perlu `SET ROLE`).
- **Deny**: seluruh akses Corporate/Financial — `v_financial_departmental_margin`, **`v_financial_business_line_group_monthly`** (larangan eksplisit tabel level-grup, M3.1 business rule #3), `payroll`, `financial_summary` — semua gagal.

## Temuan Operasional (relevan untuk pemilik infrastruktur berikutnya)

1. **Ownership schema vs objek berbeda.** Schema `analyst_views`/`mart_cleaned` dimiliki admin (`postgres`), tapi tabel `mart_cleaned.*` dimiliki `reverse_etl_writer` (dibuat lewat koneksi role itu di `sync.py`). GRANT admin ke objek yang tidak dimilikinya **sukses tanpa error tapi tidak benar-benar berlaku** (silent no-op) — `apply_grants()` di `setup_analyst_roles.py` merutekan GRANT sesuai pemilik sebenarnya per schema.
2. **Supavisor pooler cache tidak instan.** Koneksi sebagai role yang baru saja dibuat/di-grant bisa gagal auth atau "permission denied" meski grant sudah benar ada di katalog — `verify_role_isolation.py` menambahkan retry warm-up (maks 6× percobaan, jeda 5 detik) sebelum menjalankan suite verifikasi sungguhan.

## Cara Menjalankan / Merotasi

```bash
pip install -r requirements.txt
cd scripts/data_analyst_credentials
python setup_analyst_roles.py --role <nama_role>   # 1 role
python setup_analyst_roles.py --all                # seluruh 7 role, password ikut dirotasi
```

Password di-generate ulang (`secrets.token_urlsafe(24)`) tiap kali dijalankan — re-run efektif merotasi password, ditulis otomatis ke `.env` (tidak pernah dicetak ke stdout). Manual-only, tidak ada di workflow terjadwal manapun (konsisten pola `setup_reader_role.py` M1.6).
