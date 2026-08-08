with agg as (
    select
        e.property_id,
        d.department_id,
        parse_date('%Y-%m', p.period) as period_date,
        sum(p.base_salary) as base_salary_total,
        sum(p.service_charge) as service_charge_total,
        sum(p.overtime_pay) as overtime_pay_total,
        sum(p.thr) as thr_total,
        sum(p.deduction) as deduction_total,
        sum(p.net_salary) as net_salary_total
    from {{ ref('mart_cleaned__payroll') }} as p
    left join {{ ref('mart_cleaned__employees') }} as e
        on p.employee_id = e.employee_id
    left join {{ ref('dim_department') }} as d
        on e.department = d.department_name
    group by 1, 2, 3
)

select
    cur.property_id,
    cur.department_id,
    cur.period_date,
    cur.base_salary_total,
    cur.service_charge_total,
    cur.overtime_pay_total,
    cur.thr_total,
    cur.deduction_total,
    cur.net_salary_total,
    cur.net_salary_total - mom.net_salary_total as mom_growth
from agg as cur
left join agg as mom
    on cur.property_id = mom.property_id and cur.department_id = mom.department_id
    and mom.period_date = date_sub(cur.period_date, interval 1 month)
