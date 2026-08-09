-- Milestone 3.2: Spa & Event Analyst views.
-- Source: mart_aggregated.fact_spa_*/fact_event_*
-- (see docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md #4).
-- Business rule kritis M3.1: repeat-client-event and spa x event cross-sell are NOT
-- modeled here or anywhere -- client_name is free text (no structured ID) and there is
-- no guest_id link between spa_bookings and event_bookings.

CREATE OR REPLACE VIEW analyst_views.v_spa_daily AS
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

CREATE OR REPLACE VIEW analyst_views.v_spa_customer_type_daily AS
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

CREATE OR REPLACE VIEW analyst_views.v_spa_service_daily AS
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

CREATE OR REPLACE VIEW analyst_views.v_event_venue_daily AS
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

CREATE OR REPLACE VIEW analyst_views.v_event_property_daily AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.cancellation_rate
FROM mart_aggregated.fact_event_property_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW analyst_views.v_event_type_daily AS
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
