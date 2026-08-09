-- Milestone 3.2: F&B Analyst views.
-- Source: mart_aggregated.fact_fnb_* (see docs/08-serving-data-analyst/pemetaan-pola-akses-analyst.md #2).
-- property_id is resolved via dim_outlet.property_id (fact tables here are keyed by
-- outlet_id, not property_id directly -- an outlet always belongs to exactly 1 property).
-- Basket analysis is intentionally NOT a view here -- business rule kritis M3.1: it can
-- only be served row-level from mart_cleaned.fnb_transactions (grain per struk).

CREATE OR REPLACE VIEW analyst_views.v_fnb_outlet_daily AS
SELECT
    o.property_id,
    p.property_name,
    f.outlet_id,
    o.outlet_name,
    ot.outlet_type_name,
    f.period_date,
    f.revenue,
    f.transaction_count,
    f.avg_check,
    f.mom_revenue_growth,
    f.yoy_revenue_growth,
    f.capture_rate,
    f.walk_in_ratio,
    f.revenue_rank_vs_outlet_type_avg
FROM mart_aggregated.fact_fnb_outlet_daily f
LEFT JOIN mart_aggregated.dim_outlet o ON o.outlet_id = f.outlet_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = o.property_id
LEFT JOIN mart_aggregated.dim_outlet_type ot ON ot.outlet_type_id = o.outlet_type_id;

CREATE OR REPLACE VIEW analyst_views.v_fnb_category_daily AS
SELECT
    o.property_id,
    p.property_name,
    f.outlet_id,
    o.outlet_name,
    cat.category_name,
    f.period_date,
    f.revenue
FROM mart_aggregated.fact_fnb_category_daily f
LEFT JOIN mart_aggregated.dim_outlet o ON o.outlet_id = f.outlet_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = o.property_id
LEFT JOIN mart_aggregated.dim_fnb_category cat ON cat.category_id = f.category_id;

CREATE OR REPLACE VIEW analyst_views.v_fnb_hourly AS
SELECT
    o.property_id,
    p.property_name,
    f.outlet_id,
    o.outlet_name,
    f.period_date,
    f.hour_of_day,
    f.transaction_count
FROM mart_aggregated.fact_fnb_hourly f
LEFT JOIN mart_aggregated.dim_outlet o ON o.outlet_id = f.outlet_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = o.property_id;

CREATE OR REPLACE VIEW analyst_views.v_fnb_customer_type_daily AS
SELECT
    o.property_id,
    p.property_name,
    f.outlet_id,
    o.outlet_name,
    ct.customer_type_name,
    f.period_date,
    f.revenue,
    f.visit_count,
    f.revenue_per_visit
FROM mart_aggregated.fact_fnb_customer_type_daily f
LEFT JOIN mart_aggregated.dim_outlet o ON o.outlet_id = f.outlet_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = o.property_id
LEFT JOIN mart_aggregated.dim_customer_type ct ON ct.customer_type_id = f.customer_type_id;

CREATE OR REPLACE VIEW analyst_views.v_fnb_menu_item_daily AS
SELECT
    o.property_id,
    p.property_name,
    f.outlet_id,
    o.outlet_name,
    f.item_name,
    f.period_date,
    f.revenue,
    f.quantity_sold,
    f.food_cost_ratio_actual,
    f.food_cost_ratio_target,
    f.food_cost_deviation
FROM mart_aggregated.fact_fnb_menu_item_daily f
LEFT JOIN mart_aggregated.dim_outlet o ON o.outlet_id = f.outlet_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = o.property_id;

CREATE OR REPLACE VIEW analyst_views.v_fnb_waste_daily AS
SELECT
    o.property_id,
    p.property_name,
    f.outlet_id,
    o.outlet_name,
    wr.reason_name,
    f.period_date,
    f.waste_value,
    f.waste_quantity,
    f.waste_ratio
FROM mart_aggregated.fact_fnb_waste_daily f
LEFT JOIN mart_aggregated.dim_outlet o ON o.outlet_id = f.outlet_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = o.property_id
LEFT JOIN mart_aggregated.dim_waste_reason wr ON wr.reason_id = f.reason_id;

CREATE OR REPLACE VIEW analyst_views.v_fnb_inventory_status AS
SELECT
    o.property_id,
    p.property_name,
    f.outlet_id,
    o.outlet_name,
    f.period_date,
    f.low_stock_item_count
FROM mart_aggregated.fact_fnb_inventory_status f
LEFT JOIN mart_aggregated.dim_outlet o ON o.outlet_id = f.outlet_id
LEFT JOIN mart_aggregated.dim_property p ON p.property_id = o.property_id;

-- No property_id: ingredient pricing is grain-level global (not tied to 1 outlet/property).
CREATE OR REPLACE VIEW analyst_views.v_fnb_ingredient_price_daily AS
SELECT
    f.ingredient_id,
    f.period_date,
    f.avg_unit_cost
FROM mart_aggregated.fact_fnb_ingredient_price_daily f;
