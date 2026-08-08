select
    b.property_id,
    lt.loyalty_tier_id,
    b.check_in_date as period_date,
    count(*) as bookings_count,
    sum(b.total_amount) as revenue
from {{ ref('mart_cleaned__bookings') }} as b
left join {{ ref('mart_cleaned__guests') }} as g
    on b.guest_id = g.guest_id
left join {{ ref('dim_loyalty_tier') }} as lt
    on g.loyalty_tier = lt.loyalty_tier_name
where b.status in ('completed', 'confirmed')
group by 1, 2, 3
