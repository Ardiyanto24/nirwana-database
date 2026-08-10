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

## 2026-08-10 -- Fase 2: facility + spa_event roles
Did: `role_config_facility.py` (12 GRANT_TARGETS) dan `role_config_spa_event.py` (9 GRANT_TARGETS), pola sama Fase 1.
Result: worked. Kedua role: 9/9 check OK masing-masing.

## 2026-08-10 -- Fase 3: hr + financial roles
Did: `role_config_hr.py` (10 GRANT_TARGETS, 6 deny-check payroll-adjacent eksplisit: mart_cleaned.payroll, v_lookup_payroll, v_payroll_department_monthly, v_payroll_access_level_monthly, v_financial_service_charge_monthly, v_financial_labor_cost_monthly). `role_config_financial.py` (11 GRANT_TARGETS, deny-check bypass fact_financial_business_line_monthly -- business rule Overall exclusion paling kritis).
Result: worked. hr: 12/12 check OK (2 allow, 9 deny, 1 write). financial: 8/8 check OK.

## 2026-08-10 -- Fase 4: 4 domain granular roles
Did: `role_config_properties_ref.py`/`role_config_employees_directory.py` (1 GRANT_TARGETS masing-masing). `role_config_guests_pii.py`/`role_config_guests_profile.py` (1 GRANT_TARGETS masing-masing: guests_contact_view/guests_profile_view), dengan deny-check krusial di kedua arah: role guests_pii tidak boleh baca guests_profile_view, role guests_profile tidak boleh baca guests_contact_view -- membuktikan pemisahan kolom PII vs profile M4.2 benar-benar tertegakkan di level kredensial, bukan cuma di level view.
Result: worked. Keempat role lolos seluruh check, termasuk kedua uji silang guests_pii<->guests_profile.
