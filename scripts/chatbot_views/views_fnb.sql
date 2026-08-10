-- Milestone 4.2: AI Chatbot views -- domain `fnb`.
-- Source (aggregate): mart_aggregated.fact_fnb_* (see
-- docs/09-serving-ai-chatbot/pemetaan-akses-teknis-chatbot.md §2.2).
-- property_id resolved via dim_outlet.property_id (outlet always belongs to
-- exactly 1 property). Basket analysis intentionally NOT a view -- same
-- business rule kritis as M3.1/M3.2: grain per struk only exists row-level.

CREATE OR REPLACE VIEW chatbot_views.v_fnb_outlet_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_fnb_category_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_fnb_hourly AS
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

CREATE OR REPLACE VIEW chatbot_views.v_fnb_customer_type_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_fnb_menu_item_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_fnb_waste_daily AS
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

CREATE OR REPLACE VIEW chatbot_views.v_fnb_inventory_status AS
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
CREATE OR REPLACE VIEW chatbot_views.v_fnb_ingredient_price_daily AS
SELECT
    f.ingredient_id,
    f.period_date,
    f.avg_unit_cost
FROM mart_aggregated.fact_fnb_ingredient_price_daily f;

-- Row-level lookup views (Keputusan #2). Kolom dibatasi ke tabel fnb sendiri,
-- tidak join ke guests.

-- Untuk kebutuhan F&B Staff: ketersediaan bahan baku real-time per outlet.
-- property_id di-join dari fnb_outlets (fnb_inventory sendiri tidak punya
-- kolom ini) -- wajib ada untuk filter own_property di API (M4.1 Keputusan #5).
-- Kolom ditaruh di AKHIR daftar SELECT, bukan disisipkan -- CREATE OR REPLACE
-- VIEW PostgreSQL tidak mengizinkan reorder/sisip kolom existing (pola sama M3.2).
CREATE OR REPLACE VIEW chatbot_views.v_lookup_fnb_inventory AS
SELECT
    i.outlet_id,
    i.ingredient_id,
    i.ingredient_name,
    i.unit,
    i.stock_current,
    i.stock_min_threshold,
    i.unit_cost,
    o.property_id
FROM mart_cleaned.fnb_inventory i
LEFT JOIN mart_cleaned.fnb_outlets o ON o.outlet_id = i.outlet_id;

-- Untuk kebutuhan F&B Staff: menu terlaris/total penjualan hari berjalan
-- (granularitas harian di mart_aggregated bisa telat untuk "hari ini").
-- property_id sama, di-join dari fnb_outlets, ditaruh di akhir.
CREATE OR REPLACE VIEW chatbot_views.v_lookup_fnb_transactions AS
SELECT
    t.transaction_id,
    t.outlet_id,
    t.guest_id,
    t.customer_type,
    t.transaction_datetime,
    t.item_name,
    t.category,
    t.quantity,
    t.unit_price,
    t.total_price,
    o.property_id
FROM mart_cleaned.fnb_transactions t
LEFT JOIN mart_cleaned.fnb_outlets o ON o.outlet_id = t.outlet_id;

-- Untuk kebutuhan F&B Staff: komposisi bahan per menu (info alergi ke tamu).
CREATE OR REPLACE VIEW chatbot_views.v_lookup_recipe_bom AS
SELECT
    r.item_name,
    r.ingredient_id,
    r.qty_per_portion
FROM mart_cleaned.recipe_bom r;
