-- Milestone 4.2: AI Chatbot views -- domain `guests_pii` + `guests_profile`.
-- Source: mart_cleaned.guests, kolom dipisah 2 view berbeda di atas tabel
-- fisik yang sama (see docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md §3,
-- rancangan-rbac-ai-chatbot.md Bagian 4).
--
-- KOREKSI saat implementasi (M4.2): pemetaan M4.1 §3 menyebut
-- last_active_property_id diturunkan dari UNION bookings/spa_bookings/
-- event_bookings -- ternyata event_bookings TIDAK punya kolom guest_id sama
-- sekali (klien event diidentifikasi via client_name teks bebas, bukan tamu
-- terdaftar), dikonfirmasi ulang terhadap Metadata.md saat menulis SQL ini.
-- last_active_property_id di bawah hanya menggabungkan bookings + spa_bookings
-- (dua-duanya punya guest_id FK ke guests) -- event_bookings dikeluarkan.

-- PERBAIKAN PERFORMA (M4.2): draf awal pakai LEFT JOIN LATERAL per baris guest
-- (correlated subquery x 24.867 guest, scan penuh bookings+spa_bookings tiap
-- baris) -- timeout di uji coba nyata. Diganti pendekatan 1x scan agregat:
-- gabungkan bookings+spa_bookings sekali (UNION ALL), lalu DISTINCT ON per
-- guest_id diurutkan tanggal terbaru -- baru di-LEFT JOIN sekali ke guests.
CREATE OR REPLACE VIEW chatbot_views.guests_contact_view AS
SELECT
    g.guest_id,
    g.full_name,
    g.email,
    g.phone,
    lap.last_active_property_id
FROM mart_cleaned.guests g
LEFT JOIN (
    SELECT DISTINCT ON (combined.guest_id)
        combined.guest_id,
        combined.property_id AS last_active_property_id
    FROM (
        SELECT guest_id, property_id, booking_date AS activity_date
        FROM mart_cleaned.bookings
        WHERE guest_id IS NOT NULL
        UNION ALL
        SELECT guest_id, property_id, booking_date AS activity_date
        FROM mart_cleaned.spa_bookings
        WHERE guest_id IS NOT NULL
    ) combined
    ORDER BY combined.guest_id, combined.activity_date DESC
) lap ON lap.guest_id = g.guest_id;

CREATE OR REPLACE VIEW chatbot_views.guests_profile_view AS
SELECT
    g.guest_id,
    g.loyalty_tier,
    g.nationality,
    g.registered_date,
    lap.last_active_property_id
FROM mart_cleaned.guests g
LEFT JOIN (
    SELECT DISTINCT ON (combined.guest_id)
        combined.guest_id,
        combined.property_id AS last_active_property_id
    FROM (
        SELECT guest_id, property_id, booking_date AS activity_date
        FROM mart_cleaned.bookings
        WHERE guest_id IS NOT NULL
        UNION ALL
        SELECT guest_id, property_id, booking_date AS activity_date
        FROM mart_cleaned.spa_bookings
        WHERE guest_id IS NOT NULL
    ) combined
    ORDER BY combined.guest_id, combined.activity_date DESC
) lap ON lap.guest_id = g.guest_id;
