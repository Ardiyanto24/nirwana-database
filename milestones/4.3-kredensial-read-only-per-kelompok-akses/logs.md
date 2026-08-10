# Milestone 4.3 — Execution Log

## 2026-08-10 -- Mulai, breakdown via planning-and-task-breakdown skill
Did: Baca kontrak sumber (`05-serving-ai-chatbot.md` Milestone 4.3), preseden `milestones/3.5-isolasi-akses-kredensial-analyst/decisions.md` dan seluruh script `scripts/data_analyst_credentials/` (connections.py, setup_analyst_roles.py, verify_role_isolation.py, role_config_revenue.py, grant_utils.py, role_config_hr.py) untuk pola pembuatan role Postgres. Identifikasi beda struktural dari M3.5: M4.2 sudah mengunci seluruh akses (agregat+row-level) lewat view `chatbot_views` -- jadi M4.3 cuma perlu GRANT ke chatbot_views, tidak pernah ke mart_aggregated/mart_cleaned langsung, menghilangkan kerumitan owner-routing M3.5 (get_mart_cleaned_owner_connection). Sumber grant target = inventaris 67 view M4.2, bukan whitelist API (M4.4 belum ada).
Result: Plan (10 role 1:1 data_domain, GRANT hanya ke chatbot_views, 6 fase/6 checkpoint) ditulis ke plan file, disetujui user, plan mode exited. `decisions.md` ditulis lengkap.

## 2026-08-10 -- Fase 0: fondasi
Did: Query `pg_class.relowner` join `pg_roles` untuk seluruh 67 view schema `chatbot_views` -- verifikasi empiris Keputusan #3/#8: semua dimiliki 1 role (`postgres`, sama dengan role di balik `SERVING_DB_URL`). Buat `scripts/chatbot_credentials/{connections.py,verify_role_isolation.py,setup_chatbot_roles.py}` (copy pola M3.5, connections.py TANPA get_mart_cleaned_owner_connection -- tidak dibutuhkan). Update `.env.example` (10 baris `*_CHATBOT_READER_DB_URL`).
Result: worked. Asumsi terbukti: 67/67 view owner = 1 role, GRANT selalu lewat 1 koneksi admin, tidak perlu owner-routing seperti M3.5.

## 2026-08-10 -- Fase 1: reservation + fnb roles
Did: `role_config_reservation.py` (10 GRANT_TARGETS) dan `role_config_fnb.py` (11 GRANT_TARGETS), masing-masing dengan deny-check role_permissions eksplisit (M4.1 Keputusan #7) selain bypass mart_aggregated/mart_cleaned dan cross-domain. `python setup_chatbot_roles.py --role <nama>` dijalankan per role.
Result: worked. Kedua role: 9/9 check OK (2 allow, 6 deny, 1 write-deny). Tidak ada retry pooler warmup diperlukan (langsung sukses attempt pertama, beda dari beberapa kasus M3.5).
