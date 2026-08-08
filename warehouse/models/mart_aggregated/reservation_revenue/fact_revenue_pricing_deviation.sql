with agg as (
    select
        p.property_id,
        r.reason_id,
        p.date as period_date,
        avg(p.applied_rate) as avg_applied_rate,
        avg(p.base_rate) as avg_base_rate,
        safe_divide(avg(p.applied_rate - p.base_rate), nullif(avg(p.base_rate), 0)) as avg_deviation_pct,
        count(*) as reason_count
    from {{ ref('mart_cleaned__pricing_history') }} as p
    left join {{ ref('dim_pricing_reason') }} as r
        on p.reason = r.reason_name
    group by 1, 2, 3
)

select
    property_id,
    reason_id,
    period_date,
    avg_applied_rate,
    avg_base_rate,
    avg_deviation_pct,
    safe_divide(reason_count, sum(reason_count) over (partition by property_id, period_date)) as day_share_pct
from agg
