with agg as (
    select
        bl.business_line_id,
        parse_date('%Y-%m', f.period) as period_date,
        sum(f.departmental_revenue) as group_revenue
    from {{ ref('mart_cleaned__financial_summary') }} as f
    left join {{ ref('dim_business_line') }} as bl
        on f.department = bl.line_name
    group by 1, 2
)

select
    business_line_id,
    period_date,
    group_revenue,
    safe_divide(group_revenue, sum(group_revenue) over (partition by period_date)) as revenue_share_pct
from agg
