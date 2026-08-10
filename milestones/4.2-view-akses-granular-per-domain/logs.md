# Milestone 4.2 — Execution Log

## 2026-08-10 -- Mulai, breakdown via planning-and-task-breakdown skill
Did: Baca kontrak sumber (`05-serving-ai-chatbot.md` Milestone 4.2), preseden `milestones/3.2-view-dan-query-pattern-per-domain/decisions.md` (struktur task breakdown, schema `analyst_views`, pola file SQL per domain), `scripts/data_analyst_views/` (struktur file nyata: schema.sql, connections.py, apply_views.py, views_*.sql). Identifikasi beda penting: M3.2 cuma view agregat (row-level Data Analyst lewat GRANT langsung ke mart_cleaned), tapi chatbot tidak boleh GRANT langsung ke mart_cleaned mentah (kebutuhan guests_pii/profile sudah memaksa kurasi kolom) -- diputuskan seragamkan seluruh 10 domain lewat view, bukan cuma domain guest.
Result: Plan (schema chatbot_views, 2 lapis view per domain operasional, 9 file SQL, 6 fase/6 checkpoint) ditulis ke plan file, disetujui user, plan mode exited. `decisions.md` ditulis lengkap.

## 2026-08-10 -- Fase 0: fondasi
Did: Baca kolom lengkap seluruh tabel `mart_cleaned` yang relevan (bookings, daily_occupancy, fnb_transactions, recipe_bom, fnb_inventory, rooms, housekeeping_log, maintenance_tickets, venues, spa_bookings, event_bookings, staff_shifts, employee_performance, payroll, financial_summary, employees) dari `Metadata.md` untuk memastikan SQL view lookup akurat terhadap skema nyata. Buat `scripts/chatbot_views/{schema.sql,connections.py,apply_views.py}` (copy pola `scripts/data_analyst_views/`). Apply `schema.sql`.
Result: worked. `chatbot_views` terverifikasi ada di `information_schema.schemata`.

## 2026-08-10 -- Fase 1: reservation + fnb
Did: `views_reservation.sql` (8 agregat dari fact_revenue_*, dinamai domain `reservation` bukan `revenue` -- konsisten nama data_domain di role_permissions -- + 2 lookup: v_lookup_bookings, v_lookup_daily_occupancy). `views_fnb.sql` (8 agregat identik pola M3.2 + 3 lookup: v_lookup_fnb_inventory, v_lookup_fnb_transactions, v_lookup_recipe_bom). Kedua file sengaja tidak join ke `guests` -- domain guests_pii/profile harus lewat view sendiri, tidak boleh bocor lewat view domain lain. Apply via `apply_views.py`.
Result: worked. 21 view aktif di `information_schema.views` schema `chatbot_views`. Verifikasi data nyata: `v_reservation_room_type_daily` mengembalikan baris valid, `v_lookup_bookings` 217.654 baris, `v_lookup_fnb_transactions` 902.574 baris -- cocok skala tabel sumber di `Metadata.md`.
