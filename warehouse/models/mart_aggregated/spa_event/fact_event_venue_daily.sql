-- low_utilization_streak_days disederhanakan jadi rolling count 30 hari (bukan
-- consecutive streak murni -- perhitungan gaps-and-islands eksak di luar cakupan
-- waktu M5.3) -- threshold utilization_rate < 30% adalah asumsi bisnis, dicatat
-- eksplisit di sini karena tidak ada nilai baku dari dokumen manapun.
with agg as (
    select
        b.venue_id,
        b.event_date as period_date,
        count(*) as bookings_pipeline_count,
        sum(case when b.status in ('completed', 'confirmed') then b.total_revenue else 0 end) as revenue_pipeline,
        safe_divide(sum(b.capacity_booked), nullif(sum(v.max_capacity), 0)) as utilization_rate
    from {{ ref('mart_cleaned__event_bookings') }} as b
    left join {{ ref('mart_cleaned__venues') }} as v
        on b.venue_id = v.venue_id
    group by 1, 2
),

with_growth as (
    select
        cur.*,
        cur.revenue_pipeline - mom.revenue_pipeline as mom_revenue_growth,
        cur.revenue_pipeline - yoy.revenue_pipeline as yoy_revenue_growth,
        cur.utilization_rate < 0.3 as is_low_utilization
    from agg as cur
    left join agg as mom
        on cur.venue_id = mom.venue_id and mom.period_date = date_sub(cur.period_date, interval 1 month)
    left join agg as yoy
        on cur.venue_id = yoy.venue_id and yoy.period_date = date_sub(cur.period_date, interval 1 year)
)

select
    venue_id,
    period_date,
    bookings_pipeline_count,
    revenue_pipeline,
    utilization_rate,
    mom_revenue_growth,
    yoy_revenue_growth,
    sum(cast(is_low_utilization as int64)) over (
        partition by venue_id order by unix_date(period_date)
        range between 29 preceding and current row
    ) as low_utilization_days_last_30
from with_growth
