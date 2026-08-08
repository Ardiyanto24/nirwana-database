select
    b.property_id,
    ct.customer_type_id,
    b.service_date as period_date,
    sum(b.price) as revenue,
    count(*) as visit_count,
    safe_divide(sum(b.price), count(*)) as revenue_per_visit
from {{ ref('mart_cleaned__spa_bookings') }} as b
left join {{ ref('dim_customer_type') }} as ct
    on b.customer_type = ct.customer_type_name
where b.status in ('completed', 'confirmed')
group by 1, 2, 3
