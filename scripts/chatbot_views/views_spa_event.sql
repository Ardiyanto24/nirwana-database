-- Milestone 4.2: AI Chatbot views -- domain `spa_event`.
-- Source (aggregate): mart_aggregated.fact_spa_*/fact_event_*
-- (see docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md §2.4).
-- Business rule kritis M3.1 (berlaku sama untuk chatbot): repeat-client-event
-- dan cross-sell spa x event TIDAK dimodelkan di sini atau di mana pun --
-- client_name teks bebas (tanpa ID terstruktur), tidak ada guest_id penghubung
-- antara spa_bookings dan event_bookings.

CREATE OR REPLACE VIEW chatbot_views.v_spa_daily AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.revenue,
    f.booking_count,
    f.walk_in_ratio,
    f.avg_lead_time_days,
    f.median_lead_time_days,
    f.cancellation_rate
FROM mart_aggregated.fact_spa_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW chatbot_views.v_spa_customer_type_daily AS
SELECT
    f.property_id,
    p.property_name,
    ct.customer_type_name,
    f.period_date,
    f.revenue,
    f.visit_count,
    f.revenue_per_visit
FROM mart_aggregated.fact_spa_customer_type_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_customer_type ct ON ct.customer_type_id = f.customer_type_id;

CREATE OR REPLACE VIEW chatbot_views.v_spa_service_daily AS
SELECT
    f.property_id,
    p.property_name,
    s.service_name,
    f.period_date,
    f.booking_count,
    f.revenue,
    f.revenue_share_pct
FROM mart_aggregated.fact_spa_service_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_spa_service s ON s.service_id = f.service_id;

CREATE OR REPLACE VIEW chatbot_views.v_event_venue_daily AS
SELECT
    v.property_id,
    p.property_name,
    f.venue_id,
    v.venue_name,
    vt.venue_type_name,
    v.max_capacity,
    f.period_date,
    f.bookings_pipeline_count,
    f.revenue_pipeline,
    f.utilization_rate,
    f.mom_revenue_growth,
    f.yoy_revenue_growth,
    f.low_utilization_days_last_30
FROM mart_aggregated.fact_event_venue_daily f
LEFT JOIN mart_aggregated.dim_venue v ON v.venue_id = f.venue_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = v.property_id
LEFT JOIN mart_aggregated.dim_venue_type vt ON vt.venue_type_id = v.venue_type_id;

CREATE OR REPLACE VIEW chatbot_views.v_event_property_daily AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.cancellation_rate
FROM mart_aggregated.fact_event_property_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW chatbot_views.v_event_type_daily AS
SELECT
    f.property_id,
    p.property_name,
    et.event_type_name,
    f.period_date,
    f.event_count,
    f.revenue
FROM mart_aggregated.fact_event_type_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_event_type et ON et.event_type_id = f.event_type_id;

-- Row-level lookup views (Keputusan #2). guest_id diteruskan sebagai FK
-- mentah (nullable, walk-in) -- tidak join ke guests, domain guests_pii
-- terpisah.

-- Untuk kebutuhan Spa & Event Staff: jadwal booking spa hari ini/mendatang.
CREATE OR REPLACE VIEW chatbot_views.v_lookup_spa_bookings AS
SELECT
    s.spa_booking_id,
    s.property_id,
    s.guest_id,
    s.customer_type,
    s.service_name,
    s.booking_date,
    s.service_date,
    s.duration_minutes,
    s.price,
    s.status
FROM mart_cleaned.spa_bookings s;

-- Untuk kebutuhan Spa & Event Staff: detail booking event, ketersediaan venue.
CREATE OR REPLACE VIEW chatbot_views.v_lookup_event_bookings AS
SELECT
    e.event_id,
    e.property_id,
    e.venue_id,
    e.client_name,
    e.event_type,
    e.event_date,
    e.venue_name,
    e.capacity_booked,
    e.total_revenue,
    e.status
FROM mart_cleaned.event_bookings e;

-- Untuk kebutuhan Spa & Event Staff: kapasitas maksimal venue.
CREATE OR REPLACE VIEW chatbot_views.v_lookup_venues AS
SELECT
    v.venue_id,
    v.property_id,
    v.venue_name,
    v.venue_type,
    v.max_capacity
FROM mart_cleaned.venues v;
