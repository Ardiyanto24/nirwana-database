with cleaning as (
    select
        r.property_id,
        rt.room_type_id,
        h.date as period_date,
        time_diff(h.cleaning_end_time, h.cleaning_start_time, minute) as duration_minutes
    from {{ ref('mart_cleaned__housekeeping_log') }} as h
    left join {{ ref('mart_cleaned__rooms') }} as r
        on h.room_id = r.room_id
    left join {{ ref('dim_room_type') }} as rt
        on r.room_type = rt.room_type_name
    where h.status = 'completed'
),

agg as (
    select
        property_id,
        room_type_id,
        period_date,
        avg(duration_minutes) as avg_cleaning_duration_minutes
    from cleaning
    group by 1, 2, 3
)

select
    property_id,
    room_type_id,
    period_date,
    avg_cleaning_duration_minutes,
    avg(avg_cleaning_duration_minutes) over (partition by room_type_id) as baseline_duration_minutes
from agg
