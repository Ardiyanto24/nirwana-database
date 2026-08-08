select
    outlet_id,
    c.category_id,
    date(f.transaction_datetime) as period_date,
    sum(f.total_price) as revenue
from {{ ref('mart_cleaned__fnb_transactions') }} as f
left join {{ ref('dim_fnb_category') }} as c
    on f.category = c.category_name
group by 1, 2, 3
