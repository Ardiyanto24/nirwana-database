with agg as (
    select
        b.property_id,
        s.service_id,
        b.service_date as period_date,
        count(*) as booking_count,
        sum(b.price) as revenue
    from {{ ref('mart_cleaned__spa_bookings') }} as b
    left join {{ ref('dim_spa_service') }} as s
        on b.service_name = s.service_name
    where b.status in ('completed', 'confirmed')
    group by 1, 2, 3
)

select
    property_id,
    service_id,
    period_date,
    booking_count,
    revenue,
    safe_divide(revenue, sum(revenue) over (partition by property_id, period_date)) as revenue_share_pct
from agg
