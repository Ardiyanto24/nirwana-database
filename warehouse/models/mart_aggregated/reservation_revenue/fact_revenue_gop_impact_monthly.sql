-- Grain: property_id x period_date (bulanan). Cross-domain: financial_summary.gop
-- (domain Corporate/Financial). financial_summary.period adalah STRING 'YYYY-MM'.
with monthly_pricing as (
    select
        property_id,
        date_trunc(date, month) as period_date,
        avg(applied_rate - base_rate) as avg_pricing_deviation
    from {{ ref('mart_cleaned__pricing_history') }}
    group by 1, 2
),

monthly_gop as (
    select
        property_id,
        parse_date('%Y-%m', period) as period_date,
        safe_divide(gop, nullif(departmental_revenue, 0)) as gop_margin
    from {{ ref('mart_cleaned__financial_summary') }}
    where department = 'Overall'
)

select
    g.property_id,
    g.period_date,
    p.avg_pricing_deviation,
    g.gop_margin
from monthly_gop as g
left join monthly_pricing as p
    on g.property_id = p.property_id and g.period_date = p.period_date
