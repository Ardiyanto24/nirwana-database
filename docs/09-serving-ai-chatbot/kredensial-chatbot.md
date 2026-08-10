# Kebijakan Akses dan Kredensial — AI Chatbot

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 4.3 (`milestones/4.3-kredensial-read-only-per-kelompok-akses/`) |
| **Kode** | `scripts/chatbot_credentials/` |
| **Input utama** | `docs/09-serving-ai-chatbot/{pemetaan-akses-teknis-chatbot.md,view-query-pattern-chatbot.md}` (M4.1/4.2) |
| **Status** | Selesai — 10 role read-only, seluruhnya terverifikasi terisolasi |

---

## Cara Membaca Dokumen Ini

Dokumen ini adalah Output resmi kedua Milestone 4.3 ("Dokumentasi eksplisit batasan kredensial ini sebagai referensi audit keamanan"). Tiap `data_domain` punya 1 kredensial Postgres read-only di serving project, dicatat juga di inventaris project-wide `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md`. Isolasi bersifat **table/schema-level** (GRANT/REVOKE) — bukan Row-Level Security, konsisten satu-satunya pola akses yang pernah dipakai project ini (lihat `decisions.md` M3.5/M4.3).

Ini implementasi konkret **Lapis 2 RBAC** chatbot (`rancangan-arsitektur-data-platform-elt.md` §8.2) — dirancang tetap aman meskipun Lapis 1 (validasi intent di application layer chatbot) gagal.

## Prinsip Desain

- **GRANT hanya ke `chatbot_views.<view>`, tidak pernah ke `mart_aggregated`/`mart_cleaned` langsung** — lebih ketat dari kredensial Data Analyst (M3.5), yang masih grant row-level langsung ke `mart_cleaned`. Seluruh 67 view chatbot (agregat maupun row-level) sudah mengkurasi kolom, jadi tidak ada alasan legitimate menyentuh tabel dasar.
- **Sumber kebenaran GRANT = inventaris view M4.2** (bukan whitelist API — Milestone 4.4 belum dibangun saat M4.3 dikerjakan).
- **Read-only murni**: `NOSUPERUSER NOCREATEDB NOCREATEROLE`, cuma `SELECT`, tidak ada `INSERT`/`UPDATE`/`DELETE` — diverifikasi eksplisit tiap role.
- **Tidak ada role union** — 10 role domain berdiri sendiri (beda dari `property_gm_analyst_reader` M3.5). Komposisi multi-domain per persona (mis. General Manager butuh 7+4 domain sekaligus) adalah tanggung jawab Milestone 4.4 (API), bukan credential layer.

## 10 Role

| Role | Env Var | Jumlah View (`chatbot_views`) |
|---|---|---|
| `reservation_chatbot_reader` | `RESERVATION_CHATBOT_READER_DB_URL` | 10 (8 agregat + 2 lookup) |
| `fnb_chatbot_reader` | `FNB_CHATBOT_READER_DB_URL` | 11 (8 agregat + 3 lookup) |
| `facility_chatbot_reader` | `FACILITY_CHATBOT_READER_DB_URL` | 12 (9 agregat + 3 lookup) |
| `spa_event_chatbot_reader` | `SPA_EVENT_CHATBOT_READER_DB_URL` | 9 (6 agregat + 3 lookup) |
| `hr_chatbot_reader` | `HR_CHATBOT_READER_DB_URL` | 10 (8 agregat + 2 lookup, **tanpa payroll**) |
| `financial_chatbot_reader` | `FINANCIAL_CHATBOT_READER_DB_URL` | 11 (9 agregat + 2 lookup) |
| `properties_ref_chatbot_reader` | `PROPERTIES_REF_CHATBOT_READER_DB_URL` | 1 |
| `employees_directory_chatbot_reader` | `EMPLOYEES_DIRECTORY_CHATBOT_READER_DB_URL` | 1 |
| `guests_pii_chatbot_reader` | `GUESTS_PII_CHATBOT_READER_DB_URL` | 1 (`guests_contact_view`) |
| `guests_profile_chatbot_reader` | `GUESTS_PROFILE_CHATBOT_READER_DB_URL` | 1 (`guests_profile_view`) |

Total 67 view digrant, cocok persis jumlah view aktif `chatbot_views` (M4.2 Checkpoint 5).

## Bukti Isolasi per Role

Seluruh bukti di bawah diverifikasi lewat `scripts/chatbot_credentials/verify_role_isolation.py` (connect-as-role sungguhan, bukan asumsi) — detail lengkap di `milestones/4.3-kredensial-read-only-per-kelompok-akses/logs.md`.

### 8 role domain (pola seragam)

- **Allow:** SELECT ke 1 view agregat + 1 view lookup (atau 1 view saja untuk `properties_ref`/`employees_directory`) milik domain sendiri — sukses.
- **Deny:** SELECT langsung ke tabel dasar `mart_aggregated.fact_<domain>_*`/`dim_*` **dan** `mart_cleaned.<table>` mentah (bypass kedua arah — lebih ketat dari M3.5 yang cuma menguji bypass `mart_aggregated`) — `InsufficientPrivilege`. SELECT ke `mart_cleaned.role_permissions` (M4.1 Keputusan #7, tidak pernah jadi target siapa pun) — `InsufficientPrivilege`. SELECT ke view/tabel domain lain — `InsufficientPrivilege`.
- **Write:** `INSERT` ke tabel `mart_cleaned` — `InsufficientPrivilege` (role bahkan tidak punya `USAGE` sama sekali ke schema itu).

### HR — larangan payroll (business rule kritis carry-over M3.1 #2, berlaku sama)

- **Deny diperkuat**: 6 target payroll-adjacent sekaligus diuji — `mart_cleaned.payroll` langsung, `v_lookup_payroll`, `v_payroll_department_monthly`, `v_payroll_access_level_monthly`, `v_financial_service_charge_monthly`, `v_financial_labor_cost_monthly`. **Semua gagal**.

### Financial — pengujian kritis business rule `Overall` exclusion

- **Deny paling krusial**: SELECT langsung ke `mart_aggregated.fact_financial_business_line_monthly` (tabel dasar di balik `v_financial_departmental_margin`) — **gagal**. Membuktikan filter `WHERE line_name NOT IN ('Overall','Corporate Overhead')` (M4.2) tidak bisa dilewati lewat query langsung ke tabel di baliknya.

### `guests_pii` vs `guests_profile` — pengujian paling krusial di seluruh milestone

- **Allow**: `guests_pii_chatbot_reader` → `guests_contact_view`; `guests_profile_chatbot_reader` → `guests_profile_view`.
- **Deny silang, kedua arah**: `guests_pii_chatbot_reader` mencoba SELECT `guests_profile_view` — **gagal**. `guests_profile_chatbot_reader` mencoba SELECT `guests_contact_view` — **gagal**. Membuktikan pemisahan kolom PII (`email`/`phone`) vs profil analitis (`loyalty_tier`/`nationality`) di atas 1 tabel fisik `mart_cleaned.guests` yang sama benar-benar tertegakkan di level kredensial, bukan cuma di level view (M4.2 KK2 sudah membuktikan level view; M4.3 membuktikan level akses).

## Temuan Operasional

1. **Tidak ada owner-routing** (beda dari M3.5) — seluruh 67 view `chatbot_views` dimiliki 1 role admin yang sama (diverifikasi `pg_class.relowner`, Fase 0), karena Keputusan #3 melarang grant ke tabel dasar sama sekali. `apply_grants()` di `setup_chatbot_roles.py` jadi lebih sederhana dari `setup_analyst_roles.py` — 1 koneksi admin untuk semua grant.
2. **Supavisor pooler cache tidak instan** (temuan sama M3.5) — 2 dari 10 role (`reservation_chatbot_reader`, `spa_event_chatbot_reader`) sempat butuh 1× retry warm-up saat `--all` dijalankan ulang (password rotasi), sisanya langsung sukses attempt pertama.

## Cara Menjalankan / Merotasi

```bash
pip install -r requirements.txt
cd scripts/chatbot_credentials
python setup_chatbot_roles.py --role <nama_role>   # 1 role
python setup_chatbot_roles.py --all                # seluruh 10 role, password ikut dirotasi
```

Password di-generate ulang (`secrets.token_urlsafe(24)`) tiap kali dijalankan — re-run efektif merotasi password, ditulis otomatis ke `.env` (tidak pernah dicetak ke stdout). Manual-only, tidak ada di workflow terjadwal manapun (konsisten pola M3.5/M1.6).
