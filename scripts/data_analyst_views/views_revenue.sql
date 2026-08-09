-- Milestone 3.2: Revenue Analyst views.
-- Source: mart_aggregated.fact_revenue_* (see docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md #1).
-- fact_revenue_pace_booking_snapshot intentionally excluded -- implementation status
-- vs BigQuery Sandbox DML block is unresolved (Known Gap, M3.1 report.md).

CREATE OR REPLACE VIEW analyst_views.v_revenue_room_type_daily AS
SELECT
    f.property_id,
    p.property_name,
    p.region,
    rt.room_type_name,
    f.period_date,
    f.rooms_sold,
    f.total_rooms_available,
    f.occupancy_rate,
    f.adr,
    f.revpar,
    f.revenue,
    f.room_type_revenue_share_pct
FROM mart_aggregated.fact_revenue_room_type_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_room_type rt ON rt.room_type_id = f.room_type_id;

CREATE OR REPLACE VIEW analyst_views.v_revenue_channel_daily AS
SELECT
    f.property_id,
    p.property_name,
    p.region,
    c.channel_name,
    f.period_date,
    f.revenue,
    f.bookings_count,
    f.cancellations_count,
    f.no_shows_count
FROM mart_aggregated.fact_revenue_channel_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_channel c ON c.channel_id = f.channel_id;

CREATE OR REPLACE VIEW analyst_views.v_revenue_los_daily AS
SELECT
    f.property_id,
    p.property_name,
    rt.room_type_name,
    c.channel_name,
    f.period_date,
    f.avg_los_nights,
    f.median_los_nights
FROM mart_aggregated.fact_revenue_los_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_room_type rt ON rt.room_type_id = f.room_type_id
LEFT JOIN mart_aggregated.dim_channel c ON c.channel_id = f.channel_id;

CREATE OR REPLACE VIEW analyst_views.v_revenue_property_daily AS
SELECT
    f.property_id,
    p.property_name,
    p.region,
    f.period_date,
    f.avg_lead_time_days,
    f.median_lead_time_days,
    f.mom_occupancy_growth,
    f.yoy_occupancy_growth,
    f.mom_adr_growth,
    f.yoy_adr_growth,
    f.mom_revpar_growth,
    f.yoy_revpar_growth,
    f.repeat_guest_rate,
    f.revpar_rank_group,
    f.adr_rank_group,
    f.occupancy_rank_group
FROM mart_aggregated.fact_revenue_property_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

-- Cross-domain (booking pricing x GOP): gop_margin here comes from financial_summary's
-- Overall row via M5.3's transform, consistent with the "Overall = GOP source" rule
-- also enforced in views_corporate_financial.sql.
CREATE OR REPLACE VIEW analyst_views.v_revenue_gop_impact_monthly AS
SELECT
    f.property_id,
    p.property_name,
    f.period_date,
    f.avg_pricing_deviation,
    f.gop_margin
FROM mart_aggregated.fact_revenue_gop_impact_monthly f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id;

CREATE OR REPLACE VIEW analyst_views.v_revenue_pricing_deviation AS
SELECT
    f.property_id,
    p.property_name,
    r.reason_name,
    f.period_date,
    f.avg_applied_rate,
    f.avg_base_rate,
    f.avg_deviation_pct,
    f.day_share_pct
FROM mart_aggregated.fact_revenue_pricing_deviation f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_pricing_reason r ON r.reason_id = f.reason_id;

CREATE OR REPLACE VIEW analyst_views.v_revenue_loyalty_daily AS
SELECT
    f.property_id,
    p.property_name,
    lt.loyalty_tier_name,
    f.period_date,
    f.bookings_count,
    f.revenue
FROM mart_aggregated.fact_revenue_loyalty_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_loyalty_tier lt ON lt.loyalty_tier_id = f.loyalty_tier_id;

CREATE OR REPLACE VIEW analyst_views.v_revenue_nationality_daily AS
SELECT
    f.property_id,
    p.property_name,
    ng.group_name AS nationality_group_name,
    f.period_date,
    f.bookings_count,
    f.revenue
FROM mart_aggregated.fact_revenue_nationality_daily f
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = f.property_id
LEFT JOIN mart_aggregated.dim_nationality_group ng ON ng.nationality_group_id = f.nationality_group_id;
