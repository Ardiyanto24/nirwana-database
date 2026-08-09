# Milestone 3.5: Isolasi Akses dan Kredensial Read-Only — Logs

## 2026-08-09 — Mulai kerja

- Plan disetujui via Plan Mode. `decisions.md` ditulis, mengunci 10 keputusan teknis (isolasi table/schema-level bukan RLS, 7 role, role inheritance untuk Property/GM, whitelist M3.4 sebagai sumber kebenaran, verifier isolasi baru, dst).
- Folder dibuat: `milestones/3.5-isolasi-akses-kredensial-analyst/`, `scripts/data_analyst_credentials/`.
- Mulai Task 1 (Fase 0 — verifikasi asumsi view-owner + bangun infra role).

## 2026-08-09 — Checkpoint 1

- **Verifikasi empiris Keputusan #8 (paling krusial di milestone ini)**: dibuat role uji coba sekali pakai (`_test_view_owner_check`) dengan HANYA `GRANT SELECT` ke `analyst_views.v_revenue_room_type_daily` (tanpa grant apa pun ke schema `mart_aggregated`). Hasil: `SELECT` ke view sukses (19.746 baris), `SELECT` langsung ke `mart_aggregated.fact_revenue_room_type_daily` **gagal** `permission denied for schema mart_aggregated`. Asumsi terbukti benar — Postgres view berjalan dengan privilege pemilik, role analyst tidak pernah perlu grant apa pun ke `mart_aggregated` schema, dan bypass filter business rule (mis. `Overall` exclusion) otomatis mustahil tanpa grant eksplisit. Role uji coba dibersihkan (`REVOKE` eksplisit lalu `DROP ROLE` — dicatat: `DROP OWNED BY` gagal karena butuh privilege role itu sendiri, harus `REVOKE` manual per objek dulu).
- `scripts/data_analyst_credentials/{connections.py, grant_utils.py, verify_role_isolation.py, setup_analyst_roles.py}` dibuat. `verify_role_isolation.py` adalah verifier isolasi Postgres generik pertama di project ini (sebelumnya cuma ada versi BigQuery, `verify_dataset_isolation.py` M2.5) — dipakai ulang 7× di checkpoint berikutnya. `grant_utils.derive_grant_targets()` menurunkan daftar GRANT dari whitelist M3.4 (Keputusan #4).
- `.env.example` ditambah 7 baris placeholder `*_ANALYST_READER_DB_URL`.
- Verifikasi: seluruh modul berhasil di-import tanpa error.

## 2026-08-09 — Checkpoint 2: Revenue role (2 temuan operasional signifikan)

- `role_config_revenue.py` ditulis, GRANT target diturunkan dari `whitelist_revenue.py` (8 view + 2 tabel row-level).
- **Temuan #1 — schema `analyst_views`/`mart_cleaned` DAN objek di dalamnya punya pemilik BERBEDA.** Percobaan pertama gagal: role admin (`postgres` via `SERVING_DB_URL`) ternyata **bukan superuser** di project serving ini (`rolsuper=false`) dan tidak punya otoritas GRANT atas objek yang tidak dimilikinya — `GRANT SELECT ON mart_cleaned.bookings` yang dijalankan via admin **sukses tanpa error tapi tidak benar-benar berlaku** (dikonfirmasi lewat `pg_class.relacl` — grant tidak muncul). Akar masalah: tabel `mart_cleaned.*` dimiliki `reverse_etl_writer` (dibuat lewat koneksi role itu di `sync.py`), sedangkan schema `mart_cleaned` itu sendiri dan seluruh view `analyst_views.*` dimiliki `postgres` (admin). Solusi: `apply_grants()` di `setup_analyst_roles.py` diperbaiki untuk merutekan `GRANT USAGE ON SCHEMA` selalu lewat admin (pemilik schema), tapi `GRANT SELECT` ke tabel `mart_cleaned` lewat koneksi `reverse_etl_writer` (`get_mart_cleaned_owner_connection()`, baru ditambahkan ke `connections.py`).
- **Temuan #2 — Supavisor pooler cache tidak langsung sinkron.** Setelah perbaikan Temuan #1, verifikasi masih gagal 2x berturut-turut dengan `permission denied`/`password authentication failed` meski grant sudah benar terbukti ada di `pg_class.relacl`/`pg_namespace.nspacl`. Diagnosis: pooler Supavisor menyimpan cache kredensial/privilege yang tidak langsung ter-refresh pasca `CREATE ROLE`/`ALTER ROLE`/`GRANT`. Solusi: `verify_role_isolation.py` ditambah mekanisme warm-up-retry (`_connect_with_warmup`, maks 6 percobaan, jeda 5 detik) sebelum menjalankan suite verifikasi sungguhan — terbukti berhasil pada percobaan ke-2 (5 detik) saat dites ulang.
- **Verifikasi final (setelah kedua fix)**: seluruh check lolos — `ALLOW` ke view/tabel sendiri sukses, `DENY` ke `mart_aggregated` langsung/`payroll`/view HR/`fnb_transactions` gagal `InsufficientPrivilege`, `WRITE` (INSERT) gagal. `REVENUE_ANALYST_READER_DB_URL` ditulis ke `.env` (dikonfirmasi ada, value tidak pernah dicetak).
- **Catatan pemulihan**: sesi sempat terputus (komputer mati) tepat setelah checkpoint ini selesai tapi sebelum commit — dicek ulang saat resume: role `revenue_analyst_reader` dan entri `.env` masih utuh di database sungguhan (state Postgres tidak terpengaruh restart lokal), lanjut commit tanpa perlu mengulang kerja.

## 2026-08-09 — Checkpoint 3: F&B role

- `role_config_fnb.py` ditulis, GRANT target dari `whitelist_fnb.py` (8 view + `fnb_transactions`).
- Dengan kedua fix Checkpoint 2 (routing ownership + warmup-retry) sudah di tempat, role ini berhasil lolos verifikasi **tanpa retry sama sekali** — mengonfirmasi kedua fix itu genuinely menyelesaikan akar masalah, bukan kebetulan.
- Verifikasi: `ALLOW` ke `v_fnb_outlet_daily`/`fnb_transactions` sukses, `DENY` ke `mart_aggregated.fact_fnb_outlet_daily`/`payroll`/`bookings`/HR watchlist gagal `InsufficientPrivilege`, `WRITE` gagal. `FNB_ANALYST_READER_DB_URL` ditulis ke `.env`.

## 2026-08-09 — Checkpoint 4: Facility/Ops role

- `role_config_facility.py` ditulis, GRANT target dari `whitelist_facility.py` (9 view + `maintenance_tickets`).
- Lolos verifikasi bersih tanpa retry.
- Verifikasi: `ALLOW` ke `v_maintenance_ticket_daily`/`maintenance_tickets` sukses, `DENY` ke `mart_aggregated.fact_maintenance_ticket_daily`/`payroll`/`bookings`/HR watchlist gagal, `WRITE` gagal. `FACILITY_ANALYST_READER_DB_URL` ditulis ke `.env`.

## 2026-08-09 — Checkpoint 5: Spa & Event role

- `role_config_spa_event.py` ditulis, GRANT target dari `whitelist_spa_event.py` (6 view + `event_bookings`).
- Lolos verifikasi bersih tanpa retry.
- Verifikasi: `ALLOW` ke `v_event_venue_daily`/`event_bookings` sukses, `DENY` ke `mart_aggregated.fact_event_venue_daily`/`payroll`/`bookings`/HR watchlist gagal, `WRITE` gagal. `SPA_EVENT_ANALYST_READER_DB_URL` ditulis ke `.env`.

## 2026-08-09 — Checkpoint 6: HR role — business rule kritis KK1 diverifikasi

- `role_config_hr.py` ditulis, GRANT target dari `whitelist_hr.py` (8 view + `staff_shifts`/`employee_performance`, tanpa payroll sama sekali).
- **Deny-check diperkuat khusus untuk KK1 M3.5** (contoh literal dokumen sumber, "HR Analyst tidak bisa mengakses `payroll`") — 5 deny-check terkait payroll sekaligus: `mart_cleaned.payroll` langsung, `v_payroll_department_monthly`, `v_payroll_access_level_monthly`, `v_financial_service_charge_monthly`, `v_financial_labor_cost_monthly`. Semua gagal `InsufficientPrivilege` sesuai harapan.
- Lolos verifikasi bersih tanpa retry.

## 2026-08-09 — Checkpoint 7: Corporate/Financial role — pengujian paling kritis di seluruh milestone

- `role_config_corporate_financial.py` ditulis, GRANT target dari `whitelist_corporate_financial.py` (9 view + `financial_summary`/`payroll` — satu-satunya role yang memang berhak payroll).
- **Deny-check terpenting M3.5**: `SELECT` langsung ke `mart_aggregated.fact_financial_business_line_monthly` (tabel dasar di balik `v_financial_departmental_margin`) — kalau ini tembus, role bisa melihat baris `Overall`/`Corporate Overhead` yang sengaja disembunyikan filter view (business rule M3.2). Hasil: **gagal `InsufficientPrivilege`**, konsisten temuan Keputusan #8 Checkpoint 1 (view privilege pemilik, bypass tabel dasar otomatis mustahil tanpa grant eksplisit).
- Verifikasi lengkap: `ALLOW` ke `v_financial_departmental_margin`/`payroll`/`financial_summary` sukses; `DENY` ke tabel dasar bypass, `bookings`, `fnb_transactions`, HR watchlist view semua gagal; `WRITE` gagal. Lolos bersih tanpa retry.

## 2026-08-09 — Checkpoint 8: Property/GM role (role inheritance)

- `role_config_property_gm.py` ditulis — **jalur berbeda** dari 6 role domain: tidak ada `grant_targets`, cuma `member_of` (5 role domain non-financial). `setup_analyst_roles.py` ditambah `apply_membership()`: `GRANT revenue_analyst_reader, fnb_analyst_reader, facility_analyst_reader, spa_event_analyst_reader, hr_analyst_reader TO property_gm_analyst_reader` — 1 statement, bukan re-grant 39 objek.
- Verifikasi: `ALLOW` ke 1 view/tabel representatif tiap 5 domain (revenue, fnb, facility, spa-event, hr) semua sukses lewat privilege warisan — membuktikan `INHERIT` default Postgres bekerja tanpa perlu `SET ROLE` eksplisit. `DENY`: tabel dasar bypass, **`v_financial_departmental_margin`, `v_financial_business_line_group_monthly`** (business rule #3 M3.1 — larangan eksplisit akses tabel level-grup), `payroll`, `financial_summary` — semua gagal `InsufficientPrivilege`. `WRITE` gagal. Lolos bersih tanpa retry.
- Role union Property/GM Analyst selesai tanpa perlu artefak GRANT baru — konsisten pola "tidak butuh artefak terpisah" yang sudah berlaku sejak M3.2/M3.3/M3.4.

## 2026-08-09 — Checkpoint 9 (final) — Tutup milestone

- `docs/06-akses-kredensial/kebijakan-akses-kredensial-scoped.md` diupdate: 7 baris inventaris baru, bagian "Siapa Boleh Memegang" ditambah entri analyst, referensi verifier Postgres generik baru (menggantikan pola inline lama untuk kredensial analyst spesifik).
- `docs/08-serving-data-analyst/kredensial-analyst.md` ditulis — Output resmi #2 M3.5.
- **Verifikasi akhir menyeluruh**: `pg_roles` dikonfirmasi seluruh 7 role `rolcanlogin=true, rolsuper=false, rolcreatedb=false, rolcreaterole=false`. Sempat ditemukan `information_schema.role_table_grants` tidak menampilkan grant lengkap untuk tabel yang di-grant oleh `reverse_etl_writer` (bukan admin) — dikonfirmasi ini keterbatasan visibility `information_schema` untuk non-superuser, bukan grant yang hilang; `pg_class.relacl` dipakai sebagai sumber kebenaran dan menunjukkan jumlah grant persis cocok dengan log tiap checkpoint (revenue=10, fnb=9, facility=10, spa_event=7, hr=10, corporate_financial=11, property_gm=0 langsung/mewarisi).
- `report.md` ditulis, mendokumentasikan 2 temuan operasional signifikan (ownership routing, pooler warm-up) sebagai deviations eksplisit.
- Milestone ditutup. Fase Data Analyst Serving (M3.1-3.5) selesai penuh.
