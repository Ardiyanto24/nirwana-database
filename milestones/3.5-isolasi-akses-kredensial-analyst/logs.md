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
