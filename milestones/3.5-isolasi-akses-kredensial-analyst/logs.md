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
