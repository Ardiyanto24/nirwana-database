with cleaning as (
    select
        staff_id,
        date as period_date,
        time_diff(cleaning_end_time, cleaning_start_time, minute) as duration_minutes
    from {{ ref('mart_cleaned__housekeeping_log') }}
    where status = 'completed'
),

agg as (
    select
        staff_id,
        period_date,
        avg(duration_minutes) as avg_cleaning_duration_minutes
    from cleaning
    group by 1, 2
)

select
    staff_id,
    period_date,
    avg_cleaning_duration_minutes,
    avg(avg_cleaning_duration_minutes) over (partition by period_date) as team_avg_duration_minutes
from agg
