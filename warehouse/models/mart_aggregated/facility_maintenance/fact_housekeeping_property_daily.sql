-- Cross-domain: delayed_rate_vs_occupancy join ke daily_occupancy (Keputusan #6 decisions.md).
with delayed as (
    select
        r.property_id,
        h.date as period_date,
        count(*) as total_count,
        countif(h.status = 'delayed') as delayed_count
    from {{ ref('mart_cleaned__housekeeping_log') }} as h
    left join {{ ref('mart_cleaned__rooms') }} as r
        on h.room_id = r.room_id
    group by 1, 2
),

occupancy as (
    select
        property_id,
        date as period_date,
        safe_divide(sum(rooms_sold), nullif(sum(total_rooms_available), 0)) as occupancy_rate
    from {{ ref('mart_cleaned__daily_occupancy') }}
    group by 1, 2
)

select
    d.property_id,
    d.period_date,
    safe_divide(d.delayed_count, nullif(d.total_count, 0)) as delayed_rate,
    o.occupancy_rate
from delayed as d
left join occupancy as o
    on d.property_id = o.property_id and d.period_date = o.period_date
