select
    e.property_id,
    d.department_id,
    p.review_period,
    avg(p.score) as avg_performance_score
from {{ ref('mart_cleaned__employee_performance') }} as p
left join {{ ref('mart_cleaned__employees') }} as e
    on p.employee_id = e.employee_id
left join {{ ref('dim_department') }} as d
    on e.department = d.department_name
group by 1, 2, 3
