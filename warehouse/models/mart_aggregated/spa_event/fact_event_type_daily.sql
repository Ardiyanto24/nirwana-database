select
    eb.property_id,
    et.event_type_id,
    eb.event_date as period_date,
    count(*) as event_count,
    sum(case when eb.status in ('completed', 'confirmed') then eb.total_revenue else 0 end) as revenue
from {{ ref('mart_cleaned__event_bookings') }} as eb
left join {{ ref('dim_event_type') }} as et
    on eb.event_type = et.event_type_name
group by 1, 2, 3
