with daily as (
    select
        s.employee_id,
        e.department,
        date_trunc(s.date, month) as period_date,
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
),

agg as (
    select
        employee_id,
        department,
        period_date,
        sum(overtime_hours) as overtime_hours,
        safe_divide(countif(status = 'late'), count(*)) as late_rate
    from daily
    group by 1, 2, 3
),

dept_avg as (
    select
        department,
        period_date,
        avg(overtime_hours) as dept_avg_overtime,
        avg(late_rate) as dept_avg_late_rate
    from agg
    group by 1, 2
)

select
    a.employee_id,
    a.period_date,
    a.overtime_hours,
    a.overtime_hours - d.dept_avg_overtime as overtime_vs_dept_avg,
    a.late_rate,
    a.late_rate - d.dept_avg_late_rate as late_vs_dept_avg
from agg as a
left join dept_avg as d
    on a.department = d.department and a.period_date = d.period_date
