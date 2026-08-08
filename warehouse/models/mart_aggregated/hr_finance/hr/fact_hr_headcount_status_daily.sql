select
    e.property_id,
    d.department_id,
    st.status_id,
    current_date() as period_date,
    count(*) as employee_count
from {{ ref('mart_cleaned__employees') }} as e
left join {{ ref('dim_department') }} as d
    on e.department = d.department_name
left join {{ ref('dim_employee_status') }} as st
    on e.status = st.status_name
group by 1, 2, 3, 4
