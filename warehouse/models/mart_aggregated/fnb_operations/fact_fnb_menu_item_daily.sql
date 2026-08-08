-- food_cost_ratio_target: target Food 34% / Beverage 24% / Dessert 28%, dari role-play
-- Weekly Food Cost & Margin Report (pemetaan-kebutuhan-data-analyst.md §2.1) -- angka
-- bisnis tetap, bukan turunan tabel manapun.
with sales as (
    select
        outlet_id,
        item_name,
        any_value(category) as category,
        date(transaction_datetime) as period_date,
        sum(total_price) as revenue,
        sum(quantity) as quantity_sold
    from {{ ref('mart_cleaned__fnb_transactions') }}
    group by 1, 2, 4
),

recipe_cost as (
    select
        r.item_name,
        ip.date as period_date,
        sum(r.qty_per_portion * ip.unit_cost) as cost_per_portion
    from {{ ref('mart_cleaned__recipe_bom') }} as r
    left join {{ ref('mart_cleaned__ingredient_price_history') }} as ip
        on r.ingredient_id = ip.ingredient_id
    group by 1, 2
)

select
    s.outlet_id,
    s.item_name,
    s.period_date,
    s.revenue,
    s.quantity_sold,
    safe_divide(rc.cost_per_portion * s.quantity_sold, nullif(s.revenue, 0)) as food_cost_ratio_actual,
    case
        when s.category = 'Food' then 0.34
        when s.category = 'Beverage' then 0.24
        when s.category = 'Dessert' then 0.28
    end as food_cost_ratio_target,
    safe_divide(rc.cost_per_portion * s.quantity_sold, nullif(s.revenue, 0))
        - case
            when s.category = 'Food' then 0.34
            when s.category = 'Beverage' then 0.24
            when s.category = 'Dessert' then 0.28
        end as food_cost_deviation
from sales as s
left join recipe_cost as rc
    on s.item_name = rc.item_name and s.period_date = rc.period_date
