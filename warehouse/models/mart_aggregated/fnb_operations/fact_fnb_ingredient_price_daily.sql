select
    ingredient_id,
    date as period_date,
    avg(unit_cost) as avg_unit_cost
from {{ ref('mart_cleaned__ingredient_price_history') }}
group by 1, 2
