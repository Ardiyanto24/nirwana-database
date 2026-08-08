select
    e.property_id,
    al.access_level_id,
    parse_date('%Y-%m', p.period) as period_date,
    sum(p.service_charge) as service_charge_total,
    sum(p.base_salary) as base_salary_total,
    safe_divide(sum(p.service_charge), nullif(sum(p.base_salary), 0)) as service_charge_to_base_ratio
from {{ ref('mart_cleaned__payroll') }} as p
left join {{ ref('mart_cleaned__employees') }} as e
    on p.employee_id = e.employee_id
left join {{ ref('dim_access_level') }} as al
    on e.access_level = al.access_level_name
group by 1, 2, 3
