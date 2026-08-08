with labor_cost as (
    select
        e.property_id,
        parse_date('%Y-%m', p.period) as period_date,
        sum(p.base_salary + p.service_charge + p.overtime_pay) as labor_cost
    from {{ ref('mart_cleaned__payroll') }} as p
    left join {{ ref('mart_cleaned__employees') }} as e
        on p.employee_id = e.employee_id
    group by 1, 2
),

revenue_monthly as (
    select
        property_id,
        date_trunc(period_date, month) as period_date,
        sum(revenue_runrate) as revenue
    from {{ ref('fact_financial_revenue_runrate_daily') }}
    group by 1, 2
)

select
    l.property_id,
    l.period_date,
    safe_divide(l.labor_cost, nullif(r.revenue, 0)) as labor_cost_pct_revenue
from labor_cost as l
left join revenue_monthly as r
    on l.property_id = r.property_id and l.period_date = r.period_date
