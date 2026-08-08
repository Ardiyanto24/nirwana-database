-- Grain: property_id x room_type_id x channel_id x period_date -- satu-satunya
-- metrik Revenue yang genuinely butuh ketiga dimensi sekaligus (M5.1 baris 7).
select
    b.property_id,
    rt.room_type_id,
    c.channel_id,
    b.check_in_date as period_date,
    avg(b.nights) as avg_los_nights,
    approx_quantiles(b.nights, 2)[offset(1)] as median_los_nights
from {{ ref('mart_cleaned__bookings') }} as b
left join {{ ref('dim_room_type') }} as rt
    on b.room_type = rt.room_type_name
left join {{ ref('dim_channel') }} as c
    on b.booking_channel = c.channel_name
where b.status in ('completed', 'confirmed')
group by 1, 2, 3, 4
