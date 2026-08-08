with tx_level as (
    select distinct
        transaction_id,
        outlet_id,
        date(transaction_datetime) as period_date,
        customer_type
    from {{ ref('mart_cleaned__fnb_transactions') }}
),

revenue as (
    select
        outlet_id,
        date(transaction_datetime) as period_date,
        customer_type,
        sum(total_price) as revenue
    from {{ ref('mart_cleaned__fnb_transactions') }}
    group by 1, 2, 3
),

visits as (
    select
        outlet_id,
        period_date,
        customer_type,
        count(*) as visit_count
    from tx_level
    group by 1, 2, 3
)

select
    r.outlet_id,
    ct.customer_type_id,
    r.period_date,
    r.revenue,
    v.visit_count,
    safe_divide(r.revenue, nullif(v.visit_count, 0)) as revenue_per_visit
from revenue as r
left join visits as v
    on r.outlet_id = v.outlet_id and r.period_date = v.period_date and r.customer_type = v.customer_type
left join {{ ref('dim_customer_type') }} as ct
    on r.customer_type = ct.customer_type_name
