-- overtime_hours: (jam kerja - 8) per shift, clock_out < clock_in ditangani sebagai
-- shift lintas tengah malam (+24 jam) -- M5.1 §5.3: "clock_out - clock_in - 8 jam".
with shifts as (
    select
        e.property_id,
        d.department_id,
        s.date as period_date,
        s.status,
        case
            when s.clock_in is not null and s.clock_out is not null then
                greatest(
                    (case when s.clock_out < s.clock_in
                        then time_diff(s.clock_out, s.clock_in, minute) + 24 * 60
                        else time_diff(s.clock_out, s.clock_in, minute)
                    end) / 60.0 - 8,
                    0
                )
        end as overtime_hours
    from {{ ref('mart_cleaned__staff_shifts') }} as s
    left join {{ ref('mart_cleaned__employees') }} as e
        on s.employee_id = e.employee_id
    left join {{ ref('dim_department') }} as d
        on e.department = d.department_name
)

select
    property_id,
    department_id,
    period_date,
    countif(status = 'present') as present_count,
    countif(status = 'late') as late_count,
    countif(status = 'leave') as leave_count,
    countif(status = 'absent') as absent_count,
    sum(overtime_hours) as overtime_hours_total
from shifts
group by 1, 2, 3
