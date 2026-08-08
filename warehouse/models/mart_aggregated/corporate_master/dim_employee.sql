-- dim_employee: employee_id natural key. full_name diteruskan apa adanya
-- (Audit PII M5.2: domain employees_directory, akses granular diatur RBAC layer M4.x,
-- bukan masking di data layer -- lihat desain-skema-mart-aggregated.md Audit PII).
select
    e.employee_id,
    trim(e.full_name) as full_name,
    d.department_id,
    a.access_level_id
from {{ ref('mart_cleaned__employees') }} as e
left join {{ ref('dim_department') }} as d
    on e.department = d.department_name
left join {{ ref('dim_access_level') }} as a
    on e.access_level = a.access_level_name
