with waste as (
    select
        w.outlet_id,
        r.reason_id,
        w.date as period_date,
        sum(w.quantity_wasted) as waste_quantity,
        sum(w.quantity_wasted * ip.unit_cost) as waste_value
    from {{ ref('mart_cleaned__fnb_waste_log') }} as w
    left join {{ ref('dim_waste_reason') }} as r
        on w.reason = r.reason_name
    left join {{ ref('mart_cleaned__ingredient_price_history') }} as ip
        on w.ingredient_id = ip.ingredient_id and w.date = ip.date
    group by 1, 2, 3
),

usage as (
    -- total pemakaian ingredient (dari recipe_bom x transaksi) sebagai denominator waste_ratio
    select
        o.outlet_id,
        date(f.transaction_datetime) as period_date,
        sum(r.qty_per_portion * f.quantity) as total_usage_qty
    from {{ ref('mart_cleaned__fnb_transactions') }} as f
    left join {{ ref('mart_cleaned__recipe_bom') }} as r
        on f.item_name = r.item_name
    left join {{ ref('mart_cleaned__fnb_outlets') }} as o
        on f.outlet_id = o.outlet_id
    group by 1, 2
)

select
    w.outlet_id,
    w.reason_id,
    w.period_date,
    w.waste_value,
    w.waste_quantity,
    safe_divide(w.waste_quantity, nullif(u.total_usage_qty, 0)) as waste_ratio
from waste as w
left join usage as u
    on w.outlet_id = u.outlet_id and w.period_date = u.period_date
