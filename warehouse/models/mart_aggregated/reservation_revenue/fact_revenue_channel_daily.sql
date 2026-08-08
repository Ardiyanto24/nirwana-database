-- Grain: property_id x channel_id x period_date (tanpa room_type -- lihat catatan
-- koreksi grain di desain-skema-mart-aggregated.md).
select
    b.property_id,
    c.channel_id,
    b.check_in_date as period_date,
    sum(case when b.status in ('completed', 'confirmed') then b.total_amount else 0 end) as revenue,
    count(*) as bookings_count,
    countif(b.status = 'cancelled') as cancellations_count,
    countif(b.status = 'no-show') as no_shows_count
from {{ ref('mart_cleaned__bookings') }} as b
left join {{ ref('dim_channel') }} as c
    on b.booking_channel = c.channel_name
group by 1, 2, 3
