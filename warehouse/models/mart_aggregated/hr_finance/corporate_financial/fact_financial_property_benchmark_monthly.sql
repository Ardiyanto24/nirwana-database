select
    property_id,
    period_date,
    rank() over (partition by period_date order by gop_margin_pct desc) as gop_margin_rank
from {{ ref('fact_financial_overall_monthly') }}
