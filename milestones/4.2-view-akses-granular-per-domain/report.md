# Milestone 4.2: View Akses Granular per Domain — Report

**Status:** Completed
**Date completed:** 2026-08-10

## Kriteria Keberhasilan — Hasil

- [x] **Setiap domain data punya view yang mengembalikan hanya kolom yang relevan dengan domain tersebut.** — 67 view aktif di `chatbot_views` (verifikasi: `information_schema.views`), dikelompokkan per 10 `data_domain` sesuai `pemetaan-akses-teknis-chatbot.md`. Tidak ada view yang join lintas domain di luar batas yang dikontrakkan (mis. view domain `reservation`/`fnb`/`facility`/`spa_event`/`hr` tidak pernah join ke `guests` — kontak/profil tamu cuma lewat `guests_contact_view`/`guests_profile_view` sendiri).
- [x] **Percobaan mengakses kolom PII lewat `guests_profile_view` (atau sebaliknya) gagal karena kolom tersebut memang tidak ada di view itu.** — Diverifikasi terprogram (`information_schema.columns`): `guests_profile_view` = `guest_id, loyalty_tier, nationality, registered_date, last_active_property_id` (tidak ada `email`/`phone`/`full_name`); `guests_contact_view` = `guest_id, full_name, email, phone, last_active_property_id` (tidak ada `loyalty_tier`/`nationality`). Assertion Python lolos, bukan dicek visual saja.
- [x] **Filter `own_property`/`all_properties` terbukti bekerja benar pada uji coba dengan beberapa `property_id` berbeda.** — Diuji pada 6 view representatif (agregat: `v_reservation_room_type_daily`, `v_financial_departmental_margin`, `v_hr_employee_monthly`; lookup: `v_lookup_bookings`, `v_lookup_fnb_inventory`, `v_lookup_housekeeping_log`) dengan `WHERE property_id IN ('P01','P02') GROUP BY property_id` — seluruhnya menghasilkan 2 baris berbeda, keduanya non-kosong. Termasuk 2 view lookup yang `property_id`-nya hasil join (bukan native), membuktikan join bekerja benar, bukan cuma kolom native yang teruji.

## Deliverables

- `scripts/chatbot_views/{schema.sql,connections.py,apply_views.py,views_reservation.sql,views_fnb.sql,views_facility.sql,views_spa_event.sql,views_hr.sql,views_financial.sql,views_properties_ref.sql,views_employees_directory.sql,views_guests.sql}` — 67 view aktif di schema `chatbot_views`, serving PostgreSQL.
- `docs/09-serving-ai-chatbot/view-query-pattern-chatbot.md` — inventaris seluruh view, pola sama `view-query-pattern-analyst.md`.
- Update `docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md` §3 (koreksi `event_bookings` tidak punya `guest_id`).

## Deviations from decisions.md

- Tidak ada deviasi dari `decisions.md` — seluruh 7 keputusan teknis dieksekusi persis seperti direncanakan (schema `chatbot_views`, 2 lapis view per domain operasional, nama `guests_contact_view`/`guests_profile_view` dikunci, `property_id` selalu mentah, plain SQL + Python runner, koneksi admin, 9 file per domain).
- **2 koreksi teknis ditemukan saat implementasi** (bukan deviasi dari keputusan, melainkan detail yang salah di pemetaan M4.1 §3, diperbaiki begitu ketahuan — pola sama seperti koreksi grain M5.3):
  1. `event_bookings` tidak punya kolom `guest_id` — dikeluarkan dari `UNION` `last_active_property_id`.
  2. Draf awal `guests_contact_view`/`guests_profile_view` pakai `LEFT JOIN LATERAL` per baris guest (correlated subquery × 24.893 guest) — timeout nyata (>120 detik). Diganti 1x scan agregat dengan `DISTINCT ON` — turun jadi 0.44 detik.
  3. (Ditemukan Fase 3) 3 lookup view (`v_lookup_fnb_inventory`, `v_lookup_fnb_transactions`, `v_lookup_housekeeping_log`) awalnya lupa menyertakan `property_id` — tabel sumbernya tidak punya kolom itu native, perlu join ke `fnb_outlets`/`rooms`. Diperbaiki sebelum Checkpoint 3 selesai.

## Known Gaps / Follow-ups

- **Index performa** belum ditambahkan untuk `chatbot_views` — tidak ada milestone index khusus untuk chatbot (beda dari Data Analyst yang punya M3.3 tersendiri). Query `guests_contact_view`/`guests_profile_view` sudah terbukti cepat (0.44 detik) tanpa index tambahan karena pendekatan `DISTINCT ON` 1x scan, tapi performa view lain (terutama `v_lookup_*` di atas tabel besar seperti `fnb_transactions` 902k baris, `housekeeping_log` 424k baris) belum diuji di bawah beban query API sungguhan (Milestone 4.4) — revisit kalau ada gejala lambat.
- **`v_lookup_financial_summary`** mengembalikan seluruh baris termasuk `Overall`/`Corporate Overhead` — pemanggil (API, M4.4) wajib menerapkan filter yang sesuai konteks (GOP dari baris `Overall`, departmental margin exclude `Overall`), sama seperti versi agregat. Belum ada enforcement di level view untuk row-level ini (beda dari `v_financial_departmental_margin` yang sudah menanam `WHERE`).
- Seluruh Known Gap carry-over dari M3.1/M3.2 (threshold SLA belum final untuk kasus lain selain Facility ticket, gap data harga menu resmi, dst) tetap berlaku sama untuk chatbot — tidak diulang di sini, lihat `pemetaan-akses-teknis-chatbot.md`.

## Handoff Notes

- **Untuk Milestone 4.3 (kredensial):** Skema `chatbot_views` siap di-GRANT per view/per kelompok akses (10 kelompok sesuai `data_domain`, per M4.1 §4). Belum ada role Postgres apa pun yang dibuat di milestone ini — `SERVING_DB_URL` (admin) dipakai murni untuk authoring/apply DDL, sama pola M3.2.
- **Untuk Milestone 4.4 (API):** Filter `own_property`/`all_properties` **belum diterapkan di mana pun** — setiap view mengembalikan seluruh baris lintas 5 properti apa adanya (`property_id` sebagai kolom mentah). API wajib menyuntikkan `WHERE property_id = :user_property_id` untuk role `own_property`, memvalidasi terhadap `role_permissions.access_scope`. Filtering performa individu staff (`staff_id`/`assigned_staff_id` = diri sendiri untuk role Staff) juga sepenuhnya belum diterapkan — sama-sama tanggung jawab M4.4.
- **`v_lookup_financial_summary`** butuh perhatian khusus di API — beda dari view agregat yang sudah aman secara desain, filter GOP vs departmental margin untuk data row-level ini masih harus ditulis eksplisit di query layer.
